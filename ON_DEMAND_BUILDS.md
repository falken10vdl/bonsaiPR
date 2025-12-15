# On-Demand Builds Guide

BonsaiPR supports **on-demand builds** in addition to the weekly automated releases. This allows you to create custom builds with the latest PRs at any time, not just on Sundays.

## 🎯 What are On-Demand Builds?

On-demand builds are manual builds triggered whenever you need the absolute latest changes:

- **🔄 Latest PRs**: Includes all PRs merged since the last weekly build
- **⚡ Immediate**: No need to wait until Sunday at 2:00 AM UTC
- **🧪 Testing**: Perfect for testing urgent fixes or new features
- **📦 Same Quality**: Uses the same 3-stage automation as weekly builds

## 🚀 Quick Start

### Prerequisites

1. **Linux System**: The build process requires a Linux environment
2. **Python 3.11+**: Ensure Python is installed
3. **Dependencies**: Install required packages (see [Setup](#setup) below)
4. **GitHub Token**: Required for creating releases (stored in `.env` file)

### Setup

1. **Clone the Repository**
   ```bash
   cd ~/bonsaiPRDevel
   git clone https://github.com/falken10vdl/bonsaiPR.git
   cd bonsaiPR/automation
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Copy the example configuration
   cp .env.example .env
   
   # Edit .env and set your GitHub token
   nano .env  # or use your preferred editor
   ```

   Required `.env` settings:
   ```bash
   GITHUB_TOKEN=your_github_token_here
   BUILD_BASE_DIR=/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build
   REPORT_PATH=/home/falken10vdl/bonsaiPRDevel
   IFCOPENSHELL_REPO_DIR=/home/falken10vdl/bonsaiPRDevel/IfcOpenShell
   ```

4. **Verify Setup**
   ```bash
   cd scripts
   python 00_clone_merge_and_create_branch.py --help
   ```

## 🔨 Running an On-Demand Build

### Complete Build (All 3 Stages)

The simplest way is to run all three stages sequentially:

```bash
cd ~/bonsaiPRDevel/bonsaiPR/automation/scripts

# Stage 1: Clone and merge PRs
python 00_clone_merge_and_create_branch.py

# Stage 2: Build addons (takes 10-15 minutes)
python 01_build_bonsaiPR_addons.py

# Stage 3: Upload to GitHub releases
python 02_upload_to_falken10vdl.py
```

**Expected Duration**: 15-20 minutes total

### Using the Orchestration System

Alternatively, use the main orchestrator (recommended for production):

```bash
cd ~/bonsaiPRDevel/bonsaiPR/automation/src
python main.py
```

This runs all three stages automatically with comprehensive logging.

## 📋 What Happens During a Build

### Stage 1: PR Merging (00_clone_merge_and_create_branch.py)

**What it does:**
- Fetches latest changes from IfcOpenShell v0.8.0 branch
- Retrieves all open pull requests via GitHub API
- Attempts to merge PRs in ascending order (oldest first)
- Skips draft PRs and those with conflicts
- Creates a new branch: `weekly-build-0.8.4-alphaYYMMDDHHMM`
- Generates initial README report with merge statistics

**Output:**
- New branch in `falken10vdl/IfcOpenShell` fork
- `README-bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM.txt` in reports directory
- Console output showing which PRs were merged/skipped/failed

**Example Output:**
```
✅ Successfully applied: 25 PRs
❌ Failed to apply: 5 PRs
⚠️  Skipped (draft/repo issues): 26 PRs
```

### Stage 2: Building (01_build_bonsaiPR_addons.py)

**What it does:**
- Clones/updates the build repository
- Checks out the newly created PR-merged branch
- Applies comprehensive bonsai → bonsaiPR transformations:
  - Renames files, directories, and internal references
  - Updates branding and metadata
  - Fixes dependency paths
- Builds addons for 4 platforms using Makefile:
  - 🐧 Linux (x64)
  - 🍎 macOS Intel (x64)
  - 🍎 macOS Apple Silicon (ARM64)
  - 🪟 Windows (x64)
- Appends build information to README report

**Output:**
- 4 platform-specific `.zip` files in `dist/` directory
- Updated README with build details
- Build logs showing progress for each platform

**Build Time:** ~10-15 minutes

### Stage 3: Release & Upload (02_upload_to_falken10vdl.py)

**What it does:**
- Creates a new GitHub release with tag `v0.8.4-alphaYYMMDDHHMM`
- Uploads all 4 platform addon files
- Uploads the complete README report as documentation
- Generates release description from merged PR list
- Appends upload information to README report

**Output:**
- New release visible at: `https://github.com/falken10vdl/bonsaiPR/releases`
- Release includes:
  - 4 addon ZIP files
  - Complete README documentation
  - PR statistics and links
  - Source branch reference

## 🔍 Monitoring Build Progress

### Real-Time Console Output

Each script provides detailed console output:

```bash
# Stage 1 Output
Found 56 open pull requests
✅ Successfully applied PR #4862
⚠️  Skipping PR #643: PR is in DRAFT status
❌ Failed to apply PR #7316: Merge conflict

# Stage 2 Output
Building for platform: linux
✅ Linux build completed: 146,196,410 bytes
Building for platform: macos-arm64
...

# Stage 3 Output
Creating GitHub release: v0.8.4-alpha2512141830
✅ Successfully uploaded bonsaiPR_py311-0.8.4-alpha251214-linux-x64.zip
...
```

### Log Files

When using the orchestrator (`main.py`), logs are saved to:
```
automation/logs/automation_YYYYMMDD_HHMMSS.log
```

### Progress Indicators

- **Stage 1**: PR merge progress with success/fail indicators
- **Stage 2**: Platform-by-platform build progress
- **Stage 3**: File upload progress with size information

## ⚠️ Troubleshooting

### Common Issues

#### 1. Build Fails with Version Variable Error

**Error:** `cannot access local variable 'version' where it is not associated with a value`

**Solution:** This was fixed in recent commits. Pull the latest changes:
```bash
cd ~/bonsaiPRDevel/bonsaiPR
git pull origin main
```

#### 2. GitHub Token Authentication Fails

**Error:** `GITHUB_TOKEN not found in environment variables`

**Solution:** 
1. Check your `.env` file exists in `automation/` directory
2. Verify `GITHUB_TOKEN=your_token` is set correctly
3. Ensure the token has `repo` scope permissions

#### 3. README File Not Found

**Error:** `No existing README found from clone script`

**Solution:** Run Stage 1 first - it creates the initial README file.

#### 4. Build Directory Not Found

**Error:** `The built addons directory does not exist`

**Solution:** Check `BUILD_BASE_DIR` in `.env` points to correct location:
```bash
BUILD_BASE_DIR=/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build
```

#### 5. Permission Denied Errors

**Solution:** Ensure scripts are executable:
```bash
chmod +x ~/bonsaiPRDevel/bonsaiPR/automation/scripts/*.py
```

### Debug Mode

For detailed debugging, check the logs:
```bash
# View latest log
tail -f ~/bonsaiPRDevel/bonsaiPR/automation/logs/automation_*.log

# Search for errors
grep -i error ~/bonsaiPRDevel/bonsaiPR/automation/logs/automation_*.log
```

## 📊 Understanding Build Artifacts

### README Report File

The README file grows through each stage:

**After Stage 1:**
- PR merge statistics
- List of successfully merged PRs with links
- Failed PRs with failure reasons
- Skipped PRs with skip reasons
- Source commit hash

**After Stage 2:**
- Build details (date, version, method)
- List of built addon files with sizes
- Platform breakdown

**After Stage 3:**
- Upload timestamp and release URL
- Asset list with download links
- Complete workflow documentation

### Addon Files

Each platform gets a specific addon file:
- **Naming**: `bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM-{platform}.zip`
- **Size**: 120-150 MB depending on platform
- **Contents**: Complete BonsaiPR addon ready for Blender installation

### Source Branch

The merged source code is available in the fork:
- **Repository**: `https://github.com/falken10vdl/IfcOpenShell`
- **Branch**: `weekly-build-0.8.4-alphaYYMMDDHHMM`
- **Purpose**: Transparency, testing, and debugging

## 🔧 Advanced Usage

### Building Specific Platforms Only

Modify `01_build_bonsaiPR_addons.py` to comment out unwanted platforms:

```python
# In the build function, comment platforms you don't need:
# build_addon('macos')         # Skip macOS Intel
# build_addon('macosm1')       # Skip macOS ARM
build_addon('linux')           # Build only Linux
# build_addon('windows')       # Skip Windows
```

### Testing Without Upload

Run stages 1 and 2, but skip stage 3 to avoid creating a release:

```bash
python 00_clone_merge_and_create_branch.py
python 01_build_bonsaiPR_addons.py
# Skip stage 3 - no release created
```

### Excluding Specific PRs

Add PR numbers to the exclusion list in `.env`:

```bash
EXCLUDED=5452,1234,5678
```

These PRs will be skipped even if they're open and not draft.

### Manual Release Upload

If stage 3 fails mid-upload, you can manually upload remaining assets:

1. Go to: `https://github.com/falken10vdl/bonsaiPR/releases`
2. Find the draft release
3. Click "Edit"
4. Upload missing addon files from `bonsaiPR-build/src/bonsaiPR/dist/`
5. Click "Update release"

## 🔄 Workflow Best Practices

### Before Starting a Build

1. **Check Disk Space**: Builds require ~5GB free space
   ```bash
   df -h /home/falken10vdl/bonsaiPRDevel
   ```

2. **Check for New PRs**: Visit [IfcOpenShell PRs](https://github.com/IfcOpenShell/IfcOpenShell/pulls)

3. **Review Recent Changes**: Check if there are important updates since last build

### During the Build

- **Don't interrupt** Stage 2 (building) - it can corrupt the build
- **Monitor console** for any error messages
- **Stage 1 is safe to retry** if it fails
- **Stage 3 is idempotent** - safe to re-run if upload fails

### After the Build

1. **Verify Release**: Check `https://github.com/falken10vdl/bonsaiPR/releases`
2. **Test One Platform**: Download and test in Blender
3. **Announce**: Share the release link with PR authors
4. **Clean Up**: Optionally remove old build directories to save space

## 📅 When to Use On-Demand Builds

### Good Reasons

- ✅ Important bug fix merged that users need immediately
- ✅ New feature PR merged and author wants to test with other PRs
- ✅ Weekly build had issues and you need a clean rebuild
- ✅ Testing before the scheduled Sunday build
- ✅ Multiple new PRs merged since last build

### Less Ideal Reasons

- ❌ Just to have the latest version (wait for Sunday)
- ❌ No new PRs have been merged
- ❌ Testing a single PR (use the PR's branch directly)

## 🔗 Related Documentation

- **[Main README](../README.md)**: Overview of BonsaiPR project
- **[Automation README](../automation/README.md)**: Detailed automation system documentation
- **[Releases](https://github.com/falken10vdl/bonsaiPR/releases)**: Download existing builds

## 💡 Tips & Tricks

### Speed Up Builds

- Run on a system with SSD storage
- Use a multi-core CPU (builds use parallel compilation)
- Ensure good internet connection for PR fetching and uploads

### Reduce Storage Usage

After a successful build, you can delete:
```bash
# Remove build artifacts (keeps dist/)
rm -rf ~/bonsaiPRDevel/bonsaiPR-build/src/bonsaiPR/build/

# Remove very old README reports
find ~/bonsaiPRDevel -name "README-bonsaiPR*.txt" -mtime +30 -delete
```

### Verify Build Integrity

Compare file sizes with previous builds:
```bash
ls -lh ~/bonsaiPRDevel/bonsaiPR-build/src/bonsaiPR/dist/
```

Expected sizes:
- Linux: ~140-150 MB
- macOS (both): ~130-140 MB
- Windows: ~115-125 MB

---

**Need Help?** Open an issue at: https://github.com/falken10vdl/bonsaiPR/issues
