Summary: It finds which PR(s) conflict with a skipped PR in the BonsaiPR build, decides which one to rebase onto the other based on merge readiness, executes the fix, and pushes the result.

Variables (update these, then copy the Prompt section below as-is):
- `{{BONSAI_PR_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`
- `{{BUILD_BRANCH}}` → `BonsaiPR v0.8.6-alpha260507-2dcf753`
- `{{TARGET_PR}}` → `PR #7802 (duplicate_opening_on_type_duplication)`


# Prompt

I'm working with the BonsaiPR build system `{{BONSAI_PR_REPO}}`, which aggregates IfcOpenShell PRs from
https://github.com/IfcOpenShell/IfcOpenShell into installable builds. The build branch
is `{{BUILD_BRANCH}}`. The base branch is `v0.8.0`.

`{{TARGET_PR}}` is being skipped in the build with:
  "⚠️ Skipped - Conflict with other PRs. Merges cleanly with base"

I want to resolve the conflict so both PRs can be included in the same build.
Do NOT modify the BonsaiPR build script (`KNOWN_CONFLICT_RESOLUTIONS` or similar) — the fix must live on the PR branches themselves.

Please work through the following steps:

## Step 1 — Determine build merge order

Read the build script at `{{BONSAI_PR_REPO}}/automation/scripts/00_clone_merge_and_create_branch.py`
and inspect the build branch's first-parent log to determine whether PRs are merged in
**ascending** or **descending** numeric order. State the order explicitly before proceeding —
getting this wrong will cause you to test against the wrong build state.

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

Apply the fix on a local branch tracking `{{TARGET_PR}}`'s head. Resolve any conflicts
that arise during the fix itself, preserving the functional intent of `{{TARGET_PR}}`.

## Step 7 — Verify with a test merge

Before pushing, verify the fix works:

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

## Step 9 — Summary document

Provide a detailed markdown document covering:
- Which PR(s) conflict and why (with links)
- The specific commit(s) that cause the conflict
- Why the chosen fix strategy works in terms of git 3-way merge mechanics
- Exactly what files were changed and how conflicts were resolved
- The push target and the resulting commit hash
