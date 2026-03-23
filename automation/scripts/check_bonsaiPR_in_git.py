#!/usr/bin/env python3
"""
check_bonsaiPR_in_git.py - Pull latest bonsaiPR code from GitHub

This script ensures the local bonsaiPR repository (the one used by cron jobs)
is up to date with the remote GitHub repository. Run it before each build so
that any commits pushed to falken10vdl/bonsaiPR are reflected locally.

Usage:
    python3 check_bonsaiPR_in_git.py

Exit codes:
    0 - Success (repo is up to date or was updated)
    1 - Error (pull failed or repo not found)
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
BONSAI_PR_REPO_DIR = os.getenv(
    "BONSAI_PR_REPO_DIR",
    "/home/falken10vdl/bonsaiPRDevel/bonsaiPR"
)
REMOTE = "origin"
BRANCH = os.getenv("BONSAI_PR_BRANCH", "main")

# ── Logging ───────────────────────────────────────────────────────────────────
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"check_bonsaiPR_in_git_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    logging.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        logging.info(result.stdout.strip())
    if result.stderr.strip():
        # git often writes progress to stderr; treat as info unless returncode != 0
        level = logging.ERROR if result.returncode != 0 else logging.INFO
        logging.log(level, result.stderr.strip())
    return result


def check_repo_exists(repo_dir: str) -> bool:
    git_dir = Path(repo_dir) / ".git"
    if not git_dir.exists():
        logging.error(f"No git repository found at: {repo_dir}")
        return False
    return True


def get_current_commit(repo_dir: str) -> str:
    result = run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    return result.stdout.strip() if result.returncode == 0 else ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.info("=" * 60)
    logging.info("BonsaiPR Git Sync - Pulling latest code from GitHub")
    logging.info(f"Repository : {BONSAI_PR_REPO_DIR}")
    logging.info(f"Remote     : {REMOTE}")
    logging.info(f"Branch     : {BRANCH}")
    logging.info("=" * 60)

    if not check_repo_exists(BONSAI_PR_REPO_DIR):
        return 1

    commit_before = get_current_commit(BONSAI_PR_REPO_DIR)
    logging.info(f"Current HEAD : {commit_before}")

    # Fetch from remote
    fetch = run(["git", "fetch", REMOTE], cwd=BONSAI_PR_REPO_DIR)
    if fetch.returncode != 0:
        logging.error("git fetch failed — check network connectivity and credentials.")
        return 1

    # Check whether local branch is behind remote
    behind = run(
        ["git", "rev-list", "--count", f"HEAD..{REMOTE}/{BRANCH}"],
        cwd=BONSAI_PR_REPO_DIR,
    )
    if behind.returncode != 0:
        logging.error("Could not determine commit distance from remote.")
        return 1

    commits_behind = int(behind.stdout.strip() or "0")

    if commits_behind == 0:
        logging.info("✅ Already up to date — no pull needed.")
        return 0

    logging.info(f"📥 {commits_behind} new commit(s) available — pulling...")

    # Rebase local commits on top of the remote ones (keeps linear history)
    pull = run(
        ["git", "pull", "--rebase", REMOTE, BRANCH],
        cwd=BONSAI_PR_REPO_DIR,
    )
    if pull.returncode != 0:
        logging.error("git pull --rebase failed.")
        logging.error("Resolve any conflicts manually, then re-run this script.")
        return 1

    commit_after = get_current_commit(BONSAI_PR_REPO_DIR)
    logging.info(f"✅ Pull successful.")
    logging.info(f"   Before : {commit_before}")
    logging.info(f"   After  : {commit_after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
