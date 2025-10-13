import os
import subprocess
import shutil
import requests
import re
from datetime import datetime

# Configuration
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
repo_url = 'https://github.com/IfcOpenShell/IfcOpenShell.git'
base_clone_dir = '/path/to/your/bonsaiPRDevel/IfcOpenShell'
working_base_dir = '/path/to/your/bonsaiPRDevel/MergingPR'
working_dir = '/path/to/your/bonsaiPRDevel/MergingPR/IfcOpenShell'
repo = 'IfcOpenShell/IfcOpenShell'
users = ['']  # Add specific usernames or leave empty for all users

# Generate report filename with the same pattern as addons
def get_report_filename():
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    pyversion = "py311"
    report_name = f"README-bonsaiPR_{pyversion}-{version}-alpha{current_date}.txt"
    report_path = f'/path/to/your/bonsaiPRDevel/{report_name}'
    return report_path

def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"}

def clone_or_update_repository(repo_url, clone_dir):
    if os.path.exists(clone_dir):
        print(f"Updating existing repository in {clone_dir}")
        original_dir = os.getcwd()
        try:
            os.chdir(clone_dir)
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                   capture_output=True, text=True, check=True)
            current_branch = result.stdout.strip()
            subprocess.run(['git', 'reset', '--hard', 'HEAD'], check=True)
            subprocess.run(['git', 'clean', '-fd'], check=True)
            subprocess.run(['git', 'pull', 'origin', current_branch], check=True)
            print(f"Repository updated successfully")
        finally:
            os.chdir(original_dir)
    else:
        print(f"Cloning repository {repo_url} into {clone_dir}")
        subprocess.run(['git', 'clone', repo_url, clone_dir], check=True)

def copy_to_working_dir(source_dir, target_dir):
    print(f"Copying {source_dir} to {target_dir}")
    if os.path.exists(working_base_dir):
        print(f"Removing existing working base directory: {working_base_dir}")
        shutil.rmtree(working_base_dir)
    os.makedirs(working_base_dir, exist_ok=True)
    shutil.copytree(source_dir, target_dir)

def replace_bonsai_in_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        new_content = re.sub(
            r'\bbonsai\b',
            lambda m: m.group(0) + 'PR',
            content,
            flags=re.IGNORECASE
        )
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
    except (UnicodeDecodeError, PermissionError) as e:
        print(f"[DEBUG] Skipping file (decode/permission error): {file_path} ({e})")

def revert_makefile_clone_line(makefile_path):
    try:
        with open(makefile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content.replace(
            "git clone https://github.com/IfcOpenShell/bonsaiPR-translations.git build/working",
            "git clone https://github.com/IfcOpenShell/bonsai-translations.git build/working"
        )
        new_content = re.sub(
            r'zip -r bonsai_\$\((PYVERSION)\)-\$\((VERSION)\)-\$\((BLENDER_PLATFORM)\)\.zip \./bonsaiPR',
            r'zip -r bonsaiPR_$(PYVERSION)-$(VERSION)-$(BLENDER_PLATFORM).zip ./bonsaiPR',
            new_content
        )
        new_content = re.sub(
            r'zip -r bonsai_\$\((PYVERSION)\)-\$\((VERSION)\)-alpha\$\((VERSION_DATE)\)-\$\((BLENDER_PLATFORM)\)\.zip \./bonsaiPR',
            r'zip -r bonsaiPR_$(PYVERSION)-$(VERSION)-alpha$(VERSION_DATE)-$(BLENDER_PLATFORM).zip ./bonsaiPR',
            new_content
        )
        if new_content != content:
            print(f"[DEBUG] Reverting Makefile lines in: {makefile_path}")
            with open(makefile_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
    except Exception as e:
        print(f"[DEBUG] Could not update Makefile: {e}")

def replace_bonsai_in_directory(directory):
    print(f"[DEBUG] Starting bonsai replacement in directory: {directory}")
    for root, dirs, files in os.walk(directory):
        for name in files:
            file_path = os.path.join(root, name)
            replace_bonsai_in_file(file_path)
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            old_path = os.path.join(root, name)
            new_name = re.sub(
                r'\bbonsai\b',
                lambda m: m.group(0) + 'PR',
                name,
                flags=re.IGNORECASE
            )
            if new_name != name:
                new_path = os.path.join(root, new_name)
                print(f"[DEBUG] Renaming file: {old_path} -> {new_path}")
                os.rename(old_path, new_path)
        for name in dirs:
            old_dir = os.path.join(root, name)
            new_name = re.sub(
                r'\bbonsai\b',
                lambda m: m.group(0) + 'PR',
                name,
                flags=re.IGNORECASE
            )
            if new_name != name:
                new_dir = os.path.join(root, new_name)
                print(f"[DEBUG] Renaming directory: {old_dir} -> {new_dir}")
                os.rename(old_dir, new_dir)
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name.lower() in ['makefile', 'makefile.txt']:
                makefile_path = os.path.join(root, name)
                revert_makefile_clone_line(makefile_path)

def get_open_prs_for_users(repo, users):
    prs = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100&page={page}"
        response = requests.get(url, headers=github_headers())
        if response.status_code != 200:
            break
        page_prs = response.json()
        if not page_prs:
            break
        for pr in page_prs:
            if not users or users == [''] or pr['user']['login'] in users:
                prs.append({
                    'number': pr['number'],
                    'title': pr['title'],
                    'author': pr['user']['login'],
                    'head_ref': pr['head']['ref'],
                    'head_repo': pr['head']['repo']['clone_url'] if pr['head']['repo'] else None,
                    'created_at': pr['created_at'],
                    'updated_at': pr['updated_at'],
                    'url': pr['html_url']
                })
        page += 1
    return prs

def apply_prs_locally(working_dir, repo, users):
    original_dir = os.getcwd()
    try:
        os.chdir(working_dir)
        result = subprocess.run(['git', 'branch', '--show-current'], 
                               capture_output=True, text=True, check=True)
        default_branch = result.stdout.strip()
        open_prs = get_open_prs_for_users(repo, users)
        applied_prs = []
        failed_prs = []
        for pr in open_prs:
            pr_number = pr['number']
            print(f"Applying PR #{pr_number}: {pr['title']}")
            if not pr['head_repo']:
                pr['failure_reason'] = "No head repository available"
                failed_prs.append(pr)
                continue
            remote_name = f"pr_{pr_number}"
            try:
                subprocess.run(['git', 'remote', 'add', remote_name, pr['head_repo']], 
                             check=True, capture_output=True)
                subprocess.run(['git', 'fetch', remote_name, pr['head_ref']], 
                             check=True, capture_output=True)
                subprocess.run(['git', 'checkout', default_branch], 
                             check=True, capture_output=True)
                subprocess.run(['git', 'merge', '--no-ff', '-m', 
                               f"Merge PR #{pr_number}: {pr['title']}", 
                               f'{remote_name}/{pr["head_ref"]}'], 
                              check=True, capture_output=True)
                applied_prs.append(pr)
                print(f"✅ Successfully applied PR #{pr_number}")
            except subprocess.CalledProcessError as e:
                subprocess.run(['git', 'merge', '--abort'], 
                             check=False, capture_output=True)
                pr['failure_reason'] = f"Merge conflict or git error (code {e.returncode})"
                failed_prs.append(pr)
                print(f"❌ Failed to apply PR #{pr_number}")
            finally:
                subprocess.run(['git', 'remote', 'remove', remote_name], 
                             check=False, capture_output=True)
        return applied_prs, failed_prs
    finally:
        os.chdir(original_dir)

def generate_report(applied_prs, failed_prs, report_path):
    print(f"Generating report at: {report_path}")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("BONSAIPR DEVELOPMENT - PULL REQUEST MERGE REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Repository: {repo}\n")
        f.write(f"Users: {', '.join(users) if users != [''] else 'ALL USERS'}\n")
        f.write(f"Working Directory: {working_dir}\n")
        f.write("\n")
        total_prs = len(applied_prs) + len(failed_prs)
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Applied PRs: {len(applied_prs)}\n")
        f.write(f"Failed PRs: {len(failed_prs)}\n")
        for pr in applied_prs:
            f.write(f"  ✅ PR #{pr['number']}: {pr['title']}\n")
        for pr in failed_prs:
            f.write(f"  ❌ PR #{pr['number']}: {pr['title']}\n")
        f.write(f"\nSuccess Rate: {(len(applied_prs)/total_prs*100):.1f}%\n" if total_prs > 0 else "\nSuccess Rate: N/A\n")
        f.write("\n")
        f.write("DETAILS GROUPED BY AUTHOR\n")
        f.write("=" * 80 + "\n")
        all_prs = applied_prs + failed_prs
        authors = {}
        for pr in all_prs:
            author = pr['author']
            if author not in authors:
                authors[author] = {'applied': [], 'failed': []}
            if pr in applied_prs:
                authors[author]['applied'].append(pr)
            else:
                authors[author]['failed'].append(pr)
        for author in sorted(authors.keys()):
            author_applied = authors[author]['applied']
            author_failed = authors[author]['failed']
            total_author_prs = len(author_applied) + len(author_failed)
            f.write(f"\nAUTHOR: {author}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total PRs: {total_author_prs} | Applied: {len(author_applied)} | Failed: {len(author_failed)}\n")
            f.write(f"Success Rate: {(len(author_applied)/total_author_prs*100):.1f}%\n" if total_author_prs > 0 else "Success Rate: N/A\n")
            f.write("\n")
            if author_applied:
                f.write("Successfully Applied:\n")
                for pr in sorted(author_applied, key=lambda x: x['number'], reverse=True):
                    f.write(f"  ✅ PR #{pr['number']}: {pr['title']}\n")
                    f.write(f"     Branch: {pr['head_ref']}\n")
                    f.write(f"     Created: {pr['created_at']}\n")
                    f.write(f"     URL: {pr['url']}\n\n")
            if author_failed:
                f.write("Failed to Apply:\n")
                for pr in sorted(author_failed, key=lambda x: x['number'], reverse=True):
                    f.write(f"  ❌ PR #{pr['number']}: {pr['title']}\n")
                    f.write(f"     Branch: {pr['head_ref']}\n")
                    f.write(f"     Created: {pr['created_at']}\n")
                    f.write(f"     URL: {pr['url']}\n")
                    f.write(f"     Failure Reason: {pr.get('failure_reason', 'Unknown error')}\n\n")
        f.write("NEXT STEPS\n")
        f.write("-" * 40 + "\n")
        f.write("1. Review failed PRs and resolve conflicts manually if needed\n")
        f.write("2. Note that you must apply the previous PRs (applied  newest to oldest) in order to fix your conflicts\n")
        f.write("3. Test the generated bonsaiPR addon in Blender\n")
        f.write("\n")
        f.write("=" * 80 + "\n")

def main():
    print("Starting PR application process...")
    print(f"Directory structure will be:")
    print(f"  Base clone: {base_clone_dir}")
    print(f"  Working base: {working_base_dir}")
    print(f"  Working dir: {working_dir}")
    
    # Generate report filename with current date
    report_path = get_report_filename()
    print(f"Report will be saved as: {os.path.basename(report_path)}")
    
    clone_or_update_repository(repo_url, base_clone_dir)
    copy_to_working_dir(base_clone_dir, working_dir)
    applied, failed = apply_prs_locally(working_dir, repo, users)
    print("\nRemoving git files from working directory...")
    git_files_to_remove = [
        os.path.join(working_dir, '.git'),
        os.path.join(working_dir, '.gitignore'),
        os.path.join(working_dir, '.gitmodules'),
        os.path.join(working_dir, '.github')
    ]
    for git_file in git_files_to_remove:
        if os.path.exists(git_file):
            if os.path.isdir(git_file):
                print(f"Removing directory: {git_file}")
                shutil.rmtree(git_file)
            else:
                print(f"Removing file: {git_file}")
                os.remove(git_file)
    print("\nReplacing 'bonsai' with 'bonsaiPR' in working directory...")
    replace_bonsai_in_directory(working_dir)
    print("\nGenerating report...")
    generate_report(applied, failed, report_path)
    print(f"\nSummary:")
    print(f"Applied PRs: {len(applied)}")
    print(f"Failed PRs: {len(failed)}")
    for pr in applied:
        print(f"  ✅ PR #{pr['number']}: {pr['title']}")
    for pr in failed:
        print(f"  ❌ PR #{pr['number']}: {pr['title']}")
    print(f"\nDetailed report saved to: {report_path}")

if __name__ == '__main__':
    main()
