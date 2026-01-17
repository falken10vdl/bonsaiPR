# Automatic Retry with Reversed PR Order - Feature Documentation

## Overview

The BonsaiPR automation system now includes an intelligent retry mechanism that automatically detects when PRs were skipped due to conflicts with other PRs and retries the build with reversed PR order.

## How It Works

### Detection Phase

After completing a successful build (all 3 stages):

1. The system reads the generated report file (`README-bonsaiPR_*.txt`)
2. Searches for the line: `- Skipped (conflicts with other PRs): X`
3. If X > 0, the retry mechanism is triggered
4. Extracts the list of PR numbers that were skipped due to conflicts

### Retry Phase

When PRs are detected that were skipped due to conflicts:

1. **Stage 1 (Retry)**: Run `00_clone_merge_and_create_branch.py --reverse`
   - Merges PRs in descending order (newest PRs first, oldest last)
   - Creates a new branch with a different timestamp
   - Generates a new report

2. **Verification**: Compare results
   - Extract successfully merged PRs from the retry report
   - Check if any PRs that were skipped in the first build are now merged
   - **Only continue if at least one previously skipped PR was successfully merged**

3. **Stage 2 (Conditional)**: Run `01_build_bonsaiPR_addons.py`
   - **Only runs if newly merged PRs were found**
   - Builds addons for all platforms using the new branch
   - Appends build information to the new report

4. **Stage 3 (Conditional)**: Run `02_upload_to_falken10vdl.py`
   - **Only runs if newly merged PRs were found**
   - Creates a second GitHub release with the retry results
   - Uploads all platform builds and the complete report

### Smart Release Decision

The system intelligently decides whether to create a second release:

✅ **Second release IS created when:**
- At least one PR that was skipped in the first build is successfully merged in the retry

⏭️ **Second release is SKIPPED when:**
- No previously skipped PRs were merged in the retry
- The reversed order didn't help include more PRs
- A second release would be identical or worse than the first

This ensures PR authors only get notified when there's actually a new build that includes their previously skipped PR.

## Why Reverse Order?

When PRs are merged in chronological order (oldest first), newer PRs may conflict with older ones and get skipped. By reversing the order:

- **Newer PRs get priority**: Recent contributions are more likely to be included
- **More PRs included**: Different PRs may succeed when order changes
- **Better community engagement**: Contributors see their recent work in releases sooner

## Example Scenario

### First Build (Normal Order)
```
PRs attempted: #100, #101, #102, #103, #104
Successfully merged: #100, #101, #103
Failed (conflict with base): #104
Skipped (conflict with other PRs): #102  ← Triggers retry!
```

### Second Build (Reversed Order - Retry)
```
PRs attempted: #104, #103, #102, #101, #100
Successfully merged: #102, #103, #104
Failed (conflict with base): #101
Skipped (conflict with other PRs): #100
```

**Analysis:**
- Previously skipped PRs: #102
- Newly merged in retry: #102, #104
- **Newly merged from skipped list: #102** ✅

**Result**: 
- ✅ **Second release IS generated** because PR #102 (which was skipped) is now merged!
- PR author of #102 can now test their changes in this release

### Counter-Example: No New PRs Merged

### First Build
```
PRs attempted: #100, #101, #102, #103
Successfully merged: #100, #101
Skipped (conflict with other PRs): #102, #103
```

### Retry Build (Reversed Order)
```
PRs attempted: #103, #102, #101, #100
Successfully merged: #100, #101
Skipped (conflict with other PRs): #102, #103
```

**Analysis:**
- Previously skipped PRs: #102, #103
- Successfully merged in retry: #100, #101
- **Newly merged from skipped list: (none)** ❌

**Result**:
- ⏭️ **Second release is SKIPPED** - no improvement from retry
- Saves time and resources by not creating duplicate release

## Benefits

1. **Maximizes PR Inclusion**: More PRs get into releases across both builds
2. **Provides Alternatives**: Users can choose between different PR combinations
3. **Automatic**: No manual intervention required
4. **Transparent**: Both releases are clearly documented with their PR lists

## Implementation Details

### Code Location
- Main retry logic: `automation/src/main.py`
- Detection function: `check_for_skipped_conflict_prs(report_path)`
- Reverse flag support: `00_clone_merge_and_create_branch.py --reverse`

### Key Functions

```python
def check_for_skipped_conflict_prs(report_path):
    """
    Checks if report contains PRs skipped due to conflicts with other PRs
    Returns: True if skipped conflict PRs found, False otherwise
    """
    
def get_latest_report_path():
    """
    Gets the path to most recently generated report file
    Returns: Path to latest report or None
    """

def extract_pr_numbers_from_section(report_path, section_title):
    """
    Extract PR numbers from a specific section of the report
    Returns: Set of PR numbers

**When retry is triggered:**
```
🔄 RETRY WITH REVERSED PR ORDER
Found PRs skipped due to conflicts with other PRs.
Retrying with newer PRs first to maximize inclusion.
📋 First build had 2 PR(s) skipped due to conflicts: [102, 103]
```

**When newly merged PRs are found:**
```
✨ SUCCESS! Retry merged 1 PR(s) that were previously skipped:
   • PR #102
🚀 Continuing with build and release for retry...
```

**When no new PRs are merged:**
```
⏭️  RETRY SKIPPED: No previously skipped PRs were merged in retry.
   The reversed order didn't help include more PRs.
   Second release not needed - would be identical or worse
    Get the list of PR numbers that were skipped due to conflicts
    Returns: Set of PR numbers
    """

def get_successfully_merged_prs(report_path):
    """
    Get the list of PR numbers that were successfully merged
    Returns: Set of PR numbers
    """
```

### Logging

The retry process is fully logged with clear indicators:
```
🔄 RETRY WITH REVERSED PR ORDER
Found PRs skipped due to conflicts with other PRs.
Retrying with newer PRs first to maximize inclusion.
```

## Testing

Run the test suite to verify the detection logic:

```bash
cd automation/tests
python test_retry_logic.py
```

## Disabling the Feature

If you want to disable automatic retries, you can modify `main.py`:

```python
# Comment out or remove the retry check section
# if success_count == total_steps:
#     report_path = get_latest_report_path()
#     if report_path and check_for_skipped_conflict_prs(report_path):
#         ... retry logic ...
```

## Future Enhancements

Potential improvements for this feature:

1. **Configurable retry limit**: Add environment variable to control max retries
2. **Smart PR ordering**: Use AI/ML to determine optimal PR order
3. **Conflict analysis**: Provide detailed reports on which PRs conflict with each other
4. **Incremental retries**: Only retry with conflicting PRs instead of full rebuild

## Related Files

- `automation/src/main.py` - Main retry orchestration
- `automation/scripts/00_clone_merge_and_create_branch.py` - Supports --reverse flag
- `automation/tests/test_retry_logic.py` - Test suite for retry logic
- `automation/README.md` - Main automation documentation
- `automation/ON_DEMAND_BUILDS.md` - On-demand build system guide
