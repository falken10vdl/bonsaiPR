Summary: Rebases a feature branch onto the latest `v0.8.0`, resolves any conflicts by
understanding what each side changed relative to the merge-base, then logs the result.

Variables (update these, then copy the Prompt section below as-is):
- `{{REPO}}` → `c:\IfcOpenShell`
- `{{BRANCH}}` → `duplicate_opening_on_type_duplication`
- `{{BASE}}` → `v0.8.0`
- `{{LOG_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`


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

**Capture the pre-rebase tip now** — Steps 4 and 6 need it, and the rebase will rewrite
`{{BRANCH}}` out from under you: `ORIG=$(git rev-parse {{BRANCH}})` (or just use
`origin/{{BRANCH}}` later, as long as the remote is in sync with your local branch).

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

List the **overlap files** explicitly (files changed on *both* sides since the merge-base) —
these are the only files where a conflict requires real judgment. Compute the set concretely
and keep it; Steps 4 and 6 depend on it:
```
mb=$(git merge-base {{BASE}} {{BRANCH}})
comm -12 <(git diff --name-only $mb {{BRANCH}} | sort -u) \
         <(git diff --name-only $mb {{BASE}}   | sort -u)
```

> **The non-overlap invariant (relied on in Steps 4 & 6).** For any file `{{BASE}}` did *not*
> change since the merge-base, the base content is identical to the merge-base, so a correct
> rebase must reproduce the **`{{BRANCH}}` tip** version of that file *exactly*. Such files
> can only conflict because of the branch's own internal history — never because of `{{BASE}}`.
> This makes their resolution deterministic (see Step 4) and gives a strong end-state check
> (see Step 6).

> **Check for merge commits up front:** run `git log --merges {{BASE}}..{{BRANCH}}`. If it is
> non-empty, the branch absorbed other work via merges (and the same logical commits may
> appear several times). Expect this to matter: `git rebase` **flattens history and drops
> merge commits**, replaying only the linear commits — so content that entered `{{BRANCH}}`
> *only* through a merge's second parent will revert to `{{BASE}}`. That is normal and usually
> desirable for a release-branch rebase (it sheds absorbed cross-feature noise), but it means
> the final commit count will be lower than the number replayed, and you should not try to
> "rescue" the dropped content. Confirm via `git log --merges <merge-base>..{{BRANCH}} -- <file>`
> whether a given file's delta came from a merge before deciding what its correct end state is.

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

**First, triage by overlap status** (from the Step 1 set):

- **Non-overlap file** (`{{BASE}}` did not touch it): do *not* hand-merge. By the non-overlap
  invariant its correct end state is the `{{BRANCH}}`-tip version, so resolve it directly:
  ```
  git checkout {{BRANCH}} -- <file>   # the ORIGINAL branch tip (capture its hash before Step 3)
  git add <file>
  ```
  This conflicts only because of the branch's internal/duplicated history; combining
  intent commit-by-commit is wasted effort and error-prone. (Capture the pre-rebase tip
  with `ORIG=$(git rev-parse {{BRANCH}})` *before* Step 3, and use `$ORIG` here, since
  `{{BRANCH}}` itself is what's being rewritten.)
  > **Caution — this shortcut needs an end-state reconciliation.** Checking out the tip
  > version *mid-rebase* can be clobbered by later commits re-applying their patches on top
  > (producing duplicated methods / lost args that still compile). It is not self-correcting
  > per-commit; you MUST verify and re-reconcile every non-overlap file against the tip at
  > the end (Step 6).

- **Overlap file** (`{{BASE}}` also changed it): this is the only case needing real judgment.
  Resolve by hand using the three-way reasoning below.

For every **overlap** conflict:

1. **Identify the three versions**: merge-base (ancestor), `{{BASE}}` (ours/HEAD), and
   `{{BRANCH}}`'s commit (theirs).
2. **Understand what each side intended**: read surrounding context, not just the conflict
   markers. What problem did `{{BASE}}` solve? What did `{{BRANCH}}`'s commit intend?
3. **Resolve by combining intent**: keep both sets of changes where they are independent.
   If one side's change supersedes the other, keep the more complete version and ensure
   the discarded side's intent is still met. When unsure of the branch's *final* intent for
   an overlap file, consult the branch tip (`git show {{BRANCH}}:<file>`) — it shows where the
   branch landed after all its own supersessions.
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

Confirm all expected commits are present and the branch tip is clean (note the replayed
count may be lower than commits-ahead if merge commits/duplicates were dropped — see Step 1).

**3-way tree verification (the real correctness check).** `py_compile` is necessary but far
too weak — a bad merge can duplicate a method or drop an argument and still compile. Instead,
classify every file that differs between the rebased `HEAD` and the *pre-rebase* branch tip
(`ORIG`, the original `{{BRANCH}}` tip captured before Step 3 — or `origin/{{BRANCH}}` if the
remote is in sync). Each such file must match **exactly one** of:

- the **`{{BASE}}`** version — absorbed/merge-only content correctly dropped by the rebase
  (expected, fine); or
- the **branch-tip (`ORIG`)** version — feature work carried through intact (expected, fine).

Any file matching **neither** is a resolution artifact and must be fixed (for a non-overlap
file, reset it to the tip: `git checkout <ORIG> -- <file>` and fold it into the result, e.g.
`git commit --amend --no-edit`). Concretely, the only files that may legitimately match
neither are the **overlap files** (which combine both sides) plus any non-overlap file whose
tip delta is genuine linear feature work the rebase reproduced:
```
ORIG=<pre-rebase tip>            # captured before Step 3, or origin/{{BRANCH}}
for f in $(git diff --name-only $ORIG HEAD); do
  git diff --quiet {{BASE}} HEAD -- "$f" && continue   # == BASE: dropped absorbed content, OK
  git diff --quiet $ORIG   HEAD -- "$f" && continue     # == tip: feature work intact, OK
  echo "SCRUTINIZE: $f"                                  # matches neither — inspect/fix
done
```
The `SCRUTINIZE` set should reduce to the overlap files (and verified linear-feature deltas);
investigate anything else.

Then run `python -m py_compile` on every changed `.py` file (`git diff --name-only {{BASE}}
HEAD -- '*.py'`) as a final syntax gate. Valid git state does not guarantee a valid resolution.

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

> **Warning — prior build conflict fixes are invalidated by a rebase.**
> The rebase changes all commit hashes, so git no longer recognizes old commits as
> ancestors. Any previously established ancestry-merge fixes in the build (commits like
> `git merge -s ours <old-tip>`) relied on those hashes — after the rebase, the effective
> git LCA between the build and the rebased branch reverts to the base (`{{BASE}}`), and
> all previously resolved conflicts re-emerge.
>
> After pushing, check `{{LOG_REPO}}/logs/conflict-resolutions.md` for any rows where
> `{{BRANCH}}` appears as the target or conflicting PR with `fix_strategy = ancestry-merge`.
> If any exist, re-apply the fix on the rebased branch:
> ```
> git merge -s ours <key_commit-from-log-row>
> git push --force-with-lease origin {{BRANCH}}
> ```
> Then re-run the conflict resolution prompt for the affected build branch to verify and
> log the re-applied fix.

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

> **If `git pull --rebase` refuses with "you are currently rebasing" / an in-progress
> rebase** in the log repo, it's almost certainly a *stale* `.git/rebase-merge` left from
> an interrupted run — **not** real work. Don't blindly `rm -rf` it (git warns for a
> reason). Check whether it holds real state first:
> ```
> cat .git/rebase-merge/head-name .git/rebase-merge/onto .git/rebase-merge/orig-head
> ```
> If those files are absent / the directory is empty, it's a stale flag: clear it with
> `rmdir .git/rebase-merge` (which **refuses if non-empty**, so it can't destroy real
> state), then re-run the pull-rebase. A "diverged — 1 and N commits" message here is
> normal: your one log commit vs. N upstream release commits; the pull-rebase just replays
> your commit on top.

## Step 11 — Share the summary link (only after Step 10)

After the log commit is pushed in Step 10, capture the **full** hash of that pushed commit
(`git rev-parse HEAD` in `{{LOG_REPO}}`) and share a permalink to the summary file pinned to
that commit, so the link is stable even as `main` advances:
```
https://github.com/falken10vdl/bonsaiPR/blob/<full-log-commit-hash>/logs/summaries/YYYY-MM-DD-rebase-{{BRANCH}}.md
```
Use the **full 40-char hash** (not the short form) and the `falken10vdl/bonsaiPR` remote — that
is where the log repo is hosted. Post this link as the final line of the response.
