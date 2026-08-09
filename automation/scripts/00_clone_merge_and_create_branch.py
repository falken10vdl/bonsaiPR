import os
import subprocess
import requests
import re
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# pr_state lives alongside this script. main.py runs it with cwd=scripts_dir so a
# plain import works, but insert the path explicitly for direct/manual invocation.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_state
import bonsaipr_profile

# Committed per-order snapshots (state.asc/desc/upd.json). The report reads them
# to annotate each PR with how it fared under the other merge orders.
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")

# Load environment variables from .env file
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN"
)  # Set your GitHub token in environment variables
SOURCE_REPO_OWNER = os.getenv("SOURCE_REPO_OWNER", "IfcOpenShell")
SOURCE_REPO_NAME = os.getenv("SOURCE_REPO_NAME", "IfcOpenShell")
SOURCE_BASE_BRANCH = os.getenv("SOURCE_BASE_BRANCH", "v0.8.0")

upstream_repo_url = f"https://github.com/{SOURCE_REPO_OWNER}/{SOURCE_REPO_NAME}.git"
# Use token in the fork URL for authenticated operations
fork_owner = os.getenv("FORK_OWNER", os.getenv("GITHUB_OWNER", "falken10vdl"))
fork_repo = os.getenv("FORK_REPO", "IfcOpenShell")
fork_repo_url = f"https://{GITHUB_TOKEN}@github.com/{fork_owner}/{fork_repo}.git"
fork_repo_url_public = (
    f"https://github.com/{fork_owner}/{fork_repo}.git"  # For display purposes
)
work_dir = os.getenv("BASE_CLONE_DIR", "/home/falken10vdl/bonsaiPRDevel/IfcOpenShell")
upstream_repo = f"{SOURCE_REPO_OWNER}/{SOURCE_REPO_NAME}"
# Which PRs this build curates. Set BONSAIPR_PROFILE to build a named profile
# from profiles/; leave it unset and the legacy USERNAMES / EXCLUDED /
# SKIP_CPP_PRS env vars are read exactly as before, so an existing .env keeps
# working untouched. See RFC-001 s4.1 for the mapping.
#
# The three names below are the only things the ~950 lines downstream consume,
# so a profile is purely a different way of *deciding* them:
#
#   users        author allowlist ([""] means all authors)
#   excluded_prs PR numbers to skip outright
#   SKIP_CPP_PRS skip PRs that change C++ compiled into the ifcopenshell wheel
#                Bonsai loads. BonsaiPR ships the Python add-on against a pinned
#                prebuilt wheel and never recompiles C++, so a PR whose Python
#                depends on new/changed C++ either crashes at runtime or silently
#                runs the old wheel behavior. Default off so we don't drop PRs
#                whose Python is testable.
CURATION = bonsaipr_profile.load_profile()
users = CURATION.users
excluded_prs = CURATION.excluded_prs
SKIP_CPP_PRS = CURATION.skip_cpp

# File extensions that only take effect after a C++ recompile.
COMPILED_EXTS = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx", ".i", ".ipp"}

# Only C++ under these roots compiles into the wheel Bonsai imports at runtime
# (the SWIG wrapper and what it links). C++ elsewhere — ifcconvert/ (CLI),
# qtviewer/, ifcgeomserver/, ifcjni/, tests, examples — never touches the Python
# API, so it stays testable and must not trigger a skip.
WHEEL_CPP_ROOTS = (
    "src/ifcwrap/",
    "src/ifcparse/",
    "src/ifcgeom/",
    "src/serializers/",
)

# Known per-file conflict resolutions for specific PRs.
# Add an entry when a PR conflicts only because of another PR already merged,
# and the incoming PR's version of that file is the correct superset.
# Remove the entry once the upstream PR is rebased to resolve it natively.
# strategy: 'theirs' = take the incoming PR's version, 'ours' = keep current HEAD.
KNOWN_CONFLICT_RESOLUTIONS = {
    # PR #7003 (general-mirroring) conflicts with PR #7802 in tool/root.py.
    # PR #7003's version is a superset — it contains PR #7802's MappedRepresentation
    # preservation logic plus HasShapeAspects/StyledByItem handling.
    7003: [
        ("src/bonsai/bonsai/tool/root.py", "theirs"),
    ],
}


# Generate branch name and report filename with timestamp for on-demand builds
def get_branch_and_report_names():
    # Include hour-minute for multiple builds per day
    current_datetime = datetime.now().strftime("%y%m%d%H%M")

    # Fetch latest version from IfcOpenShell GitHub releases
    version = "unknown"
    try:
        api_url = f"https://api.github.com/repos/{SOURCE_REPO_OWNER}/{SOURCE_REPO_NAME}/releases"
        resp = requests.get(api_url, timeout=10)
        if resp.ok:
            releases = resp.json()
            for rel in releases:
                # Look for tag_name like bonsai-0.8.5-alpha2512300458
                m = re.match(r"bonsai-([\d.]+)-alpha", rel.get("tag_name", ""))
                if m:
                    version = m.group(1)
                    break
    except Exception as e:
        print(f"Warning: Could not fetch version from releases: {e}")
    if version == "unknown":
        version = "0.0.0"  # fallback default

    pyversion = "py311"
    branch_name = f"build-{version}-alpha{current_datetime}"
    report_name = f"README-bonsaiPR_{pyversion}-{version}-alpha{current_datetime}.txt"
    report_dir = os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")
    report_path = os.path.join(report_dir, report_name)
    return branch_name, report_path


def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"}


def get_pr_files(pr_number):
    """Return the list of file paths changed by a PR (paginated).

    Uses the GitHub files API so we can decide to skip a PR before fetching or
    merging it. On error, returns None so the caller can fail open (don't skip).
    """
    url = f"https://api.github.com/repos/{upstream_repo}/pulls/{pr_number}/files"
    files = []
    page = 1
    while True:
        try:
            response = requests.get(
                url,
                headers=github_headers(),
                params={"per_page": 100, "page": page},
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"⚠️  Could not fetch files for PR #{pr_number}: {e}")
            return None
        if response.status_code != 200:
            print(
                f"⚠️  Could not fetch files for PR #{pr_number}: "
                f"HTTP {response.status_code}"
            )
            return None
        batch = response.json()
        if not batch:
            break
        files.extend(f["filename"] for f in batch)
        if len(batch) < 100:  # Last page
            break
        page += 1
    return files


def pr_needs_cpp_recompile(pr_number):
    """True if the PR changes C++ compiled into the wheel Bonsai loads.

    Fails open (returns False) when the file list can't be fetched, so an API
    hiccup never silently drops a PR from the build.
    """
    files = get_pr_files(pr_number)
    if files is None:
        return False
    for path in files:
        if path.startswith(WHEEL_CPP_ROOTS) and (
            os.path.splitext(path)[1].lower() in COMPILED_EXTS
        ):
            return True
    return False


def try_resolve_known_conflict(pr_number):
    """Attempt to resolve a known per-file conflict for a specific PR.
    Must be called while a conflicted merge is in progress (before --abort).
    Returns True if all conflicts were resolved and the merge committed."""
    if pr_number not in KNOWN_CONFLICT_RESOLUTIONS:
        return False

    print(f"  🔧 Attempting known conflict resolution for PR #{pr_number}...")
    try:
        for file_path, strategy in KNOWN_CONFLICT_RESOLUTIONS[pr_number]:
            result = subprocess.run(
                ["git", "checkout", f"--{strategy}", file_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  ⚠️  Could not resolve {file_path}: {result.stderr.strip()}")
                subprocess.run(["git", "merge", "--abort"], capture_output=True)
                return False
            subprocess.run(["git", "add", file_path], check=True)
            print(f"  ✅ Resolved {file_path} using '{strategy}' strategy")

        env = os.environ.copy()
        env["GIT_EDITOR"] = "true"
        continue_result = subprocess.run(
            ["git", "merge", "--continue"], capture_output=True, text=True, env=env
        )
        if continue_result.returncode == 0:
            print(f"  ✅ Merge committed for PR #{pr_number} via known resolution")
            return True
        else:
            print(f"  ⚠️  merge --continue failed: {continue_result.stderr.strip()}")
            subprocess.run(["git", "merge", "--abort"], capture_output=True)
            return False

    except Exception as e:
        print(f"  ⚠️  Exception during conflict resolution for PR #{pr_number}: {e}")
        subprocess.run(["git", "merge", "--abort"], capture_output=True)
        return False


def _base_ref():
    """What to build on: the curation's pinned commit, or the branch tip.

    RFC-001. Upstream drift, not PR quality, is what breaks most merges: a PR
    that applied cleanly when written conflicts months later because the base
    moved. Pinning lets a curation keep building without every contributor
    rebasing; the cost is that upstream fixes stop arriving until the pin moves.
    """
    if CURATION.base_commit:
        print(
            f"📌 Base pinned by profile '{CURATION.name}' to "
            f"{CURATION.base_commit[:10]} (not {SOURCE_BASE_BRANCH} tip)"
        )
        return CURATION.base_commit
    return f"upstream/{SOURCE_BASE_BRANCH}"


def setup_repository():
    """Clone or update the fork repository with upstream remote"""
    def _run_git(cmd):
        """Run git command with bounded retries and lock cleanup."""
        max_attempts = 3
        retry_delay_seconds = 20
        state_file = os.path.join(
            os.path.dirname(__file__), "..", "logs", "pr_state.json"
        )

        for attempt in range(1, max_attempts + 1):
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                return
            except subprocess.CalledProcessError as e:
                combined = f"{e.stdout or ''}\n{e.stderr or ''}"
                lock_match = re.search(
                    r"Unable to create '([^']+\\.lock)': File exists", combined
                )

                is_last_attempt = attempt >= max_attempts
                if lock_match:
                    lock_path = lock_match.group(1)
                    if os.path.exists(lock_path):
                        # Stale git lock files can survive a crashed/aborted git
                        # process. Remove the lock before retrying.
                        print(f"⚠️  Detected stale git lock file: {lock_path}")
                        os.remove(lock_path)
                    else:
                        print(
                            f"⚠️  Lock error reported but lock file not present: {lock_path}"
                        )
                else:
                    err = (e.stderr or e.stdout or str(e)).strip()
                    print(f"⚠️  Git command failed: {' '.join(cmd)}")
                    if err:
                        print(f"    Reason: {err}")

                if is_last_attempt:
                    print(
                        f"❌ Git command failed after {max_attempts} attempts: {' '.join(cmd)}"
                    )
                    if os.path.exists(state_file):
                        try:
                            os.remove(state_file)
                            print(
                                f"🧹 Removed change-detection state file: {state_file}"
                            )
                        except Exception as cleanup_error:
                            print(
                                f"⚠️  Could not remove state file {state_file}: {cleanup_error}"
                            )
                    raise

                print(
                    f"🔁 Retrying git command ({attempt}/{max_attempts - 1}) "
                    f"in {retry_delay_seconds}s..."
                )
                time.sleep(retry_delay_seconds)

    # Test for a real repository, not merely a directory: an empty or
    # pre-created BASE_CLONE_DIR would otherwise take the "update" path and fail
    # on `git checkout <base>` with nothing to check out. `git clone` into an
    # existing empty directory is fine, so cloning is the safe default.
    if os.path.exists(os.path.join(work_dir, ".git")):
        print(f"Updating existing repository in {work_dir}")
        original_dir = os.getcwd()
        try:
            os.chdir(work_dir)
            # Reset to clean state
            _run_git(["git", "reset", "--hard", "HEAD"])
            _run_git(["git", "clean", "-fd"])

            # Update from upstream, then land on the base branch as upstream
            # defines it. `checkout -B` creates the local branch if the fork
            # never had one, so this does not depend on the fork's branch layout.
            _run_git(["git", "fetch", "upstream"])
            _run_git(
                [
                    "git",
                    "checkout",
                    "-B",
                    SOURCE_BASE_BRANCH,
                    _base_ref(),
                ]
            )

            # Update the origin remote URL to use token for authentication
            _run_git(["git", "remote", "set-url", "origin", fork_repo_url])

            # Push updated base branch to fork
            _run_git(["git", "push", "origin", SOURCE_BASE_BRANCH, "--force"])

            print(f"Repository updated successfully")
        finally:
            os.chdir(original_dir)
    else:
        print(f"Cloning fork repository into {work_dir}")
        subprocess.run(["git", "clone", fork_repo_url, work_dir], check=True)

        # Add upstream remote
        original_dir = os.getcwd()
        try:
            os.chdir(work_dir)
            subprocess.run(
                ["git", "remote", "add", "upstream", upstream_repo_url], check=True
            )
            subprocess.run(["git", "fetch", "upstream"], check=True)
            # A fresh clone lands on the FORK's default branch, which has nothing
            # to do with the branch being curated — for a fork whose default is
            # still v0.7.0 that means merging v0.8.0 PRs onto a v0.7.0 tree, and
            # every single one conflicts. Land on upstream's base branch
            # explicitly, exactly as the update path above does.
            subprocess.run(
                [
                    "git",
                    "checkout",
                    "-B",
                    SOURCE_BASE_BRANCH,
                    _base_ref(),
                ],
                check=True,
            )
            print(
                f"Added upstream remote, fetched, and checked out "
                f"{SOURCE_BASE_BRANCH} from upstream"
            )
        finally:
            os.chdir(original_dir)


def get_open_prs():
    """Get open pull requests from IfcOpenShell repository"""
    print("Fetching open pull requests...")
    url = f"https://api.github.com/repos/{upstream_repo}/pulls"
    params = {"state": "open", "per_page": 100, "sort": "created", "direction": "desc"}

    all_prs = []
    page = 1

    while True:
        params["page"] = page
        response = requests.get(url, headers=github_headers(), params=params)
        if response.status_code != 200:
            print(f"Error fetching PRs: {response.status_code}")
            break

        page_items = response.json()
        if not page_items:
            break

        # Pagination is decided by how many items the API returned, NOT by how
        # many survive curation. Testing the filtered count ends the walk on the
        # first page for any selective profile — a page of 100 open PRs rarely
        # contains 100 that a curator selected — and silently yields a fraction
        # of the curation, or nothing at all.
        is_last_page = len(page_items) < params["per_page"]

        # Apply the active curation. For the legacy/`everything` case this is
        # exactly the old author filter; for an `allowlist` profile it is also
        # what narrows 847 open PRs down to the ones the curator chose.
        all_prs.extend(
            pr
            for pr in page_items
            if CURATION.selects(pr["number"], (pr.get("user") or {}).get("login"))
        )
        page += 1

        if is_last_page:
            break

    if CURATION.mode == bonsaipr_profile.MODE_ALLOWLIST:
        missing = sorted(CURATION.select_prs - {pr["number"] for pr in all_prs})
        print(
            f"Found {len(all_prs)} open pull requests "
            f"(curation selects {len(CURATION.select_prs)})"
        )
        if missing:
            # Selected PRs that are no longer open: merged upstream, closed, or
            # made private. Naming them is how a curator learns their profile has
            # drifted; silently building 12 fewer PRs than asked for would not be.
            print(
                f"⚠️  {len(missing)} selected PR(s) are no longer open and will be "
                f"skipped: {', '.join('#' + str(n) for n in missing[:20])}"
                + (" …" if len(missing) > 20 else "")
            )
    else:
        print(f"Found {len(all_prs)} open pull requests")
    return all_prs


# RFC-001 phase 1.1: which already-merged PR did each blocked PR lose to?
#
# The reports have always recorded *that* a PR was conflict-skipped and which
# orders it merges under, but never *which PR beat it* - and that pairing cannot
# be reconstructed afterwards, because the losing merge is aborted and leaves no
# trace. It is the difference between "this conflicts with something" and "this
# conflicts with #7098, go talk to each other", so it is worth the one extra
# `git diff --name-only` per successful merge that capturing it costs.
#
# Module-level rather than threaded through the return signature: this script
# runs once per process and `apply_prs_to_branch` already has three return
# values consumed positionally at its only call site.
PR_RIVALS = {}

# PR number -> the curator-validated sha built instead of the PR's current tip,
# when the tip would not merge. Surfaced in the report and the manifest: a build
# that quietly ships an older commit than the PR points at is the kind of thing
# nobody can detect from the outside.
PR_PINNED = {}
# PR number -> its head sha at build time, so the report can show what was built
# alongside what the PR now points at.
_pr_tip_shas = {}


def _files_changed_by_last_merge():
    """Paths the merge just committed brought in, relative to the branch tip."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD^1", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def _conflicting_paths():
    """Unmerged paths in the working tree, read before `git merge --abort`."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def _commits_behind(pinned_sha, tip_sha):
    """How many commits the built commit is behind the PR's current head.

    "Pinned" alone does not say whether to care. One commit behind is usually a
    typo fix; forty is a PR that has moved on without you. Both objects are in
    the clone already — the pinned one was fetched to merge it, the tip when the
    PR branch was fetched — so this costs one rev-list and no network.

    Returns None when either commit is unavailable (a force-push can orphan the
    pinned one), so the caller can leave the cell blank rather than print a
    number it cannot stand behind.
    """
    if not pinned_sha or not tip_sha:
        return None
    # Exclude anything already reachable from the base. A PR branch that merges
    # upstream into itself drags in every upstream commit since its last merge,
    # and a plain `pin..tip` counts all of them — measuring other people's churn
    # rather than this PR's progress. On one real branch that was the difference
    # between 517 and 47, and 517 is the answer to a question nobody asked.
    for base_ref in (f"upstream/{SOURCE_BASE_BRANCH}", SOURCE_BASE_BRANCH):
        result = subprocess.run(
            ["git", "-C", work_dir, "rev-list", "--count",
             f"{pinned_sha}..{tip_sha}", "--not", base_ref],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            try:
                return int(result.stdout.strip())
            except ValueError:
                return None
    # No usable base ref means no honest answer; a blank cell beats the
    # unfiltered count, which would silently overstate by an order of magnitude.
    return None


def _publisher_owner():
    return os.getenv("GITHUB_OWNER", "falken10vdl")


def _publisher_repo():
    return os.getenv("GITHUB_REPO", "bonsaiPR")


def _publisher_block():
    """Who produced this manifest (RFC-001 s6).

    Identity is the whole basis of the anti-gaming rule in s9: the aggregate
    counts distinct *publishers*, so a manifest that cannot say who made it
    either cannot be counted or has to be trusted on the strength of the URL it
    was fetched from. Defaults to the release target, which is the repository a
    peer would already be pointing at.
    """
    owner, repo = _publisher_owner(), _publisher_repo()
    return {
        "id": os.getenv("BONSAIPR_PUBLISHER_ID", "").strip() or owner,
        "instance": f"https://github.com/{owner}/{repo}",
        "contact": (
            os.getenv("BONSAIPR_PUBLISHER_CONTACT", "").strip()
            or (CURATION.maintainer and f"https://github.com/{CURATION.maintainer}")
            or None
        ),
    }


def write_pinned(reports_dir, order_suffix, pinned):
    """Persist which PRs were built at a curator-validated commit.

    A sidecar for the same reason `rivals` is one: stage 2 owns the manifest for
    a full run and reconstructs its records by parsing the rendered report, so
    anything stage 0 knows and the report does not carry is lost. Without this
    the manifest records each PR's current tip as what was built - asserting that
    a commit merges when the build proved it does not.
    """
    if not pinned:
        return None
    path = os.path.join(reports_dir, f"pinned.{order_suffix}.json")
    payload = {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order": order_suffix,
        "pinned": {str(k): v for k, v in sorted(pinned.items())},
    }
    try:
        os.makedirs(os.path.abspath(reports_dir), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        print(f"📌 Recorded {len(pinned)} pinned build commit(s) -> {path}")
        return path
    except OSError as e:
        print(f"⚠️  Could not write pinned file: {e}")
        return None


def write_rivals(reports_dir, order_suffix, rivals):
    """Persist the loser -> [winners] map for one merge order.

    A sidecar rather than a new field in state.<order>.json: the state snapshot
    is parsed out of the rendered report by 02_upload, so extending it means
    touching the report format too. This keeps a production pipeline change
    small, and RFC-001 phase 2's manifest can absorb it later.
    """
    if not rivals:
        return None
    path = os.path.join(reports_dir, f"rivals.{order_suffix}.json")
    payload = {
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order": order_suffix,
        "rivals": {str(k): sorted(v) for k, v in sorted(rivals.items())},
    }
    try:
        os.makedirs(os.path.abspath(reports_dir), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        print(f"🥊 Recorded {len(rivals)} conflict pairing(s) -> {path}")
        return path
    except OSError as e:
        # Never fail a build over telemetry about the build.
        print(f"⚠️  Could not write rivals file: {e}")
        return None


def _state_pr(pr, merged_sha=None):
    """Shape a live GitHub PR dict the way pr_state.build_state expects.

    build_state was written for `02_upload`, which reconstructs these fields by
    parsing its own rendered report. Stage 0 has them natively, so this is just
    a translation - no parsing round-trip.

    `head` records THE COMMIT THIS BUILD MERGED, which is not always the PR's
    current tip: a pinned fallback builds an earlier, validated commit. Recording
    the tip regardless would assert that the tip merges when it demonstrably does
    not - the reverse of the truth, and unfalsifiable from the outside. When the
    two differ the record says so explicitly and carries both.
    """
    head = pr.get("head") or {}
    tip = (head.get("sha") or "").strip()
    built = (merged_sha or tip or "").strip()
    rec = {
        "line": f"- **PR #{pr['number']}**: {pr.get('title') or ''}",
        # 7-char to match the shas the report-parsing path produces; _sha_eq is
        # tolerant of either, but keeping one convention avoids phantom deltas.
        "last_commit": {"sha": built[:7]} if built else None,
        "author": (pr.get("user") or {}).get("login"),
        "branch": head.get("ref"),
        "url": pr.get("html_url"),
    }
    if merged_sha and tip and not merged_sha.startswith(tip[:7]):
        rec["pinned"] = True
        rec["tip"] = tip[:7]
    return rec


def write_state_snapshot(
    applied, failed, skipped, test_results, merge_order, total_prs, base_commit=None
):
    """Write state.<order>.json, events.<order>.jsonl and delta.<order>.md.

    Stage 0 is the sole owner of the manifest. It was not always: stage 2 wrote
    it for a full run by reconstructing the four PR buckets from its own rendered
    report, while stage 0 wrote it for a manifest-only run from the data it
    already had. One artefact, two producers, differing fidelity - which
    published three untruths before this was consolidated:

      * base_commit missing entirely (branch name only)
      * pinned builds recorded at the PR's tip, asserting that a commit merges
        when the build had just proved it does not
      * both fixed in stage 0 first, where they did not run for a full build

    Stage 2 still needs the run-to-run delta for the release body, so that is
    rendered here and handed over as `delta.<order>.md` rather than recomputed
    from a second snapshot.
    """
    test_results = test_results or {}
    suffix = pr_state.ORDER_SUFFIX_BY_NAME.get(merge_order, merge_order)
    state_path = os.path.join(REPORTS_DIR, f"state.{suffix}.json")
    events_path = os.path.join(REPORTS_DIR, f"events.{suffix}.jsonl")

    # Same split the report uses: merging alone against base means the conflict
    # was with another PR, not with the base.
    conflict_with_others, failed_against_base = [], []
    for pr in failed or []:
        target = (
            conflict_with_others
            if test_results.get(pr["number"]) is True
            else failed_against_base
        )
        target.append(_state_pr(pr, PR_PINNED.get(pr["number"])))

    new_state = pr_state.build_state(
        applied_prs=[_state_pr(p, PR_PINNED.get(p["number"])) for p in applied or []],
        failed_prs=failed_against_base,
        skipped_conflict_prs=conflict_with_others,
        skipped_draft_prs=[_state_pr(p, PR_PINNED.get(p["number"])) for p in skipped or []],
        merge_order=merge_order,
        base=SOURCE_BASE_BRANCH,
        base_commit=base_commit,
        total_prs=total_prs,
        publisher=_publisher_block(),
        profile=CURATION.manifest_block(
            f"https://github.com/{_publisher_owner()}/{_publisher_repo()}"
        ),
    )

    prev_state = pr_state.load_state(state_path)
    delta_md = ""
    if prev_state:
        delta = pr_state.compute_delta(prev_state, new_state, strict_order=True)
        pr_state.append_events(events_path, pr_state.delta_to_events(delta))
        delta_md = pr_state.render_delta_md(delta)
    pr_state.write_state(new_state, state_path)

    # Handed to stage 2 for the release body. Written even when empty, so its
    # absence means "stage 0 did not run / is older" rather than "no changes" -
    # stage 2 falls back to its own computation only in the former case.
    try:
        with open(
            os.path.join(REPORTS_DIR, f"delta.{suffix}.md"), "w", encoding="utf-8"
        ) as f:
            f.write(delta_md)
    except OSError as e:
        print(f"⚠️  Could not write delta summary: {e}")
    print(
        f"🧾 Wrote manifest {os.path.basename(state_path)} "
        f"({new_state['counts']['merged']} merged of {new_state['counts']['total']})"
    )


def apply_prs_to_branch(branch_name, prs):
    """Apply PRs to the new branch"""
    original_dir = os.getcwd()
    applied = []
    failed = []
    skipped = []
    # path -> PR number that last touched it on this branch. Built as we go,
    # which makes attributing a conflict exact rather than a `git log` guess.
    file_owner = {}
    # PR number -> validated sha used because the current head would not merge.
    # Reported at the end: a PR whose head has broken is a nudge worth sending.
    pinned_fallbacks = {}
    PR_RIVALS.clear()
    PR_PINNED.clear()
    _pr_tip_shas.clear()

    try:
        os.chdir(work_dir)

        # Check if branch already exists, if so delete it and recreate
        result = subprocess.run(
            ["git", "branch", "--list", branch_name], capture_output=True, text=True
        )
        if result.stdout.strip():
            print(f"Branch {branch_name} already exists, deleting and recreating...")
            subprocess.run(["git", "branch", "-D", branch_name], check=True)

        # Create and checkout new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print(f"Created new branch: {branch_name}")

        for pr in prs:
            pr_number = pr["number"]
            pr_title = pr["title"]

            # Skip PRs the active curation excludes. Quote the curator's reason
            # when they gave one - "excluded because it bypasses the tool/ layer"
            # is worth infinitely more to the PR author than "excluded".
            if pr_number in excluded_prs:
                detail = CURATION.exclusions.get(pr_number, {})
                why = f"[{detail['why']}] " if detail.get("why") else ""
                reason = detail.get("reason") or f"listed in {CURATION.source}"
                skip_reason = f"Excluded by curation: {why}{reason}"
                print(f"⚠️  Skipping PR #{pr_number}: {skip_reason}")
                pr_with_reason = pr.copy()
                pr_with_reason["skip_reason"] = skip_reason
                pr_with_reason["individual_test_merge"] = None
                skipped.append(pr_with_reason)
                continue

            # Check if PR is in draft status
            if pr.get("draft", False):
                print(f"⚠️  Skipping PR #{pr_number}: PR is in DRAFT status")
                pr_with_reason = pr.copy()
                pr_with_reason["skip_reason"] = "DRAFT status"
                pr_with_reason["individual_test_merge"] = None
                skipped.append(pr_with_reason)
                continue

            # Skip PRs that change C++ compiled into the wheel Bonsai loads.
            # Their Python may depend on C++ that BonsaiPR never recompiles, so
            # the feature won't work in the build even if the merge succeeds.
            if SKIP_CPP_PRS and pr_needs_cpp_recompile(pr_number):
                print(
                    f"⚠️  Skipping PR #{pr_number}: "
                    f"changes C++ not recompiled by BonsaiPR"
                )
                pr_with_reason = pr.copy()
                pr_with_reason["skip_reason"] = (
                    "Requires C++ recompile — not built by BonsaiPR (pinned wheel)"
                )
                pr_with_reason["individual_test_merge"] = None
                skipped.append(pr_with_reason)
                continue

            # Check if PR head repo is accessible
            if not pr.get("head") or not pr["head"].get("repo"):
                print(
                    f"⚠️  Skipping PR #{pr_number}: Repository no longer accessible (deleted fork)"
                )
                pr_with_reason = pr.copy()
                pr_with_reason["skip_reason"] = (
                    "Repository no longer accessible (deleted fork)"
                )
                pr_with_reason["individual_test_merge"] = None
                skipped.append(pr_with_reason)
                continue

            pr_head_ref = pr["head"]["ref"]
            pr_head_repo = pr["head"]["repo"]["clone_url"]
            pr_head_sha = pr["head"].get("sha")
            if pr_head_sha:
                _pr_tip_shas[pr_number] = pr_head_sha

            # Additional safety check for required fields
            if not pr_head_ref or not pr_head_repo:
                print(f"⚠️  Skipping PR #{pr_number}: Missing required PR information")
                pr_with_reason = pr.copy()
                pr_with_reason["skip_reason"] = "Missing required PR information"
                pr_with_reason["individual_test_merge"] = None
                skipped.append(pr_with_reason)
                continue

            print(f"Applying PR #{pr_number}: {pr_title}")

            try:
                # Add remote for PR if it's from a fork
                remote_name = f"pr-{pr_number}"
                subprocess.run(
                    ["git", "remote", "remove", remote_name], capture_output=True
                )  # Remove if exists
                subprocess.run(
                    ["git", "remote", "add", remote_name, pr_head_repo], check=True
                )

                # Fetch the PR branch
                fetch_result = subprocess.run(
                    ["git", "fetch", remote_name, pr_head_ref],
                    capture_output=True,
                    text=True,
                )

                if fetch_result.returncode != 0:
                    print(f"❌ Failed to fetch PR #{pr_number}: {fetch_result.stderr}")
                    failed.append(pr)
                    subprocess.run(
                        ["git", "remote", "remove", remote_name], capture_output=True
                    )
                    continue

                # Try to merge the PR
                merge_result = subprocess.run(
                    [
                        "git",
                        "merge",
                        "--no-ff",
                        "--no-edit",
                        f"{remote_name}/{pr_head_ref}",
                    ],
                    capture_output=True,
                    text=True,
                )

                if merge_result.returncode != 0 and CURATION.pins.get(pr_number):
                    # The current head does not merge, but the curator recorded a
                    # commit of this PR that did. Fall back to it rather than
                    # dropping the PR: `pin` is a fallback, not a freeze (RFC-001
                    # §4), so authors' newer work is always tried first and only
                    # a genuinely broken head costs the PR its place.
                    pinned = CURATION.pins[pr_number]
                    subprocess.run(["git", "merge", "--abort"], capture_output=True)
                    fetch_pin = subprocess.run(
                        ["git", "fetch", remote_name, pinned],
                        capture_output=True, text=True,
                    )
                    if fetch_pin.returncode == 0:
                        retry = subprocess.run(
                            ["git", "merge", "--no-ff", "--no-edit", "FETCH_HEAD"],
                            capture_output=True, text=True,
                        )
                        if retry.returncode == 0:
                            print(
                                f"📌 PR #{pr_number}: head {pr_head_sha[:7] if pr_head_sha else '?'} "
                                f"does not merge; used curator-validated {pinned[:7]}"
                            )
                            pinned_fallbacks[pr_number] = pinned
                            PR_PINNED[pr_number] = pinned
                            merge_result = retry
                        else:
                            subprocess.run(
                                ["git", "merge", "--abort"], capture_output=True
                            )
                    else:
                        print(
                            f"   ⚠️  PR #{pr_number}: pinned commit {pinned[:7]} "
                            f"could not be fetched (force-pushed away?)"
                        )

                if merge_result.returncode == 0:
                    print(f"✅ Successfully applied PR #{pr_number}")
                    applied.append(pr)
                    for path in _files_changed_by_last_merge():
                        file_owner[path] = pr_number
                elif try_resolve_known_conflict(pr_number):
                    print(
                        f"✅ Successfully applied PR #{pr_number} (resolved known conflict)"
                    )
                    applied.append(pr)
                    for path in _files_changed_by_last_merge():
                        file_owner[path] = pr_number
                else:
                    print(f"❌ Failed to apply PR #{pr_number}: {merge_result.stderr}")
                    # Read the unmerged paths BEFORE aborting - the abort is what
                    # destroys the only record of who this PR lost to.
                    rivals = []
                    for path in _conflicting_paths():
                        owner = file_owner.get(path)
                        if owner and owner not in rivals:
                            rivals.append(owner)
                    if rivals:
                        PR_RIVALS[pr_number] = rivals
                        print(
                            f"   ↳ lost to "
                            + ", ".join(f"#{r}" for r in rivals)
                        )
                    subprocess.run(["git", "merge", "--abort"], capture_output=True)
                    failed.append(pr)

                # Clean up remote
                subprocess.run(
                    ["git", "remote", "remove", remote_name], capture_output=True
                )

            except subprocess.CalledProcessError as e:
                print(f"❌ Error applying PR #{pr_number}: {e}")
                failed.append(pr)
                subprocess.run(["git", "merge", "--abort"], capture_output=True)
                subprocess.run(
                    ["git", "remote", "remove", remote_name], capture_output=True
                )

        print(f"\nPR Application Summary:")
        if pinned_fallbacks:
            print(
                f"📌 Used curator-validated commits for {len(pinned_fallbacks)} PR(s) "
                f"whose current head no longer merges:"
            )
            for n, sha in sorted(pinned_fallbacks.items()):
                print(f"     #{n} -> {sha[:7]}")
        print(f"✅ Successfully applied: {len(applied)} PRs")
        print(f"❌ Failed to apply: {len(failed)} PRs")
        print(f"⚠️  Skipped (draft/repo issues): {len(skipped)} PRs")

        return applied, failed, skipped

    finally:
        os.chdir(original_dir)


def test_failed_prs_individually(failed_prs, failure_tracking=None):
    """Test each failed PR by merging it alone against base.
    Returns:
        pr_test_results  : dict pr_number -> True/False/None
        pr_conflict_data : dict pr_number -> {"files": [...], "breaking_commits": [...]}
    """
    print("\nTesting failed PRs individually against base branch...")
    original_dir = os.getcwd()
    pr_test_results = {}
    pr_conflict_data = {}
    try:
        os.chdir(work_dir)
        for pr in failed_prs:
            pr_number = pr["number"]
            pr_title = pr["title"]
            pr_head_ref = pr.get("head", {}).get("ref")
            pr_head_repo = pr.get("head", {}).get("repo", {}).get("clone_url")
            if not pr_head_ref or not pr_head_repo:
                pr_test_results[pr_number] = None
                print(f"[SKIP] PR #{pr_number}: Missing head ref/repo for test merge.")
                continue

            test_branch = f"test-merge-pr-{pr_number}"
            print(
                f"[TEST] PR #{pr_number}: Creating branch '{test_branch}' from {SOURCE_BASE_BRANCH} and testing merge..."
            )
            try:
                # Clean up any existing test branch
                subprocess.run(
                    ["git", "branch", "-D", test_branch], capture_output=True
                )
                subprocess.run(["git", "checkout", SOURCE_BASE_BRANCH], check=True)
                subprocess.run(["git", "checkout", "-b", test_branch], check=True)

                # Add remote for PR
                remote_name = f"prtest-{pr_number}"
                subprocess.run(
                    ["git", "remote", "remove", remote_name], capture_output=True
                )
                subprocess.run(
                    ["git", "remote", "add", remote_name, pr_head_repo], check=True
                )
                fetch_result = subprocess.run(
                    ["git", "fetch", remote_name, pr_head_ref],
                    capture_output=True,
                    text=True,
                )
                if fetch_result.returncode != 0:
                    print(
                        f"[FAIL] PR #{pr_number}: Could not fetch PR branch: {fetch_result.stderr}"
                    )
                    pr_test_results[pr_number] = False
                    subprocess.run(
                        ["git", "remote", "remove", remote_name], capture_output=True
                    )
                    subprocess.run(["git", "checkout", SOURCE_BASE_BRANCH], check=True)
                    continue

                # Try to merge PR alone
                merge_result = subprocess.run(
                    [
                        "git",
                        "merge",
                        "--no-ff",
                        "--no-edit",
                        f"{remote_name}/{pr_head_ref}",
                    ],
                    capture_output=True,
                    text=True,
                )
                if merge_result.returncode == 0:
                    print(f"[PASS] PR #{pr_number}: Merges cleanly against base.")
                    pr_test_results[pr_number] = True
                else:
                    print(
                        f"[FAIL] PR #{pr_number}: Merge conflict or error: {merge_result.stderr}"
                    )
                    # Capture conflicting files before aborting
                    conflict_result = subprocess.run(
                        ["git", "diff", "--name-only", "--diff-filter=U"],
                        capture_output=True,
                        text=True,
                    )
                    conflicting_files = [
                        f.strip()
                        for f in conflict_result.stdout.strip().split("\n")
                        if f.strip()
                    ]
                    since_commit = None
                    if failure_tracking:
                        entry = failure_tracking.get(str(pr_number), {})
                        since_commit = entry.get("base_commit") or None
                    breaking_hints = find_breaking_commit_hints(
                        conflicting_files, since_commit=since_commit
                    )
                    pr_conflict_data[pr_number] = {
                        "files": conflicting_files,
                        "breaking_commits": breaking_hints,
                    }
                    subprocess.run(["git", "merge", "--abort"], capture_output=True)
                    pr_test_results[pr_number] = False

                # Clean up remote and branch
                subprocess.run(
                    ["git", "remote", "remove", remote_name], capture_output=True
                )
                subprocess.run(["git", "checkout", SOURCE_BASE_BRANCH], check=True)
                subprocess.run(
                    ["git", "branch", "-D", test_branch], capture_output=True
                )
            except Exception as e:
                print(f"[ERROR] PR #{pr_number}: Exception during test merge: {e}")
                pr_test_results[pr_number] = False
                try:
                    subprocess.run(["git", "merge", "--abort"], capture_output=True)
                    subprocess.run(
                        ["git", "remote", "remove", remote_name], capture_output=True
                    )
                    subprocess.run(["git", "checkout", SOURCE_BASE_BRANCH], check=True)
                    subprocess.run(
                        ["git", "branch", "-D", test_branch], capture_output=True
                    )
                except Exception:
                    pass
    finally:
        os.chdir(original_dir)
    return pr_test_results, pr_conflict_data


def apply_bonsai_replacements():
    """Apply bonsai → bonsaiPR text replacements and directory renames"""
    print("Applying bonsai → bonsaiPR text replacements...")

    original_dir = os.getcwd()
    try:
        os.chdir(work_dir)

        # First, rename the bonsai directory to bonsaiPR
        bonsai_src_dir = "src/bonsai"
        bonsaiPR_src_dir = "src/bonsaiPR"

        if os.path.exists(bonsai_src_dir) and not os.path.exists(bonsaiPR_src_dir):
            print(f"Renaming directory: {bonsai_src_dir} → {bonsaiPR_src_dir}")
            subprocess.run(["git", "mv", bonsai_src_dir, bonsaiPR_src_dir], check=True)

        # Find all text files (excluding binary files and .git)
        find_result = subprocess.run(
            [
                "find",
                ".",
                "-type",
                "f",
                "!",
                "-path",
                "./.git/*",
                "!",
                "-path",
                "./.*",
                "!",
                "-name",
                "*.png",
                "!",
                "-name",
                "*.jpg",
                "!",
                "-name",
                "*.jpeg",
                "!",
                "-name",
                "*.gif",
                "!",
                "-name",
                "*.ico",
                "!",
                "-name",
                "*.blend",
                "!",
                "-name",
                "*.whl",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        files = find_result.stdout.strip().split("\n")

        replacement_count = 0
        files_modified = 0

        for file_path in files:
            if not file_path.strip():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Apply replacements
                new_content = content

                # Replace "bonsai" with "bonsaiPR" (case-sensitive)
                # But preserve "BonsaiPR" if it already exists
                if "bonsaiPR" not in content.lower():
                    new_content = re.sub(r"\bbonsai\b", "bonsaiPR", new_content)

                if new_content != content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    replacement_count += content.count("bonsai") - new_content.count(
                        "bonsai"
                    )
                    files_modified += 1
                    print(f"[DEBUG] Modified: {file_path}")

            except (UnicodeDecodeError, PermissionError) as e:
                print(
                    f"[DEBUG] Skipping file (decode/permission error): {file_path} ({e})"
                )
                continue

        print(
            f"Text replacement complete: {replacement_count} replacements in {files_modified} files"
        )

        # Commit the replacements
        subprocess.run(["git", "add", "."], check=True)
        commit_result = subprocess.run(
            ["git", "commit", "-m", "Apply bonsai → bonsaiPR replacements"],
            capture_output=True,
        )
        if commit_result.returncode == 0:
            print("Committed bonsai → bonsaiPR replacements")
        else:
            print("No changes to commit for text replacements")

    finally:
        os.chdir(original_dir)


def cleanup_old_branches():
    """Delete old build branches from GitHub, keeping only the last 30"""
    print("\n🧹 Checking for old branches to clean up...")

    try:
        # Get all branches from the fork (handle pagination)
        url = f"https://api.github.com/repos/{fork_owner}/{fork_repo}/branches"
        all_branches = []
        page = 1

        while True:
            params = {"per_page": 100, "page": page}
            response = requests.get(url, headers=github_headers(), params=params)

            if response.status_code != 200:
                print(f"⚠️ Could not fetch branches: {response.status_code}")
                return

            page_branches = response.json()
            if not page_branches:
                break

            all_branches.extend(page_branches)
            page += 1

            # Safety limit: don't fetch more than 500 branches
            if len(all_branches) >= 500:
                break

        print(f"📊 Fetched {len(all_branches)} total branches from repository")

        # Filter for build branches (matching pattern build-VERSION-alphaYYMMDDHHMM)
        # Example: build-0.8.5-alpha2601071435
        build_branches = []
        for branch in all_branches:
            branch_name = branch["name"]
            # Match pattern: build-X.X.X-alphaYYMMDDHHMM
            if re.match(r"^build-[\d.]+-alpha\d{10}$", branch_name):
                build_branches.append(branch_name)

        if len(build_branches) <= 30:
            print(
                f"✅ Found {len(build_branches)} build branches (≤30), no cleanup needed"
            )
            return

        # Sort branches by timestamp in name (alphaYYMMDDHHMM)
        build_branches.sort(key=lambda x: re.search(r"alpha(\d{10})$", x).group(1))

        # Keep last 30, delete the rest
        branches_to_delete = build_branches[:-30]

        print(f"📊 Found {len(build_branches)} build branches, keeping last 30")
        print(f"🗑️  Deleting {len(branches_to_delete)} old branches...")

        deleted_count = 0
        for branch_name in branches_to_delete:
            delete_url = f"https://api.github.com/repos/{fork_owner}/{fork_repo}/git/refs/heads/{branch_name}"
            delete_response = requests.delete(delete_url, headers=github_headers())

            if delete_response.status_code == 204:
                deleted_count += 1
                print(f"  ✓ Deleted: {branch_name}")
            else:
                print(
                    f"  ✗ Failed to delete {branch_name}: {delete_response.status_code}"
                )

        print(
            f"✅ Cleanup complete: {deleted_count}/{len(branches_to_delete)} branches deleted"
        )

    except Exception as e:
        print(f"⚠️ Error during branch cleanup: {e}")


def should_push_branch():
    """Whether to publish the build branch to the fork.

    The branch is worth publishing when someone will follow a link to it — a
    release body and a report both point at it, and PR authors are invited to
    check it out and test their work alongside everyone else's.

    Nothing points at the branch from a manifest-only run: there is no release,
    and the manifest itself references PRs and commits rather than the branch.
    Pushing one anyway means a force-pushed branch per run, which at an hourly
    cadence churns the fork's branch list through a day and a half of history
    that nobody asked for and nobody reads.

    Default is unchanged (push), so the canonical instance behaves exactly as
    before. Set BONSAIPR_PUSH_BRANCH=0 to suppress it.
    """
    v = os.getenv("BONSAIPR_PUSH_BRANCH", "").strip().lower()
    return v not in ("0", "false", "no")


def push_branch_to_fork(branch_name):
    """Push the new branch to the fork"""
    original_dir = os.getcwd()
    try:
        os.chdir(work_dir)
        # Ensure origin remote is set to use token
        subprocess.run(
            ["git", "remote", "set-url", "origin", fork_repo_url], check=True
        )
        # Push the new branch to origin (fork)
        subprocess.run(["git", "push", "origin", branch_name, "--force"], check=True)
        print(f"✅ Pushed branch '{branch_name}' to fork: {fork_repo_url_public}")
        # Stay on the branch with PRs instead of returning to SOURCE_BASE_BRANCH
        print(f"📍 Repository is now on branch '{branch_name}' with applied PRs")
    finally:
        os.chdir(original_dir)


def load_failure_tracking(tracking_path):
    """Load persistent PR failure tracking data (date + commit when first seen failing)."""
    if os.path.exists(tracking_path):
        try:
            with open(tracking_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load failure tracking file: {e}")
    return {}


def save_failure_tracking(tracking_path, data):
    """Persist PR failure tracking data to disk."""
    try:
        os.makedirs(os.path.dirname(tracking_path), exist_ok=True)
        with open(tracking_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save failure tracking file: {e}")


def update_failure_tracking(
    tracking_data, currently_failing_pr_numbers, current_date, source_commit_hash
):
    """Update tracking: add first-seen entries for new failures, remove resolved ones."""
    updated = {}
    for pr_number in currently_failing_pr_numbers:
        key = str(pr_number)
        if key in tracking_data:
            updated[key] = tracking_data[key]  # preserve first-seen data
        else:
            updated[key] = {
                "first_detected": current_date,
                "base_commit": source_commit_hash,
            }
    # PRs no longer in the failing list are silently dropped (they succeeded)
    return updated


def find_breaking_commit_hints(conflicting_files, max_commits=5, since_commit=None):
    """Return upstream commits that touched the conflicting files.

    If since_commit is provided (the base branch HEAD at first-detected failure),
    the search is anchored to that revision so we don't return commits that landed
    after the PR was already broken.
    """
    if not conflicting_files:
        return []
    # Anchor to the commit where the PR first broke, so later unrelated commits
    # on the base branch don't pollute the results.
    revision = since_commit if since_commit else SOURCE_BASE_BRANCH
    seen = {}
    try:
        for file_path in conflicting_files[:5]:  # cap at 5 files for speed
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--format=%h %s (%ad, %an)",
                    "--date=short",
                    f"-{max_commits}",
                    revision,
                    "--",
                    file_path,
                ],
                capture_output=True,
                text=True,
                cwd=work_dir,
            )
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    commit_hash = line.split()[0]
                    if commit_hash not in seen:
                        seen[commit_hash] = line
    except Exception as e:
        print(f"Warning: could not retrieve breaking commit hints: {e}")
    return list(seen.values())[:max_commits]


def generate_report(
    applied_prs,
    failed_prs,
    report_path,
    branch_name,
    skipped_prs=None,
    failed_pr_test_results=None,
    commit_hash=None,
    failure_tracking=None,
    pr_conflict_data=None,
    merge_order="ascending",
):
    if skipped_prs is None:
        skipped_prs = []
    if failure_tracking is None:
        failure_tracking = {}
    if pr_conflict_data is None:
        pr_conflict_data = {}
    print(f"Generating report at: {report_path}")
    # --- Count failed PRs by reason ---
    failed_conflict_with_base = 0
    failed_conflict_with_others = 0
    failed_unknown = 0
    # If failed_pr_test_results is a dict, use it for test results
    if isinstance(failed_pr_test_results, dict):
        for pr in failed_prs:
            pr_number = pr["number"]
            test_result = failed_pr_test_results.get(pr_number, None)
            if test_result is True:
                failed_conflict_with_others += 1
            elif test_result is False:
                failed_conflict_with_base += 1
            else:
                failed_unknown += 1
    if not commit_hash:
        commit_hash = "unknown"

    # --- Cross-order stability -------------------------------------------------
    # Which PRs merge regardless of merge order, and which are in a conflict race.
    # Purely additive: with fewer than two usable snapshots (first run ever, or a
    # fresh sandbox) the columns and summary bullets are simply omitted.
    order_states = pr_state.load_order_states(REPORTS_DIR)
    robustness = pr_state.compute_robustness(order_states)
    robustness_sources = pr_state.robustness_sources(order_states)
    order_releases = pr_state.order_releases(order_states)
    show_stability = len(robustness_sources) >= 2

    def _stability_cell(pr_number):
        """Orders this PR merged under, per the snapshots listed in the Summary.

        Lists the orders explicitly rather than saying "all", because a PR the
        other snapshots predate is judged on fewer than three orders. Each order
        links to the release whose snapshot merged the PR — i.e. the exact build
        to download if you want it. Snapshots that predate release stamping have
        no URL and stay plain text.
        """
        entry = robustness.get(str(pr_number))
        if not entry:
            return "— not yet seen"
        if not entry["merged_in"]:
            return "✖ none"
        prefix = "✅" if entry["stable"] else "⚠️"
        linked = ", ".join(
            pr_state.order_link(suffix, order_releases) for suffix in entry["merged_in"]
        )
        return f"{prefix} {linked}"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# BonsaiPR Weekly Build Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"Branch: {branch_name}\n")
        f.write(f"IfcOpenShell source commit: {commit_hash}\n")
        order_desc = pr_state.order_meta(merge_order)["short"]
        f.write(f"Merge Order: {merge_order} ({order_desc})\n")
        if should_push_branch():
            f.write(
                f"Fork Repository: https://github.com/{fork_owner}/{fork_repo}/tree/{branch_name}\n\n"
            )
        else:
            # Linking to a branch that was never pushed gives the reader a 404
            # and no way to tell whether the build failed or the branch simply
            # was not published.
            f.write(f"Build branch: {branch_name} (built locally, not published)\n\n")
        f.write(f"## Summary\n")
        total_prs = len(applied_prs) + len(failed_prs) + len(skipped_prs)
        f.write(f"- Total PRs processed: {total_prs}\n")
        f.write(f"- Successfully merged: {len(applied_prs)}\n")
        f.write(f"- Failed to merge: {len(failed_prs)}\n")
        f.write(f"- Skipped (draft/repo issues): {len(skipped_prs)}\n\n")
        # --- Add detailed failed PR counts ---
        f.write(
            f"- Failed to Merge (conflicts with base {SOURCE_BASE_BRANCH}): {failed_conflict_with_base}\n"
        )
        f.write(
            f"- Skipped (conflicts with other PRs): {failed_conflict_with_others}\n"
        )
        f.write(f"- Failed to Merge (unknown): {failed_unknown}\n")
        if total_prs > 0:
            success_rate = round(100 * len(applied_prs) / total_prs, 1)
            f.write(f"- Success Rate: {success_rate}%\n\n")
        else:
            f.write(f"- Success Rate: N/A\n\n")
        if PR_PINNED:
            # A count here rather than a section: the merged table now carries
            # every fact the old section did — built commit, how far behind, and
            # a link to the head — so repeating it was two places to drift apart.
            # What a 128-row table cannot do is be noticed while skimming, which
            # is the one job left for this line.
            f.write(
                f"- Built at a validated commit (head no longer merges): "
                f"{len(PR_PINNED)} — marked 📌 below\n\n"
            )

        f.write(
            f"Note: PRs were merged in {merge_order} order ({order_desc}).\n"
        )
        if merge_order == "recorded":
            # A profile that pins one order gets one build, so there is no
            # companion release for a conflict-skipped PR to turn up in.
            f.write(
                f"      This build follows the order recorded by its curation profile, so it is\n"
                f"      not one of a set — PRs listed in the 'Conflict With Other PRs' table were\n"
                f"      blocked in this order and are simply absent here.\n\n"
            )
        else:
            companion_order = pr_state.companion_orders(
                merge_order, ["ascending", "descending", "by-updated"]
            )
            f.write(
                f"      BonsaiPR builds up to three releases per run — ascending, descending, and\n"
                f"      by-updated — to maximise inclusion. PRs listed in the 'Conflict With Other\n"
                f"      PRs' table may appear in the companion {companion_order} release.\n\n"
            )
        if show_stability:
            stable_merged = 0
            dependent_merged = 0
            unseen_merged = 0
            for pr in applied_prs:
                entry = robustness.get(str(pr["number"]))
                if not entry:
                    unseen_merged += 1
                elif entry["stable"]:
                    stable_merged += 1
                else:
                    dependent_merged += 1
            compared = ", ".join(
                pr_state.order_link(suffix, order_releases)
                for suffix, _ in robustness_sources
            )
            f.write(f"- Order-stable merges (merged under every order below): {stable_merged}\n")
            f.write(
                f"- Order-dependent merges (merged here, blocked under another order): {dependent_merged}\n"
            )
            f.write(f"- Too new to compare (absent from every snapshot): {unseen_merged}\n\n")
            f.write(
                f"Cross-order stability compares the most recent snapshot of each order ({compared}).\n"
            )
            f.write(
                "      Snapshots are written when an order's build finishes, so companion orders are\n"
            )
            f.write("      generally one run behind:\n")
            for suffix, generated_at in robustness_sources:
                release = order_releases.get(suffix, {})
                # The tag is what the "Merges under" links point at; naming it
                # here makes the vintage of each link explicit.
                build = (
                    f" — {pr_state.order_link(suffix, order_releases, release['tag'])}"
                    if release.get("tag")
                    else ""
                )
                f.write(f"      - {suffix}: {generated_at or 'unknown'}{build}\n")
            f.write(
                "      'Order-dependent' means the PR lost a conflict race to a PR it overlaps with.\n"
            )
            f.write(
                "      It is a churn signal, not a defect: nothing about the PR itself failed.\n\n"
            )
        if merge_order == "by-updated":

            def _sort_key(p):
                return p.get("updated_at", "")

            reverse_sort = True
        else:

            def _sort_key(p):
                return p["number"]

            reverse_sort = merge_order == "descending"
        # Escape a value for safe inclusion in a markdown table cell.
        def _cell(value):
            return str(value).replace("|", "\\|").replace("\n", " ").strip()

        if failed_prs:
            # Common cell builders shared by both failed-PR tables.
            def _pr_common_cells(pr):
                pr_number = pr["number"]
                pr_link = f"[#{pr_number}]({pr['html_url']})"
                author = _cell(pr['user']['login'])
                branch = _cell(pr.get('head', {}).get('ref', 'unknown'))
                last_sha = pr.get('head', {}).get('sha', '')
                if last_sha:
                    last_commit_url = f"https://github.com/{upstream_repo}/commit/{last_sha}"
                    last_commit = f"[{last_sha[:7]}]({last_commit_url})"
                else:
                    last_commit = ""
                # First-detected date and base commit from tracking
                first_detected = ""
                base_commit_cell = ""
                tracking_key = str(pr_number)
                if tracking_key in failure_tracking:
                    entry = failure_tracking[tracking_key]
                    first_detected = _cell(entry.get('first_detected', 'unknown'))
                    base_commit = entry.get("base_commit", "unknown")
                    if base_commit and base_commit != "unknown":
                        base_commit_url = (
                            f"https://github.com/{upstream_repo}/commit/{base_commit}"
                        )
                        base_commit_cell = f"[{base_commit[:7]}]({base_commit_url})"
                    else:
                        base_commit_cell = _cell(base_commit)
                return pr_link, author, branch, last_commit, first_detected, base_commit_cell

            # Partition failed PRs by individual test-merge result:
            #   True  -> merges cleanly against base, only conflicts with other PRs
            #   False/None -> fails to merge against base (problem with the PR itself)
            def _test_result_for(pr):
                if isinstance(failed_pr_test_results, dict):
                    return failed_pr_test_results.get(pr["number"], None)
                return None

            sorted_failed = sorted(failed_prs, key=_sort_key, reverse=reverse_sort)
            base_failures = [pr for pr in sorted_failed if _test_result_for(pr) is not True]
            other_conflicts = [pr for pr in sorted_failed if _test_result_for(pr) is True]

            # --- Table 1: PRs that fail to merge against the base ---
            f.write(
                f"## ❌ Failed to Merge Against Base ({len(base_failures)})\n\n"
            )
            f.write(
                "| PR | Title | Author | Branch | Last commit | First detected | Base commit | Broken by | Conflicting files |\n"
            )
            f.write(
                "|----|-------|--------|--------|-------------|----------------|-------------|-----------|--------------------|\n"
            )
            for pr in base_failures:
                pr_number = pr["number"]
                pr_link, author, branch, last_commit, first_detected, base_commit_cell = _pr_common_cells(pr)
                # Broken-by and conflicting-files detail (only for base-conflict PRs)
                conflict_info = pr_conflict_data.get(pr_number, {})
                conflicting_files = conflict_info.get("files", [])
                breaking_commits = conflict_info.get("breaking_commits", [])
                broken_by_cell = ""
                if breaking_commits:
                    broken_parts = []
                    for bc in breaking_commits:
                        parts = bc.split(None, 1)
                        if len(parts) == 2:
                            commit_hash, commit_msg = parts
                            commit_url = f"https://github.com/{upstream_repo}/commit/{commit_hash}"
                            broken_parts.append(
                                f"[{commit_hash[:7]}]({commit_url}) {_cell(commit_msg)}"
                            )
                        else:
                            broken_parts.append(f"`{_cell(bc)}`")
                    broken_by_cell = "<br>".join(broken_parts)
                conflicting_cell = ""
                if conflicting_files:
                    conflicting_cell = "<br>".join(
                        f"[{_cell(cf)}](https://github.com/{upstream_repo}/blob/{SOURCE_BASE_BRANCH}/{cf})"
                        for cf in conflicting_files
                    )
                f.write(
                    f"| {pr_link} | {_cell(pr['title'])} | {author} | {branch} | {last_commit} | "
                    f"{first_detected} | {base_commit_cell} | {broken_by_cell} | {conflicting_cell} |\n"
                )
            f.write("\n")

            # --- Table 2: PRs that merge cleanly against base but conflict with other PRs ---
            f.write(
                f"## 🔀 Conflict With Other PRs ({len(other_conflicts)})\n\n"
            )
            f.write(
                "These PRs merge cleanly against the base on their own, but conflict with "
                "another PR already merged in this release."
                + (
                    # A profile pinning one order produces one build, so there is
                    # no companion for the PR to turn up in. Promising one here
                    # contradicts the note above and sends the reader looking for
                    # a release that was never made.
                    " This curation builds a single order, so there is no companion "
                    "release — they are simply absent from it.\n\n"
                    if merge_order == "recorded"
                    else " They may appear in the companion release built in the "
                    "opposite order.\n\n"
                )
            )
            merges_under_header = " Merges under |" if show_stability else ""
            merges_under_rule = "--------------|" if show_stability else ""
            f.write(
                "| PR | Title | Author | Branch | Last commit | First detected | Base commit |"
                f"{merges_under_header}\n"
            )
            f.write(
                "|----|-------|--------|--------|-------------|----------------|-------------|"
                f"{merges_under_rule}\n"
            )
            for pr in other_conflicts:
                pr_link, author, branch, last_commit, first_detected, base_commit_cell = _pr_common_cells(pr)
                merges_under = (
                    f" {_stability_cell(pr['number'])} |" if show_stability else ""
                )
                f.write(
                    f"| {pr_link} | {_cell(pr['title'])} | {author} | {branch} | {last_commit} | "
                    f"{first_detected} | {base_commit_cell} |{merges_under}\n"
                )
            f.write("\n")
        if skipped_prs:
            f.write(f"## ⚠️ Skipped PRs ({len(skipped_prs)})\n\n")
            f.write("| PR | Title | Author | Branch | Last commit | Reason |\n")
            f.write("|----|-------|--------|--------|-------------|--------|\n")
            for pr in sorted(skipped_prs, key=_sort_key, reverse=reverse_sort):
                pr_link = f"[#{pr['number']}]({pr['html_url']})"
                author = _cell(pr['user']['login'])
                branch = _cell(pr.get('head', {}).get('ref', 'unknown'))
                last_sha = pr.get('head', {}).get('sha', '')
                if last_sha:
                    last_commit_url = f"https://github.com/{upstream_repo}/commit/{last_sha}"
                    last_commit = f"[{last_sha[:7]}]({last_commit_url})"
                else:
                    last_commit = ""
                # If there is an individual test merge comment, use it as reason
                skip_reason = pr.get("skip_reason", None)
                test_result = pr.get("individual_test_merge", None)
                if test_result:
                    reason = test_result
                elif skip_reason:
                    reason = skip_reason
                else:
                    reason = "Repository no longer accessible (deleted fork)"
                f.write(
                    f"| {pr_link} | {_cell(pr['title'])} | {author} | {branch} | {last_commit} | {_cell(reason)} |\n"
                )
            f.write("\n")
        if applied_prs:
            f.write(f"## ✅ Successfully Merged PRs ({len(applied_prs)})\n\n")
            if PR_PINNED:
                f.write(
                    "📌 marks a PR built at an earlier commit this curation had "
                    "validated, because its current head no longer merges. "
                    "**Last commit** is always what this build actually merged, and "
                    "**Behind head** is how many of the PR's *own* commits it trails "
                    "its current head by — upstream merged into the branch is not "
                    "counted. Click it to see what is missing.\n\n"
                    "Two consequences worth acting on: you are testing an older version "
                    "of these PRs than the branch now holds, and their authors may not "
                    "know their head has stopped merging — which is true for everyone "
                    "building them, not just for this curation.\n\n"
                )
            stability_header = " Order stability |" if show_stability else ""
            stability_rule = "-----------------|" if show_stability else ""
            # Only worth a column when something is actually pinned; otherwise it
            # is an empty column on every row of a 128-row table.
            behind_header = " Behind head |" if PR_PINNED else ""
            behind_rule = "-------------|" if PR_PINNED else ""
            f.write(
                f"| PR | Title | Author | Branch | Created | Last commit |{behind_header}{stability_header}\n"
            )
            f.write(
                f"|----|-------|--------|--------|---------|-------------|{behind_rule}{stability_rule}\n"
            )
            for pr in sorted(applied_prs, key=_sort_key, reverse=reverse_sort):
                pr_link = f"[#{pr['number']}]({pr['html_url']})"
                author = _cell(pr['user']['login'])
                branch = _cell(pr.get('head', {}).get('ref', 'unknown'))
                created = _cell(pr['created_at'][:10])
                # The commit THIS BUILD merged, which is not always the PR's
                # current tip: a pinned fallback builds an earlier, validated
                # commit. Showing the tip would present a commit that does not
                # merge as though it were in the build.
                pinned_sha = PR_PINNED.get(pr['number'])
                last_sha = pinned_sha or pr.get('head', {}).get('sha', '')
                if last_sha:
                    last_commit_url = f"https://github.com/{upstream_repo}/commit/{last_sha}"
                    last_commit = f"[{last_sha[:7]}]({last_commit_url})"
                    if pinned_sha:
                        last_commit += " 📌"
                else:
                    last_commit = ""
                # How far the built commit trails the PR's head, linked to that
                # head so the reader can go and look at what they are missing.
                behind = ""
                if PR_PINNED:
                    tip_sha = _pr_tip_shas.get(pr['number'])
                    n = _commits_behind(pinned_sha, tip_sha)
                    if n is None:
                        behind = " |"
                    else:
                        tip_url = f"https://github.com/{upstream_repo}/commit/{tip_sha}"
                        behind = f" [{n}]({tip_url}) |"
                stability = (
                    f" {_stability_cell(pr['number'])} |" if show_stability else ""
                )
                f.write(
                    f"| {pr_link} | {_cell(pr['title'])} | {author} | {branch} | {created} | {last_commit} |{behind}{stability}\n"
                )
            f.write("\n")
        f.write(f"## Developer Instructions\n\n")
        f.write(f"To use this branch for development:\n\n")
        f.write(f"```bash\n")
        f.write(f"git clone https://github.com/{fork_owner}/{fork_repo}.git\n")
        f.write(f"cd {fork_repo}\n")
        f.write(f"git checkout {branch_name}\n")
        f.write(f"```\n\n")
        f.write(
            f"This branch contains the latest IfcOpenShell {SOURCE_BASE_BRANCH} branch with "
        )
        f.write(f"{len(applied_prs)} merged community pull requests. ")
        f.write(
            f"PR authors can use this branch to test their changes and make adjustments.\n"
        )


def main():
    print("Starting weekly BonsaiPR branch creation...")
    print("This script creates clean branches with merged PRs for PR authors to test.")
    print(
        "No bonsai→bonsaiPR renaming is done here - that happens in the build script."
    )
    # Validate GitHub token
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found in environment variables")
        print("Please check your .env file and ensure GITHUB_TOKEN is set")
        return
    branch_name, report_path = get_branch_and_report_names()
    print(f"Branch name: {branch_name}")
    print(f"Report will be saved as: {os.path.basename(report_path)}")

    # Load persistent PR failure tracking
    report_dir = os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")
    tracking_path = os.path.join(report_dir, "pr_failure_tracking.json")
    failure_tracking = load_failure_tracking(tracking_path)
    print(
        f"📋 Loaded failure tracking for {len(failure_tracking)} PR(s) from {tracking_path}"
    )

    # Parse order flags
    reverse_order = "--reverse" in sys.argv
    by_updated_order = "--by-updated" in sys.argv
    if by_updated_order:
        merge_order_str = "by-updated"
        print(
            "Merging PRs in descending order of last update (most recently updated first)"
        )
    elif reverse_order:
        merge_order_str = "descending"
        print("Merging PRs in descending order (highest to lowest number)")
    elif CURATION.data.get("order_seq"):
        # Announced properly once the PRs are actually sorted, below; saying
        # "ascending" here would be a lie the log never retracts.
        merge_order_str = "recorded"
    else:
        merge_order_str = "ascending"
        print("Merging PRs in ascending order (lowest to highest number)")
    # Setup repository
    setup_repository()
    # Get the commit hash of the source repository BEFORE merging any PRs
    try:
        source_commit_hash = (
            subprocess.check_output(["git", "-C", work_dir, "rev-parse", "HEAD"])
            .decode()
            .strip()
        )
    except Exception:
        source_commit_hash = "unknown"
    # Get open PRs
    prs = get_open_prs()
    # Sort PRs
    recorded = CURATION.data.get("order_seq") or []
    if recorded and not reverse_order and not by_updated_order:
        # RFC-001 §5.3: a distilled profile carries the sequence its curator
        # actually built in — a hand-validated order known to produce a working
        # tree, where asc/desc/upd are guesses. PRs absent from the recording
        # (added upstream since the branch was distilled) go last, in number
        # order, so a stale profile degrades instead of dropping them.
        rank = {int(n): i for i, n in enumerate(recorded)}
        merge_order_str = "recorded"
        prs = sorted(prs, key=lambda pr: (rank.get(pr["number"], len(rank)), pr["number"]))
        unranked = sum(1 for pr in prs if pr["number"] not in rank)
        print(
            f"Merging PRs in the order recorded by profile '{CURATION.name}'"
            + (f" ({unranked} newer PR(s) appended)" if unranked else "")
        )
    elif by_updated_order:
        prs = sorted(prs, key=lambda pr: pr.get("updated_at", ""), reverse=True)
    else:
        prs = sorted(prs, key=lambda pr: pr["number"], reverse=reverse_order)
    if not prs:
        print("No open PRs found, creating branch with just main branch updates")
        applied, failed, skipped = [], [], []
        failed_pr_test_results = {}
        pr_conflict_data = {}
        # Actually create the branch before pushing it. apply_prs_to_branch()
        # normally does this, but it is skipped entirely on this path, so the
        # push below used to fail with "src refspec does not match any" — an
        # error that says nothing about the real problem, which is that the
        # curation matched no open PRs.
        original_dir = os.getcwd()
        try:
            os.chdir(work_dir)
            subprocess.run(["git", "branch", "-D", branch_name], capture_output=True)
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        finally:
            os.chdir(original_dir)
        # Push branch to fork (even if empty)
        if should_push_branch():
            push_branch_to_fork(branch_name)
        else:
            print(f"⏭️  Branch {branch_name} kept local (BONSAIPR_PUSH_BRANCH=0)")
        # Print current branch for verification
        os.chdir(work_dir)
        result = subprocess.run(
            ["git", "branch", "--show-current"], capture_output=True, text=True
        )
        print(f"[VERIFICATION] Current branch after merge: {result.stdout.strip()}")
        os.chdir(os.path.dirname(__file__))
        failure_tracking = update_failure_tracking(
            failure_tracking,
            set(),
            datetime.now().strftime("%Y-%m-%d"),
            source_commit_hash,
        )
        save_failure_tracking(tracking_path, failure_tracking)
        generate_report(
            applied,
            failed,
            report_path,
            branch_name,
            skipped,
            failed_pr_test_results,
            source_commit_hash,
            failure_tracking,
            pr_conflict_data,
            merge_order=merge_order_str,
        )
        print(f"\n🎉 Weekly BonsaiPR branch creation completed!")
        print(
            f"✅ Branch created: https://github.com/{fork_owner}/{fork_repo}/tree/{branch_name}"
            if should_push_branch()
            else f"✅ Branch created locally: {branch_name} (not published)"
        if should_push_branch()
        else f"✅ Branch created locally: {branch_name} (not published)"
        )
        print(f"📊 Report saved: {report_path}")
        print(
            f"📝 Summary: {len(applied)} PRs merged, {len(failed)} failed, {len(skipped)} skipped"
        )
        return
    # Apply PRs to new branch
    applied, failed, skipped = apply_prs_to_branch(branch_name, prs)
    # Persist who-lost-to-whom while it still exists (RFC-001 phase 1.1).
    _order_suffix = pr_state.ORDER_SUFFIX_BY_NAME.get(merge_order_str, merge_order_str)
    write_rivals(REPORTS_DIR, _order_suffix, PR_RIVALS)
    write_pinned(REPORTS_DIR, _order_suffix, PR_PINNED)
    # Push branch to fork BEFORE running individual PR tests
    if should_push_branch():
        push_branch_to_fork(branch_name)
        # Clean up old branches after successfully pushing new one
        cleanup_old_branches()
    else:
        print(
            f"⏭️  Branch {branch_name} kept local — nothing links to it on this "
            f"run (BONSAIPR_PUSH_BRANCH=0)"
        )
    # Print current branch for verification
    os.chdir(work_dir)
    result = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    )
    print(f"[VERIFICATION] Current branch after merge: {result.stdout.strip()}")
    os.chdir(os.path.dirname(__file__))
    # Test failed PRs individually; also get conflicting-file / breaking-commit hints
    failed_pr_test_results, pr_conflict_data = test_failed_prs_individually(failed, failure_tracking=failure_tracking)
    # Update and persist failure tracking
    currently_failing = {
        pr["number"]
        for pr in failed
        if failed_pr_test_results.get(pr["number"]) is False
    }
    failure_tracking = update_failure_tracking(
        failure_tracking,
        currently_failing,
        datetime.now().strftime("%Y-%m-%d"),
        source_commit_hash,
    )
    save_failure_tracking(tracking_path, failure_tracking)
    print(f"💾 Failure tracking saved: {len(failure_tracking)} PR(s) tracked")
    # Ensure we are on the weekly branch before generating the report
    os.chdir(work_dir)
    subprocess.run(["git", "checkout", branch_name], check=True)
    os.chdir(os.path.dirname(__file__))
    # Generate report
    generate_report(
        applied,
        failed,
        report_path,
        branch_name,
        skipped,
        failed_pr_test_results,
        source_commit_hash,
        failure_tracking,
        pr_conflict_data,
        merge_order=merge_order_str,
    )
    # The manifest, always. Stage 0 owns it whether or not stage 2 runs, because
    # stage 0 is the only place that knows what was actually built.
    try:
        write_state_snapshot(
            applied,
            failed,
            skipped,
            failed_pr_test_results,
            merge_order_str,
            len(prs),
            base_commit=source_commit_hash,
        )
    except Exception as e:
        # A manifest is downstream of the build, never a reason to fail one.
        print(f"⚠️  Could not write state snapshot: {e}")
    print(f"\n🎉 Weekly BonsaiPR branch creation completed!")
    print(
        f"✅ Branch created: https://github.com/{fork_owner}/{fork_repo}/tree/{branch_name}"
        if should_push_branch()
        else f"✅ Branch created locally: {branch_name} (not published)"
    )
    print(f"📊 Report saved: {report_path}")
    print(
        f"📝 Summary: {len(applied)} PRs merged, {len(failed)} failed, {len(skipped)} skipped"
    )


if __name__ == "__main__":
    main()
