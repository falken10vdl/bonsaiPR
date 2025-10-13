import subprocess
import os
from datetime import datetime

def run_script(script_name):
    """Run a script using subprocess."""
    try:
        print(f"Starting execution of {script_name} at {datetime.now()}")
        subprocess.run(['python3', script_name], check=True)
        print(f"Successfully executed {script_name} at {datetime.now()}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing {script_name}: {e}")
        raise  # Re-raise to stop execution if a script fails

def run_scripts_sequentially():
    """Run the automation scripts in sequence."""
    # Get the directory of this script and build absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    scripts_dir = os.path.join(project_root, 'scripts')
    
    scripts = [
        os.path.join(scripts_dir, '00_clone_merge_and_replace.py'),
        os.path.join(scripts_dir, '01_build_bonsaiPR_addons.py'),
        os.path.join(scripts_dir, '02_upload_to_falken10vdl.py'),
        os.path.join(scripts_dir, '03_upload_mergedPR.py')
    ]
    
    print(f"Starting weekly BonsaiPR automation at {datetime.now()}")
    
    for script in scripts:
        # Check if script exists before running
        if os.path.exists(script):
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