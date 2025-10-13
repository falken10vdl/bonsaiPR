import os
import subprocess
import shutil
import glob
from datetime import datetime

# Configuration
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
GITHUB_OWNER = "YOUR_GITHUB_USERNAME"
GITHUB_REPO = "bonsaiPR"
SOURCE_DIR = "/path/to/your/bonsaiPRDevel/IfcOpenShell"
TEMP_REPO_DIR = "/tmp/bonsaiPR_upload"
REPORTS_PATH = "/path/to/your/bonsaiPRDevel"

def get_branch_name():
    """Generate branch name with current date"""
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    return f"weekly-build-v{version}-alpha{current_date}"

def find_report_file():
    """Find the latest README report file"""
    current_date = datetime.now().strftime('%y%m%d')
    pattern = f"{REPORTS_PATH}/README-bonsaiPR_py311-*-alpha{current_date}.txt"
    report_files = glob.glob(pattern)
    if report_files:
        return max(report_files, key=os.path.getctime)  # Return the most recent one
    return None

def setup_git_config():
    """Configure git user for commits"""
    try:
        subprocess.run(['git', 'config', 'user.name', 'BonsaiPR Automation'], 
                      check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'automation@bonsaipr.local'], 
                      check=True, capture_output=True)
        print("✅ Git configuration set")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not set git config: {e}")

def clone_repository():
    """Clone the bonsaiPR repository"""
    print(f"Cloning repository to {TEMP_REPO_DIR}...")
    
    # Clean up any existing temp directory
    if os.path.exists(TEMP_REPO_DIR):
        shutil.rmtree(TEMP_REPO_DIR)
    
    try:
        # Clone the repository with authentication
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
        subprocess.run(['git', 'clone', repo_url, TEMP_REPO_DIR], 
                      check=True, capture_output=True)
        print("✅ Repository cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error cloning repository: {e}")
        return False

def create_new_branch(branch_name):
    """Create and checkout a new branch, and also work on main"""
    original_dir = os.getcwd()
    try:
        os.chdir(TEMP_REPO_DIR)
        setup_git_config()
        
        # Stay on main branch for direct upload
        subprocess.run(['git', 'checkout', 'main'], 
                      check=True, capture_output=True)
        
        # Remove the problematic source directory if it's a submodule
        if os.path.exists('source'):
            print("Removing existing source entry...")
            subprocess.run(['git', 'rm', '-rf', 'source'], 
                          check=False, capture_output=True)  # Don't fail if it doesn't work
        
        # Also create a weekly branch for history
        subprocess.run(['git', 'checkout', '-b', branch_name], 
                      check=True, capture_output=True)
        print(f"✅ Created weekly branch: {branch_name}")
        
        # Switch back to main for the actual upload
        subprocess.run(['git', 'checkout', 'main'], 
                      check=True, capture_output=True)
        print(f"✅ Switched to main branch for upload")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up branches: {e}")
        return False
    finally:
        os.chdir(original_dir)

def copy_source_files():
    """Copy source files from IfcOpenShell directory"""
    print(f"Copying source files from {SOURCE_DIR}...")
    
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Error: Source directory '{SOURCE_DIR}' does not exist.")
        return False
    
    try:
        # Create source directory in the repo
        source_dest = os.path.join(TEMP_REPO_DIR, 'source')
        
        # Always remove existing source directory to ensure fresh copy
        if os.path.exists(source_dest):
            print(f"Removing existing source directory...")
            shutil.rmtree(source_dest)
        
        # Copy the entire IfcOpenShell directory, but exclude .git to avoid submodule issues
        def ignore_git_files(directory, files):
            return [f for f in files if f == '.git']
        
        shutil.copytree(SOURCE_DIR, source_dest, ignore=ignore_git_files)
        print(f"✅ Source files copied to {source_dest} (excluding .git files)")
        
        # Verify the copy worked by checking some key files
        key_files = ['src', 'CMakeLists.txt', 'README.md']
        found_files = []
        for item in os.listdir(source_dest):
            if item in key_files:
                found_files.append(item)
        print(f"✅ Verified key directories/files: {found_files}")
        
        # Also copy the report file if it exists
        report_file = find_report_file()
        if report_file:
            report_dest = os.path.join(TEMP_REPO_DIR, os.path.basename(report_file))
            if os.path.exists(report_dest):
                os.remove(report_dest)  # Remove existing report
            shutil.copy2(report_file, report_dest)
            print(f"✅ Report file copied: {os.path.basename(report_file)}")
        
        # Create a timestamp file to ensure Git sees changes
        timestamp_file = os.path.join(TEMP_REPO_DIR, 'LAST_UPDATE.txt')
        with open(timestamp_file, 'w') as f:
            f.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Build: v0.8.4-alpha{datetime.now().strftime('%y%m%d')}\n")
        print(f"✅ Timestamp file created")
        
        return True
    except Exception as e:
        print(f"❌ Error copying source files: {e}")
        return False

def create_commit_message():
    """Generate commit message with PR information"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Try to read PR information from report file
    report_file = find_report_file()
    pr_count = 0
    pr_summary = ""
    
    if report_file and os.path.exists(report_file):
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count applied PRs
            applied_prs = []
            lines = content.split('\n')
            in_summary = False
            
            for line in lines:
                if "SUMMARY" in line:
                    in_summary = True
                    continue
                elif "DETAILS GROUPED BY AUTHOR" in line:
                    in_summary = False
                    continue
                elif in_summary and line.strip().startswith("✅"):
                    applied_prs.append(line.strip().replace("✅ ", ""))
            
            pr_count = len(applied_prs)
            if pr_count > 0:
                pr_summary = f"\n\nIncluded PRs:\n" + "\n".join([f"- {pr}" for pr in applied_prs[:10]])  # Limit to first 10 PRs
                if len(applied_prs) > 10:
                    pr_summary += f"\n... and {len(applied_prs) - 10} more PRs"
        except Exception as e:
            print(f"Warning: Could not read PR information from report: {e}")
    
    commit_message = f"""Weekly BonsaiPR Build - {current_date}

Automated weekly build with {pr_count} merged pull requests from IfcOpenShell repository.

Build Details:
- Date: {current_date}
- Version: 0.8.4-alpha{datetime.now().strftime('%y%m%d')}
- Source: /path/to/your/bonsaiPRDevel/IfcOpenShell
- PRs Merged: {pr_count}{pr_summary}

This build includes the latest community contributions and may contain experimental features.
"""
    
    return commit_message

def commit_and_push_changes(branch_name):
    """Commit and push changes to both main and weekly branch"""
    original_dir = os.getcwd()
    try:
        os.chdir(TEMP_REPO_DIR)
        
        # Add all changes
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        
        # Show what files are staged
        result = subprocess.run(['git', 'status', '--porcelain'], 
                               capture_output=True, text=True)
        if result.stdout:
            print(f"Files to be committed:")
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        
        # Check if there are any changes to commit
        result = subprocess.run(['git', 'diff', '--staged', '--quiet'], 
                               capture_output=True)
        if result.returncode == 0:
            print("ℹ️  No changes to commit - checking if files exist...")
            # Force add all files to make sure everything is included
            subprocess.run(['git', 'add', '.', '--force'], check=True, capture_output=True)
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], 
                                   capture_output=True)
            if result.returncode == 0:
                print("❌ Still no changes detected")
                return False
        
        # Create commit on main
        commit_message = create_commit_message()
        subprocess.run(['git', 'commit', '-m', commit_message], 
                      check=True, capture_output=True)
        print("✅ Changes committed to main")
        
        # Push main branch
        subprocess.run(['git', 'push', 'origin', 'main'], 
                      check=True, capture_output=True)
        print("✅ Changes pushed to main branch")
        
        # Also push to weekly branch for history
        subprocess.run(['git', 'checkout', branch_name], 
                      check=True, capture_output=True)
        subprocess.run(['git', 'merge', 'main'], 
                      check=True, capture_output=True)
        subprocess.run(['git', 'push', 'origin', branch_name], 
                      check=True, capture_output=True)
        print(f"✅ Changes also pushed to weekly branch: {branch_name}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error committing/pushing changes: {e}")
        return False
    finally:
        os.chdir(original_dir)

def cleanup():
    """Clean up temporary directory"""
    if os.path.exists(TEMP_REPO_DIR):
        shutil.rmtree(TEMP_REPO_DIR)
        print("✅ Temporary directory cleaned up")

def upload_merged_pr():
    """Main function to upload merged PR source code"""
    print("Starting upload of merged PR source code...")
    
    # Check if source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Error: Source directory '{SOURCE_DIR}' does not exist.")
        return False
    
    branch_name = get_branch_name()
    print(f"Branch name: {branch_name}")
    
    try:
        # Step 1: Clone repository
        if not clone_repository():
            return False
        
        # Step 2: Create new branch
        if not create_new_branch(branch_name):
            return False
        
        # Step 3: Copy source files
        if not copy_source_files():
            return False
        
        # Step 4: Commit and push changes
        if not commit_and_push_changes(branch_name):
            return False
        
        print(f"\n🎉 Upload completed successfully!")
        print(f"Source code uploaded to main branch")
        print(f"Weekly branch created: {branch_name}")
        print(f"Repository: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}")
        print(f"Main branch source: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/main/source")
        print(f"Weekly branch: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/{branch_name}")
        
        print(f"\n� Source code is now available at:")
        print(f"   https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/blob/main/source")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        cleanup()

if __name__ == '__main__':
    success = upload_merged_pr()
    exit(0 if success else 1)