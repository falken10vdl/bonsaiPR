import subprocess
import os
import sys
from datetime import datetime
from config.settings import Settings

def run_script(script_name):
    """Run a script using subprocess."""
    try:
        print(f"Starting execution of {script_name} at {datetime.now()}")
        subprocess.run(['python3', script_name], check=True)
        print(f"Successfully executed {script_name} at {datetime.now()}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing {script_name}: {e}")
        raise  # Re-raise to stop execution if a script fails

def setup_logging():
    """Ensure logs directory exists."""
    settings = Settings()
    logs_dir = settings.logs_dir
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    return logs_dir

def run_scripts_sequentially():
    """Run the automation scripts in sequence."""
    # Setup logging
    logs_dir = setup_logging()
    
    # Use settings to get the script list
    settings = Settings()
    scripts = settings.get_scripts()
    
    print(f"Starting weekly BonsaiPR automation at {datetime.now()}")
    print(f"Logs directory: {logs_dir}")
    print(f"Scripts to execute: {len(scripts)}")
    
    for i, script in enumerate(scripts, 1):
        # Check if script exists before running
        if os.path.exists(script):
            print(f"[{i}/{len(scripts)}] Executing: {os.path.basename(script)}")
            run_script(script)
        else:
            print(f"Warning: Script {script} not found, skipping...")
    
    print(f"Weekly BonsaiPR automation completed at {datetime.now()}")

def main():
    """Main entry point - simply run the scripts sequentially."""
    try:
        run_scripts_sequentially()
    except Exception as e:
        print(f"Automation failed: {e}")
        exit(1)

if __name__ == '__main__':
    main()