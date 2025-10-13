import schedule
import time
import subprocess

def run_scripts():
    scripts = [
        'scripts/00_clone_merge_and_replace.py',
        'scripts/01_build_bonsaiPR_addons.py',
        'scripts/03_upload_to_falken10vdl.py'
    ]
    
    for script in scripts:
        print(f"Running {script}...")
        subprocess.run(['python3', script], check=True)

def schedule_weekly_run():
    # Schedule the scripts to run every week on Monday at 10:00 AM
    schedule.every().monday.at("10:00").do(run_scripts)

    print("Scheduler started. Waiting for scheduled tasks...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    schedule_weekly_run()