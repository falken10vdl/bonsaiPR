# BonsaiPR Automation System

This directory contains the complete automation system for on-demand BonsaiPR builds.

## 🆕 On-Demand Build System

**NEW:** The automation now runs on-demand, building only when PRs change! See [ON_DEMAND_BUILDS.md](ON_DEMAND_BUILDS.md) for the complete guide.

## Overview

The BonsaiPR automation system performs builds that:
1. Merge latest pull requests from IfcOpenShell repository
2. Build BonsaiPR addons for multiple platforms (Linux, macOS, Windows)
3. Create GitHub releases with comprehensive documentation
4. Upload complete source code for developer access
5. **Automatically retry with reversed PR order** if conflicts are detected

### 🔄 Intelligent Retry System

After each successful build, the system checks if any PRs were skipped due to conflicts with other PRs. When detected:
- Automatically runs the merge step again with reversed PR order (newest first)
- **Verifies that previously skipped PRs are now merged**
- **Only generates a second release if the retry actually includes new PRs**
- Skips redundant releases when retry doesn't improve results
- Ensures PR authors can test their contributions when they become available

## Directory Structure

```
automation/
├── .env                # Environment configuration (create from .env.example)
├── .env.example        # Template for environment variables
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── scripts/            # Main automation scripts
│   ├── 00_clone_merge_and_create_branch.py  # PR merging with draft detection
│   ├── 01_build_bonsaiPR_addons.py          # Multi-platform addon building
│   └── 02_upload_to_falken10vdl.py          # GitHub release management
├── src/                # Main orchestration system
│   ├── main.py         # Automation orchestrator and entry point
│   └── config/         # Configuration management
│       ├── __init__.py
│       └── settings.py # Central configuration file
├── cron/               # Cron job configuration
│   └── weekly-automation.cron  # Weekly scheduling template
└── logs/               # Log directory (created automatically)
    └── cron_*.log      # Cron execution logs with timestamps
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- Git
- GitHub personal access token with repo permissions
- Build environment for IfcOpenShell (make, gcc, etc.)
- Required system packages for building addons

### 2. Environment Configuration

1. **Create `.env` file from template**:
   ```bash
   cd automation
   cp .env.example .env
   ```

2. **Edit `.env` file** with your configuration:
   ```bash
   # GitHub Configuration
   GITHUB_TOKEN=ghp_your_actual_token_here
   
   # Local Paths (example values shown)
   BASE_CLONE_DIR=/home/falken10vdl/bonsaiPRDevel/IfcOpenShell
   WORKING_DIR=/home/falken10vdl/bonsaiPRDevel/MergingPR
   REPORT_PATH=/home/falken10vdl/bonsaiPRDevel
   BUILD_BASE_DIR=/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build
   
   # Optional: Filter by specific usernames (leave empty for all)
   USERNAMES=""
   ```

3. **Important**: The `.env` file contains your GitHub token - keep it secure and never commit it to git

### 3. Install Dependencies

```bash
cd automation
pip install -r requirements.txt
```

Required packages:
- `python-dotenv` - Environment variable management
- `requests` - GitHub API interactions
- `PyGithub` (optional) - Enhanced GitHub API support

### 4. Create Required Directories

```bash
# Create logs directory for cron output
mkdir -p logs

# Verify directory structure
ls -la
```

### 5. Manual Testing

**Option A: Using the Main Orchestrator (Recommended)**
```bash
# Run the complete automation system
cd automation/src
python main.py
```

**Option B: Individual Script Testing**
```bash
cd automation/scripts

# Step 1: Test PR merging with draft detection
python 00_clone_merge_and_create_branch.py

# Step 2: Test addon building
python 01_build_bonsaiPR_addons.py

# Step 3: Test GitHub release creation
python 02_upload_to_falken10vdl.py
```

### 6. Schedule Automation

**Option A: Using Cron (Recommended for Production)**
```bash
# Navigate to the bonsaiPR directory
cd /home/falken10vdl/bonsaiPRDevel/bonsaiPR

# Install the cron job (runs weekly on Sunday at 2 AM UTC)
crontab automation/cron/weekly-automation.cron

# Verify cron installation
crontab -l
```

**Option B: Manual Execution**
```bash
# Run the complete automation system manually
cd /home/falken10vdl/bonsaiPRDevel/bonsaiPR/automation/src
python main.py
```

**View Logs**:
```bash
# View the latest cron log
ls -lt automation/logs/ | head -n 2
tail -f automation/logs/cron_*.log
```

## Script Details

### 00_clone_merge_and_create_branch.py - PR Merge & Branch Creation

**Purpose**: Merges open PRs from IfcOpenShell and creates weekly branches

**Key Features**:
- Clones/updates IfcOpenShell repository to `BASE_CLONE_DIR`
- Fetches open pull requests via GitHub API with authentication
- **Enhanced draft PR detection** using `pr.get('draft', False)`
- Attempts to merge each PR automatically with comprehensive error handling
- **Skips draft PRs and inaccessible repos** with detailed skip reasons:
  - 'DRAFT status' - PR marked as draft
  - 'Repository no longer accessible (deleted fork)' - Fork deleted
  - 'Missing required PR information' - Incomplete PR data
- **Supports reversed PR order** with `--reverse` flag (newest first)
- Creates weekly branches: `weekly-build-0.8.4-alphaYYMMDD`
- Generates initial report: `README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt`
- **Uses GitHub token from .env for authentication** (no password prompts)

**Output**:
- New branch pushed to fork: `falken10vdl/IfcOpenShell`
- Initial merge report with PR statistics

### 01_build_bonsaiPR_addons.py - Multi-Platform Build

**Purpose**: Builds BonsaiPR addons for all supported platforms

**Key Features**:
- Copies source from `BASE_CLONE_DIR` to `BUILD_BASE_DIR`
- Applies text transformations: `bonsai` → `bonsaiPR`
- Renames directory: `src/bonsai/` → `src/bonsaiPR/`
- Builds addons for multiple platforms:
  - 🐧 Linux x64
  - 🍎 macOS Intel (x64)
  - 🍎 macOS Apple Silicon (ARM64)
  - 🪟 Windows x64
- Uses Python 3.11 target
- Creates distributable zip files in `dist/` directory
- **Appends build information to existing README report**

**Output**:
- Built addon ZIP files: `bonsaiPR_py311-0.8.4-alphaYYMMDD-{platform}.zip`
- Updated README report with build details

### 02_upload_to_falken10vdl.py - GitHub Release Management

**Purpose**: Creates GitHub releases and uploads all assets

**Key Features**:
- Creates GitHub releases with semantic versioning: `v0.8.4-alphaYYMMDD`
- Uploads addon files as release assets (4 platform ZIP files)
- **Uploads complete README** (no redundant report file)
- **Enhanced release notes** with proper DRAFT PR labeling
- **Fixed parsing logic** to correctly show skipped PRs with "(DRAFT)" labels
- Generates rich markdown descriptions with complete PR categorization
- Shows accurate statistics: "⚠️ Skipped PRs (X)" with detailed skip reasons
- Handles existing releases gracefully (skips duplicate uploads)
- **Appends upload information to existing README report**
- **Uses GitHub token from .env for Git operations** (no password prompts)

**Output**:
- GitHub release at: `github.com/falken10vdl/bonsaiPR/releases`
- Uploaded assets: 4 addon ZIPs + 1 complete README
- Final README report with all three sections (merge + build + upload)

## Automation System Architecture

The BonsaiPR automation system consists of **3 main scripts** orchestrated by `main.py`:

### Execution Flow:
```
main.py (orchestrator)
  ↓
  ├─→ 00_clone_merge_and_create_branch.py
  │   └─→ Creates: README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt (initial)
  │
  ├─→ 01_build_bonsaiPR_addons.py
  │   └─→ Appends to: README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt (build info)
  │
  └─→ 02_upload_to_falken10vdl.py
      └─→ Appends to: README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt (upload info)
      └─→ Uploads: Complete README + 4 addon ZIPs to GitHub release
```

### Configuration Management:
- All scripts use `.env` file for configuration (GitHub token, paths, etc.)
- **Token-based authentication** eliminates password prompts
- **Centralized environment variables** for easy updates
- Settings loaded via `python-dotenv` library

### README Report Evolution:
The README report file grows through each stage:
1. **After script 00**: PR merge information
2. **After script 01**: + Build details
3. **After script 02**: + Upload/release information
4. **Final upload**: Complete README with all sections as GitHub release asset

## Features

- **🔒 Secure Authentication**: Token-based Git operations (no password prompts)
- **📋 Enhanced Draft PR Detection**: Automatically detects and skips draft PRs using `pr.get('draft', False)`
- **📊 Comprehensive Skip Reasons**: Detailed categorization of why PRs are skipped
- **📝 Progressive Documentation**: README report grows through each automation stage
- **🎯 Smart Asset Management**: Uploads complete README only (no redundant files)
- **🌍 Multi-Platform Builds**: Supports Linux, macOS (Intel + ARM), and Windows
- **🔍 Source Transparency**: Complete source code available in fork branches
- **🛡️ Robust Error Handling**: Graceful handling of network issues and conflicts
- **📈 Detailed Statistics**: Comprehensive PR merge, build, and upload statistics
- **♻️ Idempotent Operations**: Safe to re-run without duplicating assets

## Output

The automation produces:

### 1. GitHub Release Assets:
- **4 Platform Addons**:
  - `bonsaiPR_py311-0.8.4-alphaYYMMDD-linux-x64.zip`
  - `bonsaiPR_py311-0.8.4-alphaYYMMDD-macos-x64.zip`
  - `bonsaiPR_py311-0.8.4-alphaYYMMDD-macos-arm64.zip`
  - `bonsaiPR_py311-0.8.4-alphaYYMMDD-windows-x64.zip`
- **1 Complete README**: `README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt`

### 2. Local Files:
- **README Report**: `REPORT_PATH/README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt`
- **Cron Logs**: `automation/logs/cron_YYYYMMDD_HHMMSS.log`

### 3. GitHub Resources:
- **Release**: `github.com/falken10vdl/bonsaiPR/releases/tag/v0.8.4-alphaYYMMDD`
- **Source Branch**: `github.com/falken10vdl/IfcOpenShell/tree/weekly-build-0.8.4-alphaYYMMDD`

## Recent Enhancements (October 2025)

### Authentication & Security:
- ✅ **Token-based Git Authentication**: Uses `.env` file for GitHub token (no password prompts)
- ✅ **Secure Configuration**: Environment variables for all sensitive data
- ✅ **No Hardcoded Credentials**: All tokens/paths in `.env` file

### PR Processing:
- ✅ **Enhanced Draft PR Detection**: Reliable detection using `pr.get('draft', False)`
- ✅ **Fixed Release Notes Parsing**: Correct DRAFT labeling in GitHub releases
- ✅ **Improved Skip Categorization**: Detailed reasons for skipped PRs
- ✅ **Accurate Statistics**: Proper counting and display of skipped PRs

### Documentation & Assets:
- ✅ **Progressive README Reports**: Report grows through each automation stage
- ✅ **Smart Asset Management**: Complete README uploaded (no redundant files)
- ✅ **Professional GitHub Releases**: Clean formatting with complete PR information

## Weekly Schedule

The automation runs every **Sunday at 2:00 AM UTC** via cron:

```cron
0 2 * * 0 cd /home/falken10vdl/bonsaiPRDevel/bonsaiPR/automation/src && python3 main.py >> ../logs/cron_$(date +\%Y\%m\%d_\%H\%M\%S).log 2>&1
```

**Build Naming Pattern**: `v0.8.4-alphaYYMMDD` (e.g., `v0.8.4-alpha251021`)

## Troubleshooting

### Common Issues:

1. **"Username for 'https://github.com'" prompt**:
   - **Cause**: GitHub token not loaded from `.env` file
   - **Solution**: Ensure `.env` file exists in `automation/` directory with `GITHUB_TOKEN` set
   - **Verify**: Check that scripts use `load_dotenv()` at the top

2. **"No such file or directory: '../logs'"**:
   - **Cause**: Logs directory doesn't exist
   - **Solution**: Create directory: `mkdir -p /home/falken10vdl/bonsaiPRDevel/bonsaiPR/automation/logs`

3. **GitHub API Rate Limits**:
   - **Cause**: Too many API requests without authentication
   - **Solution**: Ensure your token is properly set in `.env` and has `repo` scope

4. **Build Failures**:
   - **Cause**: Missing IfcOpenShell build dependencies
   - **Solution**: Install: `sudo apt-get install build-essential python3-dev` (Linux)
   - **Check**: Verify `make` and `gcc` are available

5. **Network/Upload Issues**:
   - **Cause**: Temporary network problems or GitHub API issues
   - **Solution**: Scripts include retry logic; check logs for details
   - **Manual retry**: Re-run `02_upload_to_falken10vdl.py` (safe, skips duplicates)

6. **Permission Issues**:
   - **Cause**: Insufficient file/directory permissions
   - **Solution**: Ensure proper ownership: `chown -R $USER:$USER /home/falken10vdl/bonsaiPRDevel`

### Viewing Logs:

```bash
# View latest cron log
ls -lt automation/logs/ | head -n 2

# Follow log in real-time
tail -f automation/logs/cron_*.log

# Search for errors
grep -i error automation/logs/cron_*.log

# View specific script output
grep "00_clone_merge" automation/logs/cron_*.log
```

### Testing Individual Components:

```bash
# Test configuration loading
cd automation/scripts
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Token:', 'Found' if os.getenv('GITHUB_TOKEN') else 'Missing')"

# Test GitHub API access
python3 -c "from dotenv import load_dotenv; import os; import requests; load_dotenv(); r = requests.get('https://api.github.com/user', headers={'Authorization': f'token {os.getenv(\"GITHUB_TOKEN\")}'}); print('API Status:', r.status_code, r.json().get('login', 'Error'))"

# Test each script individually (see section 5 above)
```

## Environment Variables Reference

Complete list of environment variables used (from `.env` file):

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `GITHUB_TOKEN` | GitHub API authentication | `ghp_xxxxxxxxxxxx` |
| `BASE_CLONE_DIR` | IfcOpenShell clone location | `/home/falken10vdl/bonsaiPRDevel/IfcOpenShell` |
| `WORKING_DIR` | Working directory for merges | `/home/falken10vdl/bonsaiPRDevel/MergingPR` |
| `REPORT_PATH` | README report output directory | `/home/falken10vdl/bonsaiPRDevel` |
| `BUILD_BASE_DIR` | BonsaiPR build directory | `/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build` |
| `USERNAMES` | Filter PRs by author (optional) | `""` (empty = all authors) |

## Project Links

- **Main Repository**: [github.com/falken10vdl/bonsaiPR](https://github.com/falken10vdl/bonsaiPR)
- **Fork Repository**: [github.com/falken10vdl/IfcOpenShell](https://github.com/falken10vdl/IfcOpenShell)
- **Upstream**: [github.com/IfcOpenShell/IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- **Releases**: [github.com/falken10vdl/bonsaiPR/releases](https://github.com/falken10vdl/bonsaiPR/releases)

## Contributing

To modify the automation:

1. Update scripts in `automation/scripts/`
2. Update orchestrator in `automation/src/main.py`
3. Test locally before committing
4. Push changes to `falken10vdl/bonsaiPR` repository
5. Changes take effect on next scheduled run

## License

This automation system follows the same license as the Bonsai project.

## Support

For issues or questions:
- Open an issue at [github.com/falken10vdl/bonsaiPR/issues](https://github.com/falken10vdl/bonsaiPR/issues)
- Check logs in `automation/logs/` for detailed error information
- Review the troubleshooting section above

---

**Last Updated**: 2025-10-21
**System Version**: Weekly BonsaiPR Automation v2.0
**Python Version**: 3.11+
**Build Target**: v0.8.4-alpha
