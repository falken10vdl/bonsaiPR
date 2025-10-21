# BonsaiPR

Weekly automated builds of Bonsai with merged pull requests from the IfcOpenShell repository.

## About

BonsaiPR provides **automated weekly releases** that include the latest community contributions from IfcOpenShell. Each build:

- ✅ **Merges Open Pull Requests**: Automatically integrates open PRs from the community
- 🎯 **Detects Draft PRs**: Skips draft PRs and provides detailed skip reasons
- 🌍 **Multi-Platform Builds**: Windows, Linux, macOS (Intel + Apple Silicon)
- 📊 **Comprehensive Reports**: Detailed documentation of merged PRs, build info, and statistics
- 🔒 **Source Transparency**: Complete source code available in fork branches
- 🤖 **Fully Automated**: Runs every Sunday at 2:00 AM UTC via cron

### What's Different from Official Bonsai?

- **Testing Ground**: PR authors can test their changes before official merge
- **Community PRs**: Includes experimental features from community contributors
- **Weekly Updates**: Fresh builds every week with latest PRs
- **Renamed to BonsaiPR**: To distinguish from official releases

## 📦 Download

### Latest Release

Visit the [Releases](https://github.com/falken10vdl/bonsaiPR/releases) page to download the latest weekly build.

### Available Platforms

Each release includes builds for:
- 🐧 **Linux (x64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDD-linux-x64.zip`
- 🍎 **macOS Intel (x64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDD-macos-x64.zip`
- 🍎 **macOS Apple Silicon (ARM64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDD-macos-arm64.zip`
- 🪟 **Windows (x64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDD-windows-x64.zip`

### Installation

1. Download the appropriate `.zip` file for your platform
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **Install...** and select the downloaded zip file
4. Enable the **BonsaiPR** addon in the list

### Documentation

Each release includes a complete README file (`README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt`) with:
- List of successfully merged PRs
- Failed merge attempts with reasons
- Skipped PRs (drafts, inaccessible repos)
- Build details and statistics
- Release and upload information

## 💻 Source Code

The complete source code for each release is available in the IfcOpenShell fork repository:

- **🔗 Fork Repository**: [falken10vdl/IfcOpenShell](https://github.com/falken10vdl/IfcOpenShell)
- **📂 Weekly Branches**: Look for branches named `weekly-build-0.8.4-alphaYYMMDD`
- **📥 Download Source**: Each branch can be downloaded as a ZIP archive
- **👨‍💻 For PR Authors**: Clone and checkout these branches to test your PRs alongside other community changes

### Example: Clone and Test

```bash
# Clone the fork repository
git clone https://github.com/falken10vdl/IfcOpenShell.git
cd IfcOpenShell

# Checkout the latest weekly build branch
git checkout weekly-build-0.8.4-alpha251021

# Your PR is now merged with other community PRs - test away!
```

## 🤖 Automation System

The weekly builds are powered by a comprehensive 3-stage automation system:

### Architecture

```
Stage 1: PR Merging (00_clone_merge_and_create_branch.py)
  └─→ Clones IfcOpenShell, merges open PRs, creates weekly branch
  └─→ Detects and skips draft PRs with detailed reasons
  └─→ Creates initial README report

Stage 2: Building (01_build_bonsaiPR_addons.py)
  └─→ Applies bonsai → bonsaiPR transformations
  └─→ Builds addons for 4 platforms (Linux, macOS x2, Windows)
  └─→ Appends build info to README report

Stage 3: Release (02_upload_to_falken10vdl.py)
  └─→ Creates GitHub release with semantic versioning
  └─→ Uploads 4 addon ZIPs + complete README
  └─→ Appends upload info to README report
```

### Key Features

- **🔒 Secure**: Token-based authentication via `.env` file (no password prompts)
- **🎯 Smart PR Detection**: Automatically skips draft PRs and inaccessible repositories
- **📈 Progressive Documentation**: README report grows through each stage
- **♻️ Idempotent**: Safe to re-run without duplicating assets
- **⏰ Scheduled**: Runs every Sunday at 2:00 AM UTC via cron
- **� Comprehensive Statistics**: Detailed PR merge, build, and upload statistics

### Project Structure

```
bonsaiPR/
├── README.md                    # This file
├── automation/
│   ├── .env                     # Environment configuration (create from .env.example)
│   ├── .env.example             # Template for configuration
│   ├── README.md                # Detailed automation documentation
│   ├── requirements.txt         # Python dependencies
│   ├── scripts/                 # 3 main automation scripts
│   │   ├── 00_clone_merge_and_create_branch.py
│   │   ├── 01_build_bonsaiPR_addons.py
│   │   └── 02_upload_to_falken10vdl.py
│   ├── src/                     # Orchestration system
│   │   ├── main.py              # Main entry point
│   │   └── config/              # Configuration management
│   ├── cron/                    # Scheduling
│   │   └── weekly-automation.cron
│   └── logs/                    # Execution logs
│       └── cron_*.log
```

### For Developers

Want to run your own BonsaiPR builds or modify the automation?

👉 **See [`automation/README.md`](./automation/README.md)** for:
- Complete setup instructions
- Environment configuration guide
- Manual testing procedures
- Cron installation steps
- Troubleshooting guide

## ⚠️ Important Notes

### Development Build Warning

- **⚠️ Alpha Status**: These are development builds with experimental features
- **🧪 Community PRs**: Contains unreviewed community contributions
- **🎯 Testing Purpose**: Intended for PR authors and testers, not production use
- **💾 Backup First**: Always backup your Blender projects before testing

### Reporting Issues

1. **For PR-specific issues**: Contact the PR author directly (see PR list in release README)
2. **For build/automation issues**: [Open an issue](https://github.com/falken10vdl/bonsaiPR/issues) in this repository
3. **For IfcOpenShell/Bonsai issues**: Report to the [official repository](https://github.com/IfcOpenShell/IfcOpenShell/issues)

## 📅 Release Schedule

- **Frequency**: Every Sunday at 2:00 AM UTC
- **Naming Pattern**: `v0.8.4-alphaYYMMDD` (e.g., `v0.8.4-alpha251021`)
- **What's Included**: All open, non-draft PRs from IfcOpenShell as of build time
- **Source Branch**: `weekly-build-0.8.4-alphaYYMMDD` in fork repository

## 🔗 Links

- **📦 Releases**: [github.com/falken10vdl/bonsaiPR/releases](https://github.com/falken10vdl/bonsaiPR/releases)
- **💻 Source Fork**: [github.com/falken10vdl/IfcOpenShell](https://github.com/falken10vdl/IfcOpenShell)
- **🏠 Upstream**: [github.com/IfcOpenShell/IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- **📋 Issues**: [github.com/falken10vdl/bonsaiPR/issues](https://github.com/falken10vdl/bonsaiPR/issues)

## 📄 License

This project is licensed under the same license as [Bonsai/IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell).

## 🤝 Contributing

Contributions to the automation system are welcome! See [`automation/README.md`](./automation/README.md) for details on how to modify and improve the build system.

---

**Current Version**: v0.8.4-alpha (based on IfcOpenShell v0.8.0 branch)  
**Python Target**: 3.11  
**Last Updated**: October 21, 2025