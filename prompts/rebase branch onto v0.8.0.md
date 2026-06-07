Summary: Rebases a feature branch onto the latest `v0.8.0`, resolves any conflicts by
understanding what each side changed relative to the merge-base, then logs the result.

Variables (update these, then copy the Prompt section below as-is):
- `{{REPO}}` → `c:\IfcOpenShell`
- `{{BRANCH}}` → `parametric_dimensions`
- `{{BASE}}` → `v0.8.0`
- `{{LOG_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`


# Prompt

I need to rebase `{{BRANCH}}` onto the latest `{{BASE}}` in the repo at `{{REPO}}`.

Please work through the following steps:

## Step 1 — Fetch, update the local base ref, and inspect divergence

From `{{REPO}}`, fetch the latest `{{BASE}}`:
```
git fetch origin {{BASE}}
```

**Important:** `git fetch` only moves `origin/{{BASE}}` — it does NOT update your local
`{{BASE}}` branch ref, and `git rebase {{BASE}}` (Step 3) rebases onto the *local* ref.
Before doing anything else, fast-forward the local ref so you don't rebase onto a stale
base. Since you are not on `{{BASE}}`, update it in place:
```
git branch -f {{BASE}} origin/{{BASE}}
```
Confirm `git rev-parse {{BASE}}` now equals `git rev-parse origin/{{BASE}}`.
(Alternatively, rebase onto `origin/{{BASE}}` directly in Step 3.)

Then identify, against the now-current `{{BASE}}`:
- How many commits `{{BRANCH}}` is ahead of its current merge-base with `{{BASE}}`
- Which files are touched by commits on `{{BRANCH}}` that are also touched by commits
  that landed in `{{BASE}}` since the current merge-base

List any overlap files explicitly — these are candidates for conflicts.

## Step 2 — Stash uncommitted changes

If there are uncommitted changes in tracked files, stash them with a descriptive message
before starting the rebase.

**Important:** other, unrelated stashes may already exist (possibly from other branches).
Do not assume your stash is `stash@{0}`. Run `git stash list` first, then after
`git stash push` capture the exact ref it reports (e.g. `stash@{0}` at that moment) or,
more robustly, record the stash *commit hash* (`git rev-parse stash@{0}`) so you can pop
exactly that stash in Step 5 and never touch a pre-existing one.

## Step 3 — Attempt the rebase

Run:
```
git rebase {{BASE}}
```

> **Note:** `warning: skipped previously applied commit` messages are expected — they mean
> those commits were already present in `{{BASE}}` (e.g. cherry-picks) and are dropped
> automatically. This is normal and not a failure.

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

If a stash was created in Step 2, pop **the specific stash you created** — never a bare
`git stash pop`, which would pop whatever is at the top of the stack (possibly an unrelated
pre-existing stash). Apply by the ref/hash you recorded in Step 2:
```
git stash pop <recorded-ref-or-hash>
```

Confirm no new conflicts with the restored changes.

## Step 6 — Verify the result

Run:
```
git log --oneline {{BASE}}..HEAD
```

Confirm all expected commits are present and the branch tip is clean. As a sanity check
beyond git state, run `python -m py_compile` on every file that appeared in the overlap
list from Step 1 (files touched on both sides) — those are the only ones where a bad
resolution could silently produce invalid syntax. Valid git state does not guarantee a
valid resolution.

> **Note on the PR link (used in Steps 7 & 8):** a commit message like `Closes #N` references
> an *issue*, not necessarily the PR — don't assume `#N` is the PR number. Find the real PR
> by its head branch (`{{BRANCH}}`); e.g. `gh pr list --head {{BRANCH}} --state all`, or open
> the issue and follow its linked PR. If `gh` is not available or no PR exists, link the
> branch tree instead (`https://github.com/IfcOpenShell/IfcOpenShell/tree/{{BRANCH}}`).

## Step 7 — Append to rebase log

Insert one row at the top of the data in `{{LOG_REPO}}\logs\rebase-resolutions.md`
(immediately after the header and separator rows — newest entries go first):

| Column | Value |
|--------|-------|
| `date` | Current date and time (YYYY-MM-DD HH:MM:SS) |
| `branch` | `{{BRANCH}}` — link to the GitHub PR if one exists |
| `base_commit` | Short hash of `{{BASE}}` tip at time of rebase — linked to GitHub commit |
| `conflict_files` | Comma-separated file paths — each linked to the file at the result commit; `none` if clean |
| `key_v0.8.0_commit` | Short hash of the `{{BASE}}` commit that caused the conflict — linked to GitHub; `none` if clean |
| `fix_summary` | One sentence describing how each conflict was resolved |
| `result_commit` | Short hash of new branch tip — linked to GitHub commit |
| `outcome` | `clean` / `conflicts-resolved` / `failed` |

## Step 8 — Write a summary document

Write a detailed markdown summary to:
`{{LOG_REPO}}\logs\summaries\YYYY-MM-DD-rebase-{{BRANCH}}.md`

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

## Step 9 — Publish the rebased branch (only if asked)

A rebase rewrites history, so `{{BRANCH}}` will have diverged from
`origin/{{BRANCH}}` and updating the remote requires a force-push. Do **not** push
automatically — confirm first, then use a lease to avoid clobbering remote work:
```
git push --force-with-lease origin {{BRANCH}}
```

## Step 10 — Commit and push the bonsaiPR log (only if asked)

Stage the updated log and new summary file in `{{LOG_REPO}}`, commit, then
pull-rebase before pushing (the remote may have diverged if another machine pushed since
your last sync):
```
cd {{LOG_REPO}}
git add logs/rebase-resolutions.md logs/summaries/YYYY-MM-DD-rebase-{{BRANCH}}.md
git commit -m "Add rebase log entry and summary for {{BRANCH}} onto {{BASE}}"
git pull --rebase origin main
git push origin main
```
