#!/usr/bin/env python3
"""
check_pr_changes.py - PR Change Detection System

This script checks if there are any changes to open PRs that would warrant a new build:
- New PRs opened
- PRs closed/merged
- PR status changed (draft -> ready)
- PR content updated (new commits)

Returns exit code 0 if changes detected (should build), 1 if no changes (skip build)
"""

import os
import json
import requests
import hashlib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
upstream_repo = 'IfcOpenShell/IfcOpenShell'
state_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'pr_state.json')

# Parse excluded PRs
raw_excluded = os.getenv("EXCLUDED", "")
if raw_excluded:
    excluded_prs = set(int(x.strip()) for x in raw_excluded.split(",") if x.strip().isdigit())
else:
    excluded_prs = set()

# Parse usernames filter
raw_usernames = os.getenv("USERNAMES", "")
if raw_usernames:
    users = [u.strip() for u in raw_usernames.split(",") if u.strip()]
else:
    users = ['']

def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"}

def get_open_prs():
    """Fetch all open PRs from IfcOpenShell repository"""
    print("Fetching current open pull requests...")
    url = f"https://api.github.com/repos/{upstream_repo}/pulls"
    params = {"state": "open", "per_page": 100}
    
    all_prs = []
    page = 1
    
    while True:
        params["page"] = page
        response = requests.get(url, headers=github_headers(), params=params)
        if response.status_code != 200:
            print(f"Error fetching PRs: {response.status_code}")
            break
        
        prs = response.json()
        if not prs:
            break
            
        # Filter by users if specified
        if users and users != ['']:
            prs = [pr for pr in prs if pr['user']['login'] in users]
        
        all_prs.extend(prs)
        page += 1
        
        if len(prs) < 100:  # Last page
            break
    
    return all_prs

def calculate_pr_state_hash(prs):
    """Calculate a hash representing the current state of PRs"""
    # Create a normalized representation of PR state
    pr_data = []
    
    for pr in prs:
        # Skip excluded PRs
        if pr['number'] in excluded_prs:
            continue
            
        # Include key information that would trigger a rebuild
        pr_info = {
            'number': pr['number'],
            'updated_at': pr['updated_at'],
            'draft': pr.get('draft', False),
            'head_sha': pr['head']['sha'] if pr.get('head') else None,
            'state': pr['state'],
            'mergeable': pr.get('mergeable'),  # Can change over time
        }
        pr_data.append(pr_info)
    
    # Sort by PR number for consistent hashing
    pr_data.sort(key=lambda x: x['number'])
    
    # Create hash
    state_str = json.dumps(pr_data, sort_keys=True)
    return hashlib.sha256(state_str.encode()).hexdigest()

def load_previous_state():
    """Load the previous PR state from file"""
    if not os.path.exists(state_file):
        return None
    
    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load previous state: {e}")
        return None

def save_current_state(state_hash, pr_count, timestamp):
    """Save current PR state to file"""
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    
    state = {
        'hash': state_hash,
        'pr_count': pr_count,
        'timestamp': timestamp,
        'checked_at': datetime.now().isoformat()
    }
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def main():
    """Check if PR state has changed"""
    print("=" * 60)
    print("🔍 BonsaiPR Change Detection System")
    print(f"⏰ Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Validate GitHub token
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found in environment")
        return 1
    
    # Get current PRs
    current_prs = get_open_prs()
    
    # Filter out excluded and draft PRs for state comparison
    relevant_prs = [
        pr for pr in current_prs 
        if pr['number'] not in excluded_prs
        and pr.get('head') and pr['head'].get('repo')  # Exclude inaccessible repos
    ]
    
    print(f"📊 Current state: {len(relevant_prs)} relevant PRs found")
    
    # Calculate current state hash
    current_hash = calculate_pr_state_hash(relevant_prs)
    current_timestamp = datetime.now().isoformat()
    
    # Load previous state
    previous_state = load_previous_state()
    
    # Determine if build is needed
    if previous_state is None:
        print("📝 No previous state found - initial build needed")
        save_current_state(current_hash, len(relevant_prs), current_timestamp)
        return 0  # Build needed
    
    previous_hash = previous_state.get('hash')
    previous_count = previous_state.get('pr_count', 0)
    previous_check = previous_state.get('checked_at', 'unknown')
    
    print(f"📋 Previous check: {previous_check}")
    print(f"📊 Previous state: {previous_count} PRs")
    
    if current_hash != previous_hash:
        # Changes detected
        print("✨ CHANGES DETECTED!")
        print(f"   Previous hash: {previous_hash[:16]}...")
        print(f"   Current hash:  {current_hash[:16]}...")
        
        # Detailed change analysis
        if len(relevant_prs) != previous_count:
            diff = len(relevant_prs) - previous_count
            if diff > 0:
                print(f"   • {diff} new PR(s) or PR(s) became ready")
            else:
                print(f"   • {abs(diff)} PR(s) closed/merged or became draft")
        else:
            print(f"   • PR content updated (new commits or state changes)")
        
        print("🚀 NEW BUILD REQUIRED")
        save_current_state(current_hash, len(relevant_prs), current_timestamp)
        return 0  # Build needed
    else:
        print("✅ No changes detected - build not needed")
        print(f"   Hash: {current_hash[:16]}... (unchanged)")
        return 1  # No build needed

if __name__ == "__main__":
    exit(main())
