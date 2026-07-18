#!/usr/bin/env python3
"""
commit_reports.py - Commit (and optionally push) the per-order PR state snapshots.

The build writes automation/reports/state.<order>.json and events.<order>.jsonl
each run. Committing them is what turns git history into the durable run-to-run
diff record that pr_state.py's endpoint/series deltas read from
(`git show <commit>:automation/reports/state.asc.json`, etc.).

Run this AFTER a successful build. It is a no-op when nothing changed, so it is
safe to call unconditionally from the cron chain.

Pushing is OPT-IN: it only pushes when BONSAIPR_REPORTS_PUSH=1, to the remote
and branch given by BONSAIPR_REPORTS_REMOTE (default 'origin') and
BONSAIPR_REPORTS_BRANCH (default: current branch). This keeps an automated push
from happening unless the operator has explicitly turned it on.

Env:
    BONSAIPR_REPORTS_PUSH     "1" to push after committing (default: off)
    BONSAIPR_REPORTS_REMOTE   remote name (default: origin)
    BONSAIPR_REPORTS_BRANCH   branch to push (default: current HEAD branch)

Exit codes: 0 = committed or nothing-to-commit; 1 = a git step failed.
"""

import os
import sys
import json
import glob
import subprocess

# automation/reports, relative to this script (automation/scripts).
REPORTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
)
# Path git should stage — repo-relative is safer, but `git add <abs>` works too.
REPORTS_PATHSPEC = REPORTS_DIR


def _git(args, check=False):
    """Run git from the repo containing REPORTS_DIR. Returns (rc, stdout)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=REPORTS_DIR,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.returncode != 0 and result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise SystemExit(1)
    return result.returncode, result.stdout


def _summary_line():
    """Build a compact commit subject from the latest asc snapshot's counts."""
    asc = os.path.join(REPORTS_DIR, "state.asc.json")
    try:
        with open(asc, "r", encoding="utf-8") as f:
            counts = json.load(f).get("counts", {})
        return (
            f"reports: build state "
            f"({counts.get('merged', '?')} merged, "
            f"{counts.get('failed', '?')} failed, "
            f"{counts.get('skipped_conflict', '?')} skip-conflict)"
        )
    except Exception:
        return "reports: update build state snapshots"


def main():
    # The cron host is UTF-8, but a Windows console defaults to cp1252 and would
    # crash (and wrongly exit non-zero) on emoji in output. Force UTF-8 stdout.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    if not os.path.isdir(REPORTS_DIR):
        print(f"ℹ️ No reports dir yet ({REPORTS_DIR}); nothing to commit.")
        return 0

    if not glob.glob(os.path.join(REPORTS_DIR, "*.json")) and not glob.glob(
        os.path.join(REPORTS_DIR, "*.jsonl")
    ):
        print("ℹ️ No snapshot/event files present; nothing to commit.")
        return 0

    # Stage only the reports dir.
    _git(["add", "--", REPORTS_PATHSPEC], check=True)

    # Anything staged? `git diff --cached --quiet` exits 1 when there are changes.
    rc, _ = _git(["diff", "--cached", "--quiet"])
    if rc == 0:
        print("ℹ️ Reports unchanged since last commit; nothing to do.")
        return 0

    subject = _summary_line()
    rc, _ = _git(["commit", "-m", subject])
    if rc != 0:
        print("❌ git commit failed.", file=sys.stderr)
        return 1
    print(f"✅ Committed reports: {subject}")

    if os.getenv("BONSAIPR_REPORTS_PUSH") == "1":
        remote = os.getenv("BONSAIPR_REPORTS_REMOTE", "origin")
        branch = os.getenv("BONSAIPR_REPORTS_BRANCH")
        if not branch:
            _rc, out = _git(["rev-parse", "--abbrev-ref", "HEAD"])
            branch = out.strip() or "HEAD"
        print(f"⬆️ Pushing reports to {remote}/{branch} ...")
        rc, _ = _git(["push", remote, f"HEAD:{branch}"])
        if rc != 0:
            print("❌ git push failed.", file=sys.stderr)
            return 1
        print("✅ Pushed.")
    else:
        print("ℹ️ Push disabled (set BONSAIPR_REPORTS_PUSH=1 to enable).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
