#!/usr/bin/env python3
"""
main.py - BonsaiPR On-Demand Automation Orchestrator

This script orchestrates the complete automation process for BonsaiPR builds.
It coordinates all automation scripts and provides comprehensive logging.
Designed to run on-demand when PR changes are detected.

Author: BonsaiPR Automation System
Date: 2025-12-14
"""

import os
import sys
import subprocess
import datetime
import logging
from pathlib import Path

# Add the config directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

try:
    from settings import *
except ImportError:
    print("⚠️ Warning: settings.py not found, using default configuration")
    # Default settings
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_OWNER = os.getenv('GITHUB_OWNER', 'falken10vdl')
    GITHUB_REPO = os.getenv('GITHUB_REPO', 'BonsaiPR')

def setup_logging():
    """Set up comprehensive logging for automation"""
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f'automation_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

def run_script(script_name, description):
    """Run an automation script with error handling"""
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    script_path = os.path.join(scripts_dir, script_name)
    
    if not os.path.exists(script_path):
        logging.error(f"❌ Script not found: {script_path}")
        return False
    
    logging.info(f"🚀 Starting: {description}")
    logging.info(f"📄 Script: {script_name}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=scripts_dir,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logging.info(f"✅ Completed successfully: {description}")
            if result.stdout:
                logging.info(f"Output: {result.stdout}")
            return True
        else:
            logging.error(f"❌ Failed: {description}")
            logging.error(f"Exit code: {result.returncode}")
            if result.stderr:
                logging.error(f"Error: {result.stderr}")
            if result.stdout:
                logging.info(f"Output: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error(f"⏰ Timeout: {description} exceeded 1 hour")
        return False
    except Exception as e:
        logging.error(f"💥 Exception in {description}: {e}")
        return False

def main():
    """Main automation orchestration"""

    start_time = datetime.datetime.now()
    log_file = setup_logging()

    # Cleanup old automation logs: keep only last 5
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    import glob
    log_files = sorted(glob.glob(os.path.join(logs_dir, "automation_*.log")), key=os.path.getmtime, reverse=True)
    for old_log in log_files[5:]:
        try:
            os.remove(old_log)
            logging.info(f"Removed old log: {old_log}")
        except Exception as e:
            logging.warning(f"Could not remove log {old_log}: {e}")

    logging.info("=" * 60)
    logging.info("🤖 BonsaiPR On-Demand Automation System")
    logging.info(f"📅 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logging.info(f"📝 Log file: {log_file}")
    logging.info("=" * 60)
    
    # Define automation steps
    automation_steps = [
        {
            'script': '00_clone_merge_and_create_branch.py',
            'description': 'Clone repository and merge PRs with draft detection',
            'required': True
        },
        {
            'script': '01_build_bonsaiPR_addons.py',
            'description': 'Build BonsaiPR addons for multiple platforms',
            'required': True
        },
        {
            'script': '02_upload_to_falken10vdl.py',
            'description': 'Create GitHub release with enhanced PR documentation',
            'required': True
        }
    ]
    
    # Execute automation steps
    success_count = 0
    total_steps = len(automation_steps)
    
    for i, step in enumerate(automation_steps, 1):
        logging.info(f"\n📋 Step {i}/{total_steps}: {step['description']}")
        
        if run_script(step['script'], step['description']):
            success_count += 1
        elif step['required']:
            logging.error(f"💔 Required step failed, stopping automation")
            break
        else:
            logging.warning(f"⚠️ Optional step failed, continuing")
    
    # Final summary
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    
    logging.info("\n" + "=" * 60)
    logging.info("📊 AUTOMATION SUMMARY")
    logging.info(f"⏱️  Duration: {duration}")
    logging.info(f"✅ Successful steps: {success_count}/{total_steps}")
    logging.info(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if success_count == total_steps:
        logging.info("🎉 All automation steps completed successfully!")
        return 0
    else:
        logging.error("❌ Some automation steps failed")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logging.error("\n⛔ Automation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"\n💥 Unexpected error: {e}")
        sys.exit(1)