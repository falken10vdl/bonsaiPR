# Standing up a curated BonsaiPR instance

How to run your own BonsaiPR that builds *your* curation rather than every open
PR — which is what makes you a distinct publisher under
[RFC-001](../../proposals/RFC-001-federated-curated-builds.md) instead of a
second copy of the canonical answer.

The canonical instance at `falken10vdl/bonsaiPR` builds all ~847 open PRs. A
curated instance builds only what its profile selects. Two builds of *everything*
agree trivially and tell you nothing; two builds of different curations that
agree about a PR is evidence.

---

## 1. What you need

| | |
|---|---|
| A fork of `bonsaiPR` | where the workflow runs, and where reports and releases are published |
| A fork of `IfcOpenShell` | receives the **force-pushed** build branch |
| A profile in `profiles/` | your curation |
| A PAT | pushes to a *second* repo, so the built-in `GITHUB_TOKEN` is not enough |

### The fork warning

The build branch is pushed with `--force`. `FORK_OWNER`/`FORK_REPO` must name a
fork you own and do not do other work in. `BASE_CLONE_DIR` is likewise checked
out, reset, and branch-deleted — on a runner that is a scratch directory, but if
you ever run this locally, **never point it at a repository you work in**.

---

## 2. Getting a profile

If you already maintain a build branch by hand, distil it rather than writing
one:

```bash
cd automation/scripts
python distill.py profile \
  --branch  Ryan_build-0.8.6-alpha2607071335 \
  --repo    /path/to/your/IfcOpenShell \
  --name    openingdesign \
  --maintainer OpeningDesign
```

That writes `profiles/<name>.json` and `profiles/<name>.provenance.json`. Read
the provenance file before trusting the profile — it records how every commit
was attributed and with what confidence.

Otherwise, copy `profiles/example-curated.json`, rename it, and replace the
contents. Validate with:

```bash
python bonsaipr_profile.py check <name>
```

---

## 3. Repository configuration

**Secret** (Settings → Secrets and variables → Actions → Secrets):

| name | value |
|---|---|
| `BONSAIPR_TOKEN` | PAT with `repo` scope, able to push to **both** forks and create releases |

**Variables** (same page → Variables). All optional; the defaults are the
`OpeningDesign` ones:

| name | default |
|---|---|
| `BONSAIPR_OWNER` | `OpeningDesign` |
| `BONSAIPR_REPO` | `bonsaiPR` |
| `BONSAIPR_FORK_OWNER` | `OpeningDesign` |
| `BONSAIPR_FORK_REPO` | `IfcOpenShell` |

A fine-grained PAT needs, on both forks: *Contents: read and write*. On the
release target it also needs *Contents: read and write* for the release upload.

---

## 4. First run

Actions → **Curated build** → *Run workflow*. Pick your profile and start with
**`manifest-only`**.

`manifest-only` runs stage 0 only: clone, merge the profile's PRs, and write the
report plus `state.<order>.json` and `rivals.<order>.json`. That is *everything
federation consumes* — stages 1–2 only add installable zips and a GitHub
release. It is also much faster, so it is the honest way to find out whether
your profile merges at all before spending an hour on packaging.

Once that succeeds, run again with `full`.

The workflow is scheduled: **hourly `manifest-only`** (builds the run-to-run
history federation aggregates — nothing else produces it, and it cannot be
back-filled) and **daily `full`** (releases prune to the most recent 30, so daily
keeps a month of installable builds where hourly would keep 30 hours).

`inputs` is empty on a schedule trigger, so profile and stages are resolved in the
workflow's `env` block with cron-aware defaults. Change the profile a cron uses by
setting the `BONSAIPR_SCHEDULED_PROFILE` repository variable — not by editing the
dispatch defaults, which schedules ignore.

---

## 5. What to expect

- **Time is dominated by fetching**, not merging: each PR comes from a different
  contributor's fork, so a 160-PR profile does 160 fetches from 160 remotes.
- **A single-order profile builds once.** If `orders` names one order, `main.py`
  skips the descending / by-updated retries — a selective profile usually has
  few internal conflicts, so three near-identical builds would be wasted.
- **Selected PRs that closed are reported, not silently dropped.** Stage 0 prints
  which of your selected PRs are no longer open. That is your signal that the
  profile has drifted and wants regenerating.
- **Disk is the likeliest failure.** The workflow reclaims ~20 GB before
  starting; if a `full` run still fails on space, use `manifest-only`, which
  needs far less.

---

## 6. The base, and advancing it

A profile can **pin** the commit it builds on:

```json
"base": { "repo": "IfcOpenShell/IfcOpenShell", "branch": "v0.8.0",
          "commit": "644b92263d" }
```

Omit `commit` to follow the branch tip. `distill` sets it automatically to the
commit your branch was derived from, because that is where its PR set is known
to apply.

**Why pinning helps.** Upstream drift, not PR quality, is what breaks most
merges — a PR that applied cleanly when written conflicts months later because
the base moved under it. Measured on the `openingdesign` curation:

| base | date | PRs landing | vs pinned |
|---|---|---:|---|
| pinned `644b92263d` | 2026-07-07 | **158/160** | — |
| `6ca8c8ac94` | 2026-07-15 | 151/160 | +0 / −7 |
| tip `048242783e` | 2026-08-05 | 141/160 | +0 / −17 |

Advancing gained *nothing* and cost up to 17 PRs. That asymmetry is specific to
an allowlist profile: every selected PR predates the pin, so a newer base can
only take PRs away.

**What it costs.** The build stops receiving upstream fixes, and rebase debt
compounds. Pinning and never looking is how a distribution rots. Pinning *while
watching the number* is how one stays healthy — which is what the rest of this
section is for.

### 6.1 Advancing the pin

The base and the PR pins move **together** — see the warning at step 6 before
starting, because advancing one without the other makes the build worse than
leaving both alone.

**Step 1 — measure first.**

```bash
cd automation/scripts
python base_advisor.py --profile openingdesign --repo /path/to/IfcOpenShell
```

Read-only: it evaluates candidate bases with `git merge-tree`, never checks
anything out, and deletes its own scratch refs. **The "lost" column is your task
list** — those are the PRs that stop merging if you advance.

**Step 2 — split the list by who owns it.** Your own PRs you can rebase today.
Other people's you cannot. On the first run of this exercise, 8 of 11 blockers
were the curator's own.

**Step 3 — rebase your own PR branches.** This happens in your IfcOpenShell
clone, *not* in the profile: a profile references PRs, it does not contain their
commits. For each one:

```bash
git checkout <pr-branch>
git rebase origin/v0.8.0        # resolve conflicts
git push --force-with-lease     # updates the PR head
```

`--force-with-lease`, not `--force`: these are open PRs and someone else may
have pushed to them. See [`prompts/rebase branch onto v0.8.0.md`](../../prompts/rebase%20branch%20onto%20v0.8.0.md).

**Step 4 — re-measure.** The lost column should have shrunk by exactly the
number you rebased. That is the check that the work actually landed.

**Step 5 — decide about PRs that are not yours.** In descending order of
usefulness:

1. **Ask the author to rebase.** Their conflict with the base is real and affects
   every build, not only yours.
2. **Exclude it**, with a reason so the objection carries information:
   `"exclude": {"prs": {"5452": {"why": "regression", "reason": "no longer merges against v0.8.0", "since": "<their head sha>"}}}`
3. **Stay pinned** a while longer, if the PR matters more than the upstream fixes
   you are forgoing.

**Step 6 — advance the base and clear the PR pins together.** Edit
`base.commit`, **and empty or regenerate `pin`**, then rebuild. Confirm the
landing count went *up*.

> ⚠️ **Do not advance the base while carrying the old PR pins.** They are not
> independent settings. `pin` holds the commits a curator validated *against the
> old base*; replaying that old code onto a newer base conflicts more, not less,
> while the PR authors have generally been rebasing their heads *toward* the new
> base. Measured across 129 PRs:
>
> | | validated pins | current heads |
> |---|---:|---:|
> | **pinned base** (2026-07-07) | **128/129** | 127/129 |
> | **`v0.8.0` tip** | **113/129** | **116/129** |
>
> Matched pairs win. Old base with old pins lands 128; new base with current
> heads lands 116; new base with *old* pins lands 113 — worse than never having
> pinned anything. Consistency between the base and the PR commits matters more
> than the recency of either.
>
> (These are isolated merges of each PR against the base, so they measure base
> compatibility, not a build total — a real build also loses PRs to PR-vs-PR
> races. The comparison between cells is what counts.)

So when you advance:

```bash
# regenerate the profile against the new base — this re-derives `pin`
python distill.py profile --branch <your-build-branch> --repo /path/to/IfcOpenShell \
  --name <profile> --maintainer <you>
```

or, if you are not re-distilling, set `"pin": {}` by hand and let every PR build
at its current head. Re-pinning then happens naturally the next time you
hand-validate a branch.

### 6.2 A gap worth knowing about

There is currently **no way to carry a rebased copy of someone else's PR**. If an
author never rebases, the only options are to exclude the PR or stay pinned —
you cannot say "use my fixed version of their branch."

That is precisely what Debian does with `debian/patches`, and the format is one
small step away: `pin` already maps a PR to a head SHA, so allowing it to name a
ref in *your* fork would express it:

```json
"pin": { "5452": { "repo": "OpeningDesign/IfcOpenShell", "ref": "rebased/pr-5452" } }
```

Not built. Worth building the first time a PR you genuinely need is abandoned by
its author — not before.

---

## 7. Subscribing to a curated build in Blender

A full run publishes two feeds:

| feed | URL | advertises |
|---|---|---|
| root | `.../bonsaiPR/main/index.json` | "BonsaiPR" — whatever this instance builds |
| curated | `.../bonsaiPR/main/profiles/<name>/index.json` | "BonsaiPR · `<name>`" |

Both point at the same release. The difference is what the subscriber can tell:
once instances build *different* curations, "BonsaiPR" stops identifying
anything, and a per-profile feed makes subscribing a choice between curations
rather than a bet on how someone configured theirs.

To subscribe, add the curated URL as a remote repository — the steps are the
same as the root feed in the project README:

```
https://raw.githubusercontent.com/OpeningDesign/bonsaiPR/main/profiles/openingdesign/index.json
```

> ⚠️ **One at a time.** The extension id stays `bonsaiPR` in every feed, on
> purpose: curated builds are the same Python module, so they are *alternatives*,
> not companions. The existing "enable Bonsai **or** BonsaiPR, never both" rule
> applies between two curations as well. Distinct ids would wrongly imply they
> can coexist.

The root `index.json` keeps its URL and keeps working, so existing subscribers
are never moved.

---

## 8. Joining the federation

Once your instance publishes reports, others add you to their `peers.json` and
your curation starts contributing to the aggregate. Your reports are already at
a stable public URL by virtue of being committed:

```
https://raw.githubusercontent.com/<owner>/bonsaiPR/main/automation/reports/
```

Aggregate locally at any time with:

```bash
cd automation/scripts && python federate.py digest
```

Cross-publisher aggregation is RFC-001 phase 2 and is not built yet — this is
the half that has to exist first, since there is nothing to federate until a
second real curation is publishing.
