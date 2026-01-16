# BonsaiPR

On-demand builds of Bonsai with merged pull requests from the IfcOpenShell repository.

## About

BonsaiPR provides **on-demand builds** that include the latest community contributions from IfcOpenShell. Each build:

- ✅ **Merges Open Pull Requests**: Automatically integrates open PRs from the community
- 🎯 **Detects Draft PRs**: Skips draft PRs and provides detailed skip reasons
- 🌍 **Multi-Platform Builds**: Windows, Linux, macOS (Intel + Apple Silicon)
- 📊 **Comprehensive Reports**: Detailed documentation of merged PRs, build info, and statistics
- 🔒 **Source Transparency**: Complete source code available in fork branches
- ⚡ **On-Demand Builds**: Create custom builds anytime with latest PRs

### What's Different from Official Bonsai?


## 📦 Download
# Installation with automated updates

To enable automated updates for the bonsaiPR extension in Blender, open Blender and go to **Edit > Preferences**.
<p align="center">
<img src="https://github.com/falken10vdl/bonsaiPR/raw/main/images/blender_addons_disable_bonsai.png">
</p>


0. Click on **Add-ons** in the left sidebar and disable **Bonsai** if it is enabled.
<p align="center">
<img src="https://github.com/falken10vdl/bonsaiPR/raw/main/images/blender_extensions_1.png">
</p>

1. Click on **Get Extensions** in the left sidebar.

2. In the top right, click the **Repositories** dropdown 

3. and then the **plus (+) icon**.

<p align="center">
<img src="https://github.com/falken10vdl/bonsaiPR/raw/main/images/blender_extensions_2.png">
</p>

4. Select **Add Remote Repository**.

5. Enter the following URL: [https://raw.githubusercontent.com/falken10vdl/bonsaiPR/refs/heads/main/index.json](https://raw.githubusercontent.com/falken10vdl/bonsaiPR/refs/heads/main/index.json)

6. Make sure "Check for Updates on Startup" is enabled. Click **Create**

The repository will now appear in the list:
<p align="center">
<img src="https://github.com/falken10vdl/bonsaiPR/raw/main/images/blender_extensions_repo_added.png">
</p>

7. Under **Get Extensions**, type `bonsai` in the search panel and look for **BonsaiPR**. Click **Install**.
<p align="center">
<img src="https://github.com/falken10vdl/bonsaiPR/raw/main/images/blender_extensions_install_bonsaipr.png">
</p>

Blender will automatically check for updates to the bonsaiPR extension.

> ⚠️ **Warning:** You must enable either **Bonsai** or **BonsaiPR**, but **not both at the same time** in Blender. Enabling both can cause conflicts or unexpected behavior.

8. Now go to **Add-ons**. You should see **BonsaiPR** enabled and **Bonsai** disabled.
<p align="center">
<img src="https://github.com/falken10vdl/bonsaiPR/raw/main/images/blender_addons_bonsaipr_enabled.png">
</p>
Restart Blender and enjoy!

# Download

### Latest Release

Visit the [Releases](https://github.com/falken10vdl/bonsaiPR/releases) page to download the latest build.

### Creating Builds

- **⚡ On-Demand Builds**: Create builds manually with the latest PRs - see [On-Demand Builds Guide](ON_DEMAND_BUILDS.md)

### Available Platforms

Each release includes builds for:
- 🐧 **Linux (x64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM-linux-x64.zip`
- 🍎 **macOS Intel (x64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM-macos-x64.zip`
- 🍎 **macOS Apple Silicon (ARM64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM-macos-arm64.zip`
- 🪟 **Windows (x64)**: `bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM-windows-x64.zip`

### Manual Installation

1. Download the appropriate `.zip` file for your platform
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **Install...** and select the downloaded zip file
4. Enable the **BonsaiPR** addon in the list

### Documentation

Each release includes a complete README file (`README-bonsaiPR_py311-0.8.4-alphaYYMMDDHHMM.txt`) with:
- List of successfully merged PRs
- Failed merge attempts with reasons
- Skipped PRs (drafts, inaccessible repos)
- Build details and statistics
- Release and upload information

## 💻 Source Code

The complete source code for each release is available in the IfcOpenShell fork repository:

- **🔗 Fork Repository**: [falken10vdl/IfcOpenShell](https://github.com/falken10vdl/IfcOpenShell)
- **📂 Build Branches**: Look for branches named `weekly-build-0.8.4-alphaYYMMDDHHMM`
- **📥 Download Source**: Each branch can be downloaded as a ZIP archive
- **👨‍💻 For PR Authors**: Clone and checkout these branches to test your PRs alongside other community changes

### Example: Clone and Test

```bash
# Clone the fork repository
git clone https://github.com/falken10vdl/IfcOpenShell.git
cd IfcOpenShell

# Checkout the latest build branch
git checkout weekly-build-0.8.4-alpha2512141830

# Your PR is now merged with other community PRs - test away!
```

## 🤖 Automation System

The builds are powered by a comprehensive 3-stage automation system:

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

👉 **See [`ON_DEMAND_BUILDS.md`](./ON_DEMAND_BUILDS.md)** for:
- Quick start guide for manual builds
- Complete build process walkthrough
- Troubleshooting common issues
- Advanced usage and customization

👉 **See [`automation/README.md`](./automation/README.md)** for:
- Complete automation system architecture
- Environment configuration guide
- Development and debugging guide

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

## 📅 Build Information

### On-Demand Builds
- **Frequency**: Anytime when needed (urgent fixes, new features, testing)
- **Naming Pattern**: `v0.8.4-alphaYYMMDDHHMM` (includes date, hour, and minute)
- **How to Create**: See [On-Demand Builds Guide](ON_DEMAND_BUILDS.md)
- **What's Included**: All open, non-draft PRs from IfcOpenShell as of build time
- **Source Branch**: `build-0.8.4-alphaYYMMDDHHMM` in fork repository
- **Use Cases**: Testing latest PRs, urgent bug fixes, custom testing scenarios

## 🔗 Links

- **📦 Releases**: [github.com/falken10vdl/bonsaiPR/releases](https://github.com/falken10vdl/bonsaiPR/releases)
- **⚡ On-Demand Builds**: [ON_DEMAND_BUILDS.md](./ON_DEMAND_BUILDS.md)
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
**Last Updated**: December 15, 2025
