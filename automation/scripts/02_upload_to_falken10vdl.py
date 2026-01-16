import os
import subprocess
import requests
import json
import glob
import re
import time
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

# Use token in URLs for authenticated Git operations
bonsaiPR_repo_url = f'https://{GITHUB_TOKEN}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git'
bonsaiPR_repo_url_public = f'https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git'

def get_build_paths():
    """Get the paths for built addons"""
    # Updated to use the actual build directory created by 01_build script
    build_base_dir = os.getenv("BUILD_BASE_DIR", "/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build")
    return os.path.join(build_base_dir, 'src', 'bonsaiPR', 'dist')

def get_reports_path():
    """Get the reports directory"""
    return os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")

def get_branch_name():
    """Generate branch name with timestamp for on-demand builds"""
    import requests
    import re
    current_datetime = datetime.now().strftime('%y%m%d%H%M')
    version = "unknown"
    try:
        api_url = "https://api.github.com/repos/IfcOpenShell/IfcOpenShell/releases"
        resp = requests.get(api_url, timeout=10)
        if resp.ok:
            releases = resp.json()
            for rel in releases:
                m = re.match(r'bonsai-([\d.]+)-alpha', rel.get('tag_name', ''))
                if m:
                    version = m.group(1)
                    break
    except Exception as e:
        print(f"Warning: Could not fetch version from releases: {e}")
    if version == "unknown":
        version = "0.0.0"  # fallback default
    return f"build-{version}-alpha{current_datetime}"

def get_version_info():
    """Get version information for naming - includes hour+minute for on-demand builds"""
    import requests
    import re
    current_datetime = datetime.now().strftime('%y%m%d%H%M')
    version = "unknown"
    try:
        api_url = "https://api.github.com/repos/IfcOpenShell/IfcOpenShell/releases"
        resp = requests.get(api_url, timeout=10)
        if resp.ok:
            releases = resp.json()
            for rel in releases:
                m = re.match(r'bonsai-([\d.]+)-alpha', rel.get('tag_name', ''))
                if m:
                    version = m.group(1)
                    break
    except Exception as e:
        print(f"Warning: Could not fetch version from releases: {e}")
    if version == "unknown":
        version = "0.0.0"  # fallback default
    pyversion = "py311"
    return version, pyversion, current_datetime

def setup_git_authentication():
    """Setup Git to use token for authentication"""
    try:
        # Set Git credentials for the bonsaiPR repository
        subprocess.run(['git', 'config', 'user.name', 'GitHub Actions'], 
                      capture_output=True, cwd=os.getcwd())
        subprocess.run(['git', 'config', 'user.email', 'actions@github.com'], 
                      capture_output=True, cwd=os.getcwd())
        
        # Check if we're in a git repository, if not initialize one
        result = subprocess.run(['git', 'status'], capture_output=True, cwd=os.getcwd())
        if result.returncode != 0:
            print("ℹ️ Not in a git repository, initializing temporary git repo for tag operations...")
            subprocess.run(['git', 'init'], capture_output=True, cwd=os.getcwd())
            subprocess.run(['git', 'remote', 'add', 'origin', bonsaiPR_repo_url], 
                          capture_output=True, cwd=os.getcwd())
        else:
            # Update remote URL to use token
            subprocess.run(['git', 'remote', 'set-url', 'origin', bonsaiPR_repo_url], 
                          capture_output=True, cwd=os.getcwd())
        
        print("✅ Git authentication configured")
        return True
        
    except Exception as e:
        print(f"⚠️ Warning: Could not setup Git authentication: {e}")
        return False

def cleanup_local_tag(tag_name):
    """Remove local tag if it exists to prevent conflicts"""
    try:
        # Setup Git authentication first
        setup_git_authentication()
        
        # Check if the tag exists locally
        result = subprocess.run(['git', 'tag', '-l', tag_name], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        if result.stdout.strip():
            print(f"🏷️ Removing existing local tag: {tag_name}")
            subprocess.run(['git', 'tag', '-d', tag_name], 
                         capture_output=True, cwd=os.getcwd())
            print(f"✅ Local tag {tag_name} removed")
        
        # Try to remove the tag from origin to clean up remote (optional, may fail if tag doesn't exist)
        print(f"🏷️ Attempting to remove remote tag: {tag_name}")
        result = subprocess.run(['git', 'push', 'origin', f':{tag_name}'], 
                               capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"✅ Remote tag {tag_name} removed")
        else:
            print(f"ℹ️ Remote tag {tag_name} may not exist (this is normal)")
        
    except Exception as e:
        print(f"ℹ️ Note: Could not clean up tag {tag_name}: {e}")

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def get_release_tag(timestamp=None):
    """Generate release tag with timestamp for on-demand builds"""
    import requests
    import re
    if timestamp is None:
        timestamp = datetime.now().strftime('%y%m%d%H%M')
    version = "unknown"
    try:
        api_url = "https://api.github.com/repos/IfcOpenShell/IfcOpenShell/releases"
        resp = requests.get(api_url, timeout=10)
        if resp.ok:
            releases = resp.json()
            for rel in releases:
                m = re.match(r'bonsai-([\d.]+)-alpha', rel.get('tag_name', ''))
                if m:
                    version = m.group(1)
                    break
    except Exception as e:
        print(f"Warning: Could not fetch version from releases: {e}")
    if version == "unknown":
        version = "0.0.0"  # fallback default
    pyversion = "py311"
    return f"v{version}-alpha{timestamp}"

def find_report_file():
    """Find the latest README report file - searches for most recent file within last hour"""
    version, pyversion, _ = get_version_info()
    reports_path = get_reports_path()
    # Search for all README files (not just exact minute match)
    pattern = f"{reports_path}/README-bonsaiPR_{pyversion}-{version}-alpha*.txt"
    report_files = glob.glob(pattern)
    
    if not report_files:
        return None
    
    # Find the most recent file by modification time
    latest_report = max(report_files, key=os.path.getmtime)
    
    # Verify it's from within the last hour (to avoid very old files)
    file_age = time.time() - os.path.getmtime(latest_report)
    if file_age > 3600:  # 1 hour in seconds
        print(f"⚠️ Latest README file is {int(file_age/60)} minutes old, might be stale")
    
    return latest_report

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

def append_upload_info_to_readme(report_file, release_url, tag_name, addon_files):
    """Append upload information to the existing README report file"""
    if not report_file or not os.path.exists(report_file):
        print("⚠️ No existing README file found, skipping upload info append")
        return None
    
    # Append upload information to the existing report file
    with open(report_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n{'=' * 80}\n")
        f.write(f"BonsaiPR Upload & Release Information\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"## 🚀 Release Details\n\n")
        f.write(f"**Upload Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Release Tag**: {tag_name}\n")
        f.write(f"**GitHub Release**: {release_url}\n")
        f.write(f"**Release Type**: Pre-release (Alpha)\n\n")
        
        f.write(f"## 📦 Uploaded Assets\n\n")
        for addon_file in sorted(addon_files):
            filename = os.path.basename(addon_file)
            size_mb = os.path.getsize(addon_file) / (1024 * 1024)
            f.write(f"- ✅ {filename} ({size_mb:.1f} MB)\n")
        
        f.write(f"\n## 🔗 Access Links\n\n")
        f.write(f"- 📥 [Download from GitHub Releases]({release_url})\n")
        f.write(f"- 🌐 [All Releases](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases)\n\n")
    
    print(f"✅ Appended upload information to: {os.path.basename(report_file)}")
    return report_file

def create_or_update_readme():
    """DEPRECATED: Use append_upload_info_to_readme() instead"""
    # Find the existing README file created by the build script (most recent one)
    readme_path = find_report_file()
    
    if not readme_path:
        print("⚠️ No existing README file found, creating new one")
        version, pyversion, current_date = get_version_info()
        readme_filename = f"README-bonsaiPR_{pyversion}-{version}-alpha{current_date}.txt"
        readme_path = os.path.join(get_reports_path(), readme_filename)
        file_exists = False
    else:
        file_exists = True
    
    # Check if the README file already exists
    file_exists = os.path.exists(readme_path) if readme_path else False
    
    with open(readme_path, 'a' if file_exists else 'w') as f:
        if file_exists:
            # Add separator and upload information to existing file
            f.write(f"\n\n{'=' * 80}\n")
            f.write(f"BonsaiPR Upload & Release Information\n")
            f.write(f"{'=' * 80}\n\n")
        else:
            # Create new file with header (this shouldn't happen if previous scripts run first)
            f.write(f"BonsaiPR Release Report\n")
            f.write(f"{'=' * 50}\n\n")
        
        # Get current release information
        tag_name = get_release_tag()
        built_addons_path = get_build_paths()
        addon_files = glob.glob(os.path.join(built_addons_path, "*.zip")) if os.path.exists(built_addons_path) else []
        
        f.write(f"## 🚀 Release Details\n\n")
        f.write(f"**Upload Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Release Tag**: {tag_name}\n")
        f.write(f"**GitHub Release**: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{tag_name}\n")
        f.write(f"**Release Type**: Pre-release (Alpha)\n\n")
        
        f.write(f"## 📦 Released Assets\n\n")
        
        if addon_files:
            f.write(f"**Addon Files ({len(addon_files)} platforms)**:\n\n")
            for addon_file in sorted(addon_files):
                filename = os.path.basename(addon_file)
                filesize = os.path.getsize(addon_file)
                
                # Determine platform from filename
                if "windows" in filename.lower() or "win" in filename.lower():
                    platform_icon = "🪟"
                    platform_name = "Windows (x64)"
                elif "linux" in filename.lower():
                    platform_icon = "🐧"
                    platform_name = "Linux (x64)"
                elif "macosm1" in filename.lower() or "arm64" in filename.lower():
                    platform_icon = "🍎"
                    platform_name = "macOS (Apple Silicon)"
                elif "macos" in filename.lower():
                    platform_icon = "🍎"
                    platform_name = "macOS (Intel)"
                else:
                    platform_icon = "📦"
                    platform_name = "Unknown Platform"
                
                f.write(f"- {platform_icon} **{platform_name}**: `{filename}` ({filesize:,} bytes)\n")
        else:
            f.write("❌ No addon files found for release.\n")
        
        # Add report file information
        report_file = find_report_file()
        if report_file:
            report_filename = os.path.basename(report_file)
            report_filesize = os.path.getsize(report_file)
            f.write(f"\n**Documentation**:\n")
            f.write(f"- 📄 **Detailed Report**: `{report_filename}` ({report_filesize:,} bytes)\n")
        
        f.write(f"\n## 🌐 Download Links\n\n")
        f.write(f"**Direct Downloads**:\n")
        f.write(f"- 🔗 [GitHub Releases Page](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases)\n")
        f.write(f"- 🔗 [Latest Release](https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{tag_name})\n")
        f.write(f"- 🔗 [Source Code Branch](https://github.com/{FORK_OWNER}/{FORK_REPO}/tree/{get_branch_name()})\n\n")
        
        f.write(f"## 📊 Release Statistics\n\n")
        
        # Try to get some statistics from the report file
        if report_file and os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8') as rf:
                    report_content = rf.read()
                
                # Extract statistics from the report
                total_prs = 0
                successfully_merged = 0
                failed_to_merge = 0
                skipped_count = 0
                
                for line in report_content.split('\n'):
                    line = line.strip()
                    if line.startswith("- Total PRs processed:"):
                        total_prs = int(line.split(":")[1].strip())
                    elif line.startswith("- Successfully merged:"):
                        successfully_merged = int(line.split(":")[1].strip())
                    elif line.startswith("- Failed to merge:"):
                        failed_to_merge = int(line.split(":")[1].strip())
                    elif line.startswith("- Skipped (draft/repo issues):"):
                        skipped_count = int(line.split(":")[1].strip())
                
                if total_prs > 0:
                    success_rate = (successfully_merged / total_prs * 100) if total_prs > 0 else 0
                    
                    # Calculate detailed breakdown to match the old format
                    base_conflicts = report_content.count("Conflict with base branch")
                    pr_conflicts = report_content.count("Conflict with other merged PRs") 
                    merge_failures = report_content.count("Automatic merge failed") + report_content.count("Unrelated histories") + report_content.count("Git operation failed")
                    # Note: PR conflicts are now actually skipped, not failed, so they shouldn't count towards failed_to_merge
                    other_failures = failed_to_merge - base_conflicts - merge_failures
                    
                    draft_count = report_content.count("DRAFT status")
                    deleted_count = report_content.count("Repository no longer accessible")
                    missing_info_count = report_content.count("Missing required PR information")
                    other_skipped = skipped_count - pr_conflicts - draft_count - deleted_count - missing_info_count
                    
                    # Write statistics in the old detailed format
                    f.write(f"- **Total PRs Processed**: {total_prs}\n")
                    f.write(f"- **Successfully Merged**: {successfully_merged}\n")
                    f.write(f"- **Failed to Merge (conflicts with base v0.8.0)**: {base_conflicts}\n")
                    f.write(f"- **Skipped (conflicts with other PRs)**: {pr_conflicts}\n")
                    
                    if merge_failures > 0:
                        f.write(f"- **Failed to Merge (other issues)**: {merge_failures}\n")
                    if other_failures > 0:
                        f.write(f"- **Failed to Merge (unknown)**: {other_failures}\n")
                    
                    f.write(f"- **Skipped (draft/repo issues)**: {draft_count + deleted_count + missing_info_count + other_skipped}\n")
                    f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
                else:
                    f.write("- Statistics not available from report file\n")
                    
            except Exception as e:
                f.write(f"- Could not extract statistics: {e}\n")
        else:
            f.write("- No report file available for statistics\n")
        
        f.write(f"\n## 🔧 Developer Information\n\n")
        f.write(f"**For PR Authors and Contributors**:\n")
        f.write(f"- Test your PRs using the branch: `{get_branch_name()}`\n")
        f.write(f"- Download and test the appropriate addon for your platform\n")
        f.write(f"- Report issues at: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues\n")
        f.write(f"- Contribute to IfcOpenShell: https://github.com/IfcOpenShell/IfcOpenShell\n\n")
        
        f.write(f"## ⚠️ Important Notices\n\n")
        f.write(f"- **Alpha Release**: This is a development build with experimental features\n")
        f.write(f"- **Community PRs**: Includes unreviewed community contributions\n")
        f.write(f"- **Use Carefully**: Not recommended for production environments\n")
        f.write(f"- **Backup First**: Always backup your Blender projects before testing\n")
        f.write(f"- **Report Issues**: Help improve BonsaiPR by reporting bugs and issues\n\n")
        
        f.write(f"## 📅 Next Release\n\n")
        f.write(f"- **Schedule**: Next automated build will be available next Sunday at 2 AM UTC\n")
        f.write(f"- **Updates**: New PRs merged since this build will be included\n")
        f.write(f"- **Notifications**: Watch the repository for release notifications\n")
    
    if file_exists:
        print(f"📄 Upload information appended to existing README: {readme_path}")
    else:
        print(f"📄 README with upload information created: {readme_path}")
    
    return readme_path

def format_pr_with_link(pr_line, pr_url):
    """Convert a PR line to markdown with hyperlinked PR number"""
    # Extract PR number and title from line like "- **PR #123**: Title here"
    match = re.match(r'- \*\*PR #(\d+)\*\*:\s*(.+)', pr_line)
    if match and pr_url:
        pr_number = match.group(1)
        pr_title = match.group(2)
        return f"- [**PR #{pr_number}**]({pr_url}): {pr_title}"
    return pr_line  # Return original if can't parse or no URL

def generate_release_body(report_file_path, addon_files, timestamp_from_readme=None, tag_name=None):
    """Generate release description from the report file and available addon files"""
    if not report_file_path or not os.path.exists(report_file_path):
        return "Weekly BonsaiPR build with latest PRs merged."
    
    try:
        with open(report_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        # --- Parse new summary breakdown ---
        total_prs = successfully_merged = failed_to_merge = skipped_count = 0
        failed_conflict_with_base = failed_conflict_with_others = failed_unknown = 0
        applied_prs = []
        skipped_draft_prs = []
        skipped_conflict_prs = []
        failed_prs = []
        in_applied_section = False
        in_failed_section = False
        in_skipped_section = False
        current_skip_reason = None
        
        for idx, line in enumerate(lines):
            line = line.strip()
            if line.startswith("- Total PRs processed:"):
                total_prs = int(line.split(":")[1].strip())
            elif line.startswith("- Successfully merged:"):
                successfully_merged = int(line.split(":")[1].strip())
            elif line.startswith("- Failed to merge:"):
                failed_to_merge = int(line.split(":")[1].strip())
            elif line.startswith("- Skipped (draft/repo issues):"):
                skipped_count = int(line.split(":")[1].strip())
            elif line.startswith("- Failed to Merge (conflicts with base v0.8.0):"):
                failed_conflict_with_base = int(line.split(":")[1].strip())
            elif line.startswith("- Skipped (conflicts with other PRs):"):
                failed_conflict_with_others = int(line.split(":")[1].strip())
            elif line.startswith("- Failed to Merge (unknown):"):
                failed_unknown = int(line.split(":")[1].strip())
            elif line.startswith("## ✅ Successfully Merged PRs"):
                in_applied_section = True
                in_failed_section = False
                in_skipped_section = False
            elif line.startswith("## ❌ Failed to Merge PRs"):
                in_applied_section = False
                in_failed_section = True
                in_skipped_section = False
            elif line.startswith("## ⚠️ Skipped PRs"):
                in_applied_section = False
                in_failed_section = False
                in_skipped_section = True
            elif line.startswith("## "):
                in_applied_section = False
                in_failed_section = False
                in_skipped_section = False
            
            # Collect PRs with URL extraction
            if line.startswith("- **PR #"):
                pr_url = None
                # Look ahead for URL
                for j in range(idx+1, min(idx+5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith("- URL:") or next_line.startswith("  - URL:"):
                        pr_url = next_line.split("URL:", 1)[1].strip()
                        break
                
                if in_applied_section:
                    applied_prs.append({'line': line, 'url': pr_url})
                elif in_failed_section:
                    current_pr = {'line': line, 'url': pr_url, 'reason': None}
                    # Look ahead for reason
                    for j in range(idx+1, min(idx+5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith("- Reason:") or next_line.startswith("  - Reason:"):
                            current_pr['reason'] = next_line.replace("- Reason:","").replace("  - Reason:","").strip()
                            break
                    # If reason matches conflict with other PRs, categorize as skipped_conflict_prs
                    if current_pr['reason'] == "Merges cleanly against base (conflict with other PRs)":
                        skipped_conflict_prs.append({'line': line, 'url': pr_url})
                    else:
                        failed_prs.append(current_pr)
                elif in_skipped_section:
                    current_pr = {'line': line, 'url': pr_url, 'reason': None}
                    # Look ahead for reason only
                    for j in range(idx+1, min(idx+5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith("- Reason:") or next_line.startswith("  - Reason:"):
                            current_pr['reason'] = next_line.replace("- Reason:","").replace("  - Reason:","").strip()
                            break
                    # Group skipped PRs
                    if current_pr['reason'] and "DRAFT status" in current_pr['reason']:
                        skipped_draft_prs.append({'line': line, 'url': pr_url})
                    elif current_pr['reason'] == "Merges cleanly against base (conflict with other PRs)":
                        skipped_conflict_prs.append({'line': line, 'url': pr_url})
                    else:
                        failed_prs.append(current_pr)
        
        # Generate available downloads based on actual files with HHMM timestamp
        downloads_section = "## 📦 Available Downloads\n\n"
        for addon_file in addon_files:
            original_filename = os.path.basename(addon_file)
            
            # Apply same renaming logic as upload section to get the final filename with HHMM
            import re
            pattern = r'(bonsaiPR_py311-[\d.]+(?:-alpha)?)(\d{6})(-[^.]+\.zip)'
            match = re.match(pattern, original_filename)
            
            if match and timestamp_from_readme:
                renamed_filename = f"{match.group(1)}{timestamp_from_readme}{match.group(3)}"
            else:
                renamed_filename = original_filename
            
            if "windows" in renamed_filename.lower():
                platform = "Windows (x64)"
            elif "linux" in renamed_filename.lower():
                platform = "Linux (x64)"
            elif "macosm1" in renamed_filename.lower() or "arm64" in renamed_filename.lower():
                platform = "macOS (Apple Silicon)"
            elif "macos" in renamed_filename.lower():
                platform = "macOS (Intel)"
            else:
                platform = "Unknown Platform"
            
            # Create download link URL (will be filled after release is created)
            download_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{tag_name}/{renamed_filename}"
            downloads_section += f"- **{platform}**: [{renamed_filename}]({download_url})\n"
        
        success_rate = (successfully_merged / total_prs * 100) if total_prs > 0 else 0
        
        # Generate markdown description
        release_body = f"""This is an automated build of BonsaiPR with the latest pull requests merged from the IfcOpenShell repository.

{downloads_section}
## 📊 Build Statistics
- **Total PRs Processed**: {total_prs}
- **Successfully Merged**: {successfully_merged}
- **Skipped (draft PRs)**: {len(skipped_draft_prs)}
- **Skipped (conflict with other PRs)**: {len(skipped_conflict_prs)}
- **Failed PRs**: {len(failed_prs)}
- **Success Rate**: {success_rate:.1f}%

## ✅ Successfully Merged PRs ({len(applied_prs)})
"""
        for pr_dict in applied_prs:
            release_body += format_pr_with_link(pr_dict['line'], pr_dict['url']) + "\n"
        
        release_body += f"\n## ⚠️ Skipped - DRAFT PRs ({len(skipped_draft_prs)})\n"
        for pr_dict in skipped_draft_prs:
            release_body += format_pr_with_link(pr_dict['line'], pr_dict['url']) + "\n"
        
        release_body += f"\n## ⚠️ Skipped - Conflict with other PRs. Merges cleany with base  ({len(skipped_conflict_prs)})\n"
        for pr_dict in skipped_conflict_prs:
            release_body += format_pr_with_link(pr_dict['line'], pr_dict['url']) + "\n"
        
        release_body += f"\n## ❌ Failed PRs ({len(failed_prs)})\n"
        for pr in failed_prs:
            release_body += format_pr_with_link(pr['line'], pr['url'])
            if pr['reason']:
                release_body += f"\n  - Reason: {pr['reason']}"
            release_body += "\n"
        
        release_body += "\n"
        return release_body
    except Exception as e:
        print(f"Error reading report file: {e}")
        return "Weekly BonsaiPR build with latest PRs merged."

def cleanup_old_releases():
    """Delete old releases from GitHub, keeping only the last 30"""
    print("\n🧹 Checking for old releases to clean up...")
    
    try:
        # Get all releases from the repository (handle pagination)
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
        all_releases = []
        page = 1
        
        while True:
            params = {"per_page": 100, "page": page}
            response = requests.get(url, headers=github_headers(), params=params)
            
            if response.status_code != 200:
                print(f"⚠️ Could not fetch releases: {response.status_code}")
                return
            
            page_releases = response.json()
            if not page_releases:
                break
            
            all_releases.extend(page_releases)
            page += 1
            
            # Safety limit: don't fetch more than 200 releases
            if len(all_releases) >= 200:
                break
        
        # Filter for versioned releases (matching pattern vX.X.X-alphaYYMMDDHHMM)
        # Example tag: v0.8.5-alpha2601071435
        versioned_releases = []
        for release in all_releases:
            tag_name = release['tag_name']
            # Match pattern: vX.X.X-alphaYYMMDDHHMM
            if re.match(r'^v[\d.]+-alpha\d{10}$', tag_name):
                versioned_releases.append(release)
        
        if len(versioned_releases) <= 30:
            print(f"✅ Found {len(versioned_releases)} releases (≤30), no cleanup needed")
            return
        
        # Sort releases by created_at date (newest first)
        versioned_releases.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Keep first 30 (newest), delete the rest
        releases_to_delete = versioned_releases[30:]
        
        print(f"📊 Found {len(versioned_releases)} releases, keeping last 30")
        print(f"🗑️  Deleting {len(releases_to_delete)} old releases...")
        
        deleted_count = 0
        for release in releases_to_delete:
            release_id = release['id']
            tag_name = release['tag_name']
            
            # Delete the release
            delete_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/{release_id}"
            delete_response = requests.delete(delete_url, headers=github_headers())
            
            if delete_response.status_code == 204:
                # Also delete the associated tag
                tag_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/refs/tags/{tag_name}"
                tag_response = requests.delete(tag_url, headers=github_headers())
                
                deleted_count += 1
                print(f"  ✓ Deleted release: {tag_name} (tag: {'✓' if tag_response.status_code == 204 else '✗'})")
            else:
                print(f"  ✗ Failed to delete release {tag_name}: {delete_response.status_code}")
        
        print(f"✅ Cleanup complete: {deleted_count}/{len(releases_to_delete)} releases deleted")
        
    except Exception as e:
        print(f"⚠️ Error during release cleanup: {e}")

def upload_to_falken10vdl():
    print("Starting upload to GitHub releases...")
    
    # Validate GitHub token
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found in environment variables")
        print("Please check your .env file and ensure GITHUB_TOKEN is set")
        return False
    
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
    
    # Find report file (only for generating release body, not for uploading)
    report_file = find_report_file()
    if report_file:
        print(f"Found report file: {os.path.basename(report_file)} (will be used for release description)")
    else:
        print("Warning: No report file found")
    
    # Extract timestamp from README filename (e.g., README-bonsaiPR_py311-0.8.4-alpha2512142235.txt)
    timestamp_from_readme = None
    if report_file:
        import re
        readme_basename = os.path.basename(report_file)
        # Pattern: README-bonsaiPR_py311-VERSION-alphaYYMMDDHHMM.txt
        match = re.search(r'alpha(\d{10})', readme_basename)
        if match:
            timestamp_from_readme = match.group(1)
            print(f"Extracted timestamp from README: {timestamp_from_readme}")
    
    # Generate release information using timestamp from README
    tag_name = get_release_tag(timestamp_from_readme)
    # Read commit hash and branch name from README report file
    commit_hash = "unknown"
    branch_name = "unknown"
    if report_file and os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("IfcOpenShell source commit:"):
                    commit_hash = line.split(":", 1)[1].strip()
                elif line.startswith("Branch:"):
                    branch_name = line.split(":", 1)[1].strip()
                # Stop reading once we have both values
                if commit_hash != "unknown" and branch_name != "unknown":
                    break

    # Format commit hash as a short hash and link, using the short hash from the GitHub commit page if possible
    commit_url = f"https://github.com/falken10vdl/IfcOpenShell/commit/{commit_hash}" if commit_hash != "unknown" else None
    short_hash = commit_hash[:7] if commit_hash not in (None, "unknown") else "unknown"
    # Try to fetch the short hash from the commit page if possible
    try:
        import requests
        if commit_url and commit_hash != "unknown":
            resp = requests.get(commit_url, timeout=10)
            if resp.ok:
                import re
                m = re.search(r"Commit ([0-9a-f]{7,})", resp.text)
                if m:
                    short_hash = m.group(1)
    except Exception:
        pass
    if commit_url and commit_hash != "unknown":
        commit_link = f"[`{short_hash}`]({commit_url})"
    else:
        commit_link = short_hash


    # Compose release name using the short hash of the latest commit on the branch used to create this release
    ts_full = timestamp_from_readme if timestamp_from_readme else datetime.now().strftime('%y%m%d%H%M')
    ts_short = ts_full[:6]  # YYMMDD only

    # Extract version from the first addon asset filename
    version = "unknown"
    if addon_files:
        first_asset = os.path.basename(addon_files[0])
        m = re.match(r'bonsaiPR_py311-([\d.]+)', first_asset)
        if m:
            version = m.group(1)

    # Fetch the latest commit hash from the branch using the GitHub API
    branch_short_hash = "unknown"
    if branch_name != "unknown":
        api_url = f"https://api.github.com/repos/{FORK_OWNER}/{FORK_REPO}/commits/{branch_name}"
        try:
            resp = requests.get(api_url, headers=github_headers(), timeout=10)
            if resp.ok:
                data = resp.json()
                branch_commit_hash = data.get("sha", "unknown")
                branch_short_hash = branch_commit_hash[:7] if branch_commit_hash not in (None, "unknown") else "unknown"
        except Exception as e:
            print(f"Warning: Could not fetch branch commit hash: {e}")

    release_name = f"BonsaiPR v{version}-alpha{ts_short}-{branch_short_hash}"

    # Build release body with source commit and branch information
    release_body_header = f"IfcOpenShell source commit (before PR merging): {commit_link}\n"
    
    if branch_name != "unknown":
        branch_url = f"https://github.com/{FORK_OWNER}/{FORK_REPO}/tree/{branch_name}"
        release_body_header += f"Branch used to create this release: [{branch_name}]({branch_url})\n"
    
    release_body = release_body_header + "\n" + generate_release_body(report_file, addon_files, timestamp_from_readme, tag_name)

    print(f"Creating GitHub release: {tag_name}")
    
    # Clean up any existing local tag to prevent conflicts
    cleanup_local_tag(tag_name)
    
    # Create the release
    release = create_github_release(tag_name, release_name, release_body)
    if not release:
        print("Failed to create GitHub release")
        return False
    
    release_id = release["id"]
    release_url = release["html_url"]
    print(f"✅ Successfully created release: {release_url}")
    
    # Upload addon files with updated timestamp (YYMMDD -> YYMMDDHHMM from README)
    success_count = 0
    
    for addon_file in addon_files:
        original_name = os.path.basename(addon_file)
        
        # Replace the old YYMMDD format with YYMMDDHHMM format from README
        # Pattern: bonsaiPR_py311-0.8.5-alpha251214-linux-x64.zip -> bonsaiPR_py311-0.8.5-alpha2512142235-linux-x64.zip
        import re
        # Match: bonsaiPR_py311-VERSION-alphaYYMMDD-platform.zip
        pattern = r'(bonsaiPR_py311-[\d.]+(?:-alpha)?)(\d{6})(-[^.]+\.zip)'
        
        match = re.match(pattern, original_name)
        if match and timestamp_from_readme:
            asset_name = f"{match.group(1)}{timestamp_from_readme}{match.group(3)}"
            print(f"Renaming asset: {original_name} -> {asset_name}")
        else:
            # Fallback: use original name if pattern doesn't match or no timestamp found
            asset_name = original_name
            if not timestamp_from_readme:
                print(f"⚠️ No timestamp from README, using original: {asset_name}")
            else:
                print(f"⚠️ Could not parse filename pattern, using original: {asset_name}")
        
        if upload_asset_to_release(release_id, addon_file, asset_name):
            success_count += 1
    
    # REMOVED: Upload of original report file (redundant)
    # The complete README contains all the information
    
    # Append upload information to the existing README file
    readme_path = append_upload_info_to_readme(report_file, release_url, tag_name, addon_files)
    
    # Upload the complete README as an asset
    if readme_path and os.path.exists(readme_path):
        readme_asset_name = os.path.basename(readme_path)
        if upload_asset_to_release(release_id, readme_path, readme_asset_name):
            success_count += 1
            print(f"✅ Successfully uploaded complete README: {readme_asset_name}")
    
    # Update index.json with new release info
    try:
        from automation.scripts.update_index_json import update_index_json
    except ImportError:
        from update_index_json import update_index_json

    index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../index.json'))
    # Use the actual asset names as uploaded to GitHub (renamed if needed)
    # Build a list of the actual uploaded file paths (with correct names)
    uploaded_files = []
    for addon_file in addon_files:
        original_name = os.path.basename(addon_file)
        pattern = r'(bonsaiPR_py311-[\d.]+(?:-alpha)?)(\d{6})(-[^.]+\.zip)'
        match = re.match(pattern, original_name)
        if match and timestamp_from_readme:
            asset_name = f"{match.group(1)}{timestamp_from_readme}{match.group(3)}"
            # The file on disk is still addon_file, but the asset on GitHub is asset_name
            # For hash/size, use the local file; for URL, use asset_name
            # We'll pass a tuple (local_path, asset_name)
            uploaded_files.append((addon_file, asset_name))
        else:
            uploaded_files.append((addon_file, original_name))

    # Call update_index_json with correct asset names
    # Patch update_index_json to accept (local_path, asset_name) tuples
    def update_index_json_with_asset_names(index_path, release_tag, uploaded_files):
        import json, hashlib, os
        if not os.path.exists(index_path):
            print(f"index.json not found at {index_path}")
            return False
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        def get_platform(filename):
            if 'linux-x64' in filename:
                return 'linux-x64'
            elif 'macos-x64' in filename:
                return 'macos-x64'
            elif 'macos-arm64' in filename:
                return 'macos-arm64'
            elif 'windows-x64' in filename:
                return 'windows-x64'
            return None
        file_info = {}
        for local_path, asset_name in uploaded_files:
            plat = get_platform(asset_name)
            if not plat:
                continue
            size = os.path.getsize(local_path)
            with open(local_path, 'rb') as f:
                hashval = hashlib.sha256(f.read()).hexdigest()
            file_info[plat] = {
                'filename': asset_name,
                'size': size,
                'hash': hashval
            }
        for entry in index.get('data', []):
            plat_list = entry.get('platforms', [])
            if not plat_list:
                continue
            plat = plat_list[0]
            if plat in file_info:
                entry['archive_url'] = f"https://github.com/falken10vdl/bonsaiPR/releases/download/{tag_name}/{file_info[plat]['filename']}"
                entry['archive_size'] = file_info[plat]['size']
                entry['archive_hash'] = f"sha256:{file_info[plat]['hash']}"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
        print(f"index.json updated for release {tag_name}")
        return True

    update_index_json_with_asset_names(index_path, tag_name, uploaded_files)

    # Update total files count (addon files + README only)
    total_files = len(addon_files) + 1  # +1 for README only
    print(f"\n🎉 Upload completed!")
    print(f"Successfully uploaded {success_count}/{total_files} files")
    print(f"Release URL: {release_url}")
    print(f"README updated and uploaded: {readme_path}")

    # Clean up old releases after successfully creating new one
    cleanup_old_releases()

    return success_count == total_files

if __name__ == '__main__':
    success = upload_to_falken10vdl()
    exit(0 if success else 1)