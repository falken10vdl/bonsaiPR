# BonsaiPR Weekly Automation System

This directory contains the complete automation system for weekly BonsaiPR builds.

## Overview

The BonsaiPR automation system performs weekly builds that:
1. Merge latest pull requests from IfcOpenShell repository into fork branches
2. Build BonsaiPR addons with multi-core optimization (16-core parallel builds)
3. Create GitHub releases with professional release notes
4. Maintain source code branches in falken10vdl/IfcOpenShell for developer access

## Directory Structure

```
automation/
├── scripts/           # Main automation scripts
│   ├── 00_clone_merge_and_create_branch.py  # PR merging and branch creation
│   ├── 01_build_bonsaiPR_addons.py          # Multi-platform addon building with CPU optimization
│   ├── 02_upload_to_falken10vdl.py          # GitHub release management with enhanced notes
│   └── 03_upload_automation_scripts.py      # Automation system maintenance
├── src/               # Configuration and orchestration
│   ├── main.py        # Entry point for automation
│   └── config/        # Configuration management
└── .env.example       # Environment configuration template
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

### 2. Environment Configuration

1. **Create Environment File**: Copy and configure the environment template:
   ```bash
   cp .env.example .env
   ```

2. **Update Environment Variables**: Edit `.env` file with your settings:
   ```bash
   # GitHub Configuration
   GITHUB_TOKEN=your_github_token_here
   
   # Directory Paths
   BASE_CLONE_DIR=/home/yourusername/bonsaiPRDevel/IfcOpenShell
   BUILD_BASE_DIR=/home/yourusername/bonsaiPRDevel/bonsaiPR-build
   REPORT_PATH=/home/yourusername/bonsaiPRDevel
   
   # Optional: Filter PRs by specific users (comma-separated)
   USERNAMES=
   ```

3. **GitHub Token**: Create a personal access token with `repo` permissions at:
   https://github.com/settings/tokens

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r automation/requirements.txt

# Or install specific packages:
pip install requests python-dotenv
```

### 4. Manual Testing

Test individual scripts:
```bash
# Test PR merging and branch creation
python automation/scripts/00_clone_merge_and_create_branch.py

# Test addon building with CPU optimization
python automation/scripts/01_build_bonsaiPR_addons.py --platform linux

# Test GitHub releases with enhanced notes
python automation/scripts/02_upload_to_falken10vdl.py

# Test automation system maintenance
python automation/scripts/03_upload_automation_scripts.py
```

### 5. Schedule Automation

**Option A: Using Cron**
```bash
# Add to your crontab (runs weekly on Sunday at 2 AM UTC)
0 2 * * 0 cd /path/to/weekly-bonsaipr-automation && python -m automation.src.main > logs/automation-$(date +\%Y\%m\%d-\%H\%M\%S).log 2>&1
```

## Script Details

### 00_clone_merge_and_create_branch.py
- Clones/updates falken10vdl/IfcOpenShell fork repository
- Fetches open pull requests from IfcOpenShell/IfcOpenShell via GitHub API
- Attempts to merge each PR automatically with comprehensive error handling
- Creates weekly branch (e.g., `weekly-build-0.8.4-alpha251014`)
- Generates detailed merge reports with statistics
- Handles deleted repositories and inaccessible PRs gracefully
- Pushes merged branch to fork for developer access

### 01_build_bonsaiPR_addons.py
- Applies comprehensive bonsai→bonsaiPR text replacements throughout codebase
- Automatically detects and utilizes all available CPU cores (16-core optimization)
- Builds BonsaiPR addons with proper dependency management
- Supports multiple platforms with `--platform` argument:
  - linux: Linux x64
  - macos: macOS Intel (x64)  
  - macosm1: macOS Apple Silicon (ARM64)
  - win: Windows x64
- Creates distributable zip files in build directory
- Includes comprehensive automation fixes for build issues

### 02_upload_to_falken10vdl.py
- Creates GitHub releases with semantic versioning (v0.8.4-alphaYYMMDD)
- Uploads addon files as release assets with automatic platform detection
- Generates professional release notes with:
  - Dynamic download section based on available builds
  - Complete PR lists (merged, failed, skipped)
  - Build statistics and success rates
  - Source code links to weekly branches
  - Professional formatting and documentation
- Handles existing releases gracefully and updates assets

### 03_upload_automation_scripts.py
- Maintains the automation system in the main repository
- Sanitizes scripts by removing sensitive information
- Creates comprehensive documentation and examples
- Updates repository with latest automation improvements
- Handles Git conflicts and repository synchronization

## Features

- **Automated PR Integration**: Automatically discovers and merges open PRs with null-safety checks
- **Multi-Core Optimization**: Utilizes all available CPU cores (16-core parallel builds)
- **Professional Releases**: Rich GitHub releases with dynamic platform detection and comprehensive statistics
- **Source Transparency**: Complete source code available in fork repository weekly branches
- **Comprehensive Reporting**: Detailed logs, statistics, and merge reports
- **Robust Error Handling**: Graceful handling of deleted repos, network issues, and merge conflicts
- **Environment Configuration**: Flexible .env-based configuration system
- **Automated Maintenance**: Self-updating automation system with conflict resolution

## Output

The automation produces:
- **GitHub Releases**: Weekly releases with downloadable addons and professional release notes
- **Source Code Branches**: Weekly branches in falken10vdl/IfcOpenShell (e.g., `weekly-build-0.8.4-alpha251014`)
- **Build Reports**: Detailed merge and build statistics (README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt)
- **Performance Optimized Builds**: Multi-core compiled addons with comprehensive dependency management

## Weekly Schedule

By default, the automation runs every Sunday at 2:00 AM UTC, producing builds with the naming pattern:
- Release tags: `v0.8.4-alphaYYMMDD` (e.g., `v0.8.4-alpha251014`)
- Branch names: `weekly-build-0.8.4-alphaYYMMDD`
- Addon files: `bonsaiPR_py311-0.8.4-alphaYYMMDD-{platform}.zip`

## Troubleshooting

### Common Issues:

1. **GitHub API Rate Limits**: Ensure your token has sufficient permissions and check rate limit status
2. **Build Failures**: Verify IfcOpenShell build dependencies and multi-core compilation support  
3. **Network Issues**: Scripts include retry logic and comprehensive error handling
4. **Permission Issues**: Ensure proper file/directory permissions and GitHub token scope
5. **Merge Conflicts**: System automatically handles conflicts and reports failed merges
6. **Environment Variables**: Verify .env file configuration and path settings

### Source Code Locations:

- **Weekly Branches**: https://github.com/falken10vdl/IfcOpenShell/branches
- **Built Addons**: Check releases at https://github.com/falken10vdl/bonsaiPR/releases
- **Build Reports**: Downloaded with each release (README-bonsaiPR_*.txt files)

### Logs:

Check execution output and logs during script runs for detailed debugging information.

## License

This automation system follows the same license as the Bonsai project.

---

**Last Updated**: 2025-10-14  
**System Version**: Weekly BonsaiPR Automation v2.0  
**Key Features**: Multi-core optimization, enhanced error handling, professional release notes, comprehensive automation
