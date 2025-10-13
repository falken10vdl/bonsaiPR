import os
import subprocess
import sys

def build_bonsaiPR_addons():
    print("Building bonsaiPR addons...")
    
    # Define the directory where the bonsaiPR source is located
    bonsaipr_dir = '/path/to/your/bonsaiPRDevel/MergingPR/IfcOpenShell/src/bonsaiPR'
    
    # Check if the directory exists
    if not os.path.exists(bonsaipr_dir):
        print(f"Error: The bonsaiPR directory '{bonsaipr_dir}' does not exist.")
        return False
    
    # Change to the bonsaiPR directory
    original_dir = os.getcwd()
    os.chdir(bonsaipr_dir)
    print(f"Changed to directory: {bonsaipr_dir}")
    
    # Define platforms to build for
    platforms = ['linux', 'macos', 'macosm1', 'win']
    
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
    dist_dir = os.path.join(bonsaipr_dir, 'dist')
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
        print(f"\n🎉 All bonsaiPR addons built successfully!")
        print(f"Built addons are available in: {dist_dir}")
    else:
        print(f"\n⚠️  Some builds failed. Check the output above for details.")
    
    return success

if __name__ == '__main__':
    success = build_bonsaiPR_addons()
    sys.exit(0 if success else 1)
