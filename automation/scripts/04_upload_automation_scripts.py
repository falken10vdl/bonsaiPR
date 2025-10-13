import os
import subprocess
import shutil
import glob
import re
from datetime import datetime

# Configuration
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
GITHUB_OWNER = "YOUR_GITHUB_USERNAME"
GITHUB_REPO = "bonsaiPR"
SCRIPTS_SOURCE_DIR = "/path/to/your/bonsaiPRDevel/weekly-bonsaipr-automation"
TEMP_REPO_DIR = "/tmp/bonsaiPR_scripts_upload"

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

def sanitize_script_content(content):
    """Remove sensitive information from script content"""
    # Remove GitHub token
    content = re.sub(r'GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"]*"', 'GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"', content)
    
    # Remove GitHub owner (make it configurable)
    content = re.sub(r'GITHUB_OWNER = "YOUR_GITHUB_USERNAME"', 'GITHUB_OWNER = "YOUR_GITHUB_USERNAME"', content)
    
    # Remove any hardcoded paths that might be specific to this system
    content = re.sub(r'/path/to/your/', '/path/to/your/', content)
    
    return content

def copy_scripts_and_config():
    """Copy scripts and configuration files, sanitizing sensitive information"""
    print(f"Copying scripts and configuration from {SCRIPTS_SOURCE_DIR}...")
    
    if not os.path.exists(SCRIPTS_SOURCE_DIR):
        print(f"❌ Error: Scripts directory '{SCRIPTS_SOURCE_DIR}' does not exist.")
        return False
    
    try:
        # Create automation directory in the repo
        automation_dest = os.path.join(TEMP_REPO_DIR, 'automation')
        
        # Remove existing automation directory if it exists
        if os.path.exists(automation_dest):
            print(f"Removing existing automation directory...")
            shutil.rmtree(automation_dest)
        
        os.makedirs(automation_dest)
        
        # Copy scripts directory
        scripts_src = os.path.join(SCRIPTS_SOURCE_DIR, 'scripts')
        scripts_dest = os.path.join(automation_dest, 'scripts')
        
        if os.path.exists(scripts_src):
            os.makedirs(scripts_dest)
            for script_file in os.listdir(scripts_src):
                if script_file.endswith('.py'):
                    src_path = os.path.join(scripts_src, script_file)
                    dest_path = os.path.join(scripts_dest, script_file)
                    
                    # Read, sanitize, and write the script
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    sanitized_content = sanitize_script_content(content)
                    
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(sanitized_content)
                    
                    print(f"✅ Sanitized and copied: {script_file}")
        
        # Copy src directory (main orchestration)
        src_src = os.path.join(SCRIPTS_SOURCE_DIR, 'src')
        src_dest = os.path.join(automation_dest, 'src')
        
        if os.path.exists(src_src):
            def ignore_pycache(directory, files):
                return [f for f in files if f == '__pycache__' or f.endswith('.pyc')]
            
            shutil.copytree(src_src, src_dest, ignore=ignore_pycache)
            print(f"✅ Copied src directory")
        
        # Copy configuration files
        config_files = ['requirements.txt', 'README.md']
        for config_file in config_files:
            src_path = os.path.join(SCRIPTS_SOURCE_DIR, config_file)
            if os.path.exists(src_path):
                dest_path = os.path.join(automation_dest, config_file)
                shutil.copy2(src_path, dest_path)
                print(f"✅ Copied: {config_file}")
        
        # Copy cron and systemd directories
        for dir_name in ['cron', 'systemd', 'logs']:
            src_dir = os.path.join(SCRIPTS_SOURCE_DIR, dir_name)
            if os.path.exists(src_dir):
                dest_dir = os.path.join(automation_dest, dir_name)
                shutil.copytree(src_dir, dest_dir)
                print(f"✅ Copied: {dir_name} directory")
        
        # Create a comprehensive README for the automation
        readme_content = f"""# BonsaiPR Weekly Automation System

This directory contains the complete automation system for weekly BonsaiPR builds.

## Overview

The BonsaiPR automation system performs weekly builds that:
1. Merge latest pull requests from IfcOpenShell repository
2. Build BonsaiPR addons for multiple platforms (Linux, macOS, Windows)
3. Create GitHub releases with download links
4. Upload complete source code for developer access

## Directory Structure

```
automation/
├── scripts/           # Main automation scripts
│   ├── 00_clone_merge_and_replace.py    # PR merging and source modification
│   ├── 01_build_bonsaiPR_addons.py      # Multi-platform addon building
│   ├── 02_upload_to_falken10vdl.py      # GitHub release management
│   ├── 03_upload_mergedPR.py            # Source code upload
│   └── 04_upload_automation_scripts.py  # This script (automation upload)
├── src/               # Main orchestration
│   ├── main.py        # Entry point for automation
│   ├── scheduler.py   # Scheduling utilities
│   ├── script_runner.py  # Script execution management
│   └── config/        # Configuration management
├── cron/             # Cron job configuration
├── systemd/          # Systemd service configuration
├── logs/             # Log directory
└── requirements.txt  # Python dependencies
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- Git
- GitHub personal access token with repo permissions
- Build environment for IfcOpenShell (if building locally)

### 2. Configuration

1. **Update Configuration**: Edit the script files to update these variables:
   ```python
   GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
   GITHUB_OWNER = "YOUR_GITHUB_USERNAME"
   ```

2. **Update Paths**: Modify paths in scripts to match your system:
   ```python
   # Update these paths as needed
   SOURCE_DIR = "/path/to/your/IfcOpenShell"
   BUILT_ADDONS_PATH = "/path/to/your/bonsaiPR/dist"
   ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Manual Testing

Test individual scripts:
```bash
# Test PR merging
python scripts/00_clone_merge_and_replace.py

# Test addon building
python scripts/01_build_bonsaiPR_addons.py

# Test GitHub uploads
python scripts/02_upload_to_falken10vdl.py
python scripts/03_upload_mergedPR.py
```

### 5. Schedule Automation

**Option A: Using Cron**
```bash
# Install the cron job (runs weekly on Sunday at 2 AM UTC)
crontab cron/weekly-automation.cron
```

**Option B: Using Systemd**
```bash
# Copy service files
sudo cp systemd/bonsaipr-automation.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bonsaipr-automation.service
```

## Script Details

### 00_clone_merge_and_replace.py
- Clones IfcOpenShell repository
- Fetches open pull requests via GitHub API
- Attempts to merge each PR automatically
- Replaces "bonsai" with "bonsaiPR" throughout codebase
- Generates detailed merge reports with statistics

### 01_build_bonsaiPR_addons.py
- Builds BonsaiPR addons for multiple platforms:
  - Linux x64
  - macOS Intel (x64)
  - macOS Apple Silicon (ARM64)
  - Windows x64
- Uses Python 3.11 target
- Creates distributable zip files

### 02_upload_to_falken10vdl.py
- Creates GitHub releases with semantic versioning
- Uploads addon files as release assets
- Generates rich markdown descriptions with PR details
- Handles existing releases gracefully

### 03_upload_mergedPR.py
- Uploads complete IfcOpenShell source code to GitHub
- Creates both main branch and weekly branches
- Handles Git submodule issues
- Makes source code browsable for developers

## Features

- **Automated PR Integration**: Automatically discovers and merges open PRs
- **Multi-Platform Builds**: Supports all major operating systems
- **Professional Releases**: Rich GitHub releases with detailed descriptions
- **Source Transparency**: Complete source code available to developers
- **Comprehensive Reporting**: Detailed logs and statistics
- **Robust Error Handling**: Graceful handling of network issues and conflicts
- **Scheduling Flexibility**: Supports both cron and systemd scheduling

## Output

The automation produces:
- **GitHub Releases**: Weekly releases with downloadable addons
- **Source Code**: Complete browsable source code repository
- **Build Reports**: Detailed merge and build statistics
- **Log Files**: Comprehensive execution logs

## Weekly Schedule

By default, the automation runs every Sunday at 2:00 AM UTC, producing builds with the naming pattern:
- `v0.8.4-alphaYYMMDD` (e.g., `v0.8.4-alpha251013`)

## Troubleshooting

### Common Issues:

1. **GitHub API Rate Limits**: Ensure your token has sufficient permissions
2. **Build Failures**: Check IfcOpenShell build dependencies
3. **Network Issues**: Scripts include retry logic for uploads
4. **Permission Issues**: Ensure proper file/directory permissions

### Logs:

Check logs in:
- `logs/automation.log`: Main automation log
- Individual script outputs during execution

## Contributing

This automation system is designed to be:
- **Configurable**: Easy to adapt for different repositories
- **Extensible**: New scripts can be added to the workflow
- **Maintainable**: Clear separation of concerns between scripts

## License

This automation system follows the same license as the BonsaiPR project.

---

**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}
**System Version**: Weekly BonsaiPR Automation v1.0
"""
        
        readme_path = os.path.join(automation_dest, 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"✅ Created comprehensive README.md")
        
        # Create example environment file
        env_example_content = """# BonsaiPR Automation Configuration
# Copy this file to .env and update with your values

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=bonsaiPR

# Local Paths (update these for your system)
IFCOPENSHELL_SOURCE_DIR=/path/to/your/IfcOpenShell
BONSAIPR_BUILD_DIR=/path/to/your/bonsaiPR/dist
REPORTS_PATH=/path/to/your/reports

# Build Configuration
PYTHON_VERSION=py311
BONSAIPR_VERSION=0.8.4

# Scheduling (for reference)
# Weekly: Sunday at 2 AM UTC
# Cron: 0 2 * * 0
"""
        
        env_example_path = os.path.join(automation_dest, '.env.example')
        with open(env_example_path, 'w', encoding='utf-8') as f:
            f.write(env_example_content)
        print(f"✅ Created .env.example file")
        
        return True
    except Exception as e:
        print(f"❌ Error copying scripts: {e}")
        return False

def commit_and_push_changes():
    """Commit and push the automation scripts"""
    original_dir = os.getcwd()
    try:
        os.chdir(TEMP_REPO_DIR)
        setup_git_config()
        
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
            print("ℹ️  No changes to commit")
            return True
        
        # Create commit
        commit_message = f"""Add BonsaiPR Weekly Automation System - {datetime.now().strftime('%Y-%m-%d')}

Complete automation system for weekly BonsaiPR builds including:

Features:
- Automated PR merging from IfcOpenShell repository
- Multi-platform addon building (Linux, macOS, Windows)
- GitHub release management with rich descriptions
- Source code upload with developer access
- Comprehensive reporting and logging
- Flexible scheduling (cron/systemd)

Components:
- 5 main automation scripts
- Main orchestration system
- Configuration management
- Scheduling templates
- Comprehensive documentation

This system enables:
- Weekly automated builds every Sunday at 2 AM UTC
- Professional GitHub releases with addon downloads
- Complete source code transparency
- Detailed merge reports and statistics
- Robust error handling and recovery

Usage:
1. Update configuration in scripts
2. Install dependencies: pip install -r automation/requirements.txt
3. Test individual scripts
4. Set up scheduling via cron or systemd

See automation/README.md for complete setup instructions.
"""
        
        subprocess.run(['git', 'commit', '-m', commit_message], 
                      check=True, capture_output=True)
        print("✅ Changes committed")
        
        # Push changes
        subprocess.run(['git', 'push', 'origin', 'main'], 
                      check=True, capture_output=True)
        print("✅ Changes pushed to main branch")
        
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

def upload_automation_scripts():
    """Main function to upload automation scripts"""
    print("Starting upload of automation scripts...")
    
    # Check if source directory exists
    if not os.path.exists(SCRIPTS_SOURCE_DIR):
        print(f"❌ Error: Scripts directory '{SCRIPTS_SOURCE_DIR}' does not exist.")
        return False
    
    try:
        # Step 1: Clone repository
        if not clone_repository():
            return False
        
        # Step 2: Copy and sanitize scripts
        if not copy_scripts_and_config():
            return False
        
        # Step 3: Commit and push changes
        if not commit_and_push_changes():
            return False
        
        print(f"\n🎉 Upload completed successfully!")
        print(f"Automation scripts uploaded to main branch")
        print(f"Repository: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}")
        print(f"Automation directory: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/main/automation")
        
        print(f"\n📁 Uploaded automation system includes:")
        print(f"   - 5 main automation scripts (sanitized)")
        print(f"   - Complete orchestration system")
        print(f"   - Configuration templates")
        print(f"   - Scheduling examples (cron/systemd)")
        print(f"   - Comprehensive documentation")
        print(f"   - Setup instructions and examples")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        cleanup()

if __name__ == '__main__':
    success = upload_automation_scripts()
    exit(0 if success else 1)