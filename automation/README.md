# BonsaiPR Weekly Automation System

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
│   ├── 00_clone_merge_and_create_branch.py  # PR merging with draft detection
│   ├── 01_build_bonsaiPR_addons.py          # Multi-platform addon building
│   └── 02_upload_to_falken10vdl.py          # GitHub release management
├── src/               # Main orchestration system
│   ├── main.py        # Automation orchestrator and entry point
│   └── config/        # Configuration management
│       ├── __init__.py
│       └── settings.py # Central configuration file
├── cron/             # Cron job configuration
│   └── weekly-automation.cron  # Weekly scheduling template
├── logs/             # Log directory (auto-created)
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

**Option A: Using the Main Orchestrator (Recommended)**
```bash
# Run the complete automation system
cd automation/src
python main.py
```

**Option B: Individual Script Testing**
```bash
# Test PR merging with draft detection
python scripts/00_clone_merge_and_create_branch.py

# Test addon building
python scripts/01_build_bonsaiPR_addons.py

# Test GitHub release creation
python scripts/02_upload_to_falken10vdl.py
```

### 5. Schedule Automation

**Option A: Using Cron (Recommended)**
```bash
# Install the cron job (runs weekly on Sunday at 2 AM UTC)
crontab automation/cron/weekly-automation.cron

# Verify cron installation
crontab -l
```

**Option B: Manual Execution**
```bash
# Run the complete automation system manually
cd automation/src && python main.py
```

## Script Details

### 00_clone_merge_and_create_branch.py
- Clones IfcOpenShell repository
- Fetches open pull requests via GitHub API
- **Enhanced draft PR detection** using `pr.get('draft', False)`
- Attempts to merge each PR automatically with comprehensive error handling
- **Skips draft PRs** with detailed skip reasons ('DRAFT status', 'Repository no longer accessible', 'Missing PR information')
- Creates weekly branches with merged changes
- Generates detailed merge reports with statistics and PR categorization

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
- **Enhanced release notes** with proper DRAFT PR labeling
- **Fixed parsing logic** to correctly show skipped PRs with "(DRAFT)" labels
- Generates rich markdown descriptions with complete PR categorization
- Shows accurate statistics: "⚠️ Skipped PRs (6)" with detailed skip reasons
- Handles existing releases gracefully

## Automation System Architecture

The BonsaiPR automation system consists of **3 main scripts** that work together:

1. **`00_clone_merge_and_create_branch.py`** - Merges PRs and creates weekly branches
2. **`01_build_bonsaiPR_addons.py`** - Builds addons for multiple platforms  
3. **`02_upload_to_falken10vdl.py`** - Creates GitHub releases with enhanced PR documentation

The automation scripts are **automatically synchronized** since this `weekly-bonsaipr-automation` folder is part of the `falken10vdl/bonsaiPR` repository. When changes are pushed to the repository, they're immediately available for the automation system.

## Features

- **Enhanced Draft PR Detection**: Automatically detects and skips draft PRs using `pr.get('draft', False)`
- **Comprehensive Skip Reasons**: Detailed categorization of why PRs are skipped
- **Professional Release Notes**: GitHub releases with proper DRAFT labels and accurate counts
- **Multi-Platform Builds**: Supports all major operating systems
- **Source Transparency**: Complete source code available to developers
- **Robust Error Handling**: Graceful handling of network issues and conflicts
- **Detailed Reporting**: Comprehensive logs with PR statistics and skip reasons
- **Fixed Parsing Logic**: Correctly processes and displays skipped PRs in release notes

## Output

The automation produces:
- **GitHub Releases**: Weekly releases with downloadable addons and proper DRAFT PR labeling
- **Enhanced Release Notes**: Complete PR categorization with skip reasons and DRAFT labels
- **Source Code**: Complete browsable source code repository  
- **Build Reports**: Detailed merge and build statistics with draft PR handling
- **Comprehensive Logs**: Execution logs with PR processing details

## Recent Enhancements (October 2025)

- ✅ **Enhanced Draft PR Detection**: Reliable detection using `pr.get('draft', False)`
- ✅ **Fixed Release Notes Parsing**: Correct DRAFT labeling in GitHub releases
- ✅ **Improved Skip Categorization**: Detailed reasons for skipped PRs
- ✅ **Accurate Statistics**: Proper counting and display of skipped PRs
- ✅ **Professional GitHub Releases**: Clean formatting with complete PR information

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

## License

This automation system follows the same license as the Bonsai project.

---

**Last Updated**: 2025-10-14
**System Version**: Weekly BonsaiPR Automation v1.0
