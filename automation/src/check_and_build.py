#!/usr/bin/env python3
"""
check_and_build.py - Smart Build Orchestrator

This script first checks if there are PR changes, and only triggers the full
build process if changes are detected. This allows hourly cron jobs without
unnecessary builds.

Usage:
    python check_and_build.py [--force]
    
Options:
    --force    Force a build even if no changes detected
"""

import os
import sys
import subprocess
import datetime
import logging
from pathlib import Path


DEFAULT_FULL_BUILD_TIMEOUT_SECONDS = 21600  # 6 hours


def get_full_build_timeout_seconds():
    """Return full-build timeout from env, with validation and safe fallback."""
    raw = os.getenv("BONSAIPR_FULL_BUILD_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_FULL_BUILD_TIMEOUT_SECONDS

    try:
        timeout = int(raw)
        if timeout <= 0:
            raise ValueError("timeout must be > 0")
        return timeout
    except ValueError:
        logging.warning(
            "Invalid BONSAIPR_FULL_BUILD_TIMEOUT_SECONDS=%r; using default %s seconds",
            raw,
            DEFAULT_FULL_BUILD_TIMEOUT_SECONDS,
        )
        return DEFAULT_FULL_BUILD_TIMEOUT_SECONDS

def setup_logging():
    """Set up logging for the check-and-build process"""
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f'check_build_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

def check_for_changes():
    """Run the PR change detection script"""
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    check_script = os.path.join(scripts_dir, 'check_pr_changes.py')
    
    logging.info("🔍 Checking for PR changes...")
    
    try:
        result = subprocess.run(
            [sys.executable, check_script],
            cwd=scripts_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for check
        )
        
        # Print output
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    logging.info(f"   {line}")
        
        # Exit code 0 means changes detected, 1 means no changes
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logging.error("⏰ Change detection timed out")
        return False
    except Exception as e:
        logging.error(f"💥 Error checking for changes: {e}")
        return False

def run_full_build():
    """Run the complete build automation"""
    main_script = os.path.join(os.path.dirname(__file__), 'main.py')
    timeout_seconds = get_full_build_timeout_seconds()
    timeout_hours = timeout_seconds / 3600

    logging.info("🚀 Starting full build process...")
    logging.info(
        "⏱️ Full build timeout: %.2f hours (%s seconds)",
        timeout_hours,
        timeout_seconds,
    )

    try:
        result = subprocess.run(
            [sys.executable, main_script],
            cwd=os.path.dirname(__file__),
            timeout=timeout_seconds,
        )

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        logging.error(
            "⏰ Full build timed out after %.2f hours (%s seconds)",
            timeout_hours,
            timeout_seconds,
        )
        return False
    except Exception as e:
        logging.error(f"💥 Error during build: {e}")
        return False

def commit_reports():
    """Commit (and optionally push) the per-order PR state snapshots.

    Automation runs should publish updated reports by default so the repo-hosted
    markdown/archive links produced during upload resolve on GitHub. Operators
    can still opt out by exporting BONSAIPR_REPORTS_PUSH=0.

    Failures here are logged but never fail the build.
    """
    commit_script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'commit_reports.py')

    logging.info("🗂️  Committing PR state snapshots...")

    try:
        env = os.environ.copy()
        env.setdefault('BONSAIPR_REPORTS_PUSH', '1')
        result = subprocess.run(
            [sys.executable, commit_script],
            cwd=os.path.join(os.path.dirname(__file__), '..', 'scripts'),
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5 minute timeout
        )
        for stream in (result.stdout, result.stderr):
            if stream:
                for line in stream.split('\n'):
                    if line.strip():
                        logging.info(f"   {line}")
        return result.returncode == 0
    except Exception as e:
        logging.warning(f"⚠️ Could not commit reports: {e}")
        return False

MIN_FREE_GB = 1.5  # Require at least 1.5 GB free before starting a build

def check_disk_space(path='/'):
    """Return (free_gb, ok) – ok is False when free space is below MIN_FREE_GB."""
    stat = os.statvfs(path)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    return free_gb, free_gb >= MIN_FREE_GB

def main():
    """Main check-and-build orchestration"""

    start_time = datetime.datetime.now()

    # --- Disk space pre-flight check (before we even try to write a log) ---
    check_path = os.path.expanduser('~')
    free_gb, space_ok = check_disk_space(check_path)
    if not space_ok:
        msg = (
            f"FATAL: Only {free_gb:.2f} GB free on {check_path}. "
            f"At least {MIN_FREE_GB:.1f} GB is required for a build.\n"
            "Free up space (old bonsaiPR-build dir, stale logs, README reports) "
            "then retry."
        )
        print(msg, file=sys.stderr)
        sys.exit(1)

    log_file = setup_logging()

    # Cleanup old check_build logs: keep only last 5
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    import glob
    log_files = sorted(glob.glob(os.path.join(logs_dir, "check_build_*.log")), key=os.path.getmtime, reverse=True)
    for old_log in log_files[5:]:
        try:
            os.remove(old_log)
            logging.info(f"Removed old log: {old_log}")
        except Exception as e:
            logging.warning(f"Could not remove log {old_log}: {e}")

    logging.info("=" * 70)
    logging.info("🤖 BonsaiPR Smart Build System - Check and Build")
    logging.info(f"⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"📝 Log file: {log_file}")
    logging.info("=" * 70)
    
    # Check for --force flag
    force_build = '--force' in sys.argv
    if force_build:
        logging.info("⚡ FORCED BUILD MODE - Skipping change detection")
        changes_detected = True
    else:
        # Check for PR changes
        changes_detected = check_for_changes()
    
    if not changes_detected:
        logging.info("\n" + "=" * 70)
        logging.info("✅ NO CHANGES DETECTED - Build skipped")
        logging.info("💡 No new PRs or updates since last check")
        logging.info("⏭️  Will check again on next scheduled run")
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logging.info(f"⏱️  Check duration: {duration}")
        logging.info("=" * 70)
        return 0
    
    # Changes detected, run full build
    logging.info("\n" + "=" * 70)
    logging.info("✨ CHANGES DETECTED - Proceeding with build")
    logging.info("=" * 70)
    
    build_success = run_full_build()
    
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    
    logging.info("\n" + "=" * 70)
    logging.info("📊 SMART BUILD SUMMARY")
    logging.info(f"⏱️  Total duration: {duration}")
    logging.info(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if build_success:
        logging.info("🎉 Build completed successfully!")
        # Persist the per-order state snapshots so git history becomes the
        # run-to-run diff record. Never fails the build.
        commit_reports()
        logging.info("=" * 70)
        return 0
    else:
        logging.error("❌ Build failed")
        logging.info("=" * 70)
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logging.error("\n⛔ Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
