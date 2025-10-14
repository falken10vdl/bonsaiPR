#!/usr/bin/env python3
"""
BonsaiPR Addon Build Script
===========================

This script handles the build process for BonsaiPR addons:
1. Copy source from IfcOpenShell to bonsaiPR-build directory
2. Replace "bonsai" with "bonsaiPR" throughout the codebase
3. Rename src/bonsai/ directory to src/bonsaiPR/
4. Build multi-platform addon zip files
5. Place results in src/bonsaiPR/dist/

Platform targets: linux-x64, windows-x64, macos-x64, macos-arm64
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
    """Copy source from IfcOpenShell to bonsaiPR-build directory"""
    log_message("Starting source copy for bonsaiPR build")
    
    if not os.path.exists(SOURCE_DIR):
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")
    
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
        
        # Fix relative paths that still reference the old 'bonsai' directory
        # These paths should point to 'bonsaiPR' instead
        path_fixes = [
            (r'../bonsai/build/wheels/', '../bonsaiPR/build/wheels/'),
            (r'../bonsai/build/', '../bonsaiPR/build/'),
            (r'\./bonsai', './bonsaiPR'),
        ]
        
        for old_path, new_path in path_fixes:
            content = content.replace(old_path, new_path)
        
        # Fix zip filename specifically - change bonsai_ to bonsaiPR_ only in zip commands
        content = re.sub(r'(zip -r )bonsai_', r'\1bonsaiPR_', content)
        
        # Fix repository URLs - change bonsaiPR-translations.git back to bonsai-translations.git
        content = content.replace('bonsaiPR-translations.git', 'bonsai-translations.git')
        
        # Write back if changes were made
        if content != original_content:
            with open(makefile_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log_message("Makefile paths fixed successfully")
        else:
            log_message("No Makefile path fixes needed")
            
    except Exception as e:
        log_message(f"Error fixing Makefile paths: {e}", "ERROR")

def build_addons(target_platforms=None):
    """Build multi-platform addon zip files using makefile
    
    Args:
        target_platforms (list): List of platforms to build. If None, builds all platforms.
    """
    log_message("Starting addon build process using makefile")
    
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
    all_platforms = ['linux', 'windows', 'macos']  # macos covers both intel and arm
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
    """Create a build report with details"""
    version, pyversion, current_date = get_version_info()
    report_filename = f"README-bonsaiPR_{pyversion}-{version}-alpha{current_date}.txt"
    report_path = os.path.join(REPORT_PATH, report_filename)
    
    dist_dir = os.path.join(BUILD_BASE_DIR, 'src', 'bonsaiPR', 'dist')
    
    with open(report_path, 'w') as f:
        f.write(f"BonsaiPR Build Report\n")
        f.write(f"{'=' * 50}\n\n")
        f.write(f"Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Version: {version}-alpha{current_date}\n")
        f.write(f"Python Version: {pyversion}\n\n")
        
        f.write("Built Addons:\n")
        f.write("-" * 20 + "\n")
        
        if os.path.exists(dist_dir):
            addon_files = glob.glob(os.path.join(dist_dir, "*.zip"))
            for addon_file in sorted(addon_files):
                filename = os.path.basename(addon_file)
                filesize = os.path.getsize(addon_file)
                f.write(f"- {filename} ({filesize:,} bytes)\n")
        else:
            f.write("No addon files found.\n")
        
        f.write("\nBuild Configuration:\n")
        f.write("-" * 25 + "\n")
        f.write(f"Source Directory: {SOURCE_DIR}\n")
        f.write(f"Build Directory: {BUILD_BASE_DIR}\n")
        f.write("Build Method: Using Makefile in bonsaiPR directory\n")
    
    log_message(f"Build report created: {report_path}")

def parse_arguments():
    """Parse command line arguments"""
    valid_platforms = ['linux', 'windows', 'macos']
    
    if len(sys.argv) == 1:
        # No arguments provided, build all platforms
        return None
    elif len(sys.argv) == 2:
        platform = sys.argv[1].lower()
        if platform in valid_platforms:
            return [platform]
        else:
            print(f"Error: Invalid platform '{platform}'. Valid platforms are: {', '.join(valid_platforms)}")
            print(f"Usage: {sys.argv[0]} [platform]")
            print(f"  platform: One of {valid_platforms} (optional)")
            print(f"  If no platform is specified, all platforms will be built.")
            sys.exit(1)
    else:
        print(f"Error: Too many arguments.")
        print(f"Usage: {sys.argv[0]} [platform]")
        print(f"  platform: One of {valid_platforms} (optional)")
        print(f"  If no platform is specified, all platforms will be built.")
        sys.exit(1)

def main():
    """Main orchestration function"""
    log_message("Starting BonsaiPR addon build process")
    
    # Parse command line arguments
    target_platforms = parse_arguments()
    
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