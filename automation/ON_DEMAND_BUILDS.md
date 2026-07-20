# BonsaiPR On-Demand Build System

## Overview

The BonsaiPR automation system now operates on an **on-demand** basis, automatically building new releases whenever pull requests change, rather than on a fixed weekly schedule.

## How It Works

### 1. Change Detection (`check_pr_changes.py`)

Every hour (or at your configured interval), the system checks for any changes to the PR landscape:

- ✨ **New PRs opened**
- 🔄 **PRs updated** (new commits pushed)
- ✅ **PRs merged or closed**
- 📝 **PR status changed** (draft → ready for review)
- 🔀 **Merge conflicts resolved**

The script maintains a hash of the PR state in `logs/pr_state.json` to detect changes.

### 2. Smart Build Orchestration (`check_and_build.py`)

This intelligent orchestrator:
1. First runs the change detection
2. **Skips the build** if no changes detected (saves time and resources)
3. **Triggers full build** only when changes are found

### 3. Full Build Process (`main.py`)

When changes are detected, runs the complete pipeline:
1. `00_clone_merge_and_create_branch.py` - Merge all PRs
2. `01_build_bonsaiPR_addons.py` - Build addons for all platforms
3. `02_upload_to_falken10vdl.py` - Create GitHub release

### 4. Automatic Retry with Reversed PR Order

**New Feature**: After completing a build, the system automatically checks if any PRs were skipped due to conflicts with other PRs. If found:

1. **Automatically retries** the merge step with reversed PR order
2. **Verifies improvement**: Checks if any previously skipped PRs are now merged
3. **Smart decision**: Only generates a second release if the retry actually helped
   - ✅ Creates release if newly merged PRs are found
   - ⏭️ Skips release if no improvement (saves resources)

This ensures PR authors only get a new release when their previously skipped PR is actually included, giving them a chance to test their changes.

## New Naming Convention

Builds now include **hour and minute** in their names to support multiple builds per day:

```
Format: build-0.8.4-alpha{YYMMDDHHmm}
Example: build-0.8.4-alpha2512141430  (Dec 14, 2025 at 14:30)
```

This allows tracking exactly when each build was created and supports multiple releases per day (original + retry).

## Installation & Setup

### 1. Install the Cron Job

Choose your preferred check frequency:

**Hourly checks (recommended):**
```bash
crontab automation/cron/hourly-automation.cron
```

**Or edit the cron file to use a different schedule:**
- Every 2 hours: Uncomment the `*/2` line
- Every 4 hours: Uncomment the `*/4` line  
- Every 6 hours: Uncomment the `*/6` line
- Twice daily: Uncomment the `6,18` line

### 2. Verify Cron Installation

```bash
crontab -l
```

You should see your scheduled check.

### 3. Manual Testing

Test the change detection:
```bash
cd automation/scripts
python3 check_pr_changes.py
```

Test the smart build orchestrator:
```bash
cd automation/src
python3 check_and_build.py
```

Force a build regardless of changes:
```bash
cd automation/src
python3 check_and_build.py --force
```

## Configuration

All configuration is done via environment variables in `.env`:

```bash
# GitHub authentication
GITHUB_TOKEN=your_token_here

# PR filtering
USERNAMES=user1,user2,user3  # Only include PRs from these users (or leave empty for all)
EXCLUDED=1234,5678           # PR numbers to always exclude

# Paths
BASE_CLONE_DIR=/path/to/IfcOpenShell
REPORT_PATH=/path/to/reports
```

## Monitoring

### Log Files

All operations are logged:

```
automation/logs/
├── check_build_YYYYMMDD_HHMMSS.log  # Check-and-build logs
├── automation_YYYYMMDD_HHMMSS.log   # Full build logs
└── pr_state.json                     # Current PR state tracking
```

### Understanding the Output

**When no changes detected:**
```
✅ NO CHANGES DETECTED - Build skipped
💡 No new PRs or updates since last check
⏭️  Will check again on next scheduled run
```

**When changes detected:**
```
✨ CHANGES DETECTED!
   • 2 new PR(s) or PR(s) became ready
🚀 NEW BUILD REQUIRED
```

## Benefits of On-Demand Builds

✅ **Faster feedback** - New builds within an hour of PR changes  
✅ **Resource efficient** - No wasted builds when nothing changed  
✅ **Better tracking** - Precise timestamps in build names  
✅ **More responsive** - PR authors get builds quickly  
✅ **Flexible scheduling** - Adjust check frequency as needed

## Troubleshooting

### Builds not triggering

1. Check cron is running: `systemctl status crond`
2. Check cron logs: `grep CRON /var/log/cron`
3. Verify environment variables are accessible
4. Test manually with `--force` flag

### Too many builds

1. Increase check interval (every 2-4 hours instead of hourly)
2. Add more PRs to EXCLUDED list
3. Use USERNAMES filter to limit scope

### PR state file issues

If `pr_state.json` gets corrupted:
```bash
rm automation/logs/pr_state.json
# Next check will treat it as initial run and build
```

## Migration from Weekly Builds

The old weekly cron configuration is preserved in `weekly-automation.cron` for reference. The new system is backward compatible - you can run both if needed, though it's not recommended.

To switch:
1. Remove old weekly cron: `crontab -r`
2. Install new hourly cron: `crontab automation/cron/hourly-automation.cron`
3. Old builds named `weekly-build-*` will remain
4. New builds named `build-*` include timestamps

## Advanced Usage

### Custom Check Schedule

Edit `hourly-automation.cron` to create custom schedules:

By default, `check_and_build.py` also publishes updated `automation/reports`
back to the repo after a successful build so the in-repo markdown report links
stay current. Set `BONSAIPR_REPORTS_PUSH=0` in the cron environment only if
you intentionally want local-only report commits.

```cron
# Check every 30 minutes
*/30 * * * * cd /path/to/automation/src && python3 check_and_build.py

# Check only during business hours (9 AM - 5 PM)
5 9-17 * * * cd /path/to/automation/src && python3 check_and_build.py

# Check only on weekdays
5 * * * 1-5 cd /path/to/automation/src && python3 check_and_build.py
```

### Integration with CI/CD

The change detection can be integrated into webhooks or CI pipelines:

```bash
# In your webhook handler or CI script
if python3 check_pr_changes.py; then
    echo "Changes detected, triggering build"
    python3 main.py
else
    echo "No changes, skipping build"
fi
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Cron Job (Hourly)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              check_and_build.py (Orchestrator)              │
│  • Smart decision maker                                     │
│  • Prevents unnecessary builds                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  check_pr_changes.py  │
              │  • Fetch current PRs  │
              │  • Calculate hash     │
              │  • Compare with saved │
              └───────────┬───────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
    No Changes                          Changes!
        │                                   │
        ▼                                   ▼
┌──────────────┐                  ┌────────────────┐
│ Skip Build   │                  │  main.py       │
│ Log & Exit   │                  │  Full Pipeline │
└──────────────┘                  └────────┬───────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        ▼                  ▼                  ▼
              ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
              │ 00_clone_... │   │ 01_build_... │   │ 02_upload_...│
              │ Merge PRs    │   │ Build Addons │   │ Create       │
              │              │   │              │   │ Release      │
              └──────────────┘   └──────────────┘   └──────────────┘
```

## Support

For issues or questions:
1. Check logs in `automation/logs/`
2. Test scripts manually to isolate issues
3. Verify .env configuration
4. Check GitHub API rate limits

---

**Note:** The system respects GitHub API rate limits (5000 requests/hour for authenticated requests). Hourly checks use minimal API calls.
