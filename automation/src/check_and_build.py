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
    
    logging.info("🚀 Starting full build process...")
    
    try:
        result = subprocess.run(
            [sys.executable, main_script],
            cwd=os.path.dirname(__file__),
            timeout=7200  # 2 hour timeout for full build
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logging.error("⏰ Full build timed out after 2 hours")
        return False
    except Exception as e:
        logging.error(f"💥 Error during build: {e}")
        return False

def main():
    """Main check-and-build orchestration"""

    start_time = datetime.datetime.now()
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
