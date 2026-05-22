# Prompts

AI-assisted maintenance prompts for the BonsaiPR build system. Each file is a
template: fill in the variables at the top, then paste the prompt body into a
Claude Code session.

---

## resolve conflicts with other PRs.md

**When to use:** A PR appears as *"Skipped — Conflict with other PRs. Merges
cleanly with base"* in a build release. The fix must land on the PR branch
itself (ancestry-merge or rebase) so it resolves cleanly in future builds
without touching `KNOWN_CONFLICT_RESOLUTIONS`.

**Which build to target:**

Each run produces up to three releases — `[asc]` (lowest PR# first), `[desc]`
(highest PR# first), and `[upd]` (most-recently-updated first). In any
conflicting pair, the build order determines which PR "wins":

| Build | Winner (merged first) | Loser (skipped) |
|-------|-----------------------|-----------------|
| `[asc]` | lower-numbered PR | higher-numbered PR |
| `[desc]` | higher-numbered PR | lower-numbered PR |

**Prioritize `[desc]` conflicts.** The lower-numbered PR in a conflicting pair
is already included in `[asc]` automatically; fixing `[desc]` is what gets it
into both releases. The exception is when the higher-numbered PR is clearly the
better or more complete contribution — in that case fix `[asc]` instead so it
appears in both.

---

## rebase branch onto v0.8.0.md

**When to use:** A PR branch has fallen behind `v0.8.0` and conflicts with the
base branch itself (not with other PRs). This is distinct from PR-PR conflicts —
the PR fails to merge even in isolation. Rebasing onto the latest `v0.8.0` tip
resolves the divergence and clears it from the *"Failed to Merge (conflicts with
base)"* list.
