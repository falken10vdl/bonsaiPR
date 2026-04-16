Summary: It finds which PR(s) conflict with a skipped PR in the BonsaiPR build, decides which one to rebase onto the other based on merge readiness, executes the rebase, and pushes the result — all without touching the upstream-bound PR.


# Prompt

I'm working with the BonsaiPR build system `D:\Dropbox\GitHub\bonsaiPR`, which aggregates IfcOpenShell PRs from
https://github.com/IfcOpenShell/IfcOpenShell into installable builds. The build branch
is `remotes/falken10vdl/build-0.8.6-alpha2604160201`. The base branch is `v0.8.0`.

`PR #7781 (Unhide_with_alt_click`) is being skipped in the build with:
  "⚠️ Skipped - Conflict with other PRs. Merges cleanly with base"

I want to resolve the conflict so both PRs can be included in the same build, without
modifying `Unhide_with_alt_click` (it needs to stay clean for upstream submission).

Please:
1. Identify which specific PR(s) in the build branch conflict with `Unhide_with_alt_click`
   by finding commits that touch the same files.
2. Also test the other skipped PRs — they may conflict with each other, not with
   `Unhide_with_alt_click`.
3. For each conflicting PR, understand the nature of the conflict: is one a subset
   of the other? Do they solve the same problem independently?  Can you resolve by changing something in all the conflicting PR's without rebasing?
4. Decide the correct rebase direction: rebase the less mature / less likely to merge
   PR onto the more likely to merge one. Explain your reasoning before moving on to step 5.
5. Execute the rebase, resolving any conflicts.
6. Push the result to the conflicting PR's remote tracking branch using --force-with-lease.
7. Provide a detailed markdown document of what you changed and why.










