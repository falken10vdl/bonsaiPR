#!/usr/bin/env python3
r"""
harness.py - Scoped local test rig for the bonsaiPR release/report pipeline.

Runs the REAL scripts (02_upload_to_falken10vdl.py, commit_reports.py) against a
throwaway GitHub repo, driven by a synthetic README report + fake addon zips, so
you can validate release-body / delta / reports changes WITHOUT cloning
IfcOpenShell or building Blender addons.

Isolation: everything executes inside a sandbox = a fresh clone of the test repo
with the automation scripts copied in. Because the real scripts derive paths
(REPORTS_DIR, index.json, the git repo they push) from __file__, running the
copies inside the sandbox means your real working tree at d:\...\bonsaiPR is
never touched. Report/build fixtures live OUTSIDE the sandbox so they never get
committed.

Prereqs: run with the rig venv's python (has requests + dotenv), and `gh` must be
authenticated (used for the token + cloning).

    RIG=$HOME/bonsaiPR_testrig
    "$RIG/.venv/Scripts/python.exe" harness.py all

Commands:
    all      setup -> run scenario 1 -> run scenario 2 (delta) -> verify -> push
    setup    (re)create the sandbox from the CURRENT automation scripts
    run N    single run of scenario N (1 or 2)
    verify   re-verify the last two releases
    clean    delete sandbox + fixtures (keeps the venv)

Config via env (defaults shown):
    TESTBED_OWNER = theoryshaw
    TESTBED_REPO  = bonsaiPR-testbed
    RIG_ROOT      = <this file's grandparent>/../bonsaiPR_testrig  or  $HOME/bonsaiPR_testrig
"""

import os
import re
import sys
import json
import time
import shutil
import zipfile
import subprocess
import datetime

import requests

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

OWNER = os.getenv("TESTBED_OWNER", "theoryshaw")
REPO = os.getenv("TESTBED_REPO", "bonsaiPR-testbed")

# The automation dir we are testing (this file lives in automation/test_local/).
SRC_AUTOMATION = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

RIG_ROOT = os.getenv(
    "RIG_ROOT", os.path.join(os.path.expanduser("~"), "bonsaiPR_testrig")
)
SANDBOX = os.path.join(RIG_ROOT, "sandbox")           # clone of the test repo
REPORTDATA = os.path.join(RIG_ROOT, "reportdata")     # -> REPORT_PATH
BUILDDATA = os.path.join(RIG_ROOT, "builddata")       # -> BUILD_BASE_DIR
STATE_FILE = os.path.join(RIG_ROOT, "last_run.json")  # remembers tags across cmds

SANDBOX_SCRIPTS = os.path.join(SANDBOX, "automation", "scripts")

API = f"https://api.github.com/repos/{OWNER}/{REPO}"

PLATFORMS = ["linux-x64", "windows-x64", "macos-x64", "macos-arm64"]


def _token():
    return subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()


def _child_env(**extra):
    """Base env for the automation subprocesses.

    Forces UTF-8 stdio so the scripts' emoji prints don't crash on a Windows
    cp1252 console (they run on a UTF-8 Linux host in production). This changes
    only I/O encoding, not behaviour.
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.update(extra)
    return env


def _gh_api(path):
    r = requests.get(
        f"{API}{path}",
        headers={
            "Authorization": f"token {_token()}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    return r


def _fmt(ok, msg):
    return f"  {'✓' if ok else '✗'} {msg}"


# --------------------------------------------------------------------------- #
# Version (must match 02_upload's get_version_info so find_report_file matches)
# --------------------------------------------------------------------------- #

def upstream_version():
    """Mirror 02_upload.get_version_info(): newest bonsai-X.Y.Z-alpha release."""
    try:
        resp = requests.get(
            "https://api.github.com/repos/IfcOpenShell/IfcOpenShell/releases",
            timeout=15,
        )
        if resp.ok:
            for rel in resp.json():
                m = re.match(r"bonsai-([\d.]+)-alpha", rel.get("tag_name", ""))
                if m:
                    return m.group(1)
    except Exception as e:
        print(f"  (version lookup failed, using 0.0.0: {e})")
    return "0.0.0"


# --------------------------------------------------------------------------- #
# Sandbox setup
# --------------------------------------------------------------------------- #

def cmd_setup():
    print(f"● Setup sandbox at {SANDBOX}")
    os.makedirs(RIG_ROOT, exist_ok=True)
    if os.path.isdir(os.path.join(SANDBOX, ".git")):
        print("  reusing existing clone (fetch + hard reset to origin)")
        subprocess.run(["git", "fetch", "origin"], cwd=SANDBOX, check=True,
                       capture_output=True)
        # Discard any leftover reports/index from a previous run.
        subprocess.run(["git", "reset", "--hard", "origin/HEAD"], cwd=SANDBOX,
                       capture_output=True)
        subprocess.run(["git", "clean", "-fdx"], cwd=SANDBOX, capture_output=True)
    else:
        shutil.rmtree(SANDBOX, ignore_errors=True)
        print("  cloning test repo ...")
        subprocess.run(["gh", "repo", "clone", f"{OWNER}/{REPO}", SANDBOX],
                       check=True, capture_output=True)
        # Identity for commits made inside the sandbox.
        subprocess.run(["git", "config", "user.name", "bonsaiPR-testrig"],
                       cwd=SANDBOX, check=True)
        subprocess.run(["git", "config", "user.email", "testrig@example.com"],
                       cwd=SANDBOX, check=True)

    # Copy the CURRENT automation scripts/config/src into the sandbox.
    dest_root = os.path.join(SANDBOX, "automation")
    for sub in ("scripts", "config", "src"):
        src = os.path.join(SRC_AUTOMATION, sub)
        dst = os.path.join(dest_root, sub)
        if not os.path.isdir(src):
            continue
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            if name.endswith(".py") or (sub == "config" and name.endswith(".py")):
                if ".tmp." in name:
                    continue
                shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
    reports = os.path.join(dest_root, "reports")
    os.makedirs(reports, exist_ok=True)
    # Clear prior state/event snapshots (the reset above restores whatever the
    # testbed had committed) so run 1 is a true baseline with no delta.
    for name in os.listdir(reports):
        if name.startswith(("state.", "events.")):
            os.remove(os.path.join(reports, name))
    print("  copied scripts/config/src into sandbox/automation")
    print(_fmt(True, "sandbox ready"))


# --------------------------------------------------------------------------- #
# Fixture generation
# --------------------------------------------------------------------------- #

def _pr(num, title, author, sha, reason=None):
    return {
        "number": num,
        "title": title,
        "author": author,
        "branch": f"pr-{num}-branch",
        "html_url": f"https://github.com/IfcOpenShell/IfcOpenShell/pull/{num}",
        "sha": sha,
        "reason": reason,
    }


def scenario(n):
    """Return (merged, failed_table, skipped_table) PR lists for scenario n.

    failed_table holds real failures + conflict-with-other-PRs; write_report()
    splits them into the report's '## ❌ Failed to Merge Against Base' and
    '## 🔀 Conflict With Other PRs' sections (by reason).
    skipped_table holds drafts (report's '## ⚠️ Skipped PRs' section).
    """
    R_REAL = "Fails to merge against base (problem with PR itself)"
    R_CONFLICT = "Merges cleanly against base (conflict with other PRs)"
    R_DRAFT = "PR is in DRAFT status"
    if n == 1:
        merged = [_pr(101, "Add wall tool", "alice", "aaaa111"),
                  _pr(102, "Fix door swing", "bob", "bbbb111"),
                  _pr(103, "Improve schedules", "carol", "cccc111")]
        failed = [_pr(201, "Break the build", "dave", "dddd111", R_REAL),
                  _pr(301, "Nice feature, bad timing", "erin", "eeee111", R_CONFLICT)]
        skipped = [_pr(401, "WIP experiment", "frank", "ffff111", R_DRAFT)]
    elif n == 2:
        merged = [_pr(101, "Add wall tool", "alice", "aaaa222"),   # new commit
                  _pr(102, "Fix door swing", "bob", "bbbb111"),     # unchanged
                  _pr(103, "Improve schedules", "carol", "cccc111"),
                  _pr(201, "Break the build", "dave", "dddd111"),   # recovered
                  _pr(104, "New pretty panel", "grace", "gggg111")] # new PR
        failed = []
        skipped = [_pr(401, "WIP experiment", "frank", "ffff111", R_DRAFT)]  # #301 dropped
    else:
        raise SystemExit(f"unknown scenario {n}")
    return merged, failed, skipped


UP = "IfcOpenShell/IfcOpenShell"


def _commit_cell(sha):
    return f"[{sha[:7]}](https://github.com/{UP}/commit/{sha})"


def write_report(path, version, ts10, merged, failed, skipped, order="ascending"):
    total = len(merged) + len(failed) + len(skipped)
    n_conflict = sum(1 for p in failed if "conflict with other PRs" in (p["reason"] or ""))
    n_realfail = len(failed) - n_conflict
    with open(path, "w", encoding="utf-8") as f:
        f.write("# BonsaiPR Weekly Build Report\n")
        f.write(f"Generated: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S} UTC\n")
        f.write("Branch: test-branch-does-not-exist\n")
        f.write("IfcOpenShell source commit: 0123456789abcdef0123456789abcdef01234567\n")
        f.write(f"Merge Order: {order} (lowest → highest PR#)\n")
        f.write(f"Fork Repository: https://github.com/{OWNER}/IfcOpenShell/tree/test-branch\n\n")
        f.write("## Summary\n")
        f.write(f"- Total PRs processed: {total}\n")
        f.write(f"- Successfully merged: {len(merged)}\n")
        f.write(f"- Failed to merge: {len(failed)}\n")
        f.write(f"- Skipped (draft/repo issues): {len(skipped)}\n\n")
        f.write(f"- Failed to Merge (conflicts with base v0.8.0): {n_realfail}\n")
        f.write(f"- Skipped (conflicts with other PRs): {n_conflict}\n")
        f.write("- Failed to Merge (unknown): 0\n")
        rate = round(100 * len(merged) / total, 1) if total else 0
        f.write(f"- Success Rate: {rate}%\n\n")

        # The single failed table was split in two (Reason column dropped): real
        # base failures vs PRs that merge cleanly but conflict with another PR.
        base_failed = [p for p in failed if "conflict with other PRs" not in (p["reason"] or "")]
        conflict_failed = [p for p in failed if "conflict with other PRs" in (p["reason"] or "")]
        if base_failed:
            f.write(f"## ❌ Failed to Merge Against Base ({len(base_failed)})\n\n")
            f.write("| PR | Title | Author | Branch | Last commit | First detected | Base commit | Broken by | Conflicting files |\n")
            f.write("|----|-------|--------|--------|-------------|----------------|-------------|-----------|--------------------|\n")
            for p in base_failed:
                f.write(f"| [#{p['number']}]({p['html_url']}) | {p['title']} | {p['author']} | "
                        f"{p['branch']} | {_commit_cell(p['sha'])} |  |  |  |  |\n")
            f.write("\n")
        if conflict_failed:
            f.write(f"## 🔀 Conflict With Other PRs ({len(conflict_failed)})\n\n")
            f.write("These PRs merge cleanly against the base on their own, but conflict with "
                    "another PR already merged in this release.\n\n")
            f.write("| PR | Title | Author | Branch | Last commit | First detected | Base commit |\n")
            f.write("|----|-------|--------|--------|-------------|----------------|-------------|\n")
            for p in conflict_failed:
                f.write(f"| [#{p['number']}]({p['html_url']}) | {p['title']} | {p['author']} | "
                        f"{p['branch']} | {_commit_cell(p['sha'])} |  |  |\n")
            f.write("\n")
        if skipped:
            f.write(f"## ⚠️ Skipped PRs ({len(skipped)})\n\n")
            f.write("| PR | Title | Author | Branch | Last commit | Reason |\n")
            f.write("|----|-------|--------|--------|-------------|--------|\n")
            for p in skipped:
                f.write(f"| [#{p['number']}]({p['html_url']}) | {p['title']} | {p['author']} | "
                        f"{p['branch']} | {_commit_cell(p['sha'])} | {p['reason']} |\n")
            f.write("\n")
        if merged:
            f.write(f"## ✅ Successfully Merged PRs ({len(merged)})\n\n")
            f.write("| PR | Title | Author | Branch | Created | Last commit |\n")
            f.write("|----|-------|--------|--------|---------|-------------|\n")
            for p in merged:
                f.write(f"| [#{p['number']}]({p['html_url']}) | {p['title']} | {p['author']} | "
                        f"{p['branch']} | 2026-07-01 | {_commit_cell(p['sha'])} |\n")
            f.write("\n")


def make_fixtures(n, version, ts10, ts6):
    # Fresh report (single file so find_report_file is unambiguous).
    shutil.rmtree(REPORTDATA, ignore_errors=True)
    os.makedirs(REPORTDATA, exist_ok=True)
    report = os.path.join(REPORTDATA, f"README-bonsaiPR_py311-{version}-alpha{ts10}.txt")
    merged, failed, skipped = scenario(n)
    write_report(report, version, ts10, merged, failed, skipped)

    # Fresh fake addon zips (02_upload deletes BUILD_BASE_DIR at the end).
    dist = os.path.join(BUILDDATA, "src", "bonsaiPR", "dist")
    shutil.rmtree(BUILDDATA, ignore_errors=True)
    os.makedirs(dist, exist_ok=True)
    for plat in PLATFORMS:
        z = os.path.join(dist, f"bonsaiPR_py311-{version}-alpha{ts6}-{plat}.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("bonsaiPR/__init__.py", "# fake addon for testrig\n")
    return report


# --------------------------------------------------------------------------- #
# Run one scenario through the real 02_upload
# --------------------------------------------------------------------------- #

def _save_state(d):
    with open(STATE_FILE, "w") as f:
        json.dump(d, f, indent=2)


def _load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def cmd_run(n):
    n = int(n)
    version = upstream_version()
    now = datetime.datetime.now()
    # Distinct timestamp per scenario -> distinct tag/release.
    ts10 = (now + datetime.timedelta(minutes=n)).strftime("%y%m%d%H%M")
    ts6 = ts10[:6]
    tag = f"v{version}-alpha{ts10}"
    print(f"● Run scenario {n}  (version {version}, tag {tag})")

    report = make_fixtures(n, version, ts10, ts6)
    print(f"  report:  {os.path.basename(report)}")

    env = _child_env(
        GITHUB_TOKEN=_token(),
        GITHUB_OWNER=OWNER,
        GITHUB_REPO=REPO,
        FORK_OWNER=OWNER,          # branch-commit API 404s -> 'unknown', fine
        FORK_REPO="IfcOpenShell",
        REPORT_PATH=REPORTDATA,
        BUILD_BASE_DIR=BUILDDATA,
    )
    script = os.path.join(SANDBOX_SCRIPTS, "02_upload_to_falken10vdl.py")
    proc = subprocess.run([sys.executable, script], cwd=SANDBOX_SCRIPTS, env=env,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    tail = "\n".join(proc.stdout.splitlines()[-12:])
    print("  --- 02_upload tail ---")
    for line in tail.splitlines():
        print(f"    {line}")
    if proc.returncode != 0:
        print("  --- stderr ---")
        for line in proc.stderr.splitlines()[-12:]:
            print(f"    {line}")

    st = _load_state()
    st[f"scenario{n}"] = {"tag": tag, "version": version,
                          "report": os.path.basename(report)}
    _save_state(st)
    print(_fmt(proc.returncode == 0, f"02_upload exit {proc.returncode}"))
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Verify a release body via the GitHub API
# --------------------------------------------------------------------------- #

def verify_release(tag, expect_delta, expect_failed=None, expect_conflict=None):
    print(f"● Verify release {tag}  (expect delta: {expect_delta})")
    r = _gh_api(f"/releases/tags/{tag}")
    if r.status_code != 200:
        print(_fmt(False, f"release not found ({r.status_code})"))
        return False
    rel = r.json()
    body = rel.get("body", "")
    assets = [a["name"] for a in rel.get("assets", [])]
    readme_asset = next((a for a in assets if a.startswith("README-bonsaiPR")), None)

    checks = []
    checks.append(("body has '📄 Full per-PR breakdown'",
                   "📄 Full per-PR breakdown" in body))
    # These two counts come from 02_upload parsing the split failed/conflict
    # tables in the report — they go to 0 if the section parser breaks.
    if expect_failed is not None:
        checks.append((f"Build Statistics: Failed PRs = {expect_failed}",
                       f"- **Failed PRs**: {expect_failed}\n" in body))
    if expect_conflict is not None:
        checks.append(
            (f"Build Statistics: Skipped (conflict w/ other PRs) = {expect_conflict}",
             f"- **Skipped (conflict with other PRs)**: {expect_conflict}\n" in body))
    checks.append(("body no longer contains the big merged TABLE header",
                   "| PR | Branch | Title | Author | Last commit |" not in body))
    checks.append(("README asset uploaded", readme_asset is not None))
    if readme_asset:
        checks.append(("body links the README asset by name", readme_asset in body))
    checks.append(("body links the in-repo markdown report",
                   f"automation/reports/archive/{tag}.md" in body))
    checks.append((f"body under GitHub limit ({len(body)} < 125000)",
                   len(body) < 125000))
    checks.append(("delta section present" if expect_delta
                   else "no delta section (first run)",
                   ("🔁 Changes since last build" in body) == expect_delta))

    # The README asset URL resolves anonymously (public repo).
    if readme_asset:
        url = f"https://github.com/{OWNER}/{REPO}/releases/download/{tag}/{readme_asset}"
        code = requests.get(url, timeout=30, allow_redirects=True).status_code
        checks.append((f"README asset URL resolves ({code})", code == 200))

    for label, ok in checks:
        print(_fmt(ok, label))
    return all(ok for _, ok in checks)


def cmd_verify():
    st = _load_state()
    ok = True
    if "scenario1" in st:
        ok &= verify_release(st["scenario1"]["tag"], expect_delta=False,
                             expect_failed=1, expect_conflict=1)
    if "scenario2" in st:
        ok &= verify_release(st["scenario2"]["tag"], expect_delta=True,
                             expect_failed=0, expect_conflict=0)
    return ok


# --------------------------------------------------------------------------- #
# Commit + push the state snapshots via the real commit_reports.py
# --------------------------------------------------------------------------- #

def cmd_push():
    print("● Commit + push state snapshots (commit_reports.py, push enabled)")
    env = _child_env(BONSAIPR_REPORTS_PUSH="1", BONSAIPR_REPORTS_REMOTE="origin")
    script = os.path.join(SANDBOX_SCRIPTS, "commit_reports.py")
    proc = subprocess.run([sys.executable, script], cwd=SANDBOX_SCRIPTS, env=env,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    for line in proc.stdout.splitlines():
        print(f"    {line}")
    if proc.returncode != 0:
        for line in proc.stderr.splitlines()[-10:]:
            print(f"    {line}")

    # Confirm the snapshot landed on the remote default branch.
    r = _gh_api("/contents/automation/reports/state.asc.json")
    landed = r.status_code == 200
    print(_fmt(landed, f"state.asc.json present on {OWNER}/{REPO} ({r.status_code})"))
    return proc.returncode == 0 and landed


# --------------------------------------------------------------------------- #

def verify_repo_report(tag):
    """After push: the in-repo markdown report for `tag` exists and resolves."""
    path = f"automation/reports/archive/{tag}.md"
    r = _gh_api(f"/contents/{path}")
    api_ok = r.status_code == 200
    url = f"https://github.com/{OWNER}/{REPO}/blob/main/{path}"
    code = requests.get(url, timeout=30).status_code
    print(_fmt(api_ok, f"in-repo report present: {path} ({r.status_code})"))
    print(_fmt(code == 200, f"blob URL resolves in browser ({code})"))
    return api_ok and code == 200


def cmd_clean():
    for p in (SANDBOX, REPORTDATA, BUILDDATA, STATE_FILE):
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)
    print(_fmt(True, "sandbox + fixtures removed (venv kept)"))


def cmd_all():
    cmd_setup()
    ok1 = cmd_run(1)
    v1 = verify_release(_load_state()["scenario1"]["tag"], expect_delta=False,
                        expect_failed=1, expect_conflict=1)
    ok2 = cmd_run(2)
    v2 = verify_release(_load_state()["scenario2"]["tag"], expect_delta=True,
                        expect_failed=0, expect_conflict=0)
    push_ok = cmd_push()
    st = _load_state()
    print("● Verify in-repo markdown reports resolve (after push)")
    repo1 = verify_repo_report(st["scenario1"]["tag"])
    repo2 = verify_repo_report(st["scenario2"]["tag"])
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(_fmt(ok1 and v1, "scenario 1 (baseline release, no delta)"))
    print(_fmt(ok2 and v2, "scenario 2 (delta release)"))
    print(_fmt(push_ok, "reports committed + pushed to testbed"))
    print(_fmt(repo1 and repo2, "in-repo markdown reports resolve"))
    allok = ok1 and v1 and ok2 and v2 and push_ok and repo1 and repo2
    print(_fmt(allok, "OVERALL"))
    print("=" * 60)
    print(f"\nReleases: https://github.com/{OWNER}/{REPO}/releases")
    return allok


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cmd = argv[0] if argv else "all"
    if cmd == "all":
        return 0 if cmd_all() else 1
    if cmd == "setup":
        cmd_setup(); return 0
    if cmd == "run":
        return 0 if cmd_run(argv[1]) else 1
    if cmd == "verify":
        return 0 if cmd_verify() else 1
    if cmd == "push":
        return 0 if cmd_push() else 1
    if cmd == "clean":
        cmd_clean(); return 0
    print(f"unknown command: {cmd}\n{__doc__}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
