# RFC-001 — federated curated builds

**Branch:** `feat/rfc-001-federation` · **PR:** falken10vdl/bonsaiPR#11 (draft)
**Status as of:** 2026-08-09

The **engineering log for this subsystem** — permanent, and rewritten as things
change, rather than a branch note deleted when its PR merges. Federation will
keep being refined long after the phases close. See [Lifecycle](#lifecycle) for
which sections decay and which do not.

Design, evidence and measurements live in
[`proposals/RFC-001-federated-curated-builds.md`](../../proposals/RFC-001-federated-curated-builds.md).
Operating a curated instance is
[`.github/workflows/README-curated-build.md`](../../.github/workflows/README-curated-build.md).
**This file is only what those two should not carry**: where the work is, what
bit us, and what is still open.

---

## Where the work is

| phase | what | state |
|---|---|---|
| 0 | `federate.py` — aggregation math + digest | done |
| 1 | profiles, `load_profile()`, `.env` compat | done |
| 1.1 | record which PR won a merge race → `rivals.<order>.json` | done |
| 1.5 | `distill.py` — recover a profile from a build branch | done |
| — | base pinning + `base_advisor.py` | done |
| 2 | `peers.json`, `publisher` block, HTTP peer fetch | done |
| 3 | per-profile `index.json` feeds | done |
| — | pin fallback: build a validated commit when a PR's head breaks | done |
| — | manifest consolidated onto stage 0 | done |
| 4 / 5 | maintainer digest / attestations | **need buy-in — nothing to build until someone asks** |

Live instance: `OpeningDesign/bonsaiPR`, profile `openingdesign` (160 PRs, 160
pins, pinned base `644b92263d`). Latest run: **128 of 129 merged**, 11 of them
via pinned fallback. Publishes `state.rec.json`, `events.rec.jsonl`,
`rivals.rec.json`, `pinned.rec.json`, `delta.rec.md`, and a curated Blender feed
at `profiles/openingdesign/index.json`.

**Nothing runs on a timer, and that is deliberate.** An hourly manifest was tried
and removed: `streak.builds` is an artifact of run frequency rather than a
property of a change, `streak.days` measures elapsed time and does not need
frequent sampling, and every run commits report files back to the repo. Sampling
at the curator's own cadence also measures what the curator actually experiences.
A `full` run additionally publishes a release and force-pushes a build branch —
both statements, not routine.

---

## Things that cost real time

- **`FETCH_HEAD` is overwritten by the next fetch.** Bit me twice, and both
  times produced *confidently wrong* results rather than an error — a worktree
  built on a PR head instead of `v0.8.0`, and a merge of the wrong branch into a
  fork. Resolve to an explicit sha, or fetch into a named ref
  (`fetch <remote> <ref>:refs/x/y`), before doing anything with it.
- **Python stdout is buffered in GitHub Actions logs.** Every `print` from a
  script flushes at the end with near-identical timestamps, while git's own
  output appears in real time. Log ordering is not execution ordering; do not
  reason about sequence from timestamps.
- **`git merge` writes conflict output to stdout, not stderr.** The pipeline logs
  `stderr`, so an ordinary conflict shows as `❌ Failed to apply PR #N:` with
  nothing after the colon. Empty means conflict, not "no information".
- **`inputs` is empty on a `schedule` trigger.** Dispatch defaults do not apply,
  so `${{ inputs.stages }}` is `""` on a cron run and every expression built on
  it silently takes the else branch. Uncommenting a schedule would have built
  *every* open PR, unpinned, and published it as a release. The schedule has
  since been removed, but the trap is waiting for whoever adds one back: resolve
  profile and stages once in `env`, with fallbacks, and never read `inputs`
  further down.
- **An unasserted `str.replace` that matches nothing fails silently.** Three fixes
  in the report code were committed without ever being applied: the merged table
  kept showing PR tips, the "Fork Repository" line kept 404-ing, and one edit
  landed in the wrong one of four tables that share a column name. Each looked
  done in the diff. Assert the match, or use an exact edit, and then verify the
  string is in the file — presence is still not proof it is in the *right* place,
  which is what the wrong-table case shows.
- **Every change must land in two places**: `falken10vdl/bonsaiPR`
  (`feat/rfc-001-federation`, for PR #11) and `OpeningDesign/bonsaiPR` (`main`,
  which is what actually runs). The fork also drifts on its own because its own
  workflow commits reports to it — expect to merge `origin/main` before pushing.

---

## The six bugs, and why they all look alike

Every one was invisible on the canonical instance and appeared immediately on a
second one. Kept as a set because the pattern is the point: this codebase had
one operator, so anything true only of that operator's machine had never been
exercised.

| # | bug | why only we saw it |
|---|---|---|
| 1 | clone-vs-update keyed on directory existence | our workflow pre-created the dir |
| 2 | pagination checked the *filtered* count | latent until a selective profile existed |
| 3 | fresh clone never checked out the base branch | falken's host has a persistent clone; CI clones every run |
| 4 | `index.json` hardcoded falken's release URLs | only wrong for a second publisher |
| 5 | self-pull hardcoded `/home/falken10vdl/...` | only wrong off that machine |
| 6 | merge-order label fell through to `[upd]` | only wrong for a new order (`recorded`) |

Bugs 3 and 6 are the instructive ones: both produced a **green build that was
wrong** — 129 PRs merged onto a v0.7.0 tree, and a correct build labelled as a
different merge order. Neither would have been caught by exit codes.

---

## Open threads

- ~~Manifest ownership is split.~~ **Resolved.** Stage 0 owns it and hands stage 2
  `delta.<order>.md` for the release body; stage 2 falls back to its old path only
  when that file is absent. It cost three published untruths before being fixed —
  missing `base_commit`, and pinned builds recorded at the PR's tip — each
  invisible until a build shipped something false.
- **No way to carry a rebased copy of someone else's PR.** An abandoned PR can
  only be excluded or pinned around. `pin` already maps a PR to a head sha and
  would only need to accept a ref in your own fork. Deliberately unbuilt until a
  PR that actually matters is abandoned.
- **Cross-publisher comparison must group by `base_commit`.** Manifests now
  record it. An aggregate that ignores it can report a 17-PR swing that is
  entirely base drift (RFC §8.1).
- **`events.rec.jsonl` appears only from the second run** of a lineage — the
  first has no previous snapshot to diff. Not a bug; surprising once.

## Untested

- **A second *curator*.** The federation aggregates two publishers, but one is an
  anchor. Adoption signals (`selected_by`, `excluded_by`, `objections`) stay
  near-meaningless until somebody else publishes a selective profile — §3.4's
  caveat, still unresolved by anything built so far.
- **A pinned commit that has been force-pushed away.** Handled with a warning, never
  actually observed.
- **Blender installing the curated feed.** The feed is published and well-formed; no
  one has subscribed to it and installed from it.

---

## Local setup worth not rediscovering

- Anything importing `00_clone_merge_and_create_branch.py` needs `requests` and
  `python-dotenv`. The rig venv at `~/bonsaiPR_testrig/.venv` has them; the
  system Python does not.
- `bonsaipr_profile.py`, `federate.py`, `distill.py` and `base_advisor.py` run on
  a bare Python.
- `base_advisor.py` writes scratch refs under `refs/baseadv/` and deletes them in
  a `finally` — if it is ever killed mid-run, clean them by hand.

---

## <a id="lifecycle"></a>Lifecycle

**This note is permanent.** Upstream's dev-notes convention says to delete a note
when its PR merges, which assumes a *feature*: one branch, one PR, done. This is
a subsystem that will keep being refined long after the phases close, with a
running instance behind it, so there is no point at which "the context is
obsolete" becomes true.

That makes it the subsystem's engineering log rather than a branch note, and
gives it a durable split from the RFC:

| | answers | changes |
|---|---|---|
| `proposals/RFC-001-…` | what we agreed, and why | frozen; superseded by a new RFC, not rewritten |
| `proposals/RFC-001-federated-curated-builds_plain-language.md` | the same idea for a non-technical reader | updated whenever a number here is re-measured |
| this note | what to know before touching it | rewritten continuously |
| `README-curated-build.md` | how to operate an instance | rewritten as the workflow changes |

### What decays, and what does not

Sections here are deliberately of two kinds, because a reader needs to know
which parts to trust:

- **Volatile** — *Where the work is*, *Untested*. True only on the date at the
  top. Rewrite these; never let them accumulate.
- **Durable** — *Things that cost real time*, *The six bugs*, *Local setup*.
  These stay true as long as the code does. Add to them; delete only when the
  underlying cause is genuinely gone.
- **Transitional** — *Open threads*. Each entry leaves when it is resolved or
  promoted into the RFC.

### Staleness test

"We will keep it updated" is what everyone says, so here is something checkable:

> If the **Status as of** date at the top is older than the newest commit
> touching `automation/scripts/` or `profiles/`, this note is stale. Fix it
> before doing anything else.

The failure mode to guard against was never the note existing — it is a note
that still says "phase 2 next" a year after phase 2 shipped, sitting beside a
"traps" section that is still perfectly accurate, with nothing telling a reader
which is which.
