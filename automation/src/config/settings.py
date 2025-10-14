"""
settings.py - Configuration settings for BonsaiPR automation system

This file contains all configuration variables used by the automation scripts.
Update these settings according to your environment and requirements.

Author: BonsaiPR Automation System
Date: 2025-10-14
"""

import os

# GitHub Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_OWNER = os.getenv('GITHUB_OWNER', 'falken10vdl')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'BonsaiPR')

# Source Repository Configuration
SOURCE_REPO_OWNER = 'IfcOpenShell'
SOURCE_REPO_NAME = 'IfcOpenShell'
SOURCE_REPO_URL = f'https://github.com/{SOURCE_REPO_OWNER}/{SOURCE_REPO_NAME}.git'

# Build Configuration
PYTHON_VERSION = 'py311'
BONSAI_VERSION = '0.8.4'
BUILD_BASE_DIR = os.getenv('BUILD_BASE_DIR', '/home/falken10vdl/bonsaiPRDevel/bonsaiPR-build')
REPORTS_PATH = os.getenv('REPORTS_PATH', '/home/falken10vdl/bonsaiPRDevel')

# Platform Configuration
SUPPORTED_PLATFORMS = [
    {
        'name': 'linux-x64',
        'display_name': 'Linux (x64)'
    },
    {
        'name': 'windows-x64',
        'display_name': 'Windows (x64)'
    },
    {
        'name': 'macos-x64',
        'display_name': 'macOS Intel (x64)'
    },
    {
        'name': 'macos-arm64',
        'display_name': 'macOS Apple Silicon (ARM64)'
    }
]

# Automation Configuration
MAX_PRS_TO_PROCESS = 100  # Maximum number of PRs to process
SKIP_DRAFT_PRS = True     # Whether to skip draft PRs
SKIP_CLOSED_PRS = True    # Whether to skip closed PRs

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Timing Configuration
SCRIPT_TIMEOUT = 3600     # 1 hour timeout for individual scripts
API_TIMEOUT = 30          # 30 seconds for API requests
RETRY_ATTEMPTS = 3        # Number of retry attempts for failed operations

# File Paths
def get_branch_name():
    """Generate branch name with current date"""
    from datetime import datetime
    current_date = datetime.now().strftime('%y%m%d')
    return f"weekly-build-{BONSAI_VERSION}-alpha{current_date}"

def get_release_tag():
    """Generate release tag with current date"""
    from datetime import datetime
    current_date = datetime.now().strftime('%y%m%d')
    return f"v{BONSAI_VERSION}-alpha{current_date}"

def get_release_name():
    """Generate release name with current date"""
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d')
    return f"BonsaiPR Weekly Build - {current_date}"

# Validation
def validate_configuration():
    """Validate that required configuration is present"""
    errors = []
    
    if not GITHUB_TOKEN:
        errors.append("GITHUB_TOKEN is required")
    
    if not GITHUB_OWNER:
        errors.append("GITHUB_OWNER is required")
    
    if not GITHUB_REPO:
        errors.append("GITHUB_REPO is required")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True