import subprocess

def run_script(script_name):
    """Run a script using subprocess."""
    try:
        result = subprocess.run(['python3', script_name], check=True)
        print(f"Successfully executed {script_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing {script_name}: {e}")

def main():
    scripts = [
        '../scripts/00_clone_merge_and_replace.py',
        '../scripts/01_build_bonsaiPR_addons.py',
        '../scripts/03_upload_to_falken10vdl.py'
    ]
    
    for script in scripts:
        run_script(script)

if __name__ == '__main__':
    main()