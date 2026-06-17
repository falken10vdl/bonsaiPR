Summary: Rebases a feature branch onto the latest `v0.8.0`, resolves any conflicts by
understanding what each side changed relative to the merge-base, then logs the result.

Variables (update these, then copy the Prompt section below as-is):
- `{{REPO}}` → `c:\IfcOpenShell`
- `{{BRANCH}}` → `Rob2309:general-mirroring` *(the branch name on the remote — also used as the summary filename slug)*
- `{{BASE}}` → `v0.8.0`
- `{{LOG_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`
- `{{REMOTE}}` → `origin` *(set to the fork's remote name when the branch lives in a fork, e.g. `Rob2309`)*
- `{{LOCAL_BRANCH}}` → `{{BRANCH}}` *(set to the local tracking branch name when it differs from `{{BRANCH}}`, e.g. `rob2309-general-mirroring`)*
- `{{FORK}}` → *(leave blank for main-repo branches; set to author/fork identifier when `{{REMOTE}}` ≠ `origin`, e.g. `rob2309` — used to disambiguate summary filenames)*


# Prompt

I need to rebase `{{BRANCH}}` onto the latest `{{BASE}}` in the repo at `{{REPO}}`.

Please work through the following steps:

## Step 0 — Check out the feature branch

`git rebase {{BASE}}` (Step 3) rebases whatever branch is **currently checked out** —
nothing else guarantees it's the right one. Before doing anything, switch to `{{BRANCH}}`:
```
git checkout {{BRANCH}}
```
Confirm with `git rev-parse --abbrev-ref HEAD`. (If the tree is dirty or you're mid-detached-
HEAD, sort that out first — see Step 2 — but never start the rebase from the wrong branch.)

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

> **Untracked files don't matter here.** Generated/runtime files that git isn't tracking
> don't block a rebase and aren't captured by a plain `git stash push` — leave them alone.
> This step is only about *tracked* modifications.

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
4. Stage the resolved file and run `git rebase --continue`. **In a non-interactive shell,
   prefix it: `GIT_EDITOR=true git rebase --continue`** — otherwise git opens `$EDITOR` for
   the commit message and the command hangs forever. (`GIT_EDITOR=true` reuses the existing
   message; the same applies to any history command that would open an editor.)

Document each conflict: which file, which commit from `{{BASE}}` introduced the change,
what the resolution was, and why.

> **Watch for intra-branch supersession:** A later commit in `{{BRANCH}}` may undo or
> simplify a choice you made resolving an earlier conflict. If commit N added something
> and conflict M (a later commit) removes it, follow the later commit's intent — don't
> carry forward work the branch itself subsequently deleted.

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

> **These links go live only after Step 9.** `base_commit` resolves immediately, but
> `conflict_files` and `result_commit` point at the *rebased* commit, which doesn't exist
> on GitHub until the force-push in Step 9. If you stop before pushing (Steps 9–11 are
> "only if asked"), say so — those links are pending until the branch is published.

## Step 8 — Write a summary document

Write a detailed markdown summary to:
`{{LOG_REPO}}\logs\summaries\YYYY-MM-DD-rebase-{{BRANCH}}.md`

> **Fork disambiguation:** If `{{FORK}}` is set, append it to the filename:
> `YYYY-MM-DD-rebase-{{BRANCH}}-{{FORK}}.md` — this avoids collisions when the same
> branch name exists in multiple forks.

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

A rebase rewrites history, so the remote copy of `{{BRANCH}}` will have diverged and
requires a force-push. Do **not** push automatically — confirm first, then use a lease
to avoid clobbering remote work:
```
git push --force-with-lease {{REMOTE}} {{LOCAL_BRANCH}}:{{BRANCH}}
```

> For main-repo branches where `{{REMOTE}}` = `origin` and `{{LOCAL_BRANCH}}` = `{{BRANCH}}`,
> this reduces to the familiar `git push --force-with-lease origin {{BRANCH}}`.
> For fork branches, `{{REMOTE}}` is the fork's remote (e.g. `Rob2309`) and
> `{{LOCAL_BRANCH}}` may differ from `{{BRANCH}}` (e.g. `rob2309-general-mirroring`
> pushed to `Rob2309:general-mirroring`).

> **Warning — prior build conflict fixes are invalidated by a rebase.**
> The rebase changes all commit hashes, so git no longer recognizes old commits as
> ancestors. Any previously established ancestry-merge fixes in the build (commits like
> `git merge -s ours <old-tip>`) relied on those hashes — after the rebase, the effective
> git LCA between the build and the rebased branch reverts to the base (`{{BASE}}`), and
> all previously resolved conflicts re-emerge.
>
> After pushing, check `{{LOG_REPO}}/logs/conflict-resolutions.md` for any rows where
> `{{BRANCH}}` appears as the **target or conflicting PR** with `fix_strategy = ancestry-merge`.
> The re-application differs by role:
>
> **Case A — `{{BRANCH}}` was the conflicting PR** (the fix was applied to another PR's
> branch to absorb `{{BRANCH}}`'s old tip as an ancestor):
> - Find the target PR's branch name from the log row.
> - Check it out and absorb the **new** `{{BRANCH}}` tip (`{{RESULT_COMMIT}}`):
>   ```
>   git checkout <target-PR-branch>
>   git merge -s ours {{RESULT_COMMIT}} -m "Re-absorb {{BRANCH}} new tip after rebase"
>   ```
> - Verify with a test merge (same pattern as the conflict resolution prompt's Step 7).
> - Push the **target PR's** branch to its remote (not `{{REMOTE}}`).
>
> **Case B — `{{BRANCH}}` was the target PR** (the fix was applied directly to `{{BRANCH}}`
> to absorb some other PR's commit — that ancestry-merge commit was wiped by the rebase):
> - The key commit from the other PR is still valid (it wasn't affected by this rebase).
> - Re-apply on `{{BRANCH}}`:
>   ```
>   git checkout {{LOCAL_BRANCH}}
>   git merge -s ours <key_commit-from-log-row> -m "Re-apply ancestry fix after rebase"
>   git push --force-with-lease {{REMOTE}} {{LOCAL_BRANCH}}:{{BRANCH}}
>   ```
>
> In both cases, add a new row to `conflict-resolutions.md` documenting the re-application
> (don't edit the old row — the old row documents the original fix; the new row documents
> the re-application with updated commit hashes).

## Step 10 — Commit and push the bonsaiPR log (only if asked)

Stage the updated log and new summary file in `{{LOG_REPO}}`, commit, and push:
```
cd {{LOG_REPO}}
git add logs/rebase-resolutions.md logs/summaries/YYYY-MM-DD-rebase-{{BRANCH}}.md
git commit -m "Add rebase log entry and summary for {{BRANCH}} onto {{BASE}}"
git push origin main
```

> **Note on the summary filename:** if `{{FORK}}` is set, use
> `logs/summaries/YYYY-MM-DD-rebase-{{BRANCH}}-{{FORK}}.md` in the `git add` command.

## Step 11 — Share the summary link (only after Step 10)

After the log commit is pushed in Step 10, capture the **full** hash of that pushed commit
(`git rev-parse HEAD` in `{{LOG_REPO}}`) and share a permalink to the summary file pinned to
that commit, so the link is stable even as `main` advances:
```
https://github.com/falken10vdl/bonsaiPR/blob/<full-log-commit-hash>/logs/summaries/YYYY-MM-DD-rebase-{{BRANCH}}.md
```
Use the **full 40-char hash** (not the short form) and the `falken10vdl/bonsaiPR` remote — that
is where the log repo is hosted. Post this link as the final line of the response.
