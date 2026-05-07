Summary: It finds which PR(s) conflict with a skipped PR in the BonsaiPR build, decides which one to rebase onto the other based on merge readiness, executes the rebase, and pushes the result — all without touching the upstream-bound PR.

Variables (update these, then copy the Prompt section below as-is):
- `{{BONSAI_PR_REPO}}` → `D:\Dropbox\GitHub\bonsaiPR`
- `{{BUILD_BRANCH}}` → `BonsaiPR v0.8.6-alpha260507-dcd7336`
- `{{TARGET_PR}}` → `PR #7802 (duplicate_opening_on_type_duplication)`


# Prompt

I'm working with the BonsaiPR build system `{{BONSAI_PR_REPO}}`, which aggregates IfcOpenShell PRs from
https://github.com/IfcOpenShell/IfcOpenShell into installable builds. The build branch
is `{{BUILD_BRANCH}}`. The base branch is `v0.8.0`.

`{{TARGET_PR}}` is being skipped in the build with:
  "⚠️ Skipped - Conflict with other PRs. Merges cleanly with base"

I want to resolve the conflict so both PRs can be included in the same build.
The upstream PR branch on `origin` must remain unchanged — it is submitted to
IfcOpenShell for review. BonsaiPR fetches each PR's head from the author's fork remote
(not origin); determine the correct fork remote from the PR's author and push only there,
using `--force-with-lease`. Do NOT push to origin.

Please:
1. Identify which specific PR(s) in the build branch conflict with `{{TARGET_PR}}`
   by finding commits that touch the same files. Also test to see if it conflicts with any PRs that are tagged as: "Skipped - Conflict with other PRs".
2. For each conflicting PR, understand the nature of the conflict: is one a subset of the other? Do they solve the same problem independently? Do NOT modify the BonsaiPR build script (KNOWN_CONFLICT_RESOLUTIONS or similar) — the fix must live on the PR branches themselves.
3. Decide the correct rebase direction: rebase the less mature / less likely to merge PR onto the more likely to merge one. Explain your reasoning before moving on to step 4.
4. Execute the rebase, resolving any conflicts.
5. Push the rebased branch to the PR author's fork remote using --force-with-lease, targeting the same branch name the PR uses (e.g.,
   `git push <author-remote> <local-branch>:<pr-branch-name> --force-with-lease`). Do NOT push to origin.
6. Provide a detailed markdown document of what you changed and why. Provide markdown links to all conflicting PRs.
