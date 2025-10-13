# BonsaiPR

Weekly automated builds of Bonsai with merged pull requests from the IfcOpenShell repository.

## About

This repository contains automated weekly releases of BonsaiPR, which includes:
- Latest merged pull requests from the community
- Multi-platform builds (Windows, Linux, macOS)
- Detailed reports of included changes

## Download

Check the [Releases](https://github.com/falken10vdl/bonsaiPR/releases) page for the latest builds.

## Automation System

The weekly builds are powered by a comprehensive automation system located in the [`automation/`](./automation/) folder:

- **🤖 Automated PR Merging**: Automatically merges open pull requests from IfcOpenShell
- **🏗️ Multi-Platform Builds**: Builds addons for Linux, macOS, and Windows  
- **📦 GitHub Releases**: Creates releases with downloadable addons and detailed reports
- **⏰ Weekly Schedule**: Runs every Sunday at 2:00 AM UTC via cron
- **📁 [`source/`](./source/)**: Contains the complete IfcOpenShell source code with all merged PRs
- **📝 Detailed Reports**: Check the weekly reports (e.g., `README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt`) for lists of merged PRs

**For developers:** See [`automation/README.md`](./automation/README.md) for complete setup and usage instructions.

## Important Notes

⚠️ These are development builds and may contain experimental features.
Use at your own risk in production environments.
