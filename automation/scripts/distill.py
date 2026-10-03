#!/usr/bin/env python3
"""
distill.py - Recover a curation profile from a hand-composed build branch.

Why this exists
---------------
RFC-001 s5. Nobody is going to hand-write a profile listing 158 PR numbers. But
powerusers are *already* maintaining exactly that curation, as a long-lived
build branch accumulated over months of merging. Those branches are messy,
private and undocumented, and every one of them is a curation the federation
wants.

So the primary way a profile should come into existence is not by authoring one.
It is by distilling one out of a branch that already works.

Three things come out, in ascending order of value:

  1. the PR list                - which PRs the curator chose
  2. the recorded merge order   - a hand-validated sequence known to build,
                                  where BonsaiPR otherwise guesses (asc/desc/upd)
  3. the conflict resolutions   - every merge the curator resolved by hand is a
                                  conflict the automation will hit again, already
                                  solved. KNOWN_CONFLICT_RESOLUTIONS currently
                                  holds one entry.

...plus the residue: first-parent commits attributable to no PR, which in
practice turn out to be the curator's own unpublished feature work rather than
the conflict glue you would expect.

What this does NOT do
---------------------
`replay` (RFC-001 s5.5) is not implemented here. Rebuilding from the distilled
profile and reconciling against the original branch needs the build pipeline,
and belongs in its own command. This command only *reads*; it never checks out,
merges, or modifies anything.

It also never emits exclusions (RFC-001 s5.2): a PR absent from a build branch
was almost never rejected, it was never considered, and recording those as
rejections would flood the objection signal with refusals no human ever made.

The non-overlap invariant pre-filter described in RFC-001 s5.3 - auto-resolving
conflicts in files untouched between merge-base and current base - is also not
implemented yet. It applies to the rebase path rather than to reading a finished
branch, and wants its own pass.

CLI
---
    python distill.py analyze --branch BRANCH [--base v0.8.0] [--repo DIR]
    python distill.py profile --branch BRANCH --name NAME [--out DIR]

`analyze` prints the report and writes nothing.
"""

import os
import re
import sys
import json
import argparse
import subprocess
from collections import defaultdict, OrderedDict

SCHEMA_VERSION = 1

DEFAULT_BASE = "v0.8.0"
DEFAULT_PR_INDEX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "reports", "state.asc.json"
)

# Attribution confidence, most reliable first (RFC-001 s5.2).
EXACT = "exact"
PROBABLE = "probable"

# `Merge remote-tracking branch 'pr-8353/fix-4790-regen-style'`
RE_PR_REMOTE = re.compile(r"['\"]?(?:remotes/)?pr-(\d+)/")
# `Merge remote-tracking branch 'remotes/BIMvoice/fix-6508-geography-element-qto'`
RE_OWNER_BRANCH = re.compile(r"['\"](?:remotes/)?([A-Za-z0-9][\w.-]*)/(\S+?)['\"]")
# `Merge PR #9330 (unchanged @ d4e5a04fd9) into integration` - the shape a
# hand-rolled merge script writes. Anchored at the start of the subject, which
# is what separates it from the bare-#NNNN rung below: "Merge PR #N" as the
# opening words states which PR is being merged, while a #N anywhere else may
# just as easily be an issue the commit fixes.
RE_MERGE_PR = re.compile(r"^Merge\s+PR\s*#(\d+)")
# `Merge PR #7940 (Concatenate_selections) to resolve build conflicts`
RE_HASH_NUM = re.compile(r"#(\d+)")

# `refs/remotes/pr/8353` (a mirror of refs/pull/*/head) or the pipeline's own
# `refs/remotes/pr-8353/<branch>`.
RE_PR_REF = re.compile(r"^refs/remotes/pr[-/](\d+)(?:/|$)")
PR_REF_GLOBS = ("refs/remotes/pr/*", "refs/remotes/pr-*/*")


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #

def git(args, repo, check=False):
    r = subprocess.run(
        ["git"] + args, cwd=repo, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


# Unit/record separators rather than NUL: a literal NUL cannot be passed in argv
# on Windows (CreateProcess rejects it), and neither character occurs in a commit
# subject in practice.
NUL = "\x1f"
REC = "\x1e"


def first_parent_history(repo, base, branch):
    """Commits the curator personally put on the branch, oldest first.

    First-parent only, deliberately: commits that arrived *through* a merge are
    the PR author's work, not the curator's integration decisions. Walking all
    455 non-merge commits would conflate the two.
    """
    fmt = f"%H{NUL}%P{NUL}%an{NUL}%aI{NUL}%s{REC}"
    out = git(
        ["log", "--first-parent", "--format=" + fmt, f"{base}..{branch}"],
        repo, check=True,
    )
    commits = []
    for chunk in out.split(REC):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        parts = chunk.split(NUL)
        if len(parts) < 5:
            continue
        sha, parents, author, date, subject = parts[:5]
        commits.append(
            {
                "sha": sha.strip(),
                "parents": parents.split(),
                "author": author,
                "date": date,
                "subject": subject.strip(),
                "is_merge": len(parents.split()) > 1,
            }
        )
    commits.reverse()  # chronological: the order the curator built in
    return commits


def upstream_absorbed(repo, base, branch):
    """Shas whose patch already exists in base (`git cherry` marks them '-').

    These are PRs that got merged upstream since the curator cherry-picked them.
    Carrying them in a profile would be noise, so they are dropped rather than
    attributed.
    """
    out = git(["cherry", base, branch], repo)
    absorbed = set()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("- "):
            absorbed.add(line[2:].strip())
    return absorbed


def patch_id(repo, sha):
    """Content hash of a commit's diff. Survives cherry-pick, rebase and squash.

    `git show | git patch-id --stable` rather than plumbing: patch-id already
    ignores the commit header, blob hashes and line numbers, which is exactly the
    set of things that change when a commit is moved.
    """
    show = subprocess.run(
        ["git", "show", "--format=%H", sha], cwd=repo, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if show.returncode != 0 or not show.stdout.strip():
        return None
    pid = subprocess.run(
        ["git", "patch-id", "--stable"], cwd=repo, input=show.stdout,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    parts = pid.stdout.split()
    return parts[0] if parts else None


def pr_commit_index(repo, base, globs=PR_REF_GLOBS):
    """subject -> [(sha, pr_number)] over every commit on an open PR head.

    One `git log` pass across the mirrored PR refs - ~28k commits upstream, which
    is seconds. Computing a patch-id for all of them would not be, so the subject
    narrows the field to a handful and the patch-id only has to confirm.

    Empty when no PR refs are mirrored. That is a real state, not an error: a
    clone without them cannot tell a cherry-pick from original work, and the
    caller has to report the difference rather than assume the flattering answer.
    """
    args = ["log", "--source", "--format=%H" + NUL + "%S" + NUL + "%s" + REC]
    args += ["--glob=" + g for g in globs]
    args += ["--not", base]
    out = git(args, repo)
    index = defaultdict(list)
    for chunk in out.split(REC):
        parts = chunk.strip("\n").split(NUL)
        if len(parts) < 3:
            continue
        sha, ref, subject = parts[0].strip(), parts[1].strip(), parts[2].strip()
        m = RE_PR_REF.match(ref)
        if m and subject:
            index[subject].append((sha, m.group(1)))
    return index


def attribute_cherry_pick(repo, commit, index, cache):
    """Attribute a non-merge commit to the PR it was cherry-picked from.

    Nothing above this rung can see these. `attribute()` reads merge subjects,
    and a cherry-pick is not a merge - it is a new sha carrying someone else's
    patch. Before this rung existed every such commit fell through to residue and
    was reported as the curator's own unshared work: on the reference branch that
    mislabelled 75 of 81 commits, and the 81 was quoted in RFC-001 as the headline
    justification for the feature.

    Patch-id is what survives the move, so an identical patch is exact. A commit
    that keeps its subject but not its diff is the ordinary result of picking onto
    a different base - the hunks get conflict-adjusted - so it is probable rather
    than exact: the same work, adapted.
    """
    candidates = index.get(commit["subject"])
    if not candidates:
        return None, None, None

    mine = patch_id(repo, commit["sha"])
    if mine:
        for sha, pr in candidates:
            if sha not in cache:
                cache[sha] = patch_id(repo, sha)
            if cache[sha] and cache[sha] == mine:
                return pr, EXACT, f"patch-identical to {sha[:12]} on PR #{pr}"

    prs = sorted({pr for _, pr in candidates}, key=int)
    shown = ", ".join("#" + p for p in prs[:3])
    if len(prs) > 3:
        shown += f" and {len(prs) - 3} more"
    return prs[0], PROBABLE, f"subject matches {shown}, content adapted"


def files_of_commit(repo, sha):
    out = git(["show", "--format=", "--name-only", sha], repo)
    return [f.strip() for f in out.splitlines() if f.strip()]


RE_STAGE = re.compile(r"^\d{6} [0-9a-f]{7,64} [123]\t(.+)$")

# Conflicts resolved by GRAPH SURGERY rather than by editing files: the curator
# merges the rival PR's branch into this PR's branch so the two stop colliding.
# These leave no textual trace in the integration merge, and they do not sit on
# the first-parent path at all - they are pushed onto the PR branches, which is
# what `prompts/resolve conflicts with other PRs.md` tells people to do. A
# first-parent-only scan misses every one of them.
RE_ANCESTRY = re.compile(
    r"ancestry|absorb|as ancestor|resolve\s+.*conflict|fix\s+.*conflict",
    re.IGNORECASE,
)


def ancestry_resolutions(repo, base, branch, first_parent_shas):
    """Off-first-parent merges whose subject says they exist to fix a conflict."""
    fmt = f"%H{NUL}%s{REC}"
    out = git(["log", "--merges", "--format=" + fmt, f"{base}..{branch}"], repo)
    found = []
    for chunk in out.split(REC):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        parts = chunk.split(NUL)
        if len(parts) < 2:
            continue
        sha, subject = parts[0].strip(), parts[1].strip()
        if sha in first_parent_shas:
            continue
        if not RE_ANCESTRY.search(subject):
            continue
        prs = [int(n) for n in RE_HASH_NUM.findall(subject)]
        found.append({"sha": sha[:12], "subject": subject, "prs": prs})
    return found


def merge_conflicts(repo, sha):
    """Paths git could NOT have merged on its own — i.e. the curator resolved them.

    Replays the merge with `git merge-tree --write-tree`, which performs a real
    three-way merge into the object store without touching a working tree, and
    reports every conflicted path.

    The obvious-looking alternative, `git show --diff-merges=cc`, does not work:
    it lists paths where the result differs from *both* parents, which is also
    true of a perfectly ordinary automatic merge where each side edited a
    different region of the same file. Using it over-reports badly — on this
    branch it claimed 116 of 160 merges were hand-resolved when the real figure
    is far lower.
    """
    if len(git(["rev-list", "--parents", "-n", "1", sha], repo).split()) < 3:
        return []
    p1 = git(["rev-parse", f"{sha}^1"], repo).strip()
    p2 = git(["rev-parse", f"{sha}^2"], repo).strip()
    if not p1 or not p2:
        return []

    r = subprocess.run(
        ["git", "merge-tree", "--write-tree", p1, p2],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    # 0 = merged cleanly, 1 = conflicts, anything else = git could not tell us.
    if r.returncode == 0 or r.returncode > 1:
        return []
    paths = []
    for line in r.stdout.splitlines():
        m = RE_STAGE.match(line)
        if m and m.group(1) not in paths:
            paths.append(m.group(1))
    return paths


def _blob(repo, rev, path):
    r = subprocess.run(
        ["git", "show", f"{rev}:{path}"], cwd=repo,
        capture_output=True,
    )
    return r.stdout if r.returncode == 0 else None


def resolution_strategy(repo, sha, path):
    """Did the curator take one side wholesale, or hand-edit?

    Wholesale resolutions map straight onto KNOWN_CONFLICT_RESOLUTIONS'
    theirs/ours shape. Hunk-level ones do not, and pretending otherwise would
    silently apply the wrong file - so they are reported as `manual` and left
    for a human (RFC-001 s5.3).
    """
    result = _blob(repo, sha, path)
    ours = _blob(repo, f"{sha}^1", path)
    theirs = _blob(repo, f"{sha}^2", path)
    if result is None:
        return "deleted"
    if theirs is not None and result == theirs:
        return "theirs"
    if ours is not None and result == ours:
        return "ours"
    return "manual"


# --------------------------------------------------------------------------- #
# PR index
# --------------------------------------------------------------------------- #

def load_pr_index(path):
    """Build lookup tables from a committed BonsaiPR state snapshot.

    The snapshot already carries number, title, author, branch and url for every
    open PR, so the attribution ladder needs no GitHub API at all - it reuses
    what the pipeline publishes every run.
    """
    if not path or not os.path.exists(path):
        return {}, {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_num, by_owner_branch = {}, {}
    for num, rec in (data.get("prs") or {}).items():
        by_num[str(num)] = rec
        author, branch = rec.get("author"), rec.get("branch")
        if author and branch:
            by_owner_branch[(author.lower(), branch.lower())] = str(num)
    return by_num, by_owner_branch


# --------------------------------------------------------------------------- #
# Attribution ladder (RFC-001 s5.2)
# --------------------------------------------------------------------------- #

def attribute(commit, by_owner_branch):
    """(pr_number|None, confidence|None, evidence) for one first-parent commit."""
    subject = commit["subject"]

    if commit["is_merge"]:
        m = RE_PR_REMOTE.search(subject)
        if m:
            return m.group(1), EXACT, "merge subject names pr-<n>/ remote"

        m = RE_OWNER_BRANCH.search(subject)
        if m:
            owner, branch = m.group(1), m.group(2)
            pr = by_owner_branch.get((owner.lower(), branch.lower()))
            if pr:
                return pr, EXACT, f"owner/branch {owner}/{branch} matched PR index"

        m = RE_MERGE_PR.match(subject)
        if m:
            return m.group(1), EXACT, "subject opens with 'Merge PR #<n>'"

        m = RE_HASH_NUM.search(subject)
        if m:
            # Weakest rung: "#7940" in a subject usually means the PR, but it can
            # equally be an *issue* the commit fixes. Never promoted to exact.
            return m.group(1), PROBABLE, "merge subject mentions #<n>"

    return None, None, None


# --------------------------------------------------------------------------- #
# Residue clustering (RFC-001 s5.4)
# --------------------------------------------------------------------------- #

SUBJECT_PREFIX = re.compile(r"^([\w.\- ]{3,24}?):")


def cluster_residue(repo, residue, max_gap=3):
    """Group unattributed commits into candidate patch series.

    Contiguous runs in first-parent order that share files or a subject prefix.
    This is a heuristic and is presented as a proposal - RFC-001 s5.4 is explicit
    that clustering is never applied silently.
    """
    clusters = []
    current = None
    for idx, c in enumerate(residue):
        files = set(files_of_commit(repo, c["sha"]))
        prefix_m = SUBJECT_PREFIX.match(c["subject"])
        prefix = prefix_m.group(1).strip().lower() if prefix_m else None

        joins = False
        if current is not None and idx - current["_last_idx"] <= max_gap:
            if files & current["files"]:
                joins = True
            elif prefix and prefix == current["prefix"]:
                joins = True

        if joins:
            current["commits"].append(c)
            current["files"] |= files
            current["_last_idx"] = idx
        else:
            current = {
                "commits": [c],
                "files": set(files),
                "prefix": prefix,
                "_last_idx": idx,
            }
            clusters.append(current)

    for cl in clusters:
        cl["files"] = sorted(cl["files"])
        cl.pop("_last_idx", None)
        # Every cluster starts life unpublishable. RFC-001 s5.4: a build branch is
        # a personal workspace and will contain things its owner never intended to
        # ship, so opting *in* is the only safe default.
        cl["disposition"] = "private"
        cl["title"] = cl["commits"][0]["subject"]
    return clusters


# --------------------------------------------------------------------------- #
# Distillation
# --------------------------------------------------------------------------- #

def distill(repo, base, branch, pr_index_path=DEFAULT_PR_INDEX, harvest=True):
    by_num, by_owner_branch = load_pr_index(pr_index_path)
    # The default path is relative to *this file*, so running distill.py from a
    # download directory resolves it to somewhere that does not exist and every
    # attribution silently loses its title, its author, and the owner/branch
    # rung. That is a wrong answer dressed as a working run - it has already
    # caught two people, one of them the author of this comment.
    pr_index_ok = bool(by_num)
    commits = first_parent_history(repo, base, branch)
    absorbed = upstream_absorbed(repo, base, branch)

    order_seq = []           # PR numbers, in the order the curator merged them
    validated = {}           # PR number -> the head sha the curator actually merged
    provenance = []          # one row per first-parent commit
    residue = []
    probable = []
    unattributed_merges = []
    cherry_picked = []

    cherry_index = pr_commit_index(repo, base)
    pid_cache = {}

    for c in commits:
        pr, confidence, evidence = attribute(c, by_owner_branch)
        row = {
            "sha": c["sha"][:12],
            "subject": c["subject"],
            "author": c["author"],
            "date": c["date"],
            "kind": "merge" if c["is_merge"] else "commit",
        }
        if pr:
            row.update({"pr": int(pr), "confidence": confidence, "evidence": evidence})
            rec = by_num.get(pr)
            if rec:
                row["title"] = rec.get("title")
                row["pr_author"] = rec.get("author")
            else:
                row["note"] = "not in PR index (closed, merged upstream, or private)"
            if int(pr) not in order_seq:
                order_seq.append(int(pr))
            # The commit the curator actually merged: the merge's second parent.
            # Recording only PR numbers means a replay fetches whatever the head
            # is on the day it runs, which is a different commit from the one
            # that was validated - the base ends up pinned while the PRs float.
            if c["is_merge"] and len(c["parents"]) > 1:
                validated[int(pr)] = c["parents"][1]
                row["merged_head"] = c["parents"][1][:12]
            if confidence == PROBABLE:
                probable.append(row)
        elif c["is_merge"]:
            row["classification"] = "unattributed-merge"
            unattributed_merges.append(row)
        elif c["sha"] in absorbed:
            row["classification"] = "absorbed-upstream"
        else:
            cpr, cconf, cev = attribute_cherry_pick(repo, c, cherry_index, pid_cache)
            if cpr:
                row.update(
                    {
                        "pr": int(cpr),
                        "confidence": cconf,
                        "evidence": cev,
                        "classification": "cherry-picked",
                    }
                )
                rec = by_num.get(cpr)
                if rec:
                    row["title"] = rec.get("title")
                    row["pr_author"] = rec.get("author")
                # Deliberately NOT added to order_seq or validated. Taking one
                # commit off a PR is not evidence the curator wanted the whole
                # PR merged - it is often the opposite, someone lifting a single
                # fix out of a branch they did not want. Promoting these to
                # selections would silently widen the profile.
                cherry_picked.append(row)
            else:
                row["classification"] = "residue"
                residue.append(c)
        provenance.append(row)

    clusters = cluster_residue(repo, residue) if residue else []

    resolutions = []
    if harvest:
        for c in commits:
            if not c["is_merge"]:
                continue
            paths = merge_conflicts(repo, c["sha"])
            if not paths:
                continue
            pr, confidence, _ = attribute(c, by_owner_branch)
            entry = {
                "sha": c["sha"][:12],
                "pr": int(pr) if pr else None,
                "subject": c["subject"],
                "files": [],
            }
            for p in paths:
                entry["files"].append(
                    {"path": p, "strategy": resolution_strategy(repo, c["sha"], p)}
                )
            resolutions.append(entry)

    ancestry = ancestry_resolutions(
        repo, base, branch, {c["sha"] for c in commits}
    ) if harvest else []

    merges = [c for c in commits if c["is_merge"]]
    attributed_merges = sum(
        1 for r in provenance if r["kind"] == "merge" and r.get("pr")
    )
    # The branch was built on the merge-base, not on wherever the base branch
    # has since moved to - that is the commit its PR set is known to apply at.
    base_commit = git(["merge-base", base, branch], repo).strip() or None

    return {
        "base": base,
        "base_commit": base_commit,
        "branch": branch,
        "commits_first_parent": len(commits),
        "merges": len(merges),
        "attributed_merges": attributed_merges,
        "attribution_rate": (attributed_merges / len(merges)) if merges else 0.0,
        "order_seq": order_seq,
        "validated": validated,
        "provenance": provenance,
        "residue": residue,
        "pr_index": {
            "available": pr_index_ok,
            "path": os.path.abspath(pr_index_path) if pr_index_path else None,
            "prs": len(by_num),
        },
        "cherry_picked": cherry_picked,
        # Whether residue could be checked against open PRs at all. Without the
        # refs, "original work" degrades to "not a merge and not upstream yet",
        # which is what produced the 81 figure.
        "cherry_index": {
            "available": bool(cherry_index),
            "subjects": len(cherry_index),
        },
        "clusters": clusters,
        "probable": probable,
        "unattributed_merges": unattributed_merges,
        "absorbed": sorted(absorbed),
        "resolutions": resolutions,
        "ancestry_resolutions": ancestry,
    }


# --------------------------------------------------------------------------- #
# Emission
# --------------------------------------------------------------------------- #

def to_profile(result, name, maintainer=""):
    """A profile proposal. Note the total absence of an `exclude` block."""
    return OrderedDict(
        [
            ("schema", SCHEMA_VERSION),
            ("name", name),
            (
                "description",
                f"Distilled from branch {result['branch']} "
                f"({result['attributed_merges']} of {result['merges']} integration "
                f"merges attributed). Review before use.",
            ),
            ("maintainer", maintainer),
            # Pin to the commit the branch was actually built against. A
            # distilled curation is only known to work at that base; following
            # the branch tip instead would silently change what it means the
            # first time upstream moves. Delete `commit` to track the tip.
            (
                "base",
                {
                    "repo": "IfcOpenShell/IfcOpenShell",
                    "branch": result["base"],
                    "commit": result.get("base_commit"),
                },
            ),
            (
                "select",
                {
                    "mode": "allowlist",
                    "prs": list(result["order_seq"]),
                    "authors": [],
                },
            ),
            # No `exclude`: RFC-001 s5.2. Absence from a branch is not rejection.
            ("orders", ["recorded"]),
            ("order_seq", list(result["order_seq"])),
            # `pin` is a FALLBACK, not a freeze (RFC-001 s4). The build uses each
            # PR's current head so authors' fixes keep arriving, and drops back to
            # the commit the curator validated only when the current head will not
            # merge. Pinning outright would be reproducible and stagnant; pinning
            # nothing is what left 11 of 12 failures traceable to head drift.
            (
                "pin",
                {
                    str(n): sha
                    for n, sha in sorted((result.get("validated") or {}).items())
                },
            ),
        ]
    )


def to_resolution_table(result):
    """Candidate KNOWN_CONFLICT_RESOLUTIONS entries, in that dict's own shape."""
    lines = []
    for entry in result["resolutions"]:
        wholesale = [f for f in entry["files"] if f["strategy"] in ("theirs", "ours")]
        manual = [f for f in entry["files"] if f["strategy"] not in ("theirs", "ours")]
        if entry["pr"] and wholesale:
            lines.append(f"    # {entry['subject']}")
            lines.append(f"    {entry['pr']}: [")
            for f in wholesale:
                lines.append(f"        ({f['path']!r}, {f['strategy']!r}),")
            lines.append("    ],")
        for f in manual:
            lines.append(
                f"    # MANUAL, needs a human: PR {entry['pr']} {f['path']} "
                f"({entry['sha']})"
            )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def render(result, top=12):
    r = result
    out = []
    out.append(f"# Distilled from {r['branch']}  (base {r['base']})")
    out.append("")
    out.append(f"  first-parent commits   {r['commits_first_parent']}")
    out.append(f"  integration merges     {r['merges']}")
    out.append(
        f"  attributed to a PR     {r['attributed_merges']}"
        f"  ({r['attribution_rate']*100:.1f}%)"
    )
    idx = r.get("cherry_index") or {}
    if idx.get("available"):
        out.append(f"  cherry-picked from a PR{len(r.get('cherry_picked') or []):>4}")
        out.append(f"  residue (curator's own){len(r['residue']):>4}")
    else:
        out.append(f"  residue (UNVERIFIED)   {len(r['residue']):>4}")
    out.append(f"  absorbed upstream      {len(r['absorbed'])}")
    out.append(f"  textual hand-resolutions {len(r['resolutions'])}")
    out.append(f"  ancestry resolutions   {len(r.get('ancestry_resolutions') or [])}")
    out.append("")

    if r["attribution_rate"] < 0.5:
        out.append(
            "  ⚠️  Attribution below 50%. This branch is probably too unstructured "
            "to distil usefully — see RFC-001 §5.6."
        )
        out.append("")

    pri = r.get("pr_index") or {}
    if pri and not pri.get("available"):
        out.append(
            "  ⚠️  No PR index loaded, so attributions carry no title or author,"
        )
        out.append(
            "      the owner/branch rung is disabled, and every attributed PR is"
        )
        out.append(
            "      marked 'not in PR index'. The default path is relative to"
        )
        out.append(
            "      distill.py itself, so running it from outside a bonsaiPR clone"
        )
        out.append(f"      misses it. Looked in: {pri.get('path')}")
        out.append("      Fix with --pr-index, e.g.:")
        out.append(
            "        curl -O https://raw.githubusercontent.com/falken10vdl/"
            "bonsaiPR/main/automation/reports/state.asc.json"
        )
        out.append("")

    if not idx.get("available"):
        out.append(
            "  ⚠️  No PR refs mirrored, so cherry-picks cannot be told from original"
        )
        out.append(
            "      work and the residue count is an upper bound, likely a large"
        )
        out.append(
            "      overcount. Run: git fetch <remote> '+refs/pull/*/head:refs/remotes/pr/*'"
        )
        out.append("")

    if r.get("cherry_picked"):
        exact = sum(1 for x in r["cherry_picked"] if x.get("confidence") == EXACT)
        out.append(f"## Cherry-picked from open PRs ({len(r['cherry_picked'])})")
        out.append("")
        out.append(
            f"  {exact} patch-identical, {len(r['cherry_picked']) - exact} same subject"
        )
        out.append(
            "  with adapted content. Already shared — not the curator's unshared work,"
        )
        out.append(
            "  and not added to the profile: lifting one commit off a PR is not a"
        )
        out.append("  request to merge the whole thing.")
        out.append("")
        for row in r["cherry_picked"][:top]:
            out.append(f"  #{row['pr']:<6} {row['sha']}  {row['subject'][:66]}")
        if len(r["cherry_picked"]) > top:
            out.append(f"  … {len(r['cherry_picked']) - top} more")
        out.append("")

    if r["probable"]:
        out.append(f"## Probable attributions ({len(r['probable'])}) — verify these")
        out.append("")
        for row in r["probable"][:top]:
            out.append(f"  #{row['pr']:<6} {row['sha']}  {row['subject'][:70]}")
        out.append("")

    if r["unattributed_merges"]:
        out.append(f"## Unattributed merges ({len(r['unattributed_merges'])})")
        out.append("")
        for row in r["unattributed_merges"][:top]:
            out.append(f"  {row['sha']}  {row['subject'][:74]}")
        if len(r["unattributed_merges"]) > top:
            out.append(f"  … {len(r['unattributed_merges']) - top} more")
        out.append("")

    if r["resolutions"]:
        n_files = sum(len(e["files"]) for e in r["resolutions"])
        wholesale = sum(
            1 for e in r["resolutions"] for f in e["files"]
            if f["strategy"] in ("theirs", "ours")
        )
        out.append(f"## Harvested conflict resolutions ({n_files} files)")
        out.append("")
        out.append(
            f"  {wholesale} are wholesale (theirs/ours) and map straight onto"
        )
        out.append(
            f"  KNOWN_CONFLICT_RESOLUTIONS; {n_files - wholesale} are hunk-level and"
        )
        out.append("  need a human. Every one is a conflict the automation re-hits.")
        out.append("")
        for e in r["resolutions"][:top]:
            pr = f"#{e['pr']}" if e["pr"] else "(unattributed)"
            out.append(f"  {pr:<8} {e['sha']}  {e['subject'][:58]}")
            for f in e["files"]:
                out.append(f"           {f['strategy']:<8} {f['path']}")
        out.append("")

    if r.get("ancestry_resolutions"):
        out.append(
            f"## Ancestry resolutions ({len(r['ancestry_resolutions'])})"
        )
        out.append("")
        out.append(
            "  Conflicts fixed by graph surgery — merging the rival PR's branch into"
        )
        out.append(
            "  this one so they stop colliding — rather than by editing files. These"
        )
        out.append(
            "  sit on the PR branches, not the first-parent path, and leave no textual"
        )
        out.append(
            "  trace, so they do not map onto KNOWN_CONFLICT_RESOLUTIONS at all."
        )
        out.append("")
        for e in r["ancestry_resolutions"][:top]:
            prs = ", ".join(f"#{p}" for p in e["prs"]) or "—"
            out.append(f"  {e['sha']}  {prs:<10} {e['subject'][:60]}")
        out.append("")

    if r["clusters"]:
        promotable = [c for c in r["clusters"] if len(c["commits"]) > 1]
        out.append(
            f"## Residue: {len(r['residue'])} commits in {len(r['clusters'])} clusters"
        )
        out.append("")
        out.append(
            "  All default to `private` and are published only if you opt each one in."
        )
        out.append("")
        for cl in sorted(r["clusters"], key=lambda c: -len(c["commits"]))[:top]:
            out.append(
                f"  [{cl['disposition']}] {len(cl['commits']):>2} commit(s), "
                f"{len(cl['files'])} file(s)"
            )
            out.append(f"       {cl['title'][:72]}")
        if len(r["clusters"]) > top:
            out.append(f"  … {len(r['clusters']) - top} more clusters")
        out.append("")
        out.append(
            f"  {len(promotable)} cluster(s) hold more than one commit — those are the"
        )
        out.append("  likeliest candidates for becoming real PRs.")
        out.append("")

    return "\n".join(out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Recover a profile from a build branch")
    ap.add_argument("command", choices=["analyze", "profile"])
    ap.add_argument("--branch", required=True)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--pr-index", default=DEFAULT_PR_INDEX)
    ap.add_argument("--name", default=None)
    ap.add_argument("--maintainer", default="")
    ap.add_argument("--out", default=None)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--no-harvest", action="store_true")
    args = ap.parse_args(argv)

    try:
        result = distill(
            args.repo, args.base, args.branch,
            pr_index_path=args.pr_index, harvest=not args.no_harvest,
        )
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    print(render(result, top=args.top))

    if args.command == "analyze":
        return 0

    name = args.name or re.sub(r"[^\w.-]+", "-", args.branch).strip("-").lower()
    out_dir = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "profiles"
    )
    os.makedirs(out_dir, exist_ok=True)

    prof_path = os.path.join(out_dir, f"{name}.json")
    prov_path = os.path.join(out_dir, f"{name}.provenance.json")
    with open(prof_path, "w", encoding="utf-8") as f:
        json.dump(to_profile(result, name, args.maintainer), f, indent=2,
                  ensure_ascii=False)
        f.write("\n")
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "schema": SCHEMA_VERSION,
                "branch": result["branch"],
                "base": result["base"],
                "attribution_rate": round(result["attribution_rate"], 4),
                "order_seq": result["order_seq"],
                "provenance": result["provenance"],
                "clusters": [
                    {
                        "title": c["title"],
                        "disposition": c["disposition"],
                        "files": c["files"],
                        "commits": [
                            {"sha": x["sha"][:12], "subject": x["subject"]}
                            for x in c["commits"]
                        ],
                    }
                    for c in result["clusters"]
                ],
                "resolutions": result["resolutions"],
            },
            f, indent=2, ensure_ascii=False,
        )
        f.write("\n")

    print(f"✅ {prof_path}")
    print(f"   {prov_path}")

    table = to_resolution_table(result)
    if table:
        print("\nCandidate KNOWN_CONFLICT_RESOLUTIONS entries:\n")
        print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
