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

**Last Updated**: 2025-10-13
**System Version**: Weekly BonsaiPR Automation v1.0
