#!/usr/bin/env python3
"""
Test script for the automatic retry logic

This script tests the retry logic functions to ensure they correctly:
1. Detect PRs skipped due to conflicts with other PRs
2. Extract PR numbers from different report sections
3. Identify newly merged PRs in retry builds
"""

import os
import sys
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_detection_with_conflicts():
    """Test that the function correctly detects skipped conflict PRs"""
    
    # Create a sample report with skipped conflict PRs
    sample_report = """# BonsaiPR Weekly Build Report
Generated: 2026-01-17 10:30:00 UTC
Branch: weekly-build-0.8.4-alpha260117-1030
IfcOpenShell source commit: abc123def456

## Summary
- Total PRs processed: 50
- Successfully merged: 30
- Failed to merge: 10
- Skipped (draft/repo issues): 5

- Failed to Merge (conflicts with base v0.8.0): 8
- Skipped (conflicts with other PRs): 2
- Failed to Merge (unknown): 0
- Success Rate: 60.0%

## ✅ Successfully Merged PRs (30)
...
"""
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(sample_report)
        temp_path = f.name
    
    try:
        # Import the function
        from main import check_for_skipped_conflict_prs
        
        # Test detection
        result = check_for_skipped_conflict_prs(temp_path)
        
        if result:
            print("✅ TEST PASSED: Function correctly detected skipped conflict PRs")
            return True
        else:
            print("❌ TEST FAILED: Function did not detect skipped conflict PRs")
            return False
    finally:
        # Clean up
        os.unlink(temp_path)


def test_detection_without_conflicts():
    """Test that the function returns False when there are no skipped conflict PRs"""
    
    # Create a sample report without skipped conflict PRs
    sample_report = """# BonsaiPR Weekly Build Report
Generated: 2026-01-17 10:30:00 UTC
Branch: weekly-build-0.8.4-alpha260117-1030

## Summary
- Total PRs processed: 50
- Successfully merged: 40
- Failed to merge: 5
- Skipped (draft/repo issues): 5

- Failed to Merge (conflicts with base v0.8.0): 5
- Skipped (conflicts with other PRs): 0
- Failed to Merge (unknown): 0
- Success Rate: 80.0%

## ✅ Successfully Merged PRs (40)
...
"""
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(sample_report)
        temp_path = f.name
    
    try:
        # Import the function
        from main import check_for_skipped_conflict_prs
        
        # Test detection
        result = check_for_skipped_conflict_prs(temp_path)
        
        if not result:
            print("✅ TEST PASSED: Function correctly returned False for no conflicts")
            return True
        else:
            print("❌ TEST FAILED: Function incorrectly detected conflicts when there were none")
            return False
    finally:
        # Clean up
        os.unlink(temp_path)


def test_extract_pr_numbers():
    """Test extraction of PR numbers from different sections"""
    
    sample_report = """# BonsaiPR Weekly Build Report

## Summary
- Total PRs processed: 10

## ✅ Successfully Merged PRs (5)

- **PR #100**: First PR
  - Author: user1
  - URL: https://github.com/test/test/pull/100

- **PR #102**: Second PR
  - Author: user2
  - URL: https://github.com/test/test/pull/102

- **PR #105**: Third PR
  - Author: user3

## ❌ Failed to Merge PRs (3)

- **PR #101**: Failed PR 1
  - Author: user4
  - Reason: Merges cleanly against base (conflict with other PRs)

- **PR #103**: Failed PR 2
  - Author: user5
  - Reason: Merges cleanly against base (conflict with other PRs)

## ⚠️ Skipped PRs (2)

- **PR #104**: Skipped PR
  - Reason: DRAFT status
"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(sample_report)
        temp_path = f.name
    
    try:
        from main import get_successfully_merged_prs, get_skipped_conflict_prs
        
        merged = get_successfully_merged_prs(temp_path)
        skipped = get_skipped_conflict_prs(temp_path)
        
        expected_merged = {100, 102, 105}
        expected_skipped = {101, 103}
        
        if merged == expected_merged and skipped == expected_skipped:
            print("✅ TEST PASSED: PR number extraction works correctly")
            print(f"   Merged: {sorted(merged)}, Skipped: {sorted(skipped)}")
            return True
        else:
            print("❌ TEST FAILED: PR number extraction incorrect")
            print(f"   Expected merged: {sorted(expected_merged)}, got: {sorted(merged)}")
            print(f"   Expected skipped: {sorted(expected_skipped)}, got: {sorted(skipped)}")
            return False
    finally:
        os.unlink(temp_path)


def test_newly_merged_detection():
    """Test detection of PRs that were skipped in first build but merged in retry"""
    
    # Simulate first build report
    first_report = """# BonsaiPR Weekly Build Report

## ✅ Successfully Merged PRs (3)
- **PR #100**: Test
- **PR #102**: Test
- **PR #103**: Test

## ❌ Failed to Merge PRs (2)
- **PR #101**: Test
  - Reason: Merges cleanly against base (conflict with other PRs)
- **PR #104**: Test
  - Reason: Merges cleanly against base (conflict with other PRs)
"""
    
    # Simulate retry build report (reversed order)
    retry_report = """# BonsaiPR Weekly Build Report

## ✅ Successfully Merged PRs (4)
- **PR #101**: Test (NOW MERGED!)
- **PR #103**: Test
- **PR #104**: Test (NOW MERGED!)
- **PR #105**: Test

## ❌ Failed to Merge PRs (1)
- **PR #100**: Test
  - Reason: Merges cleanly against base (conflict with other PRs)
"""
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_first.txt') as f:
        f.write(first_report)
        first_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_retry.txt') as f:
        f.write(retry_report)
        retry_path = f.name
    
    try:
        from main import get_skipped_conflict_prs, get_successfully_merged_prs
        
        # Get skipped PRs from first build
        skipped_first = get_skipped_conflict_prs(first_path)
        
        # Get merged PRs from retry
        merged_retry = get_successfully_merged_prs(retry_path)
        
        # Find newly merged PRs
        newly_merged = skipped_first.intersection(merged_retry)
        
        expected_newly_merged = {101, 104}
        
        if newly_merged == expected_newly_merged:
            print("✅ TEST PASSED: Newly merged PR detection works correctly")
            print(f"   PRs that were skipped but now merged: {sorted(newly_merged)}")
            return True
        else:
            print("❌ TEST FAILED: Newly merged PR detection incorrect")
            print(f"   Expected: {sorted(expected_newly_merged)}, got: {sorted(newly_merged)}")
            return False
    finally:
        os.unlink(first_path)
        os.unlink(retry_path)


def main():
    """Run all tests"""
    print("Testing automatic retry logic...\n")
    
    test1_passed = test_detection_with_conflicts()
    print()
    test2_passed = test_detection_without_conflicts()
    print()
    test3_passed = test_extract_pr_numbers()
    print()
    test4_passed = test_newly_merged_detection()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed and test3_passed and test4_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
