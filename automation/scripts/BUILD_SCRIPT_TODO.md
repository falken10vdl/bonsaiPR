# TODO: 01_build_bonsaiPR_addons.py

The build script needs to be recreated with the following functionality:

1. Copy source from IfcOpenShell to bonsaiPR-build directory
2. Replace "bonsai" with "bonsaiPR" throughout the codebase
3. Rename src/bonsai/ directory to src/bonsaiPR/
4. Build multi-platform addon zip files
5. Place results in src/bonsaiPR/dist/

This script was working before but got corrupted during file operations.
The working version should be recreated based on the functionality 
that was previously implemented.

Key functions needed:
- copy_source_for_bonsaiPR_build()
- replace_bonsai_with_bonsaiPR() 
- build_addons()
- main() orchestration

Platform targets:
- linux-x64
- windows-x64  
- macos-x64
- macos-arm64