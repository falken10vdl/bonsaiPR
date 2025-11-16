#!/usr/bin/env python3
"""
BonsaiPR Addon Build Script
===========================

This script handles the build process for BonsaiPR addons:
1. Copy source from IfcOpenShell to bonsaiPR-build directory
2. Replace "bonsai" with "bonsaiPR" throughout the codebase
3. Rename src/bonsai/ directory to src/bonsaiPR/
4. Fix Makefile paths and build configuration automatically:
   - jQuery download paths (build/bonsai/ -> build/bonsaiPR/)
   - Translations output paths ("build/bonsai" -> "build/bonsaiPR")
   - Zip directory references (./bonsai -> ./bonsaiPR)
   - Build artifact move commands (bonsai*.zip -> bonsaiPR*.zip)
   - Zip filename prefixes (bonsai_ -> bonsaiPR_)
   - Tab indentation fixes for Makefile syntax
   - Preserve original repository URLs for external dependencies
5. Build multi-platform addon zip files
6. Place results in src/bonsaiPR/dist/

Platform targets: linux-x64, macos-x64, macosm1-arm64, win-x64

The script now automatically resolves common build failures that occur
due to hardcoded path references in the Makefile after the bonsai->bonsaiPR
transformation, ensuring reliable automated builds.
"""

import os
import subprocess
import shutil
import re
import glob
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SOURCE_DIR = os.getenv("BASE_CLONE_DIR", "/home/falken10vdl/bonsaiPRDevel/IfcOpenShell")
BUILD_BASE_DIR = os.getenv("BUILD_BASE_DIR", "/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build")
REPORT_PATH = os.getenv("REPORT_PATH", "/home/falken10vdl/bonsaiPRDevel")

# No exclusions - copy all files and directories

def get_version_info():
    """Get version information for naming"""
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    pyversion = "py311"
    return version, pyversion, current_date

def log_message(message, level="INFO"):
    """Log messages with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {level}: {message}")

def copy_source_for_bonsaiPR_build():
    """Copy source from IfcOpenShell to bonsaiPR-build directory, ensuring correct branch is checked out"""
    log_message("Starting source copy for bonsaiPR build")
    if not os.path.exists(SOURCE_DIR):
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")
    # Ensure we are on the correct weekly branch
    version, pyversion, current_date = get_version_info()
    weekly_branch = f"weekly-build-{version}-alpha{current_date}"
    original_cwd = os.getcwd()
    try:
        os.chdir(SOURCE_DIR)
        result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
        current_branch = result.stdout.strip()
        if current_branch != weekly_branch:
            log_message(f"Not on weekly branch ({weekly_branch}), switching from {current_branch}...")
            checkout_result = subprocess.run(['git', 'checkout', weekly_branch], capture_output=True, text=True)
            if checkout_result.returncode == 0:
                log_message(f"Checked out branch: {weekly_branch}")
            else:
                log_message(f"Failed to checkout branch {weekly_branch}: {checkout_result.stderr}", "ERROR")
        else:
            log_message(f"Already on weekly branch: {weekly_branch}")
    finally:
        os.chdir(original_cwd)
    # Remove existing build directory if it exists
    if os.path.exists(BUILD_BASE_DIR):
        log_message(f"Removing existing build directory: {BUILD_BASE_DIR}")
        shutil.rmtree(BUILD_BASE_DIR)
    # Create build directory
    os.makedirs(BUILD_BASE_DIR, exist_ok=True)
    log_message(f"Created build directory: {BUILD_BASE_DIR}")
    # Copy all source files without any exclusions
    log_message("Copying all source files...")
    for root, dirs, files in os.walk(SOURCE_DIR):
        # Calculate relative path
        rel_path = os.path.relpath(root, SOURCE_DIR)
        dest_root = os.path.join(BUILD_BASE_DIR, rel_path) if rel_path != '.' else BUILD_BASE_DIR
        
        # Create destination directory
        os.makedirs(dest_root, exist_ok=True)
        
        # Copy all files
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_root, file)
            shutil.copy2(src_file, dest_file)
    
    log_message("Source copy completed successfully")

def is_binary_file(file_path):
    """Check if a file is binary by reading the first chunk"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Check for null bytes which indicate binary files
            return b'\x00' in chunk
    except Exception:
        return True  # If we can't read it, treat as binary

def replace_bonsai_with_bonsaiPR():
    """Replace 'bonsai' with 'bonsaiPR' throughout the codebase including filenames and directories"""
    log_message("Starting comprehensive bonsai -> bonsaiPR replacement")
    
    # Patterns to replace (case-sensitive and case-insensitive)
    replacements = [
        (r'\bbonsai\b', 'bonsaiPR'),      # Word boundaries for exact matches
        (r'\bBonsai\b', 'BonsaiPR'),      # Capitalized version  
        (r'\bBONSAI\b', 'BONSAIPR'),      # All caps version
    ]
    
    files_processed = 0
    files_modified = 0
    files_renamed = 0
    dirs_renamed = 0
    
    # First pass: Process file contents
    log_message("Processing file contents...")
    for root, dirs, files in os.walk(BUILD_BASE_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip binary files only
            if is_binary_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply replacements
                for pattern, replacement in replacements:
                    content = re.sub(pattern, replacement, content)
                
                # Write back if changes were made
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_modified += 1
                
                files_processed += 1
                
                # Log progress every 100 files
                if files_processed % 100 == 0:
                    log_message(f"Processed {files_processed} files...")
                    
            except Exception as e:
                log_message(f"Error processing file {file_path}: {e}", "WARNING")
    
    log_message(f"File content replacement completed: {files_processed} files processed, {files_modified} files modified")
    
    # Second pass: Rename files with 'bonsai' in their names
    log_message("Renaming files containing 'bonsai'...")
    for root, dirs, files in os.walk(BUILD_BASE_DIR, topdown=False):  # topdown=False to process files before dirs
        for file in files:
            if 'bonsai' in file.lower():
                old_path = os.path.join(root, file)
                new_name = file
                
                # Apply filename replacements
                for pattern, replacement in replacements:
                    new_name = re.sub(pattern, replacement, new_name, flags=re.IGNORECASE)
                
                if new_name != file:
                    new_path = os.path.join(root, new_name)
                    try:
                        os.rename(old_path, new_path)
                        log_message(f"Renamed file: {file} -> {new_name}")
                        files_renamed += 1
                    except Exception as e:
                        log_message(f"Error renaming file {old_path}: {e}", "WARNING")
    
    # Third pass: Rename directories with 'bonsai' in their names
    log_message("Renaming directories containing 'bonsai'...")
    for root, dirs, files in os.walk(BUILD_BASE_DIR, topdown=False):  # topdown=False to process subdirs first
        for dir_name in dirs:
            if 'bonsai' in dir_name.lower():
                old_path = os.path.join(root, dir_name)
                new_name = dir_name
                
                # Apply directory name replacements
                for pattern, replacement in replacements:
                    new_name = re.sub(pattern, replacement, new_name, flags=re.IGNORECASE)
                
                if new_name != dir_name:
                    new_path = os.path.join(root, new_name)
                    try:
                        os.rename(old_path, new_path)
                        log_message(f"Renamed directory: {dir_name} -> {new_name}")
                        dirs_renamed += 1
                    except Exception as e:
                        log_message(f"Error renaming directory {old_path}: {e}", "WARNING")
    
    log_message(f"Comprehensive replacement completed:")
    log_message(f"  - {files_processed} files processed, {files_modified} files modified")
    log_message(f"  - {files_renamed} files renamed")
    log_message(f"  - {dirs_renamed} directories renamed")

def fix_makefile_paths():
    """Fix Makefile paths that reference the old bonsai directory name"""
    log_message("Fixing Makefile paths after directory rename")
    
    makefile_path = os.path.join(BUILD_BASE_DIR, 'src', 'bonsaiPR', 'Makefile')
    
    if not os.path.exists(makefile_path):
        log_message(f"Makefile not found at: {makefile_path}", "WARNING")
        return
    
    try:
        with open(makefile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = []
        
        # Fix relative paths that still reference the old 'bonsai' directory
        # These paths should point to 'bonsaiPR' instead
        path_fixes = [
            (r'../bonsai/build/wheels/', '../bonsaiPR/build/wheels/'),
            (r'../bonsai/build/', '../bonsaiPR/build/'),
            (r'\./bonsai', './bonsaiPR'),
        ]
        
        for old_path, new_path in path_fixes:
            if old_path in content:
                content = content.replace(old_path, new_path)
                fixes_applied.append(f"Path fix: {old_path} -> {new_path}")
        
        # Fix jQuery download path - change build/bonsai/ to build/bonsaiPR/
        if 'build/bonsai/' in content:
            content = content.replace('build/bonsai/', 'build/bonsaiPR/')
            fixes_applied.append("jQuery path fix: build/bonsai/ -> build/bonsaiPR/")
        
        # Fix translations output path - change "build/bonsai" to "build/bonsaiPR"
        if '"build/bonsai"' in content:
            content = content.replace('"build/bonsai"', '"build/bonsaiPR"')
            fixes_applied.append('Translations path fix: "build/bonsai" -> "build/bonsaiPR"')
        
        # Fix zip directory reference - change ./bonsai to ./bonsaiPR in zip commands
        zip_pattern = r'(zip -r [^\s]+ )(\./bonsai)(\b)'
        if re.search(zip_pattern, content):
            content = re.sub(zip_pattern, r'\1./bonsaiPR\3', content)
            fixes_applied.append("Zip directory fix: ./bonsai -> ./bonsaiPR in zip commands")
        
        # Fix mv command for build artifacts - change bonsai*.zip to bonsaiPR*.zip
        if 'build/bonsai*.zip' in content:
            content = content.replace('build/bonsai*.zip', 'build/bonsaiPR*.zip')
            fixes_applied.append("Move command fix: build/bonsai*.zip -> build/bonsaiPR*.zip")
        
        # Fix zip filename prefix - change bonsai_ to bonsaiPR_ only in zip commands
        zip_filename_pattern = r'(zip -r )bonsai_'
        if re.search(zip_filename_pattern, content):
            content = re.sub(zip_filename_pattern, r'\1bonsaiPR_', content)
            fixes_applied.append("Zip filename fix: bonsai_ -> bonsaiPR_ in zip commands")
        
        # Fix repository URLs - change bonsaiPR-translations.git back to bonsai-translations.git
        # (Keep original repository name for translations)
        if 'bonsaiPR-translations.git' in content:
            content = content.replace('bonsaiPR-translations.git', 'bonsai-translations.git')
            fixes_applied.append("Repository URL fix: bonsaiPR-translations.git -> bonsai-translations.git")
        
        # Ensure proper tab indentation for Makefile conditional blocks
        # Fix common indentation issues in ifeq/else/endif blocks
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Check for lines that should be indented with tabs in conditional blocks
            if (line.strip().startswith('cd ') or line.strip().startswith('mv ')) and not line.startswith('\t'):
                # Look back to see if we're inside an ifeq/else block
                in_conditional = False
                for j in range(i-1, max(0, i-10), -1):  # Look back up to 10 lines
                    if lines[j].strip().startswith('ifeq') or lines[j].strip().startswith('else'):
                        in_conditional = True
                        break
                    elif lines[j].strip().startswith('endif'):
                        break
                
                if in_conditional and line.startswith('    '):  # 4 spaces
                    lines[i] = '\t' + line.lstrip()  # Replace leading spaces with tab
                    fixes_applied.append(f"Indentation fix: Line {i+1} - spaces -> tab")
        
        content = '\n'.join(lines)
        
        # Write back if changes were made
        if content != original_content:
            with open(makefile_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log_message(f"Makefile fixes applied successfully ({len(fixes_applied)} fixes):")
            for fix in fixes_applied:
                log_message(f"  - {fix}")
        else:
            log_message("No Makefile path fixes needed")
            
    except Exception as e:
        log_message(f"Error fixing Makefile paths: {e}", "ERROR")

def fix_ifctester_webapp_dependencies():
    """Fix ifctester webapp node_modules issues by reinstalling dependencies"""
    log_message("Fixing ifctester webapp dependencies")
    
    ifctester_webapp_dir = os.path.join(BUILD_BASE_DIR, 'src', 'ifctester', 'webapp')
    
    if not os.path.exists(ifctester_webapp_dir):
        log_message(f"Ifctester webapp directory not found: {ifctester_webapp_dir}", "WARNING")
        return
    
    package_json_path = os.path.join(ifctester_webapp_dir, 'package.json')
    if not os.path.exists(package_json_path):
        log_message(f"Package.json not found: {package_json_path}", "WARNING")  
        return
    
    original_cwd = os.getcwd()
    
    try:
        os.chdir(ifctester_webapp_dir)
        log_message(f"Changed to ifctester webapp directory: {ifctester_webapp_dir}")
        
        # Remove existing node_modules and package-lock.json to ensure clean install
        node_modules_dir = os.path.join(ifctester_webapp_dir, 'node_modules')
        package_lock_path = os.path.join(ifctester_webapp_dir, 'package-lock.json')
        
        if os.path.exists(node_modules_dir):
            log_message("Removing existing node_modules directory")
            shutil.rmtree(node_modules_dir)
            
        if os.path.exists(package_lock_path):
            log_message("Removing existing package-lock.json")
            os.remove(package_lock_path)
        
        # Run npm install
        log_message("Running npm install to reinstall dependencies")
        result = subprocess.run(['npm', 'install'], capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            log_message("Successfully reinstalled ifctester webapp dependencies")
        else:
            log_message(f"Failed to reinstall dependencies. Return code: {result.returncode}", "ERROR")
            if result.stderr:
                log_message(f"npm install error: {result.stderr}", "ERROR")
            if result.stdout:
                log_message(f"npm install output: {result.stdout}")
    
    except Exception as e:
        log_message(f"Error fixing ifctester webapp dependencies: {e}", "ERROR")
    
    finally:
        os.chdir(original_cwd)

def clean_old_bonsai_files():
    """Clean up any leftover 'bonsai_' files from previous builds in the dist directory"""
    dist_dir = os.path.join(BUILD_BASE_DIR, 'src', 'bonsaiPR', 'dist')
    
    if not os.path.exists(dist_dir):
        return
    
    # Find and remove any files that start with 'bonsai_' (old naming)
    old_files = glob.glob(os.path.join(dist_dir, "bonsai_*.zip"))
    
    if old_files:
        log_message(f"Found {len(old_files)} old 'bonsai_' files to clean up")
        for old_file in old_files:
            try:
                os.remove(old_file)
                log_message(f"Removed old file: {os.path.basename(old_file)}")
            except Exception as e:
                log_message(f"Failed to remove {old_file}: {e}", "WARNING")
    else:
        log_message("No old 'bonsai_' files found to clean up")

def build_addons(target_platforms=None):
    """Build multi-platform addon zip files using makefile
    
    Args:
        target_platforms (list): List of platforms to build. If None, builds all platforms.
    """
    log_message("Starting addon build process using makefile")
    
    # Clean up any old 'bonsai_' files from previous builds
    clean_old_bonsai_files()
    
    # Navigate to the bonsaiPR source directory
    bonsaiPR_src = os.path.join(BUILD_BASE_DIR, 'src', 'bonsaiPR')
    
    if not os.path.exists(bonsaiPR_src):
        log_message(f"BonsaiPR source directory not found: {bonsaiPR_src}", "ERROR")
        return
    
    # Check if Makefile exists
    makefile_path = os.path.join(bonsaiPR_src, 'Makefile')
    if not os.path.exists(makefile_path):
        log_message(f"Makefile not found at: {makefile_path}", "ERROR")
        return
    
    # Platform mappings for make command
    all_platforms = ['linux', 'macos', 'macosm1', 'win']
    platforms = target_platforms if target_platforms else all_platforms
    pyversion = 'py311'
    
    log_message(f"Building for platforms: {', '.join(platforms)}")
    
    # Change to the bonsaiPR directory and run make for each platform
    original_cwd = os.getcwd()
    successful_builds = 0
    
    try:
        os.chdir(bonsaiPR_src)
        log_message(f"Changed to directory: {bonsaiPR_src}")
        
        for platform in platforms:
            log_message(f"Building addon for platform: {platform}")
            
            # Run make dist with platform and pyversion parameters
            make_cmd = ['make', 'dist', f'PLATFORM={platform}', f'PYVERSION={pyversion}']
            log_message(f"Running command: {' '.join(make_cmd)}")
            
            try:
                result = subprocess.run(make_cmd, capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    log_message(f"Successfully built addon for {platform}")
                    successful_builds += 1
                    if result.stdout:
                        log_message(f"Make output for {platform}: {result.stdout}")
                else:
                    log_message(f"Build failed for {platform} with return code: {result.returncode}", "ERROR")
                    if result.stderr:
                        log_message(f"Make error for {platform}: {result.stderr}", "ERROR")
                    if result.stdout:
                        log_message(f"Make output for {platform}: {result.stdout}")
            
            except Exception as e:
                log_message(f"Error building {platform}: {e}", "ERROR")
    
    except Exception as e:
        log_message(f"Unexpected error during build: {e}", "ERROR")
    
    finally:
        # Always return to original directory
        os.chdir(original_cwd)
        log_message(f"Returned to directory: {original_cwd}")
    
    # Check if dist directory was created with files
    dist_dir = os.path.join(bonsaiPR_src, 'dist')
    if os.path.exists(dist_dir):
        addon_files = glob.glob(os.path.join(dist_dir, "*.zip"))
        if addon_files:
            log_message(f"Build completed. {successful_builds} platforms built successfully. Found {len(addon_files)} addon files:")
            for addon_file in sorted(addon_files):
                filename = os.path.basename(addon_file)
                filesize = os.path.getsize(addon_file)
                log_message(f"  - {filename} ({filesize:,} bytes)")
        else:
            log_message("No zip files found in dist directory after build", "WARNING")
    else:
        log_message("Dist directory not created after build", "WARNING")
    
    log_message("Addon build process completed")

def create_build_report():
    """Create or update a build report with details"""
    version, pyversion, current_date = get_version_info()
    report_filename = f"README-bonsaiPR_{pyversion}-{version}-alpha{current_date}.txt"
    report_path = os.path.join(REPORT_PATH, report_filename)
    
    dist_dir = os.path.join(BUILD_BASE_DIR, 'src', 'bonsaiPR', 'dist')
    
    # Check if the report file already exists
    file_exists = os.path.exists(report_path)
    
    with open(report_path, 'a' if file_exists else 'w') as f:
        if file_exists:
            # Add separator and build information to existing file
            f.write(f"\n\n{'=' * 80}\n")
            f.write(f"BonsaiPR Build Information\n")
            f.write(f"{'=' * 80}\n\n")
        else:
            # Create new file with header (this shouldn't happen if 00_clone script runs first)
            f.write(f"BonsaiPR Build Report\n")
            f.write(f"{'=' * 50}\n\n")
        
        f.write(f"## 🔨 Build Details\n\n")
        f.write(f"**Build Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Version**: {version}-alpha{current_date}\n")
        f.write(f"**Python Version**: {pyversion}\n")
        f.write(f"**Build Method**: Makefile automation with multi-platform support\n\n")
        
        f.write("## 📦 Built Addon Files\n\n")
        
        if os.path.exists(dist_dir):
            addon_files = glob.glob(os.path.join(dist_dir, "*.zip"))
            if addon_files:
                for addon_file in sorted(addon_files):
                    filename = os.path.basename(addon_file)
                    filesize = os.path.getsize(addon_file)
                    
                    # Determine platform from filename
                    if "windows" in filename.lower() or "win" in filename.lower():
                        platform_icon = "🪟"
                        platform_name = "Windows (x64)"
                    elif "linux" in filename.lower():
                        platform_icon = "🐧"
                        platform_name = "Linux (x64)"
                    elif "macosm1" in filename.lower() or "arm64" in filename.lower():
                        platform_icon = "🍎"
                        platform_name = "macOS (Apple Silicon)"
                    elif "macos" in filename.lower():
                        platform_icon = "🍎"
                        platform_name = "macOS (Intel)"
                    else:
                        platform_icon = "📦"
                        platform_name = "Unknown Platform"
                    
                    f.write(f"- {platform_icon} **{platform_name}**: `{filename}` ({filesize:,} bytes)\n")
                
                f.write(f"\n**Total Files Built**: {len(addon_files)}\n")
            else:
                f.write("❌ No addon files found in dist directory.\n")
        else:
            f.write("❌ Dist directory not found.\n")
        
        f.write(f"\n## 🛠️ Build Configuration\n\n")
        f.write(f"- **Source Directory**: `{SOURCE_DIR}`\n")
        f.write(f"- **Build Directory**: `{BUILD_BASE_DIR}`\n")
        f.write(f"- **Target Platforms**: linux-x64, macos-x64, macosm1-arm64, win-x64\n")
        f.write(f"- **Transformations Applied**:\n")
        f.write(f"  - ✅ Source code copied from IfcOpenShell repository\n")
        f.write(f"  - ✅ Text replacement: `bonsai` → `bonsaiPR` throughout codebase\n")
        f.write(f"  - ✅ Directory rename: `src/bonsai/` → `src/bonsaiPR/`\n")
        f.write(f"  - ✅ File and directory names updated\n")
        f.write(f"  - ✅ Makefile paths corrected\n")
        f.write(f"  - ✅ Multi-platform addon compilation\n")
        
        f.write(f"\n## 📋 Installation Instructions\n\n")
        f.write(f"1. Download the appropriate addon file for your platform\n")
        f.write(f"2. In Blender, go to Edit > Preferences > Add-ons\n")
        f.write(f"3. Click 'Install...' and select the downloaded zip file\n")
        f.write(f"4. Enable the 'BonsaiPR' addon in the list\n")
        f.write(f"5. The addon will appear as 'BonsaiPR' in the N-panel\n\n")
        
        f.write(f"## ⚠️ Important Notes\n\n")
        f.write(f"- This build includes community pull requests that may be experimental\n")
        f.write(f"- Use at your own risk in production environments\n")
        f.write(f"- Report issues to: https://github.com/falken10vdl/bonsaiPR\n")
        f.write(f"- For the original IfcOpenShell project: https://github.com/IfcOpenShell/IfcOpenShell\n")
    
    if file_exists:
        log_message(f"Build information appended to existing report: {report_path}")
    else:
        log_message(f"Build report created: {report_path}")

def test_makefile_fixes_only():
    """Test mode: only copy source and apply Makefile fixes without building"""
    log_message("Running in test mode: Makefile fixes only")
    
    try:
        # Step 1: Copy source for bonsaiPR build
        copy_source_for_bonsaiPR_build()
        
        # Step 2: Replace bonsai with bonsaiPR throughout codebase
        replace_bonsai_with_bonsaiPR()
        
        # Step 3: Apply Makefile fixes
        fix_makefile_paths()
        
        # Step 4: Fix ifctester webapp dependencies
        fix_ifctester_webapp_dependencies()
        
        log_message("Test mode completed successfully - Makefile fixes applied")
        
        # Show the fixed Makefile sections for verification
        makefile_path = os.path.join(BUILD_BASE_DIR, 'src', 'bonsaiPR', 'Makefile')
        if os.path.exists(makefile_path):
            log_message("Checking key Makefile sections after fixes:")
            
            with open(makefile_path, 'r') as f:
                lines = f.readlines()
            
            # Look for lines containing our fix patterns
            for i, line in enumerate(lines, 1):
                if any(pattern in line for pattern in ['build/bonsaiPR/', 'bonsaiPR*.zip', './bonsaiPR']):
                    log_message(f"  Line {i}: {line.strip()}")
        
    except Exception as e:
        log_message(f"Test mode failed: {e}", "ERROR")
        raise

def parse_arguments():
    """Parse command line arguments"""
    valid_platforms = ['linux', 'macos', 'macosm1', 'win']
    special_modes = ['test-makefile']
    
    if len(sys.argv) == 1:
        # No arguments provided, build all platforms
        return None, False
    elif len(sys.argv) == 2:
        arg = sys.argv[1].lower()
        if arg in valid_platforms:
            return [arg], False
        elif arg in special_modes:
            return None, True  # test mode
        else:
            print(f"Error: Invalid argument '{arg}'.")
            print(f"Usage: {sys.argv[0]} [platform|test-makefile]")
            print(f"  platform: One of {valid_platforms} (optional)")
            print(f"  test-makefile: Test Makefile fixes without building")
            print(f"  If no argument is specified, all platforms will be built.")
            sys.exit(1)
    else:
        print(f"Error: Too many arguments.")
        print(f"Usage: {sys.argv[0]} [platform|test-makefile]")
        print(f"  platform: One of {valid_platforms} (optional)")
        print(f"  test-makefile: Test Makefile fixes without building")
        print(f"  If no argument is specified, all platforms will be built.")
        sys.exit(1)

def main():
    """Main orchestration function"""
    log_message("Starting BonsaiPR addon build process")
    
    # Parse command line arguments
    target_platforms, test_mode = parse_arguments()
    
    if test_mode:
        # Run test mode: only apply Makefile fixes without building
        test_makefile_fixes_only()
        return
    
    if target_platforms:
        log_message(f"Building for specific platform(s): {', '.join(target_platforms)}")
    else:
        log_message("Building for all platforms")
    
    try:
        # Step 1: Copy source for bonsaiPR build
        copy_source_for_bonsaiPR_build()
        
        # Step 2: Replace bonsai with bonsaiPR throughout codebase (files, filenames, directories)
        replace_bonsai_with_bonsaiPR()
        
        # Step 2.5: Fix Makefile paths after directory rename
        fix_makefile_paths()
        
        # Step 2.6: Fix ifctester webapp dependencies
        fix_ifctester_webapp_dependencies()
        
        # Step 3: Build addons for specified platforms
        build_addons(target_platforms)
        
        # Step 4: Create build report
        create_build_report()
        
        log_message("BonsaiPR addon build process completed successfully")
        
    except Exception as e:
        log_message(f"Build process failed: {e}", "ERROR")
        raise

if __name__ == "__main__":
    main()