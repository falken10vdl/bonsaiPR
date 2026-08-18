import os
import json
import hashlib

def write_profile_feed(index_path, profile_name, out_root=None, description=None,
                       owner=None, repo=None):
    """Publish a per-curation Blender feed at profiles/<name>/index.json.

    RFC-001 s10. The root index.json advertises "BonsaiPR" — whatever this
    instance happens to build. Once instances build *different* curations, that
    name stops identifying anything: a user subscribing to a URL cannot tell
    which selection of PRs they are about to install. A per-profile feed names
    the curation, so subscribing is a choice between curations rather than a
    choice of who to trust to have configured theirs the way you wanted.

    The extension `id` deliberately stays `bonsaiPR`. Curated builds are
    alternatives, not companions — the same one-at-a-time rule that already
    applies between Bonsai and BonsaiPR applies between two curations, because
    they are the same Python module. Distinct ids would imply they can coexist.

    Returns the path written, or None.
    """
    if not profile_name or not os.path.exists(index_path):
        return None

    owner = owner or os.getenv("GITHUB_OWNER", "falken10vdl")
    repo = repo or os.getenv("GITHUB_REPO", "bonsaiPR")

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    label = f"BonsaiPR · {profile_name}"
    tagline = description or (
        f"Bonsai built from the '{profile_name}' curation of open PRs."
    )
    # Blender rejects a tagline that runs long or ends in punctuation.
    tagline = tagline[:102].rstrip().rstrip(".")

    for entry in index.get("data", []):
        entry["name"] = label
        entry["tagline"] = tagline
        entry["website"] = f"https://github.com/{owner}/{repo}/blob/main/profiles/{profile_name}.json"

    out_root = out_root or os.path.join(os.path.dirname(index_path), "profiles")
    out_dir = os.path.join(out_root, profile_name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"📡 Wrote curated feed for '{profile_name}' -> {out_path}")
    return out_path


def update_index_json(index_path, release_tag, addon_files, owner=None, repo=None):
    """
    Update index.json with new release info for each platform.
    Args:
        index_path (str): Path to index.json
        release_tag (str): Tag of the new release (e.g., v0.8.5-alpha2601161635)
        addon_files (list): List of paths to uploaded addon zip files
        owner (str): Release owner; defaults to $GITHUB_OWNER, then falken10vdl
        repo (str): Release repo;  defaults to $GITHUB_REPO,  then bonsaiPR

    The archive URLs must point at the repository that actually holds the
    release. Hardcoding one publisher means a second instance publishes an
    index.json advertising downloads it does not host — Blender would follow
    those links to another project's builds, or to nothing.
    """
    owner = owner or os.getenv("GITHUB_OWNER", "falken10vdl")
    repo = repo or os.getenv("GITHUB_REPO", "bonsaiPR")
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
            entry['archive_url'] = f"https://github.com/{owner}/{repo}/releases/download/{release_tag}/{file_info[plat]['filename']}"
            entry['archive_size'] = file_info[plat]['size']
            entry['archive_hash'] = f"sha256:{file_info[plat]['hash']}"
            # Optionally update version/tag if needed

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
    print(f"index.json updated for release {release_tag}")
    return True
