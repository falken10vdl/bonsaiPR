# BonsaiPR

Weekly automated builds of Bonsai with merged pull requests from the IfcOpenShell repository.

## About

This repository contains automated weekly releases of BonsaiPR, which includes:
- Latest merged pull requests from the community
- Multi-platform builds (Windows, Linux, macOS)
- Detailed reports of included changes

## Download

Check the [Releases](https://github.com/falken10vdl/bonsaiPR/releases) page for the latest builds.

## Source Code

The complete source code for each release is available in the IfcOpenShell fork repository:

- **🔗 Latest Weekly Build**: [falken10vdl/IfcOpenShell](https://github.com/falken10vdl/IfcOpenShell) (weekly-build branches)
- **📥 Browse Current Week**: Check the latest `weekly-build-0.8.4-alphaYYMMDD` branch
- **👨‍💻 For PR Authors**: Use these branches to test your PRs with other merged changes

## Automation System

The weekly builds are powered by a comprehensive automation system located in the [`automation/`](./automation/) folder:

- **🤖 Automated PR Merging**: Automatically merges open pull requests from IfcOpenShell
- **🏗️ Multi-Platform Builds**: Builds addons for Linux, macOS, and Windows with 16-core optimization
- **📦 GitHub Releases**: Creates releases with downloadable addons and detailed reports
- **⏰ Weekly Schedule**: Runs every Sunday at 2:00 AM UTC via cron
- **📝 Detailed Reports**: Check the weekly reports (e.g., `README-bonsaiPR_py311-0.8.4-alphaYYMMDD.txt`) for lists of merged PRs

**For developers:** See [`automation/README.md`](./automation/README.md) for complete setup and usage instructions.

## Important Notes

⚠️ These are development builds and may contain experimental features.
Use at your own risk in production environments.

## License

This project is licensed under the same license as [bonsai](https://github.com/IfcOpenShell/IfcOpenShell) .