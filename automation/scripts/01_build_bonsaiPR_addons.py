import os
import subprocess
import sys
import re
import argparse
import multiprocessing
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_branch_name():
    """Generate branch name with current date"""
    current_date = datetime.now().strftime('%y%m%d')
    version = "0.8.4"
    return f"weekly-build-{version}-alpha{current_date}"

def copy_source_for_bonsaiPR_build():
    """Copy the merged source code to a separate build directory"""
    print("Copying source code to separate build directory...")
    
    base_dir = os.getenv("BASE_CLONE_DIR", "/home/falken10vdl/bonsaiPRDevel/IfcOpenShell")
    build_dir = os.getenv("BONSAIPR_BUILD_DIR", "/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build")
    
    # Remove existing build directory if it exists
    if os.path.exists(build_dir):
        print(f"Removing existing build directory: {build_dir}")
        subprocess.run(['rm', '-rf', build_dir], check=True)
    
    # Copy the entire source tree
    print(f"Copying {base_dir} to {build_dir}")
    subprocess.run(['cp', '-r', base_dir, build_dir], check=True)
    
    # Remove the .git directory to avoid any git tracking
    git_dir = os.path.join(build_dir, '.git')
    if os.path.exists(git_dir):
        print(f"Removing .git directory from build copy")
        subprocess.run(['rm', '-rf', git_dir], check=True)
    
    return build_dir

def apply_bonsai_replacements(build_dir):
    """Apply comprehensive bonsai → bonsaiPR replacements in all file names, directory names, and text file contents recursively"""
    print("Applying comprehensive bonsai → bonsaiPR replacements (files, directories, and text content)...")
    
    original_dir = os.getcwd()
    
    try:
        os.chdir(build_dir)
        
        # Step 1: Replace text content in all files first (before renaming files/directories)
        print("Step 1: Replacing text content in all files...")
        
        # Find all text files (excluding binary files)
        find_result = subprocess.run([
            'find', '.', '-type', 'f', 
            '!', '-name', '*.png',
            '!', '-name', '*.jpg', 
            '!', '-name', '*.jpeg',
            '!', '-name', '*.gif',
            '!', '-name', '*.ico',
            '!', '-name', '*.blend',
            '!', '-name', '*.whl',
            '!', '-name', '*.so',
            '!', '-name', '*.dylib',
            '!', '-name', '*.dll',
            '!', '-name', '*.exe',
            '!', '-name', '*.bin',
            '!', '-name', '*.pyc',
            '!', '-path', '*/.git/*',
            '!', '-path', '*/__pycache__/*'
        ], capture_output=True, text=True, check=True)
        
        files = [f for f in find_result.stdout.strip().split('\n') if f.strip()]
        
        replacement_count = 0
        files_modified = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Apply comprehensive text replacements
                new_content = content
                
                # Replace various forms of "bonsai" with "bonsaiPR"
                # Only replace if "bonsaiPR" variants don't already exist to prevent double-replacement
                if 'bonsaipr' not in content.lower():
                    # Case-sensitive replacements with negative lookahead to prevent double-replacement
                    patterns = [
                        (r'\bbonsai(?!PR)\b', 'bonsaiPR'),           # bonsai -> bonsaiPR (not already bonsaiPR)
                        (r'\bBonsai(?!PR)\b', 'BonsaiPR'),           # Bonsai -> BonsaiPR (not already BonsaiPR)
                        (r'\bBONSAI(?!PR)\b', 'BONSAIPR'),           # BONSAI -> BONSAIPR (not already BONSAIPR)
                        (r'(["\']?)bonsai(?!PR)(["\']?)', r'\1bonsaiPR\2'),  # quoted "bonsai" -> "bonsaiPR"
                        (r'bonsai(?!PR)/', 'bonsaiPR/'),             # paths: bonsai/ -> bonsaiPR/
                        (r'/bonsai(?!PR)/', '/bonsaiPR/'),           # paths: /bonsai/ -> /bonsaiPR/
                        (r'\.bonsai(?!PR)\.', '.bonsaiPR.'),         # module names: .bonsai. -> .bonsaiPR.
                        (r'_bonsai(?!PR)_', '_bonsaiPR_'),           # identifiers: _bonsai_ -> _bonsaiPR_
                        (r'bonsai(?!PR)_', 'bonsaiPR_'),             # prefixes: bonsai_ -> bonsaiPR_
                        (r'_bonsai(?!PR)', '_bonsaiPR'),             # suffixes: _bonsai -> _bonsaiPR
                        (r'bonsai(?!PR)-', 'bonsaiPR-'),             # hyphenated: bonsai- -> bonsaiPR-
                        (r'-bonsai(?!PR)', '-bonsaiPR'),             # hyphenated: -bonsai -> -bonsaiPR
                    ]
                    
                    for pattern, replacement in patterns:
                        new_content = re.sub(pattern, replacement, new_content)
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    file_replacements = len(re.findall(r'bonsai', content, re.IGNORECASE)) - len(re.findall(r'bonsai', new_content, re.IGNORECASE))
                    replacement_count += file_replacements
                    files_modified += 1
                    print(f"[DEBUG] Modified text in: {file_path} ({file_replacements} replacements)")
                    
            except (UnicodeDecodeError, PermissionError, IsADirectoryError) as e:
                print(f"[DEBUG] Skipping file (decode/permission/directory error): {file_path} ({e})")
                continue
        
        print(f"Text replacement complete: {replacement_count} replacements in {files_modified} files")
        
        # Step 2: Rename files with 'bonsai' in their filename (deepest first to avoid path issues)
        print("Step 2: Renaming files that contain 'bonsai' in their filename...")
        
        # Find all files with 'bonsai' in the filename, sorted by depth (deepest first)
        find_result = subprocess.run([
            'find', '.', '-type', 'f', '-name', '*bonsai*'
        ], capture_output=True, text=True, check=True)
        
        files_with_bonsai = [f for f in find_result.stdout.strip().split('\n') if f.strip()]
        # Sort by depth (deepest first) to avoid renaming parent directories before children
        files_with_bonsai.sort(key=lambda x: x.count('/'), reverse=True)
        
        files_renamed = 0
        for file_path in files_with_bonsai:
            # Skip if already renamed (contains bonsaiPR)
            if 'bonsaipr' in file_path.lower():
                continue
                
            dirname = os.path.dirname(file_path)
            basename = os.path.basename(file_path)
            
            # Replace 'bonsai' with 'bonsaiPR' in filename (only if not already renamed)
            new_basename = basename
            if 'bonsaipr' not in basename.lower():
                new_basename = new_basename.replace('bonsai', 'bonsaiPR')
                new_basename = new_basename.replace('Bonsai', 'BonsaiPR')
                new_basename = new_basename.replace('BONSAI', 'BONSAIPR')
            
            if new_basename != basename:
                new_file_path = os.path.join(dirname, new_basename)
                print(f"[DEBUG] Renaming file: {file_path} → {new_file_path}")
                subprocess.run(['mv', file_path, new_file_path], check=True)
                files_renamed += 1
        
        print(f"File renaming complete: {files_renamed} files renamed")
        
        # Step 3: Rename directories with 'bonsai' in their name (deepest first)
        print("Step 3: Renaming directories that contain 'bonsai' in their name...")
        
        # Find all directories with 'bonsai' in the name, sorted by depth (deepest first)
        find_result = subprocess.run([
            'find', '.', '-type', 'd', '-name', '*bonsai*'
        ], capture_output=True, text=True, check=True)
        
        dirs_with_bonsai = [d for d in find_result.stdout.strip().split('\n') if d.strip() and d != '.']
        # Sort by depth (deepest first) to avoid renaming parent directories before children
        dirs_with_bonsai.sort(key=lambda x: x.count('/'), reverse=True)
        
        dirs_renamed = 0
        for dir_path in dirs_with_bonsai:
            # Skip if already renamed (contains bonsaiPR)
            if 'bonsaipr' in dir_path.lower():
                continue
                
            parent_dir = os.path.dirname(dir_path)
            dir_name = os.path.basename(dir_path)
            
            # Replace 'bonsai' with 'bonsaiPR' in directory name (only if not already renamed)
            new_dir_name = dir_name
            if 'bonsaipr' not in dir_name.lower():
                new_dir_name = new_dir_name.replace('bonsai', 'bonsaiPR')
                new_dir_name = new_dir_name.replace('Bonsai', 'BonsaiPR')
                new_dir_name = new_dir_name.replace('BONSAI', 'BONSAIPR')
            
            if new_dir_name != dir_name:
                new_dir_path = os.path.join(parent_dir, new_dir_name)
                print(f"[DEBUG] Renaming directory: {dir_path} → {new_dir_path}")
                subprocess.run(['mv', dir_path, new_dir_path], check=True)
                dirs_renamed += 1
        
        print(f"Directory renaming complete: {dirs_renamed} directories renamed")
        
        # Step 4: Final pass to update any references that might have been created by the renaming
        print("Step 4: Final pass to update any newly created path references...")
        
        # Re-scan for any files that might need text updates after renaming
        find_result = subprocess.run([
            'find', '.', '-type', 'f', 
            '!', '-name', '*.png', '!', '-name', '*.jpg', '!', '-name', '*.jpeg',
            '!', '-name', '*.gif', '!', '-name', '*.ico', '!', '-name', '*.blend',
            '!', '-name', '*.whl', '!', '-name', '*.so', '!', '-name', '*.dylib',
            '!', '-name', '*.dll', '!', '-name', '*.exe', '!', '-name', '*.bin',
            '!', '-name', '*.pyc', '!', '-path', '*/.git/*', '!', '-path', '*/__pycache__/*'
        ], capture_output=True, text=True, check=True)
        
        files = [f for f in find_result.stdout.strip().split('\n') if f.strip()]
        final_replacements = 0
        final_files_modified = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for any remaining bonsai references that might have been missed
                new_content = content
                if 'bonsai' in content.lower() and 'bonsaipr' not in content.lower():
                    patterns = [
                        (r'\bbonsai(?!PR)\b', 'bonsaiPR'),
                        (r'\bBonsai(?!PR)\b', 'BonsaiPR'),
                        (r'\bBONSAI(?!PR)\b', 'BONSAIPR'),
                    ]
                    
                    for pattern, replacement in patterns:
                        new_content = re.sub(pattern, replacement, new_content)
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    file_replacements = len(re.findall(r'bonsai', content, re.IGNORECASE)) - len(re.findall(r'bonsai', new_content, re.IGNORECASE))
                    final_replacements += file_replacements
                    final_files_modified += 1
                    print(f"[DEBUG] Final pass modified: {file_path} ({file_replacements} replacements)")
                    
            except (UnicodeDecodeError, PermissionError, IsADirectoryError) as e:
                continue
        
        print(f"Final pass complete: {final_replacements} additional replacements in {final_files_modified} files")
        
        # Step 5: Clean up any double-replacements that might have occurred
        print("Step 5: Cleaning up any double-replacements (bonsaiPRPR -> bonsaiPR)...")
        cleanup_replacements = 0
        cleanup_files_modified = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                # Fix any double-replacements
                if 'bonsaiPRPR' in content or 'BonsaiPRPR' in content or 'BONSAIPRPR' in content:
                    new_content = new_content.replace('bonsaiPRPR', 'bonsaiPR')
                    new_content = new_content.replace('BonsaiPRPR', 'BonsaiPR')
                    new_content = new_content.replace('BONSAIPRPR', 'BONSAIPR')
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    file_replacements = content.count('bonsaiPRPR') + content.count('BonsaiPRPR') + content.count('BONSAIPRPR')
                    cleanup_replacements += file_replacements
                    cleanup_files_modified += 1
                    print(f"[DEBUG] Cleaned up double-replacements in: {file_path} ({file_replacements} fixes)")
                    
            except (UnicodeDecodeError, PermissionError, IsADirectoryError) as e:
                continue
        
        print(f"Double-replacement cleanup complete: {cleanup_replacements} fixes in {cleanup_files_modified} files")
        
        print("\n=== COMPREHENSIVE REPLACEMENT SUMMARY ===")
        print(f"Total text replacements: {replacement_count + final_replacements}")
        print(f"Total files with text modified: {files_modified + final_files_modified}")
        print(f"Total files renamed: {files_renamed}")
        print(f"Total directories renamed: {dirs_renamed}")
        print(f"Double-replacement cleanups: {cleanup_replacements} in {cleanup_files_modified} files")
        print("Comprehensive bonsai → bonsaiPR replacement completed successfully!")
            
    finally:
        os.chdir(original_dir)

def apply_makefile_fixes(build_dir):
    """Apply specific fixes to Makefile to resolve BonsaiPR build issues"""
    print("Applying specific Makefile fixes for BonsaiPR build...")
    
    # Find all Makefiles in the build directory
    makefile_paths = []
    for root, dirs, files in os.walk(build_dir):
        for file in files:
            if file.lower() in ['makefile', 'makefile.am', 'makefile.in']:
                makefile_paths.append(os.path.join(root, file))
    
    fixes_applied = 0
    
    for makefile_path in makefile_paths:
        try:
            with open(makefile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix 1: Correct bonsaiPR-translations repository reference
            content = content.replace('bonsaiPR-translations.git', 'bonsai-translations.git')
            content = content.replace('bonsaiPR-translations', 'bonsai-translations')
            
            # Fix 2: Handle double-replacement issues (bonsaiPRPR -> bonsaiPR)
            content = content.replace('bonsaiPRPR', 'bonsaiPR')
            content = content.replace('BonsaiPRPR', 'BonsaiPR')
            content = content.replace('BONSAIPRPR', 'BONSAIPR')
            
            # Fix 3: Fix git commands to work in non-git build directory
            # Replace dynamic git commands with static values for build context
            git_patterns = [
                # Replace git hash with static value for build
                (r'GIT_HASH=\$\(shell git rev-parse --short HEAD\)', 'GIT_HASH=weekly-build-unknown'),
                (r'GIT_HASH := \$\(shell git rev-parse --short HEAD\)', 'GIT_HASH := weekly-build-unknown'),
                # Replace git date with static value for build
                (r'GIT_DATE=\$\(shell git log -1 --format=%cI\)', 'GIT_DATE=2024-10-14T10:00:00+00:00'),
                (r'GIT_DATE := \$\(shell git log -1 --format=%cI\)', 'GIT_DATE := 2024-10-14T10:00:00+00:00'),
            ]
            
            for pattern, replacement in git_patterns:
                content = re.sub(pattern, replacement, content)
            
            # Fix 4: Optimize parallel builds by detecting CPU cores
            import multiprocessing
            cpu_cores = multiprocessing.cpu_count()
            print(f"[DEBUG] Detected {cpu_cores} CPU cores for parallel builds")
            
            # Add or update MAKEFLAGS for parallel builds if not already set optimally
            makeflags_pattern = r'MAKEFLAGS\s*[:=]\s*-j\d+'
            optimal_makeflags = f'MAKEFLAGS := -j{cpu_cores}'
            
            if re.search(makeflags_pattern, content):
                # Update existing MAKEFLAGS
                content = re.sub(makeflags_pattern, optimal_makeflags, content)
                print(f"[DEBUG] Updated existing MAKEFLAGS to use {cpu_cores} cores")
            else:
                # Add MAKEFLAGS at the top of the Makefile (after any initial comments)
                lines = content.split('\n')
                insert_index = 0
                
                # Skip initial comments and empty lines
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#'):
                        insert_index = i
                        break
                
                # Insert MAKEFLAGS before the first non-comment line
                lines.insert(insert_index, f'# Automatically detected CPU cores for parallel builds')
                lines.insert(insert_index + 1, optimal_makeflags)
                lines.insert(insert_index + 2, '')
                content = '\n'.join(lines)
                print(f"[DEBUG] Added MAKEFLAGS to use {cpu_cores} cores for parallel builds")
            
            # Write back if changes were made
            if content != original_content:
                with open(makefile_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixes_applied += 1
                print(f"[DEBUG] Applied fixes to: {makefile_path}")
                
        except (UnicodeDecodeError, PermissionError) as e:
            print(f"[DEBUG] Skipping Makefile (decode/permission error): {makefile_path} ({e})")
            continue
    
    print(f"Makefile fixes complete: {fixes_applied} Makefiles updated")

def build_bonsaiPR_addons(target_platform=None):
    """
    Build BonsaiPR addons for users.
    
    Args:
        target_platform (str, optional): Specific platform to build for ('linux', 'macos', 'macosm1', 'win').
                                       If None, builds for all platforms.
    """
    print("Building BonsaiPR addons for users...")
    
    if target_platform:
        print(f"Target platform: {target_platform}")
    else:
        print("Target platforms: all (linux, macos, macosm1, win)")
    
    # Use the IfcOpenShell repository (which should now be on the correct branch)
    base_dir = os.getenv("BASE_CLONE_DIR", "/home/falken10vdl/bonsaiPRDevel/IfcOpenShell")
    
    # Ensure we're on the correct branch first
    original_dir = os.getcwd()
    try:
        os.chdir(base_dir)
        
        # Check current branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                               capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()
        expected_branch = get_branch_name()
        
        if current_branch != expected_branch:
            print(f"Warning: Expected to be on branch '{expected_branch}', but on '{current_branch}'")
            print("Attempting to checkout correct branch...")
            try:
                subprocess.run(['git', 'checkout', expected_branch], check=True)
                print(f"✅ Switched to branch: {expected_branch}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Could not switch to branch {expected_branch}: {e}")
                return False
        else:
            print(f"✅ On correct branch: {current_branch}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking git branch: {e}")
        return False
    finally:
        os.chdir(original_dir)
    
    # Copy source code to separate build directory (no git tracking)
    build_dir = copy_source_for_bonsaiPR_build()
    
    # Apply comprehensive bonsai → bonsaiPR renaming in the build copy
    apply_bonsai_replacements(build_dir)
    
    # Apply specific Makefile fixes for BonsaiPR build issues
    apply_makefile_fixes(build_dir)
    
    # After comprehensive renaming, the directory structure will have changed
    # Check for both possible directory structures
    bonsai_dir = os.path.join(build_dir, 'src', 'bonsai')  # Original structure
    bonsaiPR_dir = os.path.join(build_dir, 'src', 'bonsaiPR')  # After renaming
    
    # Determine which directory exists after renaming
    if os.path.exists(bonsaiPR_dir):
        build_source_dir = bonsaiPR_dir
        print(f"Using renamed directory for build: {build_source_dir}")
    elif os.path.exists(bonsai_dir):
        build_source_dir = bonsai_dir
        print(f"Using original directory for build: {build_source_dir}")
    else:
        print(f"Error: Neither '{bonsai_dir}' nor '{bonsaiPR_dir}' exists after renaming.")
        print("Make sure the source copy and renaming completed successfully.")
        return False
    
    # Change to the build source directory for building
    os.chdir(build_source_dir)
    print(f"Changed to directory: {build_source_dir}")
    
    # Make sure the build/wheels directory exists for the renamed addon
    # Check for both possible addon directory names
    inner_bonsai_dir = os.path.join(build_source_dir, 'bonsai')
    inner_bonsaiPR_dir = os.path.join(build_source_dir, 'bonsaiPR')
    
    if os.path.exists(inner_bonsaiPR_dir):
        addon_dir = inner_bonsaiPR_dir
        print(f"Found renamed addon directory: {addon_dir}")
    elif os.path.exists(inner_bonsai_dir):
        addon_dir = inner_bonsai_dir
        print(f"Found original addon directory: {addon_dir}")
    else:
        print(f"Error: Neither '{inner_bonsai_dir}' nor '{inner_bonsaiPR_dir}' exists.")
        return False
    
    wheels_dir = os.path.join(addon_dir, 'build', 'wheels')
    if not os.path.exists(wheels_dir):
        print(f"Creating wheels directory: {wheels_dir}")
        os.makedirs(wheels_dir, exist_ok=True)
    
    # Define platforms to build for
    all_platforms = ['linux', 'macos', 'macosm1', 'win']
    
    # Use target platform if specified, otherwise build for all platforms
    if target_platform:
        if target_platform.lower() not in [p.lower() for p in all_platforms]:
            print(f"❌ Error: Invalid platform '{target_platform}'. Valid platforms are: {', '.join(all_platforms)}")
            return False
        platforms = [target_platform.lower()]
    else:
        platforms = all_platforms
    
    success = True
    
    for platform in platforms:
        print(f"\n--- Building for platform: {platform} ---")
        try:
            # Run the make dist command for each platform
            cmd = ['make', 'dist', f'PLATFORM={platform}', 'PYVERSION=py311']
            print(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ Successfully built for {platform}")
            if result.stdout:
                print(f"Output: {result.stdout}")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error building for {platform}: {e}")
            if e.stdout:
                print(f"Stdout: {e.stdout}")
            if e.stderr:
                print(f"Stderr: {e.stderr}")
            success = False
            # Continue with other platforms even if one fails
    
    # Change back to original directory
    os.chdir(original_dir)
    
    # Check if dist directory was created and list contents
    dist_dir = os.path.join(build_source_dir, 'dist')
    if os.path.exists(dist_dir):
        print(f"\n--- Contents of dist directory: {dist_dir} ---")
        try:
            dist_contents = os.listdir(dist_dir)
            if dist_contents:
                for item in dist_contents:
                    print(f"  - {item}")
            else:
                print("  (empty)")
        except Exception as e:
            print(f"Error listing dist directory: {e}")
    else:
        print(f"\n⚠️  Warning: Dist directory '{dist_dir}' was not created")
        success = False
    
    if success:
        print(f"\n🎉 All BonsaiPR addons built successfully for users!")
        print(f"Built addons are available in: {dist_dir}")
        print(f"Users can download and install these alongside the official bonsai addon")
        print(f"Build directory (can be cleaned up): {build_dir}")
    else:
        print(f"\n⚠️  Some builds failed. Check the output above for details.")
    
    return success

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Build BonsaiPR addons for users with comprehensive bonsai→bonsaiPR renaming',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 01_build_bonsaiPR_addons.py                    # Build for all platforms
  python 01_build_bonsaiPR_addons.py --platform linux  # Build only for Linux
  python 01_build_bonsaiPR_addons.py -p win            # Build only for Windows
  
Valid platforms: linux, macos, macosm1, win
        """
    )
    
    parser.add_argument(
        '-p', '--platform',
        type=str,
        help='Target platform to build for (linux, macos, macosm1, win). If not specified, builds for all platforms.'
    )
    
    return parser.parse_args()

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    print("Starting BonsaiPR addon build process...")
    print("This script:")
    print("1. Takes the clean weekly branch created by script 1")
    print("2. Copies source code to separate build directory (no git tracking)")
    print("3. Applies COMPREHENSIVE bonsai→bonsaiPR renaming:")
    print("   - Replaces text content in all files recursively") 
    print("   - Renames all files containing 'bonsai' in filename")
    print("   - Renames all directories containing 'bonsai' in name")
    print("   - Handles multiple case variants (bonsai, Bonsai, BONSAI)")
    print("   - Prevents double-replacement (bonsaiPR→bonsaiPRPR)")
    print("   - Cleans up any accidental double-replacements")
    print("4. Applies specific Makefile fixes:")
    print("   - Fixes repository references (bonsaiPR-translations → bonsai-translations)")
    print("   - Replaces git commands with static values for build context")
    print("   - Handles double-replacement cleanup in Makefiles")
    print("   - Optimizes parallel builds by auto-detecting CPU cores")
    print("5. Builds addon packages that don't conflict with official bonsai")
    print("6. Leaves original IfcOpenShell repository untouched")
    print()
    
    if args.platform:
        print(f"Building for single platform: {args.platform}")
    else:
        print("Building for all platforms (use --platform to specify a single platform for testing)")
    print()
    
    success = build_bonsaiPR_addons(target_platform=args.platform)
    sys.exit(0 if success else 1)
