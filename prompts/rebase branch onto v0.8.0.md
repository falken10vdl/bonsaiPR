Summary: Rebases a feature branch onto the latest `v0.8.0`, resolves any conflicts by
understanding what each side changed relative to the merge-base, then logs the result.

Variables (update these, then copy the Prompt section below as-is):
- `{{REPO}}` → `c:\IfcOpenShell`
- `{{BRANCH}}` → `general-mirroring`
- `{{BASE}}` → `v0.8.0`


# Prompt

I need to rebase `{{BRANCH}}` onto the latest `{{BASE}}` in the repo at `{{REPO}}`.

Please work through the following steps:

## Step 1 — Fetch and inspect divergence

From `{{REPO}}`, fetch the latest `{{BASE}}` and identify:
- How many commits `{{BRANCH}}` is ahead of its current merge-base with `{{BASE}}`
- Which files are touched by commits on `{{BRANCH}}` that are also touched by commits
  that landed in `{{BASE}}` since the current merge-base

List any overlap files explicitly — these are candidates for conflicts.

## Step 2 — Stash uncommitted changes

If there are uncommitted changes in tracked files, stash them with a descriptive message
before starting the rebase. Note the stash ref so it can be restored afterward.

## Step 3 — Attempt the rebase

Run:
```
git rebase {{BASE}}
```

If it completes cleanly, skip to Step 5.

## Step 4 — Resolve each conflict

For every conflict that arises:

1. **Identify the three versions**: merge-base (ancestor), `{{BASE}}` (ours/HEAD), and
   `{{BRANCH}}`'s commit (theirs).
2. **Understand what each side intended**: read surrounding context, not just the conflict
   markers. What problem did `{{BASE}}` solve? What did `{{BRANCH}}`'s commit intend?
3. **Resolve by combining intent**: keep both sets of changes where they are independent.
   If one side's change supersedes the other, keep the more complete version and ensure
   the discarded side's intent is still met.
4. Stage the resolved file and run `git rebase --continue`.

Document each conflict: which file, which commit from `{{BASE}}` introduced the change,
what the resolution was, and why.

## Step 5 — Restore stash (if applicable)

If a stash was created in Step 2, pop it now:
```
git stash pop
```

Confirm no new conflicts with the restored changes.

## Step 6 — Verify the result

Run:
```
git log --oneline {{BASE}}..HEAD
```

Confirm all expected commits are present and the branch tip is clean.

## Step 7 — Append to rebase log

Insert one row at the top of the data in `D:\Dropbox\GitHub\bonsaiPR\logs\rebase-resolutions.md`
(immediately after the header and separator rows — newest entries go first):

| Column | Value |
|--------|-------|
| `date` | Today's date (YYYY-MM-DD) |
| `branch` | `{{BRANCH}}` — link to the GitHub PR if one exists |
| `base_commit` | Short hash of `{{BASE}}` tip at time of rebase — linked to GitHub commit |
| `conflict_files` | Comma-separated file paths — each linked to the file at the result commit |
| `key_v0.8.0_commit` | Short hash of the `{{BASE}}` commit that caused the conflict — linked to GitHub |
| `fix_summary` | One sentence describing how each conflict was resolved |
| `result_commit` | Short hash of new branch tip — linked to GitHub commit |
| `outcome` | `clean` / `conflicts-resolved` / `failed` |

## Step 8 — Write a summary document

Write a detailed markdown summary to:
`D:\Dropbox\GitHub\bonsaiPR\logs\summaries\YYYY-MM-DD-rebase-{{BRANCH}}.md`

The document header must include a **Branch** line that hyperlinks `{{BRANCH}}` to its
GitHub PR (if one exists) or to the branch on GitHub
(`https://github.com/IfcOpenShell/IfcOpenShell/tree/{{BRANCH}}`).

The document should cover:
- What commits were on `{{BRANCH}}` that are not in `{{BASE}}`
- Which files conflicted and why (with commit links)
- The specific change from `{{BASE}}` that caused each conflict
- How each conflict was resolved and why that resolution is correct
- The final branch tip commit hash

Then add a `Summary` column entry to the log row added in Step 7, linking to this file
using a relative path (e.g., `[{{BRANCH}}](summaries/YYYY-MM-DD-rebase-{{BRANCH}}.md)`).
