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

def check_for_skipped_conflict_prs(report_path):
    """Check if the report contains PRs skipped due to conflicts with other PRs"""
    if not os.path.exists(report_path):
        logging.warning(f"⚠️ Report file not found: {report_path}")
        return False
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the count line indicating conflicts with other PRs
        # Format: "- Skipped (conflicts with other PRs): X"
        import re
        match = re.search(r'- Skipped \(conflicts with other PRs\):\s+(\d+)', content)
        if match:
            count = int(match.group(1))
            if count > 0:
                logging.info(f"📊 Found {count} PR(s) skipped due to conflicts with other PRs")
                return True
        
        return False
    except Exception as e:
        logging.error(f"❌ Error checking report: {e}")
        return False

def get_latest_report_path():
    """Get the path to the most recently generated report file"""
    report_dir = os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")
    import glob
    report_files = sorted(glob.glob(os.path.join(report_dir, "README-bonsaiPR_*.txt")), 
                         key=os.path.getmtime, reverse=True)
    if report_files:
        return report_files[0]
    return None

def extract_pr_numbers_from_section(report_path, section_title):
    """Extract PR numbers from a specific section of the report
    
    Args:
        report_path: Path to the report file
        section_title: Title of the section (e.g., '## ❌ Failed to Merge PRs')
    
    Returns:
        Set of PR numbers found in that section
    """
    if not os.path.exists(report_path):
        return set()
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        pr_numbers = set()
        
        # Find the section
        lines = content.split('\n')
        in_section = False
        
        for line in lines:
            # Check if we've entered the target section
            if section_title in line:
                in_section = True
                continue
            
            # Check if we've entered a new section (stop reading)
            if in_section and line.startswith('##'):
                break
            
            # Extract PR numbers from lines in the section
            if in_section:
                # Match patterns like "- **PR #123**:" or "**PR #123**:"
                match = re.search(r'\*\*PR #(\d+)\*\*', line)
                if match:
                    pr_numbers.add(int(match.group(1)))
        
        return pr_numbers
    except Exception as e:
        logging.error(f"❌ Error extracting PR numbers: {e}")
        return set()

def get_skipped_conflict_prs(report_path):
    """Get the list of PR numbers that were skipped due to conflicts with other PRs"""
    return extract_pr_numbers_from_section(report_path, '## ❌ Failed to Merge PRs')

def get_successfully_merged_prs(report_path):
    """Get the list of PR numbers that were successfully merged"""
    return extract_pr_numbers_from_section(report_path, '## ✅ Successfully Merged PRs')

def run_script(script_name, description, args=None):
    """Run an automation script with error handling"""
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    script_path = os.path.join(scripts_dir, script_name)
    
    if not os.path.exists(script_path):
        logging.error(f"❌ Script not found: {script_path}")
        return False
    
    logging.info(f"🚀 Starting: {description}")
    logging.info(f"📄 Script: {script_name}")
    
    try:
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        result = subprocess.run(
            cmd,
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

    # Cleanup old README-bonsaiPR_*.txt files: keep only last 5
    # Use the same default as 00_clone_merge_and_create_branch.py
    report_dir = os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")
    readme_files = sorted(glob.glob(os.path.join(report_dir, "README-bonsaiPR_*.txt")), key=os.path.getmtime, reverse=True)
    for old_readme in readme_files[5:]:
        try:
            os.remove(old_readme)
            logging.info(f"Removed old README: {old_readme}")
        except Exception as e:
            logging.warning(f"Could not remove README {old_readme}: {e}")

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
    
    # Check if we should retry with reversed PR order
    if success_count == total_steps:
        report_path = get_latest_report_path()
        if report_path and check_for_skipped_conflict_prs(report_path):
            logging.info("\n" + "=" * 60)
            logging.info("🔄 RETRY WITH REVERSED PR ORDER")
            logging.info("Found PRs skipped due to conflicts with other PRs.")
            logging.info("Retrying with newer PRs first to maximize inclusion.")
            logging.info("=" * 60)
            
            # Get the PRs that were skipped in the first build
            skipped_prs_first_build = get_skipped_conflict_prs(report_path)
            logging.info(f"📋 First build had {len(skipped_prs_first_build)} PR(s) skipped due to conflicts: {sorted(skipped_prs_first_build)}")
            
            # Step 1: Run merge with reversed order
            logging.info(f"\n📋 Retry Step 1/3: Clone repository and merge PRs (REVERSED ORDER)")
            if run_script('00_clone_merge_and_create_branch.py', 
                         'Clone repository and merge PRs (REVERSED ORDER)', 
                         ['--reverse']):
                
                # Get the new report and check if any previously skipped PRs are now merged
                retry_report_path = get_latest_report_path()
                if retry_report_path:
                    merged_prs_retry = get_successfully_merged_prs(retry_report_path)
                    
                    # Find PRs that were skipped in first build but merged in retry
                    newly_merged_prs = skipped_prs_first_build.intersection(merged_prs_retry)
                    
                    if newly_merged_prs:
                        logging.info(f"\n✨ SUCCESS! Retry merged {len(newly_merged_prs)} PR(s) that were previously skipped:")
                        for pr_num in sorted(newly_merged_prs):
                            logging.info(f"   • PR #{pr_num}")
                        logging.info("\n🚀 Continuing with build and release for retry...")
                        
                        # Continue with build and upload since we have newly merged PRs
                        retry_success_count = 1  # Already completed step 1
                        retry_steps = [
                            {
                                'script': '01_build_bonsaiPR_addons.py',
                                'description': 'Build BonsaiPR addons for multiple platforms (RETRY)',
                                'args': None,
                                'required': True
                            },
                            {
                                'script': '02_upload_to_falken10vdl.py',
                                'description': 'Create GitHub release (RETRY)',
                                'args': None,
                                'required': True
                            }
                        ]
                        
                        for i, step in enumerate(retry_steps, 2):  # Start at 2 since step 1 is done
                            logging.info(f"\n📋 Retry Step {i}/3: {step['description']}")
                            
                            if run_script(step['script'], step['description'], step.get('args')):
                                retry_success_count += 1
                            elif step['required']:
                                logging.error(f"💔 Required retry step failed, stopping retry")
                                break
                            else:
                                logging.warning(f"⚠️ Optional retry step failed, continuing")
                        
                        if retry_success_count == 3:
                            logging.info("\n🎉 Retry completed successfully! Generated additional release.")
                            logging.info(f"   New PRs included: {sorted(newly_merged_prs)}")
                        else:
                            logging.warning("\n⚠️ Retry partially completed")
                    else:
                        logging.info(f"\n⏭️  RETRY SKIPPED: No previously skipped PRs were merged in retry.")
                        logging.info("   The reversed order didn't help include more PRs.")
                        logging.info("   Second release not needed - would be identical or worse.")
                else:
                    logging.error("❌ Could not find retry report path")
            else:
                logging.error("❌ Retry merge step failed")
    
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