import os
import subprocess
import requests
import json
import glob
from datetime import datetime

# Configuration
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
GITHUB_OWNER = "YOUR_GITHUB_USERNAME"
GITHUB_REPO = "bonsaiPR"
BUILT_ADDONS_PATH = "/path/to/your/bonsaiPRDevel/MergingPR/IfcOpenShell/src/bonsaiPR/dist"
REPORTS_PATH = "/path/to/your/bonsaiPRDevel"

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
    pattern = f"{REPORTS_PATH}/README-bonsaiPR_py311-*-alpha{current_date}.txt"
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

def generate_release_body(report_file_path):
    """Generate release description from the report file"""
    if not report_file_path or not os.path.exists(report_file_path):
        return "Weekly BonsaiPR build with latest PRs merged."
    
    try:
        with open(report_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract key information from the report
        lines = content.split('\n')
        applied_prs = []
        failed_prs = []
        in_summary = False
        
        for line in lines:
            if "SUMMARY" in line:
                in_summary = True
                continue
            elif "DETAILS GROUPED BY AUTHOR" in line:
                in_summary = False
                continue
            elif in_summary and line.strip().startswith("✅"):
                applied_prs.append(line.strip())
            elif in_summary and line.strip().startswith("❌"):
                failed_prs.append(line.strip())
        
        # Generate markdown description
        release_body = f"""# BonsaiPR Weekly Build - {datetime.now().strftime('%Y-%m-%d')}

This is an automated weekly build of BonsaiPR with the latest pull requests merged from the IfcOpenShell repository.

## 📦 Available Downloads
- **Windows (x64)**: `bonsaiPR_py311-0.8.4-alpha{datetime.now().strftime('%y%m%d')}-windows-x64.zip`
- **Linux (x64)**: `bonsaiPR_py311-0.8.4-alpha{datetime.now().strftime('%y%m%d')}-linux-x64.zip`
- **macOS (Intel)**: `bonsaiPR_py311-0.8.4-alpha{datetime.now().strftime('%y%m%d')}-macos-x64.zip`
- **macOS (Apple Silicon)**: `bonsaiPR_py311-0.8.4-alpha{datetime.now().strftime('%y%m%d')}-macosm1-arm64.zip`

## 📋 Included Pull Requests

### ✅ Successfully Merged PRs ({len(applied_prs)})
"""
        
        for pr in applied_prs:
            # Extract PR number and title from the line
            pr_clean = pr.replace("✅ ", "").strip()
            release_body += f"- {pr_clean}\n"
        
        if failed_prs:
            release_body += f"\n### ❌ Failed to Merge ({len(failed_prs)})\n"
            for pr in failed_prs:
                pr_clean = pr.replace("❌ ", "").strip()
                release_body += f"- {pr_clean}\n"
        
        release_body += f"""
## 📊 Build Statistics
- **Total PRs Processed**: {len(applied_prs) + len(failed_prs)}
- **Successfully Merged**: {len(applied_prs)}
- **Failed to Merge**: {len(failed_prs)}
- **Success Rate**: {(len(applied_prs)/(len(applied_prs) + len(failed_prs))*100):.1f}% (if any PRs were processed)

## 📄 Full Report
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
    
    # Check if the built addons directory exists
    if not os.path.exists(BUILT_ADDONS_PATH):
        print(f"Error: The built addons directory '{BUILT_ADDONS_PATH}' does not exist.")
        return False
    
    # Find addon files
    addon_files = glob.glob(os.path.join(BUILT_ADDONS_PATH, "*.zip"))
    if not addon_files:
        print(f"Error: No addon zip files found in '{BUILT_ADDONS_PATH}'")
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
    release_body = generate_release_body(report_file)
    
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
