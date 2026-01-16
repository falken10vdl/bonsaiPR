import os
import json
import hashlib

def update_index_json(index_path, release_tag, addon_files):
    """
    Update index.json with new release info for each platform.
    Args:
        index_path (str): Path to index.json
        release_tag (str): Tag of the new release (e.g., v0.8.5-alpha2601161635)
        addon_files (list): List of paths to uploaded addon zip files
    """
    if not os.path.exists(index_path):
        print(f"index.json not found at {index_path}")
        return False

    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    # Map platform from filename
    def get_platform(filename):
        if 'linux-x64' in filename:
            return 'linux-x64'
        elif 'macos-x64' in filename:
            return 'macos-x64'
        elif 'macos-arm64' in filename:
            return 'macos-arm64'
        elif 'windows-x64' in filename:
            return 'windows-x64'
        return None

    # Build a dict: platform -> file info
    file_info = {}
    for path in addon_files:
        fname = os.path.basename(path)
        plat = get_platform(fname)
        if not plat:
            continue
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            hashval = hashlib.sha256(f.read()).hexdigest()
        file_info[plat] = {
            'filename': fname,
            'size': size,
            'hash': hashval
        }

    # Update index.json data entries
    for entry in index.get('data', []):
        plat_list = entry.get('platforms', [])
        if not plat_list:
            continue
        plat = plat_list[0]
        if plat in file_info:
            entry['archive_url'] = f"https://github.com/falken10vdl/bonsaiPR/releases/download/{release_tag}/{file_info[plat]['filename']}"
            entry['archive_size'] = file_info[plat]['size']
            entry['archive_hash'] = f"sha256:{file_info[plat]['hash']}"
            # Optionally update version/tag if needed

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
    print(f"index.json updated for release {release_tag}")
    return True
