

Variables (update these, then copy the Prompt section below as-is):
- `{{BONSAI_PR_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`
- `{{IFCOPENSHELL_REPO}}` → `C:\IfcOpenShell`
- `{{BUILD_BRANCH}}` → `BonsaiPR v0.8.6-alpha260608-c65433c [asc]`
- `{{TARGET_PR}}` → `PR #7802 (duplicate_opening_on_type_duplication):`



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

> **Also check whether the build already contains an old copy of `{{TARGET_PR}}` itself.**
> This happens when the branch was previously fixed via ancestry-merge in an earlier build,
> and has since been rebased (all hashes changed). Search `git log <build-branch>` for the
> branch name or PR number in merge commit messages (e.g. `git log --oneline <build-branch>
> | grep -i "8083\|parametric_dimensions"`). If found, the "conflicting commit" is that old
> tip of `{{TARGET_PR}}` in the build — not a separate PR.

## Step 3 — Understand the nature of each conflict

For each conflicting PR: is one a subset of the other? Do they solve the same problem
independently? Are they in the same region of a file or just the same file?

> **IFC pset file ID collision:** If both PRs add new entities to a `.ifc` pset file
> (e.g. `Psets_BBIM_Annotation.ifc`) and both start numbering from the same ID (e.g. both
> add `#34`), keep the higher-priority PR's IDs unchanged and renumber the lower-priority
> PR's entities sequentially after the last used ID. Update any back-references (e.g. the
> header property list `(…,#34,#35)`) to match the new IDs.

> **Cascading conflicts from prior resolutions:** The conflict may not be between the
> original PR content but between two independent *resolutions* of the same earlier
> conflict. If a file appears in prior resolution summaries, check those summaries first —
> the correct position for an insertion may already be established by the first resolution,
> and the fix is to make the lower-priority PR match it.

> **Rebase-induced false conflict:** If `{{TARGET_PR}}` was previously in the build (found
> in Step 2 above) and the branch was later rebased, ALL of `{{TARGET_PR}}`'s code will
> conflict with the build's old copy — because git's LCA reverted to the base when the
> hashes changed. The signal: every conflict region is in code that *only* `{{TARGET_PR}}`
> adds, and the build simply has a slightly older version of it. No other PR touched those
> regions. The fix is always **Option A with `-s ours`** (see below) — no content resolution
> needed.

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

**Choose between plain merge and `-s ours`:**

- **`git merge <commit>`** — use when the conflicting commit's content is genuinely absent
  from `{{TARGET_PR}}` and needs to be incorporated. Git performs a normal 3-way merge;
  resolve any conflicts that arise.

- **`git merge -s ours <commit>`** — use when shifting the LCA to the target commit will
  cause all conflict regions to auto-resolve without touching any file content. This works
  in two distinct situations:
  - `{{TARGET_PR}}`'s files *already reflect* the conflicting commit's intent (e.g. the
    branch was previously in the build under different hashes due to a rebase), OR
  - The build made **no further changes to the conflicting regions** after the target commit
    (so only `{{TARGET_PR}}`'s changes are visible from the new LCA → git auto-takes
    `{{TARGET_PR}}`'s version with no conflict, even if the content differs from the
    target commit's).

  **Before executing, verify for each conflict file** that the build made no overlapping
  changes above the new LCA:
  ```
  git diff <target-commit>..<build-tip> -- <conflict-file>
  ```
  If the build DID change the conflicting region above the target commit, `-s ours` alone
  won't resolve that file — combine with a content-fix commit or use a different approach.

Think through:
- After the conflicting PR is merged into the build, what is the LCA between the build tip
  and `{{TARGET_PR}}`'s branch?
- What would the LCA be if the conflicting commit were an ancestor of `{{TARGET_PR}}`?
- Does shifting the LCA eliminate the conflict without requiring any code changes in
  `{{TARGET_PR}}`?
- For each conflict file: does the build change the conflicting region between the target
  commit and the build tip? (`git diff <target-commit>..<build-tip> -- <file>`) If not →
  `-s ours` will auto-resolve it. If yes → content fix also needed.

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

### Option C — Content fix (new commit)

Use this when neither ancestry-merge nor rebase is right — specifically when two PRs
independently resolved the same earlier conflict but chose different code orderings, and
now conflict with each other over position rather than content.

Neither PR's content is wrong; they're just inconsistent. The fix is a new commit on the
lower-priority PR that repositions its additions to match the ordering the higher-priority
PR's resolution already established. After the fix, both sides make the same change at the
same position relative to their LCA → clean auto-merge.

> **Signal:** The conflict is in a file that already has prior resolution summaries, and
> the conflict markers show functionally identical code in different relative positions.

### Decision rule

> Does `{{TARGET_PR}}`'s content need to change, or does only its ancestry need to change?
> Content must change → **rebase** (or **content-fix** if the change is only positional).
> Only ancestry → **merge the specific commit**.

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
| `conflicting_prs` | Comma-separated PR numbers — each linked to its GitHub PR; branch name |
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
