import os
import subprocess
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set your GitHub token in environment variables
upstream_repo_url = 'https://github.com/IfcOpenShell/IfcOpenShell.git'
# Use token in the fork URL for authenticated operations
fork_repo_url = f'https://{GITHUB_TOKEN}@github.com/falken10vdl/IfcOpenShell.git'
fork_repo_url_public = 'https://github.com/falken10vdl/IfcOpenShell.git'  # For display purposes
work_dir = os.getenv("BASE_CLONE_DIR", "/home/falken10vdl/bonsaiPRDevel/IfcOpenShell")
upstream_repo = 'IfcOpenShell/IfcOpenShell'
fork_owner = 'falken10vdl'
fork_repo = 'IfcOpenShell'
users = os.getenv("USERNAMES", "").split(",") if os.getenv("USERNAMES") else ['']  # Add specific usernames or leave empty for all users

# Generate branch name and report filename with the same pattern as addons
def get_branch_and_report_names():
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    pyversion = "py311"
    branch_name = f"weekly-build-{version}-alpha{current_date}"
    report_name = f"README-bonsaiPR_{pyversion}-{version}-alpha{current_date}.txt"
    report_dir = os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")
    report_path = os.path.join(report_dir, report_name)
    return branch_name, report_path

def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"}

def setup_repository():
    """Clone or update the fork repository with upstream remote"""
    if os.path.exists(work_dir):
        print(f"Updating existing repository in {work_dir}")
        original_dir = os.getcwd()
        try:
            os.chdir(work_dir)
            # Reset to clean state
            subprocess.run(['git', 'reset', '--hard', 'HEAD'], check=True)
            subprocess.run(['git', 'clean', '-fd'], check=True)
            subprocess.run(['git', 'checkout', 'v0.8.0'], check=True)
            
            # Update from upstream
            subprocess.run(['git', 'fetch', 'upstream'], check=True)
            subprocess.run(['git', 'reset', '--hard', 'upstream/v0.8.0'], check=True)
            
            # Update the origin remote URL to use token for authentication
            subprocess.run(['git', 'remote', 'set-url', 'origin', fork_repo_url], check=True)
            
            # Push updated v0.8.0 to fork
            subprocess.run(['git', 'push', 'origin', 'v0.8.0', '--force'], check=True)
            
            print(f"Repository updated successfully")
        finally:
            os.chdir(original_dir)
    else:
        print(f"Cloning fork repository into {work_dir}")
        subprocess.run(['git', 'clone', fork_repo_url, work_dir], check=True)
        
        # Add upstream remote
        original_dir = os.getcwd()
        try:
            os.chdir(work_dir)
            subprocess.run(['git', 'remote', 'add', 'upstream', upstream_repo_url], check=True)
            subprocess.run(['git', 'fetch', 'upstream'], check=True)
            print("Added upstream remote and fetched latest changes")
        finally:
            os.chdir(original_dir)

def get_open_prs():
    """Get open pull requests from IfcOpenShell repository"""
    print("Fetching open pull requests...")
    url = f"https://api.github.com/repos/{upstream_repo}/pulls"
    params = {"state": "open", "per_page": 100}
    
    all_prs = []
    page = 1
    
    while True:
        params["page"] = page
        response = requests.get(url, headers=github_headers(), params=params)
        if response.status_code != 200:
            print(f"Error fetching PRs: {response.status_code}")
            break
        
        prs = response.json()
        if not prs:
            break
            
        # Filter by users if specified
        if users and users != ['']:
            prs = [pr for pr in prs if pr['user']['login'] in users]
        
        all_prs.extend(prs)
        page += 1
        
        if len(prs) < 100:  # Last page
            break
    
    print(f"Found {len(all_prs)} open pull requests")
    return all_prs

def apply_prs_to_branch(branch_name, prs):
    """Apply PRs to the new branch"""
    original_dir = os.getcwd()
    applied = []
    failed = []
    skipped = []
    
    try:
        os.chdir(work_dir)
        
        # Check if branch already exists, if so delete it and recreate
        result = subprocess.run(['git', 'branch', '--list', branch_name], capture_output=True, text=True)
        if result.stdout.strip():
            print(f"Branch {branch_name} already exists, deleting and recreating...")
            subprocess.run(['git', 'branch', '-D', branch_name], check=True)
        
        # Create and checkout new branch
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
        print(f"Created new branch: {branch_name}")
        
        for pr in prs:
            pr_number = pr['number']
            pr_title = pr['title']
            
            # Check if PR is in draft status
            if pr.get('draft', False):
                print(f"⚠️  Skipping PR #{pr_number}: PR is in DRAFT status")
                pr_with_reason = pr.copy()
                pr_with_reason['skip_reason'] = 'DRAFT status'
                skipped.append(pr_with_reason)
                continue
            
            # Check if PR head repo is accessible
            if not pr.get('head') or not pr['head'].get('repo'):
                print(f"⚠️  Skipping PR #{pr_number}: Repository no longer accessible (deleted fork)")
                pr_with_reason = pr.copy()
                pr_with_reason['skip_reason'] = 'Repository no longer accessible (deleted fork)'
                skipped.append(pr_with_reason)
                continue
            
            pr_head_ref = pr['head']['ref']
            pr_head_repo = pr['head']['repo']['clone_url']
            
            # Additional safety check for required fields
            if not pr_head_ref or not pr_head_repo:
                print(f"⚠️  Skipping PR #{pr_number}: Missing required PR information")
                pr_with_reason = pr.copy()
                pr_with_reason['skip_reason'] = 'Missing required PR information'
                skipped.append(pr_with_reason)
                continue
            
            print(f"Applying PR #{pr_number}: {pr_title}")
            
            try:
                # Add remote for PR if it's from a fork
                remote_name = f"pr-{pr_number}"
                subprocess.run(['git', 'remote', 'remove', remote_name], 
                             capture_output=True)  # Remove if exists
                subprocess.run(['git', 'remote', 'add', remote_name, pr_head_repo], check=True)
                
                # Fetch the PR branch
                fetch_result = subprocess.run(['git', 'fetch', remote_name, pr_head_ref], 
                                            capture_output=True, text=True)
                
                if fetch_result.returncode != 0:
                    print(f"❌ Failed to fetch PR #{pr_number}: {fetch_result.stderr}")
                    failed.append(pr)
                    subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
                    continue
                
                # Try to merge the PR
                merge_result = subprocess.run(['git', 'merge', '--no-ff', '--no-edit', 
                                            f"{remote_name}/{pr_head_ref}"], 
                                           capture_output=True, text=True)
                
                if merge_result.returncode == 0:
                    print(f"✅ Successfully applied PR #{pr_number}")
                    applied.append(pr)
                else:
                    print(f"❌ Failed to apply PR #{pr_number}: {merge_result.stderr}")
                    subprocess.run(['git', 'merge', '--abort'], capture_output=True)
                    failed.append(pr)
                
                # Clean up remote
                subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Error applying PR #{pr_number}: {e}")
                failed.append(pr)
                subprocess.run(['git', 'merge', '--abort'], capture_output=True)
                subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
        
        print(f"\nPR Application Summary:")
        print(f"✅ Successfully applied: {len(applied)} PRs")
        print(f"❌ Failed to apply: {len(failed)} PRs")
        print(f"⚠️  Skipped (draft/repo issues): {len(skipped)} PRs")
        
        return applied, failed, skipped
        
    finally:
        os.chdir(original_dir)

def test_failed_prs_individually(failed_prs):
    """Test each failed PR by merging it alone against base. Returns a dict: pr_number -> True/False"""
    print("\nTesting failed PRs individually against base branch...")
    original_dir = os.getcwd()
    pr_test_results = {}
    try:
        os.chdir(work_dir)
        for pr in failed_prs:
            pr_number = pr['number']
            pr_title = pr['title']
            pr_head_ref = pr.get('head', {}).get('ref')
            pr_head_repo = pr.get('head', {}).get('repo', {}).get('clone_url')
            if not pr_head_ref or not pr_head_repo:
                pr_test_results[pr_number] = None
                print(f"[SKIP] PR #{pr_number}: Missing head ref/repo for test merge.")
                continue

            test_branch = f"test-merge-pr-{pr_number}"
            print(f"[TEST] PR #{pr_number}: Creating branch '{test_branch}' from v0.8.0 and testing merge...")
            try:
                # Clean up any existing test branch
                subprocess.run(['git', 'branch', '-D', test_branch], capture_output=True)
                subprocess.run(['git', 'checkout', 'v0.8.0'], check=True)
                subprocess.run(['git', 'checkout', '-b', test_branch], check=True)

                # Add remote for PR
                remote_name = f"prtest-{pr_number}"
                subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
                subprocess.run(['git', 'remote', 'add', remote_name, pr_head_repo], check=True)
                fetch_result = subprocess.run(['git', 'fetch', remote_name, pr_head_ref], capture_output=True, text=True)
                if fetch_result.returncode != 0:
                    print(f"[FAIL] PR #{pr_number}: Could not fetch PR branch: {fetch_result.stderr}")
                    pr_test_results[pr_number] = False
                    subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
                    subprocess.run(['git', 'checkout', 'v0.8.0'], check=True)
                    continue

                # Try to merge PR alone
                merge_result = subprocess.run([
                    'git', 'merge', '--no-ff', '--no-edit', f"{remote_name}/{pr_head_ref}"
                ], capture_output=True, text=True)
                if merge_result.returncode == 0:
                    print(f"[PASS] PR #{pr_number}: Merges cleanly against base.")
                    pr_test_results[pr_number] = True
                else:
                    print(f"[FAIL] PR #{pr_number}: Merge conflict or error: {merge_result.stderr}")
                    subprocess.run(['git', 'merge', '--abort'], capture_output=True)
                    pr_test_results[pr_number] = False

                # Clean up remote and branch
                subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
                subprocess.run(['git', 'checkout', 'v0.8.0'], check=True)
                subprocess.run(['git', 'branch', '-D', test_branch], capture_output=True)
            except Exception as e:
                print(f"[ERROR] PR #{pr_number}: Exception during test merge: {e}")
                pr_test_results[pr_number] = False
                try:
                    subprocess.run(['git', 'merge', '--abort'], capture_output=True)
                    subprocess.run(['git', 'remote', 'remove', remote_name], capture_output=True)
                    subprocess.run(['git', 'checkout', 'v0.8.0'], check=True)
                    subprocess.run(['git', 'branch', '-D', test_branch], capture_output=True)
                except Exception:
                    pass
    finally:
        os.chdir(original_dir)
    return pr_test_results

def apply_bonsai_replacements():
    """Apply bonsai → bonsaiPR text replacements and directory renames"""
    print("Applying bonsai → bonsaiPR text replacements...")
    
    original_dir = os.getcwd()
    try:
        os.chdir(work_dir)
        
        # First, rename the bonsai directory to bonsaiPR
        bonsai_src_dir = "src/bonsai"
        bonsaiPR_src_dir = "src/bonsaiPR"
        
        if os.path.exists(bonsai_src_dir) and not os.path.exists(bonsaiPR_src_dir):
            print(f"Renaming directory: {bonsai_src_dir} → {bonsaiPR_src_dir}")
            subprocess.run(['git', 'mv', bonsai_src_dir, bonsaiPR_src_dir], check=True)
        
        # Find all text files (excluding binary files and .git)
        find_result = subprocess.run([
            'find', '.', '-type', 'f', 
            '!', '-path', './.git/*',
            '!', '-path', './.*',
            '!', '-name', '*.png',
            '!', '-name', '*.jpg', 
            '!', '-name', '*.jpeg',
            '!', '-name', '*.gif',
            '!', '-name', '*.ico',
            '!', '-name', '*.blend',
            '!', '-name', '*.whl'
        ], capture_output=True, text=True, check=True)
        
        files = find_result.stdout.strip().split('\n')
        
        replacement_count = 0
        files_modified = 0
        
        for file_path in files:
            if not file_path.strip():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Apply replacements
                new_content = content
                
                # Replace "bonsai" with "bonsaiPR" (case-sensitive)
                # But preserve "BonsaiPR" if it already exists
                if 'bonsaiPR' not in content.lower():
                    new_content = re.sub(r'\bbonsai\b', 'bonsaiPR', new_content)
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    replacement_count += content.count('bonsai') - new_content.count('bonsai')
                    files_modified += 1
                    print(f"[DEBUG] Modified: {file_path}")
                    
            except (UnicodeDecodeError, PermissionError) as e:
                print(f"[DEBUG] Skipping file (decode/permission error): {file_path} ({e})")
                continue
        
        print(f"Text replacement complete: {replacement_count} replacements in {files_modified} files")
        
        # Commit the replacements
        subprocess.run(['git', 'add', '.'], check=True)
        commit_result = subprocess.run(['git', 'commit', '-m', 'Apply bonsai → bonsaiPR replacements'], 
                                     capture_output=True)
        if commit_result.returncode == 0:
            print("Committed bonsai → bonsaiPR replacements")
        else:
            print("No changes to commit for text replacements")
            
    finally:
        os.chdir(original_dir)

def push_branch_to_fork(branch_name):
    """Push the new branch to the fork"""
    original_dir = os.getcwd()
    try:
        os.chdir(work_dir)
        # Ensure origin remote is set to use token
        subprocess.run(['git', 'remote', 'set-url', 'origin', fork_repo_url], check=True)
        # Push the new branch to origin (fork)
        subprocess.run(['git', 'push', 'origin', branch_name, '--force'], check=True)
        print(f"✅ Pushed branch '{branch_name}' to fork: {fork_repo_url_public}")
        # Stay on the branch with PRs instead of returning to v0.8.0
        print(f"📍 Repository is now on branch '{branch_name}' with applied PRs")
    finally:
        os.chdir(original_dir)

def generate_report(applied_prs, failed_prs, report_path, branch_name, skipped_prs=None, failed_pr_test_results=None):
    if skipped_prs is None:
        skipped_prs = []
    print(f"Generating report at: {report_path}")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# BonsaiPR Weekly Build Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"Branch: {branch_name}\n")
        f.write(f"Fork Repository: https://github.com/{fork_owner}/{fork_repo}/tree/{branch_name}\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Total PRs processed: {len(applied_prs) + len(failed_prs) + len(skipped_prs)}\n")
        f.write(f"- Successfully merged: {len(applied_prs)}\n")
        f.write(f"- Failed to merge: {len(failed_prs)}\n")
        f.write(f"- Skipped (draft/repo issues): {len(skipped_prs)}\n\n")
        if applied_prs:
            f.write(f"## ✅ Successfully Merged PRs ({len(applied_prs)})\n\n")
            for pr in applied_prs:
                f.write(f"- **PR #{pr['number']}**: {pr['title']}\n")
                f.write(f"  - Author: {pr['user']['login']}\n")
                f.write(f"  - URL: {pr['html_url']}\n")
                f.write(f"  - Created: {pr['created_at'][:10]}\n\n")
        if failed_prs:
            f.write(f"## ❌ Failed to Merge PRs ({len(failed_prs)})\n\n")
            for pr in failed_prs:
                pr_number = pr['number']
                f.write(f"- **PR #{pr_number}**: {pr['title']}\n")
                f.write(f"  - Author: {pr['user']['login']}\n")
                f.write(f"  - URL: {pr['html_url']}\n")
                f.write(f"  - Reason: Merge conflict or other error\n")
                if failed_pr_test_results is not None and pr_number in failed_pr_test_results:
                    test_result = failed_pr_test_results[pr_number]
                    if test_result is True:
                        f.write(f"  - Individual test merge: ✅ Merges cleanly against base (conflict with other PRs)\n\n")
                    elif test_result is False:
                        f.write(f"  - Individual test merge: ❌ Fails to merge against base (problem with PR itself)\n\n")
                    else:
                        f.write(f"  - Individual test merge: ⚠️ Not tested (missing info)\n\n")
                else:
                    f.write(f"  - Individual test merge: Not tested\n\n")
        if skipped_prs:
            f.write(f"## ⚠️ Skipped PRs ({len(skipped_prs)})\n\n")
            for pr in skipped_prs:
                f.write(f"- **PR #{pr['number']}**: {pr['title']}\n")
                f.write(f"  - Author: {pr['user']['login']}\n")
                f.write(f"  - URL: {pr['html_url']}\n")
                skip_reason = pr.get('skip_reason', 'Repository no longer accessible (deleted fork)')
                f.write(f"  - Reason: {skip_reason}\n\n")
        f.write(f"## Developer Instructions\n\n")
        f.write(f"To use this branch for development:\n\n")
        f.write(f"```bash\n")
        f.write(f"git clone https://github.com/{fork_owner}/{fork_repo}.git\n")
        f.write(f"cd {fork_repo}\n")
        f.write(f"git checkout {branch_name}\n")
        f.write(f"```\n\n")
        f.write(f"This branch contains the latest IfcOpenShell v0.8.0 branch with ")
        f.write(f"{len(applied_prs)} merged community pull requests. ")
        f.write(f"PR authors can use this branch to test their changes and make adjustments.\n")

def main():
    print("Starting weekly BonsaiPR branch creation...")
    print("This script creates clean branches with merged PRs for PR authors to test.")
    print("No bonsai→bonsaiPR renaming is done here - that happens in the build script.")
    # Validate GitHub token
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found in environment variables")
        print("Please check your .env file and ensure GITHUB_TOKEN is set")
        return
    branch_name, report_path = get_branch_and_report_names()
    print(f"Branch name: {branch_name}")
    print(f"Report will be saved as: {os.path.basename(report_path)}")
    # Setup repository
    setup_repository()
    # Get open PRs
    prs = get_open_prs()
    if not prs:
        print("No open PRs found, creating branch with just main branch updates")
        applied, failed, skipped = [], [], []
        failed_pr_test_results = {}
        # Push branch to fork (even if empty)
        push_branch_to_fork(branch_name)
        generate_report(applied, failed, report_path, branch_name, skipped, failed_pr_test_results)
        print(f"\n🎉 Weekly BonsaiPR branch creation completed!")
        print(f"✅ Branch created: https://github.com/{fork_owner}/{fork_repo}/tree/{branch_name}")
        print(f"📊 Report saved: {report_path}")
        print(f"📝 Summary: {len(applied)} PRs merged, {len(failed)} failed, {len(skipped)} skipped")
        return
    # Apply PRs to new branch
    applied, failed, skipped = apply_prs_to_branch(branch_name, prs)
    # Push branch to fork BEFORE running individual PR tests
    push_branch_to_fork(branch_name)
    # Test failed PRs individually
    failed_pr_test_results = test_failed_prs_individually(failed)
    # Generate report
    generate_report(applied, failed, report_path, branch_name, skipped, failed_pr_test_results)
    print(f"\n🎉 Weekly BonsaiPR branch creation completed!")
    print(f"✅ Branch created: https://github.com/{fork_owner}/{fork_repo}/tree/{branch_name}")
    print(f"📊 Report saved: {report_path}")
    print(f"📝 Summary: {len(applied)} PRs merged, {len(failed)} failed, {len(skipped)} skipped")

if __name__ == "__main__":
    main()
