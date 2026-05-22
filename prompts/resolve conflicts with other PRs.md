

Variables (update these, then copy the Prompt section below as-is):
- `{{BONSAI_PR_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`
- `{{IFCOPENSHELL_REPO}}` → `C:\IfcOpenShell`
- `{{BUILD_BRANCH}}` → `BonsaiPR v0.8.6-alpha260522-346f424 [desc]`
- `{{TARGET_PR}}` → `PR #7965 (inset_section_endpoints)`



I'm working with the BonsaiPR build system `{{BONSAI_PR_REPO}}`, which aggregates IfcOpenShell PRs from
https://github.com/IfcOpenShell/IfcOpenShell into installable builds. The local IfcOpenShell
clone is at `{{IFCOPENSHELL_REPO}}`. The build branch is `{{BUILD_BRANCH}}`. The base branch is `v0.8.0`.

`{{TARGET_PR}}` is being skipped in the build with:
  "⚠️ Skipped - Conflict with other PRs. Merges cleanly with base"

I want to resolve the conflict so both PRs can be included in the same build.
Do NOT modify the BonsaiPR build script (`KNOWN_CONFLICT_RESOLUTIONS` or similar) — the fix must live on the PR branches themselves.

Please work through the following steps:

## Step 1 — Build merge order

Parse the suffix of `{{BUILD_BRANCH}}`: `[asc]` = ascending (lowest PR number first),
`[desc]` = descending (highest PR number first), `[upd]` = by-updated (most recently
updated PR first). State the order explicitly before proceeding — getting this wrong will
cause you to test against the wrong build state and misidentify which PR was merged before
`{{TARGET_PR}}`.

## Step 2 — Identify the conflicting PR(s)

Find all PRs in the build branch that touch the same files as `{{TARGET_PR}}`. Also test
whether any PRs already tagged "Skipped - Conflict with other PRs" conflict with it.

Determine the **exact commit** from the conflicting PR that introduces the conflict — not
just which PR, but which specific commit hash and what it changed.

## Step 3 — Understand the nature of each conflict

For each conflicting PR: is one a subset of the other? Do they solve the same problem
independently? Are they in the same region of a file or just the same file?

## Step 4 — Determine the correct fix strategy

There are two fundamentally different tools. Choose based on whether `{{TARGET_PR}}`'s
**content** needs to change or only its **ancestry** needs to change.

### Option A — `git merge <specific-commit>` (ancestry fix)

Use this when `{{TARGET_PR}}`'s intent is independent of the conflicting change and its
code does not need updating — the conflict arises only because git's 3-way merge sees
both sides changing the same lines relative to their common ancestor.

Merging the specific conflicting commit into `{{TARGET_PR}}`'s branch makes it an actual
ancestor. The build's LCA (merge-base) shifts from the old common ancestor to that commit,
so git's 3-way merge no longer sees a contest — only `{{TARGET_PR}}` makes further changes
above that point.

Think through:
- After the conflicting PR is merged into the build, what is the LCA between the build tip
  and `{{TARGET_PR}}`'s branch?
- What would the LCA be if the conflicting commit were an ancestor of `{{TARGET_PR}}`?
- Does shifting the LCA eliminate the conflict without requiring any code changes in
  `{{TARGET_PR}}`?

### Option B — `git rebase` (content fix)

Use this when `{{TARGET_PR}}`'s code actually needs to change to be correct given what
the conflicting PR introduced. Common cases:

- The conflicting PR changed a function signature or moved a function, and `{{TARGET_PR}}`
  calls it — PR must be updated to use the new form.
- One PR is a logical continuation of the other and should explicitly depend on it.
- The conflict is trivial line-number drift (unrelated insertions above the target region)
  and replaying `{{TARGET_PR}}`'s patch on the new context resolves it cleanly.

Rebase replays `{{TARGET_PR}}`'s commits on top of the conflicting PR's branch, letting you
update the code at each step. The result is a linear history where `{{TARGET_PR}}` is
explicitly built on top of the other PR.

### Decision rule

> Does `{{TARGET_PR}}`'s content need to change, or does only its ancestry need to change?
> Content must change → **rebase**. Only ancestry → **merge the specific commit**.

State which option applies and why before executing.

## Step 5 — Find the correct push target

Before pushing, determine where `{{TARGET_PR}}`'s head branch actually lives:

- Check the GitHub PR to see if the head ref is on the author's fork (`author:branch`)
  or directly on `origin` (`IfcOpenShell/IfcOpenShell:branch`).
- Maintainers with write access to the main repo often push PR branches directly to
  `origin` — do not assume all PRs come from forks.
- Identify the correct remote accordingly.

## Step 6 — Execute the fix

Working in `{{IFCOPENSHELL_REPO}}`, apply the fix on a local branch tracking `{{TARGET_PR}}`'s
head. Resolve any conflicts that arise during the fix itself, preserving the functional
intent of `{{TARGET_PR}}`.

## Step 7 — Verify with a test merge

Before pushing, verify the fix works in `{{IFCOPENSHELL_REPO}}`:

1. Check out the build state **immediately before `{{TARGET_PR}}` would be attempted**
   (i.e., the merge commit of the last PR processed before `{{TARGET_PR}}` in build order).
2. Attempt `git merge --no-ff --no-edit <fixed-branch>` from that state.
3. Confirm it merges cleanly with zero conflicts.

## Step 8 — Push

Push to the correct remote identified in Step 5, using `--force-with-lease`, targeting
the same branch name the PR uses:

```
git push <remote> <local-branch>:<pr-branch-name> --force-with-lease
```

## Step 9 — Append to conflict resolution log

Insert one row at the top of the data in `{{BONSAI_PR_REPO}}/logs/conflict-resolutions.md`
(immediately after the header and separator rows — newest entries go first):

| Column | Value |
|--------|-------|
| `date` | Current date and time (YYYY-MM-DD HH:MM:SS) |
| `build_branch` | `{{BUILD_BRANCH}}` — link to the GitHub release |
| `build_order` | ascending / descending / by-updated |
| `target_pr` | PR number — link to the GitHub PR; branch name |
| `conflicting_prs` | Comma-separated PR numbers — each linked to its GitHub PR |
| `conflict_files` | Comma-separated file paths — each linked to the file at the result commit |
| `key_commit` | Short commit hash — linked to the GitHub commit |
| `fix_strategy` | `ancestry-merge` / `rebase` / `none` (companion release had it) |
| `push_remote` | Remote name pushed to |
| `result_commit` | Short commit hash — linked to the GitHub commit |
| `outcome` | `fixed` / `skipped-companion-had-it` / `failed` |

## Step 10 — Summary document

Write a detailed markdown summary to:
`{{BONSAI_PR_REPO}}/logs/summaries/YYYY-MM-DD-PR-XXXX.md`

The document should cover:
- Which PR(s) conflict and why (with links)
- The specific commit(s) that cause the conflict
- Why the chosen fix strategy works in terms of git 3-way merge mechanics
- Exactly what files were changed and how conflicts were resolved
- The push target and the resulting commit hash

Then add a `Summary` column entry to the log row added in Step 9, linking to this file
using a relative path (e.g., `[PR #XXXX vs #YYYY](summaries/YYYY-MM-DD-PR-XXXX.md)`).
