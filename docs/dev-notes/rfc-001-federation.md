# RFC-001 — federated curated builds

**Branch:** `feat/rfc-001-federation` · **PR:** falken10vdl/bonsaiPR#11 (draft)
**Status as of:** 2026-10-04

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
| — | `docs/TUTORIAL.md` — curator + subscriber walkthrough | done |
| 4 / 5 | maintainer digest / attestations | **need buy-in — nothing to build until someone asks** |

Live instance: `OpeningDesign/bonsaiPR`, profile `openingdesign`. On 2026-10-03
the profile was retargeted from v0.8.0 (156 PRs, pinned base `644b92263d`; last
run **128 of 129 merged**, 11 via pinned fallback) to **v0.9.0 at tip**: the
same branch's still-open PRs, its recorded order except #8228 ahead of #7813.
First built as 119 PRs (full run 37148950237: 109 merged; #8251 lost to a
runner fetch error). Then 22 more, cherry-picked onto the branch in full and
missed by `distill` until it learned to see them (see below), took it to 141
PRs with 132 pins, each the head that merged in a full in-order replay at
`d1d6a6b78d`; `base_advisor.py --in-stack` agrees, 132 of 141. That day seven
stack collisions were fixed in the PR branches themselves (#8083, #8201,
#7940/#8241, #8319, #8242, #8171, #9494) and one by order (#8228 over #7813,
which now drops). Publishes `state.rec.json`, `events.rec.jsonl`,
`rivals.rec.json`, `pinned.rec.json`, `delta.rec.md`, and a curated Blender feed
at `profiles/openingdesign/index.json`. By 2026-10-04 the profile had grown to
172 PRs (163 pins). Most of the increase came from a second `distill` pass, plus
more collisions fixed in PR branches. Full run 37258017497 merged **163**: 8
failed and need an author rebase, and #7813 drops by design. #8971 is left out on
purpose because it overlaps #8200 across a whole function. Instance artefacts
carry the `Frankenstein_` prefix (`BONSAIPR_ASSET_PREFIX`).

**Nothing runs on a timer, and that is deliberate.** An hourly manifest was tried
and removed: `streak.builds` is an artifact of run frequency rather than a
property of a change, `streak.days` measures elapsed time and does not need
frequent sampling, and every run commits report files back to the repo. Sampling
at the curator's own cadence also measures what the curator actually experiences.
A `full` run additionally publishes a release and force-pushes a build branch —
both statements, not routine.

---

## Things that cost real time

- **A commit's sha does not survive being moved; its patch-id does.** This is one
  bug that surfaced twice in an hour, in two different files, and both times the
  wrong answer looked plausible enough to publish:
  - *Behind head* used `rev-list pin..tip`, which assumes the pin is an ancestor
    of the head. On a force-pushed branch it is not, so the count silently became
    "length of the branch" — #8083 read 47, which happened to be its exact commit
    count. Nine of eleven pinned PRs turned out to be rebased.
  - `attribute()` only ever matched merge subjects, so every cherry-picked commit
    fell through to residue and was reported as the curator's own unshared work.
    That produced **81**, which reached RFC-001 as the headline justification for
    phase 1.5. The real number is 6; 75 were already on open PRs.

  The same file already used `git cherry` — patch-id — to detect upstream
  absorption. The knowledge was present and applied on one side of the ladder
  only. When comparing commits across branches, ask first whether a rebase or a
  cherry-pick would break the comparison.
- **"Does this PR merge?" has two different answers.** `base_advisor.py` merged
  each PR onto the base *alone* and reported 127/129 — while the real build
  needed a pinned fallback for eleven of them, because they collide with PRs
  merged earlier in the same run. Its docstring said it answered "how many of my
  selected PRs actually merge?", which is how it came to be quoted in RFC §6 as
  evidence that advancing the base gains nothing. It cannot see a stack
  interaction, so `+0` there means *unknown*, not *zero*. `--in-stack` replays
  the curation in order (`merge-tree` chained through `commit-tree`, no worktree)
  and is the mode to decide on. It also has to score only PRs the build
  considers: `refs/pull/<n>/head` resolves long after a PR closes, so the first
  version scored 156 selected PRs against a build universe of 129 and reported
  six closed PRs among the casualties of advancing. Filtered, the replay
  reproduces the pipeline's pin count exactly, which is the check that makes it
  trustworthy.
- **Every full build published a release missing 3 of its 7 zips, green.** The
  runner installs Python 3.11; stage 1 shells out to `python3.13` by name for the
  Blender 5.1 variants, which failed with `python3.13: not found` on all three
  targets. `build_addons()` returned `len(addon_files) > 0` — one zip is enough —
  so the run exited 0, the release went out, and the feed was updated. Found only
  because a release had 5 assets where a doc said 7, and the curator knew the
  missing ones were the py313 set. The interpreter is now installed and a partial
  build fails the run; the deeper lesson is that a *count* of expected artefacts
  is worth having, because "some output exists" is not a success condition.
- **A regex can be dead code and still read correctly in a diff.** A patch meant
  to write a backslash-b escape wrote a literal backspace byte (0x08) into the pattern instead,
  so the new attribution rung compiled cleanly and matched nothing. The diff
  looked right; `repr()` of the compiled pattern is what showed it. Test a regex
  against its inputs — reviewing it is not enough.
- **A number that flatters the design deserves the most scrutiny, not the least.**
  The 81 was attractive — it reframed the feature — and so it went into three
  documents without anyone testing it. The user's own "that isn't really new
  work, it's usually work pushed to a PR and then cherry-picked" is what broke it.
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
- **A profile's `base.branch` was read and then ignored.** `bonsaipr_profile.py`
  parsed it, but stages 0-2 took the branch only from `SOURCE_BASE_BRANCH`, which
  the workflow hardcoded to `v0.8.0`. A v0.9.0 profile without a pinned commit
  would have merged onto v0.8.0's tip, been labelled 0.8, and finished green.
  Caught while preparing the first v0.9.0 profile, before it ran. Now
  `resolve_base_branch()` decides for every stage: the profile's branch wins,
  the env var may only agree with it, and the workflow exports what the profile
  says instead of hardcoding it. The same was true of `exclude.drafts`: parsed,
  never read, every draft skipped regardless; stage 0's draft check now honours
  it (needed for #8928, a draft the curation carries).
- **The first v0.9.0 full run (37148950237) published three wrong things,
  green.** (1) #8251 hit `fatal: unable to read tree` while being fetched, was
  never merged, then merged cleanly in the individual re-test and was reported
  as "conflict with other PRs"; a fetch is now retried once, and a PR that
  still cannot be fetched is skipped in the re-test (result unknown) and its
  report row says why. (2) The manifest said `"release": {"tag": null}`: stage
  2 stopped writing the manifest when stage 0 took it over, and with it the
  release stamp; stage 2 now stamps the release into stage 0's manifest once
  the release exists. (3) The feed still offered Intel Mac subscribers an
  August v0.8.6 build: entries were only ever updated, never dropped, so a
  target the new base no longer builds kept its old URL. Entries for unbuilt
  targets are now dropped, and new targets get an entry cloned from a sibling
  of the same python version, so a target can come back.
- **`distill` only knew the PRs it had been shown, and never promoted a pick.**
  It found PR heads only under `refs/remotes/pr*`, the refs this pipeline's
  merges create; a working clone keeps them under `refs/prhead/<n>` (3,187 in
  the reference checkout). Anything opened after the last pipeline fetch was
  invisible, so its commits read as the curator's own work: 91 "residue"
  commits were in fact 78 commits on open PRs and 13 genuinely unshared. And a
  cherry-picked PR was never selected, even when every commit was on the
  branch: #9765 was one commit, byte-identical, and missing from the build.
  Now `refs/prhead/*` and `refs/pull/*/head` are scanned too; a PR whose every
  own commit (beyond the `v*` release branches) is on the branch by patch-id
  is selected, at the position of its last picked commit; "all present but
  some adapted" (usually an earlier version of the PR) and "partial" are
  listed for review, not selected. 22 open PRs came back that way. A third
  review bucket, "substance", separates PRs whose code is all there but whose
  test or doc commits are not, usually because they were added after the pick
  (#9044, #9555, #9557). Before, these were "partial" and looked like a partial
  pick. A PR's commits can also arrive *inside* another merged
  PR (#8061/#8062/#8064 rode in on #8083): those are not cherry-picks and the
  host PR already carries them, so a whole-branch comparison overcounts.
- **A sidecar skipped when empty is a stale sidecar.** `write_pinned()` and
  `write_rivals()` returned early when there was nothing to record, so the
  previous run's file stayed. The first v0.9.0 run pinned nothing and left
  `pinned.rec.json` saying 11 PRs were pinned, from a v0.8.0 run in August;
  the next full run's stage 2 would have recorded those 11 as built at their
  old v0.8.0 commits, in the published manifest. Both now always write,
  empty when nothing applies, which `federate.py` already reads as "none"
  (no file stays "unknown"). Same run: `commit_reports.py` titled every
  commit from `state.asc.json`, so a curated instance's commits carried the
  canonical counts (578 merged for a run that merged 110); it now uses the
  snapshot actually staged, asc first.
- **The base decides what can be built, not stage 1.** Stage 1 kept its own
  target list (py311 on linux/macos/macosm1/win, py313 without macos). v0.9.0
  dropped Intel macOS, so a full v0.9.0 run would have asked `make` for
  py311/macos, been refused, and, under the partial-build rule, failed after
  ~40 minutes. falken's canonical v0.9.0 builds hit the same refusal without
  that rule and publish 6 zips where the list promises 7. Stage 1 now narrows
  its list to the Makefile's `SUPPORTED_PYVERSIONS`/`SUPPORTED_PLATFORMS` and
  records what it skipped in `build_targets.json` (`skipped_unsupported`):
  7 zips on v0.8.0, 6 on v0.9.0.
- **On Windows, text-mode stdin turns `\n` into `\r\n`.** `base_advisor.py`
  piped its `delete refs/baseadv/<n>` list to `git update-ref --stdin` with
  `text=True`; git read every ref name with a trailing CR, rejected the batch,
  and deleted nothing. The result was captured and never checked, so every run
  on Windows left one ref per scored PR in the user's repo, each pinning a PR's
  objects against gc, while its own comment promised it never would. Found
  2026-10-03 when 138 refs survived a run. Fixed by sending bytes and reporting
  leftovers. `git patch-id` is unaffected (it ignores whitespace), so the
  same pattern in `distill.py` and stage 0 is harmless, but anything else
  that feeds git line-oriented stdin needs bytes.
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
- **A PR that merges upstream quietly leaves the build.** It is no longer open,
  so stage 0 never sees it, while its pin stays in the profile. #7839 merged into
  v0.9.0 between two runs: the manifest said 162 merged against 163 pins, and it
  read like a lost PR. Its code is in the base, so nothing is missing. Remove it
  from `select.prs`, `order_seq` and `pin` when that happens, and check
  `gh pr view <n> --json state,mergedAt` before chasing a count that is one low.

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

- **A second *publishing* curator.** One has now appeared partially: an outside
  poweruser (osarch, 2026-08-22) keeps a hand-built `integration` branch and has
  run `distill` against it, which found two real usability defects — see the
  attribution rung and the PR-index warning above. They build locally and publish
  nothing, so the federation still aggregates two publishers, one of them an
  anchor. Adoption signals (`selected_by`, `excluded_by`, `objections`) stay
  near-meaningless until somebody else publishes a selective profile — §3.4's
  caveat, still unresolved by anything built so far.
- **A pinned commit that has been force-pushed away.** Handled with a warning. No
  longer hypothetical in the milder form: 9 of 11 pins sit on branches that have
  since been rebased, so the pin is no longer an ancestor of the head even though
  the object still exists. Losing the object outright is still unobserved.
- ~~**Blender installing the curated feed.**~~ **Done, 2026-08-09.** Added as a
  remote repository from
  `raw.githubusercontent.com/OpeningDesign/bonsaiPR/main/profiles/openingdesign/index.json`
  and installed successfully. That closes the last consumer-side unknown: the
  feed is not just well-formed, it is one Blender actually accepts. Note the
  release it points at was the first to carry the py313 variants at all — every
  earlier one served Blender 4.x only, silently.

---

## Local setup worth not rediscovering

- Anything importing `00_clone_merge_and_create_branch.py` needs `requests` and
  `python-dotenv`. The rig venv at `~/bonsaiPR_testrig/.venv` has them; the
  system Python does not.
- `bonsaipr_profile.py`, `federate.py`, `distill.py` and `base_advisor.py` run on
  a bare Python.
- `base_advisor.py` writes scratch refs under `refs/baseadv/` and deletes them in
  a `finally`, warning if any survive. If it is ever killed mid-run, clean them
  by hand: `git for-each-ref --format="delete %(refname)" refs/baseadv/ | git update-ref --stdin`.
  Before 2026-10-03 the cleanup silently did nothing on Windows (see above), so
  a repo it ran against there may still hold them.

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
