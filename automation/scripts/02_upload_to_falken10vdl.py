import os
import subprocess
import requests
import json
import glob
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set your GitHub token in environment variables
GITHUB_OWNER = "falken10vdl"
GITHUB_REPO = "bonsaiPR"
FORK_OWNER = "falken10vdl"
FORK_REPO = "IfcOpenShell"

def get_build_paths():
    """Get the paths for built addons"""
    # Updated to use the actual build directory created by 01_build script
    build_base_dir = os.getenv("BUILD_BASE_DIR", "/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build")
    return os.path.join(build_base_dir, 'src', 'bonsaiPR', 'dist')

def get_reports_path():
    """Get the reports directory"""
    return os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")

def get_branch_name():
    """Generate branch name with current date"""
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    return f"weekly-build-{version}-alpha{current_date}"

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def get_release_tag():
    """Generate release tag with current date"""
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    pyversion = "py311"
    return f"v{version}-alpha{current_date}"

def find_report_file():
    """Find the latest README report file"""
    current_date = datetime.now().strftime('%y%m%d')
    reports_path = get_reports_path()
    pattern = f"{reports_path}/README-bonsaiPR_py311-*-alpha{current_date}.txt"
    report_files = glob.glob(pattern)
    if report_files:
        return max(report_files, key=os.path.getctime)  # Return the most recent one
    return None

def create_github_release(tag_name, release_name, release_body):
    """Create a new GitHub release or get existing one"""
    # First check if release already exists
    existing_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag_name}"
    existing_response = requests.get(existing_url, headers=github_headers())
    
    if existing_response.status_code == 200:
        release_data = existing_response.json()
        print(f"ℹ️ GitHub release already exists: {release_data['html_url']}")
        return release_data
    
    # Create new release if it doesn't exist
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
    
    data = {
        "tag_name": tag_name,
        "target_commitish": "main",  # or "master" depending on your default branch
        "name": release_name,
        "body": release_body,
        "draft": False,
        "prerelease": True  # Set to True since these are alpha releases
    }
    
    response = requests.post(url, headers=github_headers(), json=data)
    
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error creating release: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def check_asset_exists(release_id, asset_name):
    """Check if an asset already exists in the release"""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/{release_id}/assets"
    response = requests.get(url, headers=github_headers())
    
    if response.status_code == 200:
        assets = response.json()
        for asset in assets:
            if asset['name'] == asset_name:
                return True
    return False

def upload_asset_to_release(release_id, file_path, asset_name):
    """Upload an asset to a GitHub release (skip if already exists)"""
    # Check if asset already exists
    if check_asset_exists(release_id, asset_name):
        print(f"ℹ️ Asset {asset_name} already exists, skipping upload")
        return True
    
    url = f"https://uploads.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/{release_id}/assets"
    
    params = {"name": asset_name}
    
    try:
        with open(file_path, 'rb') as f:
            headers = github_headers()
            headers["Content-Type"] = "application/octet-stream"
            
            response = requests.post(url, headers=headers, params=params, data=f, timeout=300)
        
        if response.status_code == 201:
            print(f"✅ Successfully uploaded {asset_name}")
            return True
        else:
            print(f"❌ Error uploading {asset_name}: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Network error uploading {asset_name}: {e}")
        # If it's a network error but the asset might have been uploaded, check again
        if check_asset_exists(release_id, asset_name):
            print(f"ℹ️ Asset {asset_name} appears to have been uploaded despite error")
            return True
        return False

def generate_release_body(report_file_path, addon_files):
    """Generate release description from the report file and available addon files"""
    if not report_file_path or not os.path.exists(report_file_path):
        return "Weekly BonsaiPR build with latest PRs merged."
    
    try:
        with open(report_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract key information from the report
        lines = content.split('\n')
        applied_prs = []
        failed_prs = []
        skipped_prs = []
        total_prs = 0
        successfully_merged = 0
        failed_to_merge = 0
        skipped_count = 0
        
        # Parse summary section
        in_applied_section = False
        in_failed_section = False
        in_skipped_section = False
        
        for line in lines:
            line = line.strip()
            
            # Parse summary statistics
            if line.startswith("- Total PRs processed:"):
                total_prs = int(line.split(":")[1].strip())
            elif line.startswith("- Successfully merged:"):
                successfully_merged = int(line.split(":")[1].strip())
            elif line.startswith("- Failed to merge:"):
                failed_to_merge = int(line.split(":")[1].strip())
            elif line.startswith("- Skipped (draft/repo issues):"):
                skipped_count = int(line.split(":")[1].strip())
            
            # Parse PR sections
            elif line.startswith("## ✅ Successfully Merged PRs"):
                in_applied_section = True
                in_failed_section = False
                in_skipped_section = False
                continue
            elif line.startswith("## ❌ Failed to Merge PRs"):
                in_applied_section = False
                in_failed_section = True
                in_skipped_section = False
                continue
            elif line.startswith("## ⚠️ Skipped PRs"):
                in_applied_section = False
                in_failed_section = False
                in_skipped_section = True
                continue
            elif line.startswith("## "):
                in_applied_section = False
                in_failed_section = False
                in_skipped_section = False
                continue
            
            # Collect PRs - simplified approach
            if line.startswith("- **PR #"):
                if in_applied_section:
                    applied_prs.append(line)
                elif in_failed_section:
                    failed_prs.append(line)
                elif in_skipped_section:
                    # For skipped PRs, we'll check the next few lines for the reason
                    skipped_prs.append(line)
        
        # Now we need to re-read the file to add DRAFT labels to skipped PRs
        # This is a simplified approach - we'll check the reason lines
        with open(report_file_path, 'r') as f:
            lines = f.readlines()
        
        # Process skipped PRs to add DRAFT labels
        in_skipped_section = False
        current_pr_line = None
        skipped_prs_with_labels = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("## ⚠️ Skipped PRs"):
                in_skipped_section = True
                continue
            elif line.startswith("## "):
                in_skipped_section = False
                if current_pr_line:
                    skipped_prs_with_labels.append(current_pr_line)
                    current_pr_line = None
                continue
                
            if in_skipped_section:
                if line.startswith("- **PR #"):
                    if current_pr_line:
                        skipped_prs_with_labels.append(current_pr_line)
                    current_pr_line = line
                elif line.startswith("- Reason:") and current_pr_line:
                    reason = line.replace("- Reason:", "").strip()
                    if "DRAFT status" in reason:
                        # Add (DRAFT) to the PR line
                        current_pr_line = current_pr_line.replace("**: ", "** (DRAFT): ")
                    skipped_prs_with_labels.append(current_pr_line)
                    current_pr_line = None
        
        # Add any remaining PR
        if current_pr_line:
            skipped_prs_with_labels.append(current_pr_line)
        
        # Replace the original skipped_prs with the labeled version
        skipped_prs = skipped_prs_with_labels
        
        # Generate available downloads based on actual files
        downloads_section = "## 📦 Available Downloads\n\n"
        for addon_file in addon_files:
            filename = os.path.basename(addon_file)
            if "windows" in filename.lower():
                platform = "Windows (x64)"
            elif "linux" in filename.lower():
                platform = "Linux (x64)"
            elif "macosm1" in filename.lower() or "arm64" in filename.lower():
                platform = "macOS (Apple Silicon)"
            elif "macos" in filename.lower():
                platform = "macOS (Intel)"
            else:
                platform = "Unknown Platform"
            
            downloads_section += f"- **{platform}**: `{filename}`\n"
        
        # Calculate success rate
        success_rate = (successfully_merged / total_prs * 100) if total_prs > 0 else 0
        
        # Generate markdown description
        release_body = f"""# BonsaiPR Weekly Build - {datetime.now().strftime('%Y-%m-%d')}

This is an automated weekly build of BonsaiPR with the latest pull requests merged from the IfcOpenShell repository.

{downloads_section}
## 📋 Included Pull Requests

### ✅ Successfully Merged PRs ({successfully_merged})

"""
        
        for pr in applied_prs:
            release_body += f"{pr}\n"
        
        if failed_prs:
            release_body += f"\n### ❌ Failed to Merge ({failed_to_merge})\n\n"
            for pr in failed_prs:
                release_body += f"{pr}\n"
        
        if skipped_prs:
            release_body += f"\n### ⚠️ Skipped PRs ({skipped_count})\n\n"
            for pr in skipped_prs:
                release_body += f"{pr}\n"
        
        release_body += f"""
## 📊 Build Statistics
- **Total PRs Processed**: {total_prs}
- **Successfully Merged**: {successfully_merged}
- **Failed to Merge**: {failed_to_merge}
- **Skipped (draft/repo issues)**: {skipped_count}
- **Success Rate**: {success_rate:.1f}%

## 📄 Source Code
The complete source code for this release is available in the IfcOpenShell fork:

- **🔗 Browse Source**: [falken10vdl/IfcOpenShell:weekly-build-0.8.4-alpha{datetime.now().strftime('%y%m%d')}](https://github.com/falken10vdl/IfcOpenShell/tree/weekly-build-0.8.4-alpha{datetime.now().strftime('%y%m%d')})
- **📥 Download ZIP**: [Source Archive](https://github.com/falken10vdl/IfcOpenShell/archive/weekly-build-0.8.4-alpha{datetime.now().strftime('%y%m%d')}.zip)
- **👨‍💻 For PR Authors**: Checkout the branch above to test your PRs with other merged changes

## 📋 Full Report
Download the complete merge report for detailed information about each PR, including failure reasons and author statistics.

## ⚠️ Important Notes
- This is a **development build** and may contain experimental features
- These builds include community pull requests that may not be fully tested
- Use at your own risk in production environments
- Report issues to the [BonsaiPR repository](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO})

## 🔄 Next Build
The next automated build will be available next Sunday at 2 AM UTC.
"""
        
        return release_body
        
    except Exception as e:
        print(f"Error reading report file: {e}")
        return "Weekly BonsaiPR build with latest PRs merged."

def upload_to_falken10vdl():
    print("Starting upload to GitHub releases...")
    
    # Get build paths
    built_addons_path = get_build_paths()
    
    # Check if the built addons directory exists
    if not os.path.exists(built_addons_path):
        print(f"Error: The built addons directory '{built_addons_path}' does not exist.")
        return False
    
    # Find addon files
    addon_files = glob.glob(os.path.join(built_addons_path, "*.zip"))
    if not addon_files:
        print(f"Error: No addon zip files found in '{built_addons_path}'")
        return False
    
    print(f"Found {len(addon_files)} addon files to upload:")
    for file in addon_files:
        print(f"  - {os.path.basename(file)}")
    
    # Find report file
    report_file = find_report_file()
    if report_file:
        print(f"Found report file: {os.path.basename(report_file)}")
    else:
        print("Warning: No report file found")
    
    # Generate release information
    tag_name = get_release_tag()
    release_name = f"BonsaiPR v0.8.4-alpha{datetime.now().strftime('%y%m%d')} - Weekly Build"
    release_body = generate_release_body(report_file, addon_files)
    
    print(f"Creating GitHub release: {tag_name}")
    
    # Create the release
    release = create_github_release(tag_name, release_name, release_body)
    if not release:
        print("Failed to create GitHub release")
        return False
    
    release_id = release["id"]
    release_url = release["html_url"]
    print(f"✅ Successfully created release: {release_url}")
    
    # Upload addon files
    success_count = 0
    for addon_file in addon_files:
        asset_name = os.path.basename(addon_file)
        if upload_asset_to_release(release_id, addon_file, asset_name):
            success_count += 1
    
    # Upload report file if it exists
    if report_file:
        report_asset_name = os.path.basename(report_file)
        if upload_asset_to_release(release_id, report_file, report_asset_name):
            success_count += 1
            print(f"✅ Successfully uploaded report: {report_asset_name}")
    
    total_files = len(addon_files) + (1 if report_file else 0)
    print(f"\n🎉 Upload completed!")
    print(f"Successfully uploaded {success_count}/{total_files} files")
    print(f"Release URL: {release_url}")
    
    return success_count == total_files

if __name__ == '__main__':
    success = upload_to_falken10vdl()
    exit(0 if success else 1)
