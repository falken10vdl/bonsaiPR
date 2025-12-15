# Quick Start: On-Demand Builds

## What Changed?

✨ **Builds now trigger automatically when PRs change** - no more fixed weekly schedule!

## New Features

- 🕐 **Hourly checks** for PR changes (configurable)
- 🚀 **Instant builds** when changes detected
- 💤 **Skips builds** when nothing changed (saves resources)
- 🏷️ **Timestamped names** with hour+minute (e.g., `build-0.8.4-alpha2512141430`)

## Quick Setup

### 1. Install hourly cron job

```bash
cd /home/falken10vdl/bonsaiPRDevel/bonsaiPR/automation
crontab cron/hourly-automation.cron
```

### 2. Verify it's installed

```bash
crontab -l
```

You should see:
```
5 * * * * cd /home/falken10vdl/bonsaiPRDevel/bonsaiPR/automation/src && /usr/bin/python3 check_and_build.py
```

### 3. Test it manually (optional)

```bash
# Test change detection only
cd automation/scripts
python3 check_pr_changes.py

# Test full smart build
cd ../src
python3 check_and_build.py

# Force a build (skip change detection)
python3 check_and_build.py --force
```

## How It Works

```
Every hour → Check for PR changes → Changes? → Yes → Full Build
                                           ↓
                                           No → Skip (log & wait)
```

## What Gets Checked?

- New PRs opened
- PRs updated (new commits)
- PRs merged/closed
- Draft status changed to ready
- Merge conflicts resolved

## Adjust Check Frequency

Edit `cron/hourly-automation.cron` and uncomment your preferred schedule:

```bash
# Every hour (default)
5 * * * * ...

# Every 2 hours
5 */2 * * * ...

# Every 4 hours  
5 */4 * * * ...

# Twice daily (6 AM and 6 PM)
5 6,18 * * * ...
```

Then reinstall: `crontab cron/hourly-automation.cron`

## Monitoring

Check logs:
```bash
ls -lht automation/logs/ | head
```

Latest check log:
```bash
tail -f automation/logs/check_build_*.log
```

## Reverting to Weekly Builds

If you want to go back to weekly builds:

```bash
crontab cron/weekly-automation.cron
```

## Full Documentation

See [ON_DEMAND_BUILDS.md](ON_DEMAND_BUILDS.md) for complete details.

---

**That's it!** The system is now checking for PR changes every hour and building automatically. 🎉
