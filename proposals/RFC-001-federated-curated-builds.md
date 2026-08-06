# RFC-001: Federated Curated Builds

**Status:** Draft — for discussion
**Author:** theoryshaw
**Audience:** falken10vdl, BonsaiPR collaborators, OSArch
**Target:** BonsaiPR automation (`automation/`)

---

## Contents

- [1. The problem](#s1)
- [2. Non-goals](#s2)
- [3. What already exists (and why this is smaller than it sounds)](#s3)
  - [3.1 The aggregation algorithm exists](#s3-1)
  - [3.2 The published artifact exists](#s3-2)
  - [3.3 Curation exists, but is not an artifact](#s3-3)
  - [3.4 The honest caveat that shapes everything below](#s3-4)
- [4. Artifact 1: the Profile](#s4)
  - [4.1 Backwards compatibility](#s4-1)
  - [4.2 How an exclusion actually works](#s4-2)
- [5. Distilling a profile from an existing build branch](#s5)
  - [5.1 What a real poweruser branch actually contains](#s5-1)
  - [5.2 The `distill` command](#s5-2)
  - [5.3 Two things worth more than the PR list](#s5-3)
  - [5.4 Residue handling, and the privacy default](#s5-4)
  - [5.5 Replay and reconciliation](#s5-5)
  - [5.6 Where this is weakest](#s5-6)
- [6. Artifact 2: the Manifest](#s6)
- [7. Artifact 3: the Peer index](#s7)
- [8. The aggregator and its signals](#s8)
  - [8.1 Signal definitions](#s8-1)
  - [8.2 Integration robustness is not functional robustness](#s8-2)
  - [8.3 What rejection reveals that selection cannot](#s8-3)
  - [8.4 Worked example](#s8-4)
- [9. Trust and anti-gaming](#s9)
- [10. Consumption: per-profile Blender feeds](#s10)
- [11. Phasing](#s11)
- [12. Implementation results](#s12)
  - [12.1 What the current backlog looks like](#s12-1)
  - [12.2 The anti-gaming rule, demonstrated](#s12-2)
  - [12.3 What phase 0 changed about the plan](#s12-3)
  - [12.4 Phase 1 results](#s12-4)
- [13. Risks and open questions](#s13)
- [14. Summary](#s14)

---

## <a id="s1"></a>1. The problem

**AI moved the bottleneck in open source from writing code to curating it.** Producing a
plausible patch is now nearly free; deciding whether it belongs is not, and that cost
lands on the smallest group in any project. Everything below follows from that one
observation, and none of it is specific to Bonsai — Bonsai is just where the numbers
happen to be in front of us.

Those numbers: as of 2026-08-06 a build run sees **847 open PRs**, of which 454 merge
cleanly under every merge order, 181 merge under some and not others, and 212 merge
under none ([§12](#s12)). Every one of the first two groups is a change that *might* be
worth merging upstream, and the only evidence a maintainer has for any of them is the PR
diff and whatever comments it accumulated.

BonsaiPR already changed the question from *"should this be merged?"* to *"who wants to
use this?"* — but it currently answers that question with a single, one-size-fits-all
build. Everyone gets everything.

This RFC proposes the next step: let people publish their own **curated** builds, and
let those curations **aggregate** into a signal that says which PRs and which
*combinations* of PRs actually hold up in practice.

The payoff for an upstream maintainer is a line like this on a PR:

> Selected by 6 of 9 independent curators. Merged cleanly in 14 consecutive builds
> over 42 days. Conflicts only with #7098. No curator has dropped it.

That is a materially different kind of evidence from three "LGTM" comments.

---

## <a id="s2"></a>2. Non-goals

Stating these up front because they are the failure modes this design is steering around.

- **No user telemetry.** Nothing here reports on people, installs, sessions, or usage.
  The unit of data is a *build manifest* — a machine-readable statement of what a
  curator chose to build. It is published deliberately, by a person, as a file in a
  git repo. If a signal can only be obtained by watching users, it is out of scope.
- **No central server.** Aggregation is a pull over public URLs. Any curator can run
  the aggregator over any peer list and get the same answer.
- **No new governance authority.** This produces evidence. It does not produce
  decisions, votes, or merge rights. Upstream maintainers remain free to ignore all
  of it.

  It would be dishonest, though, to stop there. Evidence has second-order governance
  effects whether a document disclaims them or not, and the most likely one is worth
  saying out loud: **a public, continuous record of who curates well will probably
  change how people become maintainers.** Today that path runs on visibility and
  personal relationship, which is slow, reproduces the existing group's blind spots,
  and depends on an incumbent having time to notice you. A public record does not
  replace the moment someone grants merge rights — it makes that grant answer to
  something. Two years of well-adopted curation becomes hard to ignore, and social
  proximity alone becomes harder to promote on.

  That is a feature, and it is also the design's most obvious way to go wrong, so it
  is tracked as a risk in [§13](#s13) rather than claimed as a benefit.
- **Not a fork of BonsaiPR.** Every phase below is backwards compatible with the
  canonical falken10vdl instance, and phases 0–1 require no change to how that
  instance runs.

---

## <a id="s3"></a>3. What already exists (and why this is smaller than it sounds)

Most of the substrate is built. This RFC is largely about *generalizing* three things
that already work.

### <a id="s3-1"></a>3.1 The aggregation algorithm exists

[`pr_state.py:239`](../automation/scripts/pr_state.py) `compute_robustness()` already
takes N independent builds of the same PR set and, per PR, computes:

```
merged_in   [source, ...]   sources whose build merged this PR
blocked_in  [source, ...]   sources that saw it but did not merge it
stable      bool            merged in every source that saw it, seen by >= 2
```

Today N = 3 and the sources are the canonical instance's own `asc` / `desc` / `upd`
merge orders. **Federation is the same function with the source key changed from a
merge order to a publisher.** The sorting, the "seen by ≥ 2" guard, and the provenance
tracking in `robustness_sources()` all carry over unchanged.

That function is already consumed to render per-PR stability into the build report at
[`00_clone_merge_and_create_branch.py:973-976`](../automation/scripts/00_clone_merge_and_create_branch.py).
That is where a federated signal would render too.

### <a id="s3-2"></a>3.2 The published artifact exists

`automation/reports/state.{asc,desc,upd}.json` is already a normalized, diff-stable,
per-PR snapshot, committed every run, with an append-only companion
`events.{asc,desc,upd}.jsonl`. It already carries `base`, `merge_order`,
`generated_at`, `counts`, and per PR: `status`, `head`, `title`, `author`, `branch`,
`url`.

It is already pushed to a public repo by `commit_reports.py`, which means it is
already fetchable at a stable `raw.githubusercontent.com` URL. **A peer needs nothing
we do not already publish**, except a statement of *who published it and under what
curation* ([§6](#s6)).

### <a id="s3-3"></a>3.3 Curation exists, but is not an artifact

`USERNAMES`, `EXCLUDED`, and `SKIP_CPP_PRS` in
[`.env.example:23-28`](../automation/.env.example) are already a curation mechanism, and
[`.env.collaborator.example`](../automation/.env.collaborator.example) already anticipates
other people running their own instances.

What is missing is that a curation is currently **three comma-separated strings in an
untracked `.env`**. It cannot be named, versioned, shared, forked, diffed, or cited.
That is the actual gap, and [§4](#s4) addresses it.

### <a id="s3-4"></a>3.4 The honest caveat that shapes everything below

**Today, "included in a BonsaiPR build" carries almost no information**, because the
canonical build includes every non-draft PR that merges. A signal built on inclusion
would report "included by 1 of 1" for 485 PRs and mean nothing.

The signal only becomes informative once curation is *selective* — once a curator has
said "I want these 40, not those 445." This is why profiles are not a nice-to-have
bolted onto the aggregator; **they are the precondition for the aggregator to carry
any information at all.** The two halves ship together or not at all.

---

## <a id="s4"></a>4. Artifact 1: the Profile

A profile is a curation expressed as a committed file. It is the thing a person
maintains, forks, and is known for.

`profiles/architecture-production.json`:

```json
{
  "schema": 1,
  "name": "architecture-production",
  "description": "Bonsai for production architectural documentation. Drawing, scheduling, and sheet workflows. No experimental UI.",
  "maintainer": "theoryshaw",
  "inherits": "falken10vdl/everything",
  "base": {
    "repo": "IfcOpenShell/IfcOpenShell",
    "branch": "v0.8.0"
  },
  "select": {
    "mode": "allowlist",
    "prs": [7123, 7151, 7798, 8719, 9019],
    "authors": [],
    "labels": []
  },
  "exclude": {
    "prs": {
      "7098": {
        "why": "architecture",
        "reason": "bypasses the tool/ abstraction and calls ifcopenshell directly",
        "since": "8f09b96"
      },
      "8206": "crashes on IFC4X3 files"
    },
    "authors": [],
    "drafts": true,
    "cpp": true
  },
  "prefer": [[7900, 8123]],
  "pin": {
    "7123": "8f09b96"
  },
  "orders": ["ascending", "descending", "by-updated"]
}
```

Notes on the design:

- **`mode`** is `allowlist` (only these PRs) or `everything` (current BonsaiPR
  behaviour: all non-draft PRs, minus `exclude`). `everything` keeps the canonical
  instance expressible as a profile, which is what makes migration free.
- **`inherits`** handles the common case — *"whatever the canonical build ships, minus
  these three."* Without it, every curator has to restate 485 PR numbers and the file
  churns on every upstream change. Resolution is a shallow merge: the parent's
  `select` is the starting set, the child's `exclude` and `select` are applied on top.
  **Exclusions union rather than replace** — a child saying "also not this one" must
  never silently drop the parent's refusals, which is the one merge rule that would
  quietly change a curation's meaning if it went the other way. An `owner/profile`
  reference is federated and needs phase 2 to fetch; until then only the local part
  resolves, with a warning, rather than silently building something other than what
  the file asks for.
- **`pin`** freezes a PR at a known-good head SHA. This is what makes a curated build
  a *stable product* rather than something that silently changes under the user when a
  contributor force-pushes. It is also, deliberately, a strong quality signal — a
  curator who pins is saying "I tested this exact commit." One caveat: if the contributor
  rebases or force-pushes their PR branch, the old SHA becomes orphaned — no longer
  fetchable from any public ref, and impossible to verify even in principle. This is
  distinct from a PR simply advancing (where the old SHA remains reachable as an
  ancestor of the new tip). The reconciliation report ([§5.5](#s5-5)) distinguishes these
  two cases, and `pinned_by` ([§8.1](#s8-1)) counts only pins whose SHA is still reachable.
- **`orders`** is per-profile because a selective profile with 40 PRs may have no
  conflicts at all, in which case building three orders is wasted CPU.
- **`exclude.prs` carries a reason, not just a number.** This is the single most
  important field in the format and the argument for it is [§8.3](#s8-3): what a
  curator *refuses* is more architecturally informative than what they accept. A bare
  list of numbers throws that away. Mechanics in [§4.2](#s4-2).
- **`prefer`** records *"when these two collide, take the first."* A pairwise
  preference is not a rejection of the loser, and collapsing it into one would be the
  fastest way to make the objection signal lie — see [§4.2](#s4-2). It is also directly
  useful to the build itself, since it is the same shape of knowledge as
  `KNOWN_CONFLICT_RESOLUTIONS`.

### <a id="s4-1"></a>4.1 Backwards compatibility

`.env` keys map onto an implicit profile, so nothing breaks and nobody is forced to
migrate:

| `.env` today  | Profile field           |
|---------------|-------------------------|
| *(unset)*     | `select.mode: everything` |
| `USERNAMES`   | `select.authors`        |
| `EXCLUDED`    | `exclude.prs`           |
| `SKIP_CPP_PRS`| `exclude.cpp`           |

Integration point: the env parsing block at
[`00_clone_merge_and_create_branch.py:41-62`](../automation/scripts/00_clone_merge_and_create_branch.py)
becomes a call to `load_profile()` that returns the same `users` / `excluded_prs` /
`SKIP_CPP_PRS` values it produces today, sourced either from a profile file
(`BONSAIPR_PROFILE=architecture-production`) or from the legacy env vars. The ~950
lines of merge logic downstream do not change.

### <a id="s4-2"></a>4.2 How an exclusion actually works

An exclusion is the highest-value thing in a profile ([§8.3](#s8-3)) and also the
easiest to get wrong, so the mechanics matter more than the field does.

**An exclusion only means anything relative to a baseline that would have included it.**
If a profile says `inherits: falken10vdl/everything` and then excludes #8123, that is a real
subtraction: the PR *was* in the set and the curator took it out. If a profile is a bare
`allowlist` of 40 PRs, the other 445 are not rejected — they are absent, and were very
likely never looked at. `exclude` on a profile with no `inherits` is therefore almost
always a mistake and should raise a validation warning rather than being silently
aggregated.

**The `since` SHA is what keeps this fair.** An exclusion records the head commit it was
made against:

```json
"8206": { "why": "regression", "reason": "crashes on IFC4X3 files", "since": "8f09b96" }
```

Once the PR advances past that commit, the objection goes **stale** and stops counting
until someone reaffirms it. Without this the aggregate becomes a permanent public mark
on a contribution based on a months-old snapshot — the author fixes the crash three
weeks later and the objection follows them anyway. Staleness is not a nicety here; it is
the difference between a signal and a grudge.

**`why` is a small controlled vocabulary; `reason` is free text.** Category makes the
data aggregatable, free text keeps it honest, and neither works alone:

| `why` | meaning | feeds the design signal? |
|---|---|---|
| `architecture` | works, but is built the wrong way | **yes — this is the one** |
| `regression` | it broke something | no — this is a bug report |
| `scope` | fine, but not what this profile is for | no |
| `duplicate` | superseded by another PR | no |
| `performance` / `unstable` | measured or observed problems | no |

Both fields are optional. A bare `"8206": "reason string"` and even a plain array of
numbers stay valid and mean "excluded, no reason given." **Reasons are encouraged and
never required** — a mandatory field would simply fill up with `"n/a"`.

**Capture it at the moment of discovery, not in bulk afterwards.** The realistic
sequence is: a build misbehaves, the delta report says what is new since the last good
one, the curator finds the culprit, and has to act right then. That is also the only
moment they know precisely why. Reasons written later, in a batch, will be worthless:

```
bonsaipr exclude 8206 --why regression --reason "crashes on IFC4X3 files"
```

**What the loader warns about.** All of these are warnings, never failures — a curation
that is slightly wrong should still build. They are the cases that would quietly corrupt
the aggregate rather than break a run:

| condition | why it matters |
|---|---|
| `exclude` on an allowlist with no `inherits` | asserts rejections nobody made |
| unknown `why` category | carried, but silently absent from the design signal |
| `since` that is not a sha | staleness can never be checked |
| **a reason with no `since`** | **the objection can never go stale, so it is permanent** |
| circular `inherits` | resolution would not terminate |

The fourth one only became obvious while implementing: a curator who writes a careful
architectural reason and omits `since` has, without meaning to, made a permanent public
mark on someone's PR. Warning about it is the difference between the staleness rule
being a design intention and being a thing that actually happens.

**A preference is not a rejection.** "I took #7900 over #8123 because they collide" says
nothing about #8123's quality — the curator may well like it. That belongs in `prefer`,
as an edge between two PRs. Recording it as an exclusion would make every PR that merely
lost a merge race accumulate objections it never earned, which is the single fastest way
to make this whole aggregate dishonest.

---

## <a id="s5"></a>5. Distilling a profile from an existing build branch

Nobody is going to hand-write a profile listing 158 PR numbers. But powerusers are
*already* maintaining exactly that curation — as a long-lived, hand-composed build
branch, accumulated over months of merging and cherry-picking. Those branches are
messy, private, and undocumented, and every one of them is a curation that the
federation wants.

So the primary way a profile should come into existence is not by authoring one. It is
by **distilling one out of a branch that already works.**

### <a id="s5-1"></a>5.1 What a real poweruser branch actually contains

Measured by `distill.py` against `Ryan_build-0.8.6-alpha2607071335`, base `v0.8.0` at
`6f3acc84ee`, on 2026-08-06. (An earlier draft of this section quoted figures taken
against a different `v0.8.0` tip; base branches move, so any measurement like this has
to name the commit it was taken against.)

| | count | |
|---|---:|---|
| commits ahead of base | 655 | |
| merge commits | 183 | |
| **first-parent merges** | **160** | deliberate integration acts by the curator |
| — carrying `pr-NNNN/` in the subject | **158** | attributable by regex alone |
| — attributed once the PR index is consulted | **160** | **100%** |
| first-parent non-merge commits | 94 | |
| — already absorbed upstream | 13 | dropped, not attributed |
| — **residue** | **81** | the curator's own unpublished work |
| first-parent merges needing a textual hand-resolution | **1** | |
| off-path **ancestry resolutions** | **7** | see [§5.3](#s5-3) |

Three findings from this that shape the design:

**The branch is already a declarative curation.** 158 of 160 integration acts name their
PR directly (`Merge remote-tracking branch 'pr-8353/fix-4790-regen-style'`). Attribution
is a regex, not an inference problem. The other two name a fork and branch
(`BIMvoice/fix-6508-geography-element-qto`) and resolve against the PR index — which is
just `state.asc.json`, already published every run, so the ladder needs no GitHub API at
all. Combined attribution is 100%.

**The residue is not glue — it is unpublished feature work.** I expected the local
commits to be conflict fixups. They are not. They are substantive features, many
already citing upstream issues: annotations shared across drawings (#9019), linked-model
include/exclude filters, storey elevation sync (#8545), `MergeDuplicateContexts`,
appended-asset style preservation (#8667, #8666). Some correspond to PRs the author
opened elsewhere; some have never been offered upstream at all. They cluster into 24
candidate patch series, 13 of which hold more than one commit.

That reframes this feature. It is not only an on-ramp to profiles — it is a way to find
contributions that already exist and were never submitted.

**Hand-resolved conflicts are far rarer than they look, and hide somewhere else.** This
is a correction: an earlier draft claimed roughly twelve, extrapolated from a sample
that used `git show --diff-merges=cc` as an evil-merge detector. That test is wrong —
it also reports every ordinary automatic merge where two sides edited different regions
of one file. Replaying all 160 merges with `git merge-tree --write-tree`, which performs
a real three-way merge and reports genuine conflicts, gives **1**. See [§5.3](#s5-3) for
where the other resolutions actually live.

### <a id="s5-2"></a>5.2 The `distill` command

```
bonsaipr distill --branch Ryan_build-0.8.6-alpha2607071335 --base v0.8.0
```

Walks first-parent history and classifies each commit down a ladder, most reliable
first:

| # | Evidence | Result | Confidence |
|---|---|---|---|
| 1 | merge subject matches `pr-(\d+)/` | PR N | exact |
| 2 | merge subject names `owner/branch`, resolved via GitHub `head.label` | PR N | exact |
| 3 | merge subject contains `(#NNNN)` | PR N | probable |
| 4 | commit patch-id matches a commit in an open PR | PR N | exact |
| 5 | commit patch-id matches a PR's *combined* diff (squashed cherry-pick) | PR N | exact |
| 6 | `git cherry` finds an equivalent already in base | drop — absorbed upstream | exact |
| 7 | none of the above | residue | — |

Steps 4–5 cost nothing extra: BonsaiPR already fetches every open PR every run, so the
patch-id index is a by-product of work the pipeline does anyway. Step 5 exists because a
squashed cherry-pick's patch-id matches the PR's *combined* diff and no individual
commit in it — naive matching misses those entirely.

**`distill` must not emit exclusions.** A PR absent from a build branch was, in almost
every case, never considered — not rejected. Recording those 445 absences as
`exclude.prs` would flood the `objections` signal ([§8.3](#s8-3)) with reasonless
rejections that no human ever made, and that signal is only worth having because every
entry in it is a deliberate act. A distilled profile therefore lists what the branch
merged and nothing else; exclusions are added afterwards, by hand, when the curator
actually means one.

Every classification is written to `profiles/<name>.provenance.json` with its evidence
and confidence. **Nothing is silently guessed.** A curator can audit why any commit was
attributed the way it was, which matters because step 3 is a heuristic and step 4 fails
whenever a cherry-pick required conflict resolution (the resolved diff no longer matches
the original patch-id).

### <a id="s5-3"></a>5.3 Two things worth more than the PR list

**The recorded merge order.** BonsaiPR currently *guesses* at order, building asc, desc,
and by-updated to maximise inclusion. A poweruser branch encodes something better: a
hand-validated sequence that is known to produce a build that works. That justifies a
fourth order:

```json
"orders": ["recorded"],
"order_seq": [8353, 8352, 8351, 8349, "…"]
```

**The conflict resolutions — but not the ones this document originally expected.**
`KNOWN_CONFLICT_RESOLUTIONS` in
[`00_clone_merge_and_create_branch.py:83`](../automation/scripts/00_clone_merge_and_create_branch.py)
is a hand-maintained table of *"when PR A conflicts with PR B in this file, take this
side."* It has **exactly one entry**, and the original hope here was that a poweruser
branch would yield a dozen more.

Measured, it yields **one** textual hand-resolution, and that one is hunk-level rather
than wholesale, so it does not reduce to `theirs`/`ours` and cannot be added to the table
mechanically. As a source of entries for that particular table, distillation is close to
a dead end.

**The resolutions are real; they are just expressed as graph surgery.** Seven merges on
this branch fix conflicts by *absorbing the rival PR's ancestry* — merging the colliding
branch into the PR branch so the two stop conflicting at all:

```
Merge PR #7940 (Concatenate_selections) to resolve build conflicts
Merge PR #7965 (inset_section_endpoints) ancestry to fix build conflict
Absorb old-pd ancestry to fix build merge conflict with PR #7798
```

This is exactly what [`prompts/resolve conflicts with other PRs.md`](../prompts/resolve%20conflicts%20with%20other%20PRs.md)
already tells contributors to do — *"the fix must land on the PR branch itself
(ancestry-merge or rebase) so it resolves cleanly in future builds without touching
`KNOWN_CONFLICT_RESOLUTIONS`."* The project's own documented practice steers people away
from the table, which is why the table has one entry and why a branch following that
practice yields no more.

Two consequences:

- **These merges are not on the first-parent path.** They sit on the PR branches, so a
  first-parent-only scan — the obvious way to write `distill` — misses every one of
  them. It has to scan the full merge graph for them separately.
- **The knowledge they carry is a pair, not a file strategy**: *"#7798 needs old-pd's
  ancestry"*, *"#8083 and this collide."* That is the same shape as
  [`prefer`](#s4) and as the `rivals` signal, not the same shape as
  `KNOWN_CONFLICT_RESOLUTIONS`. Harvesting it should feed those.

**The non-overlap invariant — a resolution the tool can derive without human input.**
The categories above require judgement. There is one that does not: if a file
was *not changed between the merge-base and the current base*, its correct post-rebase
state is exactly the branch tip — not `--ours`, not `--theirs`, not a merge. This is
derivable in full from `git diff` and costs no human time. `distill` should apply it as
an automated pre-filter and report the split explicitly: *"N conflicts auto-resolved via
non-overlap invariant; M overlap files require human review."* On the `parametric_dimensions`
rebase this distinction separated 22 trivially deterministic resolutions from the 8
files that actually needed a human decision.

### <a id="s5-4"></a>5.4 Residue handling, and the privacy default

The 81 residue commits are clustered into candidate patch series — contiguous runs in
first-parent order with overlapping file sets — and each cluster is presented for a
human decision:

- **`link`** — patch-id matches an open PR the curator authored elsewhere. Fold into
  `select.prs`; it is already public.
- **`promote`** — a coherent, never-submitted feature. Emit as a formatted patch series
  with a suggested title. *This is the "you have three unsubmitted features" report.*
- **`private`** — never publish. Local dev notes, machine-specific paths, scratch work.

**The default is `private`.** Residue is not published unless a human opts a cluster in,
one at a time. A build branch is a personal workspace and will contain things its owner
never intended to ship; a tool that published it by default would be a serious
misfeature. Clustering is a heuristic and is presented as a proposal, never applied
silently.

### <a id="s5-5"></a>5.5 Replay and reconciliation

The distilled profile is then rebuilt through the normal pipeline: current `v0.8.0`,
plus the profile's PRs at their *current* heads, in the recorded order, with the
recorded resolutions.

**This will not reproduce the original branch, and should not claim to.** The PRs have
advanced since they were merged; that is the entire point of replaying rather than
shipping the branch. So the output is a reconciliation report, not a pass/fail:

- PRs whose head moved since the branch merged them (behaviour may have changed)
- PRs now closed or absorbed upstream — dropped, with the commit that absorbed them
- PRs that no longer merge in the recorded order — the order needs revisiting
- Residue patches that no longer apply
- **Pins referencing orphaned commits** — the pinned SHA is no longer fetchable from any
  public ref due to a contributor force-push or rebase; the pin must be reaffirmed
  against the current tip before the build runs (distinct from "PR advanced," where
  the old SHA is still reachable as an ancestor)
- A tree diff of replay vs. original branch, restricted to paths the profile claims

A curator reads that report and decides. The tool's job is to make the divergence
visible and attributable, not to assert equivalence it cannot verify.

### <a id="s5-6"></a>5.6 Where this is weakest

- **Distillation is lossy.** A branch's behaviour is the product of its exact merge
  order *and* its resolutions *and* the PR heads at the time. Replaying against advanced
  heads can legitimately produce different behaviour. [§5.5](#s5-5) is the mitigation, not a
  guarantee.
- **Attribution depends on the curator's habits.** `pr-NNNN/` is *one* person's naming
  convention, and it is why regex alone attributes 98.75% of its merges. Someone who
  cherry-picks without `-x` and without naming conventions falls through to patch-id,
  which conflict resolution defeats. `distill` should report its attribution rate per
  branch and say plainly when a branch is too unstructured to be worth distilling.
- **It only works on branches built by merging.** A branch maintained by rebasing loses
  the merge-commit evidence entirely and depends wholly on patch-id matching.
- **Ancestry-merge commits inflate distillation complexity even on merge-based branches.**
  `git merge -s ours` commits — used to establish git ancestry between a build branch
  and upstream PRs — each silently contribute their second-parent commit chains into the
  branch's reachable history. The `parametric_dimensions` branch carried three such
  commits; when replayed during rebase, those three generated 13 duplicate commits and
  ~30 conflict rounds across 52 total commits. `distill` must recognize `-s ours` merges
  (identifiable by their empty tree-delta relative to HEAD) and skip their second-parent
  chains rather than walking them as integrations. It should also report the count
  upfront, since it predicts conflict workload: *"3 ancestry-merge commits found —
  duplicate chains excluded from walk."* Branches with ten or more such merges may be
  impractical to rebase without a structured resolution strategy.

---

## <a id="s6"></a>6. Artifact 2: the Manifest

The manifest is what a curator publishes and a peer consumes. It is
`state.<order>.json` plus an identity block — because "PR #7123 merged cleanly" is
useless without knowing *who* built it, *from what base*, and *under which curation*.

```json
{
  "schema": 2,

  "publisher": {
    "id": "theoryshaw",
    "instance": "https://github.com/theoryshaw/bonsaiPR",
    "contact": "https://github.com/theoryshaw"
  },
  "profile": {
    "name": "architecture-production",
    "url": "https://github.com/theoryshaw/bonsaiPR/blob/main/profiles/architecture-production.json",
    "digest": "sha256:1f3a…",
    "selected": 41
  },
  "build": {
    "id": "v0.8.6-alpha2607301845",
    "order": "ascending",
    "base": "v0.8.0",
    "base_commit": "8deefe497cca8b9fd41e29e809ec0d0ad9478169",
    "generated_at": "2026-07-30T18:58:24Z"
  },

  "counts": { "merged": 38, "failed": 2, "skipped_conflict": 1, "skipped_draft": 0, "total": 41 },
  "prs": { "7123": { "status": "merged", "head": "8f09b96", "…": "…" } }
}
```

Everything under `counts` and `prs` is exactly what `build_state()` emits today.
`build.base_commit` is already captured — it is printed in the report header as
*"IfcOpenShell source commit: …"*. Only `publisher` and `profile` are genuinely new,
and `profile.digest` is what lets a consumer verify that a claimed curation matches the
file it points at.

Integration point: [`02_upload_to_falken10vdl.py:1118-1142`](../automation/scripts/02_upload_to_falken10vdl.py),
which already calls `build_state()` and `write_state()`. Schema 1 readers ignore
unknown keys, so bumping to 2 is additive.

**Publication** requires no new infrastructure: `commit_reports.py` already pushes
`automation/reports/` to the publisher's repo. A curator running their own fork
already produces the manifest at a stable raw URL for free.

---

## <a id="s7"></a>7. Artifact 3: the Peer index

`federation/peers.json` — the list of curators an aggregator pulls from. Explicitly a
*subscription*, not a registry: there is no authority, and different people can run
different peer lists.

```json
{
  "schema": 1,
  "peers": [
    {
      "id": "falken10vdl",
      "display_name": "BonsaiPR (canonical)",
      "reports_base": "https://raw.githubusercontent.com/falken10vdl/bonsaiPR/main/automation/reports/",
      "profiles": ["everything"],
      "role": "anchor"
    },
    {
      "id": "theoryshaw",
      "display_name": "Architectural production",
      "reports_base": "https://raw.githubusercontent.com/theoryshaw/bonsaiPR/main/automation/reports/",
      "profiles": ["architecture-production"],
      "role": "curator"
    }
  ]
}
```

`role: anchor` marks the canonical everything-build. It is excluded from adoption
counts ([§8.1](#s8-1)) — an anchor including a PR is not a curatorial endorsement, it is the
absence of one.

---

## <a id="s8"></a>8. The aggregator and its signals

`automation/scripts/federate.py`:

```
fetch peers.json → fetch each peer's manifests → validate → aggregate → emit
  federation/federation.json     machine-readable, per-PR signals
  federation/DIGEST.md           maintainer-facing summary
```

What the aggregate is measuring is worth naming precisely, because it is not the thing
most governance mechanisms measure. Committees, votes, and review threads optimize for
**consensus** — *we discussed this and agreed.* This optimizes for **independent
agreement** — *we never spoke, and we each arrived at the same place anyway.* The second
is the stronger signal, for the same reason independent replication outranks committee
endorsement in science: nobody talked anybody into it. It is also the only kind of
agreement obtainable from volunteers scattered across time zones who will never reliably
attend the same meeting.

### <a id="s8-1"></a>8.1 Signal definitions

Each signal states plainly what it does and does not mean. This matters more than the
math — a signal that gets over-read is worse than no signal.

| Signal | Definition | What it means | What it does **not** mean |
|---|---|---|---|
| `selected_by` | distinct non-anchor publishers whose profile selects the PR | someone deliberately wanted this | that anyone used it |
| `merged_by` | distinct publishers whose build merged it cleanly | it integrates | that it works |
| `blocked_by` | publishers that selected it but could not merge it | it conflicts under some curation | that it is bad |
| `pinned_by` | publishers pinning a specific head SHA | a curator tested that exact commit | ongoing validity |
| `streak.builds` / `streak.days` | consecutive builds merged, and elapsed span | it has survived upstream drift | absence of latent bugs |
| `rivals` | PR numbers it lost merge races to, and how often | a real, specific conflict to resolve | fault on either side |
| `divergence` | merged for some publishers, blocked for others | base- or order-sensitive | flakiness |
| `excluded_by` | distinct publishers who deliberately excluded it, counting only non-stale exclusions ([§4.2](#s4-2)) | someone saw it and said no | that it is broken |
| `objections` | those exclusions' reasons, grouped by `why` category and recurrence | *why* they said no — see [§8.3](#s8-3) | consensus; two people can object for opposite reasons |
| `lost_to` | PRs that curators explicitly `prefer` over this one | a curatorial choice between two options | a judgment on this PR's quality |

`streak` is derivable from data already being logged. `rivals` is **not** — see
[§12](#s12); the reports record that a conflict occurred and which orders a PR merges
under, but never which PR won the race, so the pairing cannot be reconstructed after
the fact.

**`streak` and `churn` must be computed against a single lineage.** Each merge order is
an independent history — the same PR can be merged in `asc` and conflict-skipped in
`desc` on the same run — so interleaving two orders' event logs produces a status
history that never happened, and pooling their build timestamps counts every run once
per order. Phase 0 quotes both against `asc`, which is the canonical lineage elsewhere
in this pipeline. This is easy to get wrong and expensive to notice: the first
implementation did exactly this and reported 376-build streaks against a history
containing 140 builds.

Note the asymmetry between `blocked_by` and `excluded_by`: the first is the automation
failing to merge something a curator wanted, the second is a curator not wanting it.
Conflating them would be the single easiest way to make this whole aggregate lie.

`pinned_by` counts only pins whose SHA is currently reachable from the PR's head ref or
any public ancestor thereof. A force-pushed PR branch orphans the old SHA; a broken pin
must not count toward the signal until reaffirmed. The reconciliation report
([§5.5](#s5-5)) surfaces these as the distinct *orphaned* category rather than folding
them into the general "PR head moved" bucket.

### <a id="s8-2"></a>8.2 Integration robustness is not functional robustness

Everything above measures whether a PR *merges and keeps merging*. None of it measures
whether the resulting Bonsai does the right thing. A PR can merge cleanly into 9 builds
for 6 months and still be wrong.

This should be stated on every rendered digest, not buried. Two honest ways to
narrow the gap, both later phases:

1. **Curator attestation** — an optional `attest` block in the profile: *"I used this
   in production for 3 months."* Signed by a person, worth more than any automatic
   count, and impossible to compute.
2. **Profile-level smoke results** — if a curator runs a test suite against their
   build, publish pass/fail in the manifest. Turns `verification` into a real signal
   for the profiles that opt in.

### <a id="s8-3"></a>8.3 What rejection reveals that selection cannot

There is a fair objection to this whole proposal: **aggregation is selective, not
generative.** It can rank the things people built. It cannot produce the thing nobody
proposed — the abstraction that should have been used, the refactor that collapses five
PRs into one, the "this approach is wrong, do it the other way." Selection pressure over
a population only chooses among the variants present, so aggregating *inclusions*
produces coherence — things that work together survive together — which resembles
architecture from a distance while being a different thing.

Aggregated *exclusions with reasons* get closer to the real thing, for a simple reason:
inclusion is a statement about usefulness, and rejection is usually a statement about
principle. Nobody excludes a working PR from their own build without a view about how
the software ought to be put together. **An exclusion with a reason is compressed
architectural knowledge** — and note that almost every signal open source currently
collects (stars, installs, downloads, reactions) is positive-only, which means the more
informative half of the record is the half nobody keeps.

But five different things look like "not in my build," and only one of them carries
design information. Conflating them is how this signal would become worthless:

| what happened | recorded as | signal |
|---|---|---|
| never considered — the 445 nobody looked at | *nothing* | none, and it must stay that way ([§5.2](#s5-2)) |
| could not merge — conflicts | `blocked_by` | automation-level, not a human act |
| lost a race — curator preferred another PR | `prefer` → `lost_to` | a choice between two options |
| tried it, it broke | `why: regression` | a bug report, and a useful one |
| **works fine, curator does not want it** | **`why: architecture`** | **the design signal** |

So the interesting output is not a count. It is a recurring *reason*:

```
#8123  excluded by 5 curators (2 stale, not counted)
       3 cite [architecture]: bypasses the tool/ abstraction, calls ifcopenshell directly
       1 cite [scope]:        not relevant to a documentation-focused build
       1 no reason given
```

Three independent people rejecting the same PR *for the same architectural reason* is a
design principle being discovered rather than decreed — and it is legible to a
maintainer, a newcomer, and an AI reviewer alike, which is exactly what an
Architecture Decision Record is for. The difference is that this one is derived from
what people actually did, and it costs nobody a meeting.

**Nothing renders publicly on a single objection.** One curator excluding a PR is an
opinion, not a signal, and publishing it against a named contributor's work would be
mostly a way to hurt people. Two or more *independent* curators citing the same category
is the threshold; below it the data stays raw. Reasons are always quoted verbatim with
attribution — you own your words — and nothing is ever rendered as a score on a
*person*.

Three limits worth keeping in view:

- **It is still a lagging indicator.** It surfaces principles after enough people have
  independently hit the same wall. Architectural judgment is most valuable *before* the
  work, where "don't build it that way" saves the effort.
- **This is where maintainer participation matters most.** If maintainers curate — and
  they will, because they need working builds too — their exclusion lists are the
  highest-signal input in the entire system: an architectural stance in executable
  form, continuously maintained and publicly diffable in a way an Architecture Decision
  Record is not.
- **It depends on people bothering, and most will not.** The likely outcome is many
  bare exclusions and a thin seam of categorized ones, written by the handful of
  curators who care about design — which is arguably the right population, but it means
  this signal stays sparse for a long time, exactly as [§3.4](#s3-4) says the inclusion
  signal does. The `bonsaipr exclude` one-liner in [§4.2](#s4-2) exists because
  friction at that moment is the whole ballgame.

### <a id="s8-4"></a>8.4 Worked example

```
PR #7123 — "Extend profiles and extrusions to 3D cursor"

  selected_by   6 of 9 curators          ████████░░
  merged_by     6 of 6 that selected it  ██████████
  pinned_by     2 (theoryshaw, firm-a)
  streak        14 builds / 42 days
  rivals        #7098 (blocked in 3 of 6, ascending order only)
  divergence    none
  excluded_by   1 (falken10vdl — "needs a rebase onto the new ShapeBuilder API")

  ⚠ Integration signal only. No functional verification reported.
```

---

## <a id="s9"></a>9. Trust and anti-gaming

Any aggregate is attackable. The specific attack here is cheap: spin up 50 forks, each
publishing a profile that selects your PR, and manufacture consensus.

Mitigations, in order of importance:

1. **Count publishers, never builds.** A publisher running 3 merge orders × 24 builds
   a day contributes exactly one vote. The canonical instance's asc/desc/upd collapse
   to one.
2. **Subscription, not registry.** There is no global list to inject yourself into. A
   peer appears in *your* aggregate because *you* added them to *your* `peers.json`.
   Sybils cost nothing to create and gain nothing without adoption.
3. **Anchors do not vote.** The everything-build inflates every count equally, which is
   the same as informing none of them.
4. **Weight by divergence, not agreement.** A curator whose profile is identical to
   another's adds no independent information. Optionally down-weight near-duplicate
   profiles by set overlap.
5. **Publish the peer list with every digest.** Any claim of "6 of 9 curators" is
   meaningless without naming the 9. The digest must always name them.
6. **Attestations are signed by humans and never aggregated automatically.** They are
   quoted, with attribution, or not shown.

What this explicitly does *not* try to do is prevent a determined bad actor from
publishing a dishonest manifest. It makes dishonesty *attributable* — a manifest names
its publisher, and the profile digest can be checked against the file — and leaves the
consequences social.

---

## <a id="s10"></a>10. Consumption: per-profile Blender feeds

The Blender extension side follows for free. `update_index_json.py` currently writes a
single `index.json` with one add-on entry, `id: bonsaiPR`. A profile-aware version
writes `profiles/<name>/index.json` per profile, letting a user subscribe their Blender
to *a curation* rather than to "the" BonsaiPR:

```
https://raw.githubusercontent.com/theoryshaw/bonsaiPR/main/profiles/architecture-production/index.json
```

The existing root `index.json` stays exactly where it is and keeps working. The
one-add-on-at-a-time constraint in the README (Bonsai *or* BonsaiPR, never both) still
applies, and now applies across profiles too — worth a warning in the UI text.

---

## <a id="s11"></a>11. Phasing

Deliberately ordered so each phase is useful alone and none of the early ones require
falken10vdl to change how the canonical instance runs.

| Phase | Deliverable | Requires |
|---|---|---|
| **0** ✅ | `federate.py` run over the existing `state.{asc,desc,upd}.json` as three synthetic publishers. Proves the signal math and the rendering against real data. **Done — results in [§12](#s12).** | nothing |
| **1** ✅ | Profile format + `load_profile()` + `.env` compat shim. Canonical instance expressible as `everything`. **Done — `bonsaipr_profile.py`, `profiles/everything.json`; notes in [§12.4](#s12-4).** | small change at `00_clone_…py:41-62` |
| **1.1** ✅ | Record the *winning* PR number when a merge conflict skips a PR, so `rivals` becomes computable. Discovered in phase 0 ([§12](#s12)); cheap now, unrecoverable retroactively. **Done — `reports/rivals.<order>.json`.** | small change at `00_clone_…py` |
| **1.5** | `distill` ([§5](#s5)) — attribution ladder, provenance file, residue clustering, harvested conflict resolutions. Run against `Ryan_build-0.8.6-…` as the first real input. | phase 1 |
| **2** | Manifest schema 2 (`publisher` / `profile` blocks) + `peers.json` + real cross-publisher aggregation. | small change at `02_upload_…py:1118` |
| **3** | Per-profile `index.json` feeds. | `update_index_json.py` |
| **4** | Maintainer digest — optionally as a bot comment or a status check on the upstream PR. | upstream buy-in |
| **5** | Attestations and profile-level smoke results ([§8.2](#s8-2)). | curator opt-in |

Phase 0 is the one that settles whether the signal math is worth anything, and it can
be written and run today against data already in the repo.

Phase 1.5 is arguably the one that settles whether *anyone will participate*, and it has
its own standalone payoff regardless of federation: even if no one ever publishes a
manifest, surfacing 81 commits of a curator's unsubmitted feature work is worth the
build on its own.

---

## <a id="s12"></a>12. Implementation results

`automation/scripts/federate.py` implements the aggregation math and its rendering. It
touches nothing in the build pipeline, reads only files the repo already produces, and
runs in about two seconds. Run it with `python federate.py digest` from
`automation/scripts/`.

### <a id="s12-1"></a>12.1 What the current backlog looks like

Against the snapshots of 2026-08-06:

```
847 PRs seen  =  454 merged everywhere  +  181 divergent  +  212 merged by nobody
```

**181 of 847 — 21% of the open backlog — is divergent**: merged under one merge order
and blocked under another. That number is the best single argument in this document.
It is not a hypothetical about future curators; it is a measurement saying that a fifth
of all open PRs are already sensitive to the order they are integrated in, and that this
fact is currently scattered across three release pages and visible to nobody.

Under real federation the identical computation reads *"some curators can carry this and
others cannot"* — which is exactly the question a maintainer wants answered before
merging.

Streak and churn work as designed: 549 PRs carry a continuous-merge streak, the longest
running 140 builds across 18.4 days, and the most volatile PR has changed bucket 36
times.

### <a id="s12-2"></a>12.2 The anti-gaming rule, demonstrated

`federate.py --real-publishers` stops promoting merge orders to publishers and counts
the single real one. **`stable` drops from 454 to 0.**

That is not a bug — it is [§9](#s9)'s central rule executing. `stable` requires
agreement from at least two *independent publishers*, and one person running three merge
orders is one publisher. The rule is therefore not an aspiration in a document; it is a
runnable assertion, and the two modes differ by exactly the amount the rule is supposed
to bite.

### <a id="s12-3"></a>12.3 What phase 0 changed about the plan

- **`rivals` cannot be computed, and the data to compute it is being thrown away.** The
  reports record *that* a PR was conflict-skipped and which orders it merges under, but
  never *which PR beat it*. That pairing is one of the more actionable signals in
  [§8.1](#s8-1) — it names a specific, fixable collision — and it is unrecoverable
  retroactively. Recording the winner at conflict time is small and should land early,
  hence phase 1.1.
- **Signal correctness is lineage-sensitive** in a way that is not obvious and fails
  quietly. See [§8.1](#s8-1); the first implementation pooled all three orders and
  produced 376-build streaks against a 140-build history.
- **"Unavailable" has to be a first-class output.** `federation.json` carries an
  `unavailable` block naming every signal it cannot compute and why, so a consumer can
  distinguish *zero* from *unknown*. Without it, a phase-0 aggregate looks like every PR
  has zero objections, which is false in the most misleading possible direction.

Nothing in phase 0 validates the parts of this proposal that depend on people. It
proves the arithmetic and the rendering; whether curators materialise, and whether they
write reasons, remains entirely untested.

### <a id="s12-4"></a>12.4 Phase 1 results

`bonsaipr_profile.py` plus `profiles/everything.json`. The claim in
[§4.1](#s4-1) — that nobody is forced to migrate — is now verified rather than
asserted, against the real merge script:

| configuration | `users` | `excluded_prs` | `SKIP_CPP_PRS` |
|---|---|---|---|
| nothing set | `['']` | `[]` | `False` |
| legacy `.env` vars | `['theoryshaw', 'falken10vdl']` | `[7098, 8123]` | `True` |
| `BONSAIPR_PROFILE` set | `['']` | 3, with reasons | `True` |

The first row is the important one: with no profile configured the canonical instance
produces byte-identical curation decisions to before. The merge script's ~950 lines
downstream were not touched — a profile only changes how those three values are
*decided*.

Two things the implementation had to settle that this document had left ambiguous:

- **Inherited exclusions union rather than replace** ([§4](#s4)). The other reading
  would let a child profile silently discard its parent's refusals, which is a change
  of meaning disguised as a merge rule.
- **A reason without a `since` sha is a permanent objection.** Now warned about
  ([§4.2](#s4-2)). This is the failure mode most likely to happen by accident and it
  lands on a contributor rather than on the curator who caused it.

Phase 1.1 records `reports/rivals.<order>.json` as a sidecar rather than extending
`state.<order>.json`, because the state snapshot is parsed back out of the *rendered
report* by `02_upload_to_falken10vdl.py` — extending it would have meant changing the
report format in the same pass. [§6](#s6)'s manifest can absorb it later.

**Nothing here is retroactive.** Rival pairings start accumulating on the next real
build run; every run before that lost them permanently, which was the argument for
landing phase 1.1 early rather than when a later phase wanted the signal.

---

## <a id="s13"></a>13. Risks and open questions

**Risks**

- *The signal is thin until curation is selective.* Addressed by shipping profiles with
  the aggregator ([§3.4](#s3-4)), but it means the first several months of federation data will
  be sparse. Phase 0 exists partly to avoid over-investing before that is known.
- *Curator burnout.* This proposal creates a new maintenance role. If maintaining a
  profile is not substantially cheaper than maintaining a fork, nobody will do it.
  `inherits` and `pin` keep the ongoing cost near zero; `distill` ([§5](#s5)) removes the
  up-front cost, since the first profile is generated from a branch the curator
  already has rather than authored from nothing.
- *Good architecture is frequently unpopular, and this measures popularity.* Saying no
  to a well-liked feature because it bypasses an abstraction is the job; an aggregate
  built on adoption will systematically under-rate whoever does it. Conferred authority
  is biased toward insularity, earned-by-metric is biased toward crowd-pleasing, and
  neither bias is obviously worse — but the second one is newer, so it is the one
  nobody will see coming. The moment standing confers anything, it becomes worth
  optimizing for. `objections` ([§8.3](#s8-3)) is a partial hedge, since it rewards
  articulating an unpopular principle rather than accumulating agreement, but it is a
  hedge and not a fix. Anyone rendering a digest should resist ranking *people*.
- *Exclusion reasons become noise, or become weapons.* Free text invites `"broken"`,
  `"don't like it"`, and occasionally something unkind about the author. [§4.2](#s4-2)
  and [§8.3](#s8-3) specify the guards — `why` categories, `since`-SHA staleness so an
  objection expires when the PR is fixed, a two-independent-curator threshold before
  anything renders publicly, verbatim attributed quoting, and never scoring a person —
  but guards on paper are not the same as guards in code. The clustering step in
  particular should not publish anything against a named contributor's PR without a
  human having looked at it.
- *Distillation publishes something private by accident.* A build branch is a personal
  workspace. The residue default is `private` and opt-in is per-cluster ([§5.4](#s5-4)), but
  this is the failure mode most likely to actually happen and it deserves a second
  pair of eyes on the implementation, not just the design.
- *Fragmentation.* Nine curated builds mean nine slightly different Bonsais, and bug
  reports get harder. Mitigated by every build already carrying a manifest that
  states exactly what is in it — arguably *better* than today's situation.
- *Ancestry-merge debt becomes a rebase liability.* Poweruser build branches commonly
  use `git merge -s ours` to establish git ancestry between accumulated PRs, preventing
  re-application of already-merged content on future merges. Each such commit silently
  inflates a future rebase: three ancestry-merge commits on `parametric_dimensions`
  produced 13 duplicate commits and ~30 conflict rounds on a 52-commit replay. A branch
  maintained over a year with ten or more such merges may become impractical to rebase
  without the explicit resolution strategy documented in the log. `distill` ([§5](#s5)) must
  detect and skip these — identifiable by their empty tree-delta relative to HEAD — and
  warn curators before they invest in a distillation pass. The profile-based model
  eliminates this pattern entirely: because the aggregator manages merge sequence
  explicitly via `order_seq` and `KNOWN_CONFLICT_RESOLUTIONS`, no PR branch ever needs
  to become a git parent of another, so no `merge -s ours` commits are needed. This is
  a concrete structural advantage of profile-based builds that is not obvious from the
  profile format alone.
- *Schema churn.* Manifests are consumed by other people's tools. Schema 2 should be
  additive-only, and the version must be checked, not assumed.
- *Storage.* `automation/reports/` is already ~52 MB — 1.5 MB of live state/event JSON
  plus 206 archived markdown reports. Aggregating N peers multiplies the fetch, not
  the local storage, but each peer carries that same growing archive in their own repo,
  and the archive retention policy is worth settling before N gets large.

**Open questions**

1. **Profile format: JSON or TOML?** JSON matches everything else in the repo
   (`index.json`, `state.json`) and needs no dependency. TOML is materially nicer to
   hand-edit and is stdlib-readable on 3.11+, but the automation host's Python version
   is not pinned anywhere I can find. *Leaning JSON for consistency.*
2. **Where does `peers.json` live** — canonical repo (one blessed list, simpler, more
   centralized) or per-curator (fully federated, but no shared view)? *Leaning
   per-curator with the canonical repo publishing a suggested default.*
3. **Should the aggregate be published back to the canonical repo**, so there is one
   well-known digest people can link to, even though anyone can compute their own?
4. **Does upstream (IfcOpenShell) actually want this?** Phase 4 is the only phase that
   touches upstream, and it should not be built until a maintainer says the digest
   would be useful. Everything through phase 3 is valuable regardless of the answer.
5. **Attestation format** — freeform prose is honest but unaggregatable; structured
   fields are aggregatable but invite exactly the over-reading [§8.2](#s8-2) warns about.
6. **Should the canonical instance build a `recorded` order** ([§5.3](#s5-3)) from a distilled
   profile, alongside asc/desc/upd? It would test whether a human-validated order beats
   all three guesses at inclusion — a cheap and fairly interesting experiment — but it
   costs a fourth build per run.
7. **Who owns a distilled profile?** It is derived from one person's branch but names
   other people's PRs and may harvest their conflict resolutions. Attribution in the
   provenance file is probably sufficient, but it should be settled before the first
   one is published, not after.

---

## <a id="s14"></a>14. Summary

Three artifacts — a **profile** (curation as a committed file), a **manifest** (a build
declaring who made it and from what), and a **peer list** (who you aggregate) — plus
two scripts: one that generalizes `compute_robustness()` from three merge orders to N
publishers, and one that **distills a profile out of a build branch someone is already
maintaining by hand**.

Most of the machinery already exists. What is genuinely new is naming the curation and
publishing who did it, which is what turns BonsaiPR from *one build everybody shares*
into *a network of curated builds whose agreement means something*.

The field I would defend hardest is the smallest one: a **reason** attached to an
exclusion ([§8.3](#s8-3)). Inclusion counts measure usefulness, and there is a fair
objection that aggregating them produces coherence rather than architecture. Rejections
are different — nobody excludes a working PR from their own build without a view about
how the software ought to be put together. Three curators independently refusing the
same PR for the same stated reason is a design principle being discovered rather than
decreed, and it costs nobody a meeting.

The measurement in [§5.1](#s5-1) is the part I would point at first. A single poweruser branch
turned out to be 100% mechanically attributable to open PRs, and to contain 81 commits
of real feature work that upstream has never seen. Whatever happens
to the federation idea, that branch — and every branch like it — is holding
information the project could be using today.
