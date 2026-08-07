# AGENTS.md

Guidelines for AI coding agents working on BonsaiPR. Intended to be read by any
agent regardless of platform, alongside tool-specific configuration.

## Read first

**Before touching an in-progress feature, read its note in
[`docs/dev-notes/`](docs/dev-notes/).** Those notes exist so a session starting
cold does not re-derive context, repeat a dead end, or re-discover a trap that
already cost someone a day. Keep the relevant note current as you work.

Convention borrowed from IfcOpenShell/IfcOpenShell#8201, with one change: notes
here cover multi-phase *programmes* as well as single features, so they are
pruned and promoted at each phase boundary rather than deleted when a PR merges.
See the Lifecycle section of any note.

## Where things live

| | |
|---|---|
| `proposals/` | design proposals (RFC-NNN). The argument and the evidence. |
| `docs/dev-notes/` | working notes for unmerged/ongoing work. Volatile by design. |
| `automation/scripts/` | the pipeline: stage 0 merge, 1 build, 2 release, plus tooling |
| `profiles/` | curations — which PRs a build selects, and on what base |
| `.github/workflows/` | the curated-build workflow and its setup guide |

## Working rules

- **This automation had one operator for most of its life.** Anything true only
  of that machine — an absolute path, a hardcoded owner, a persistent clone —
  is a latent bug. Six were found the first time it ran somewhere else. When
  touching setup or publishing code, ask what it assumes about *whose* machine
  it is on.
- **A green run is not a correct run.** Two of those six produced successful
  builds that were wrong: PRs merged onto the wrong base branch, and a build
  labelled with the wrong merge order. Check the artefact, not the exit code.
- **Measure before designing.** Several conclusions here reversed under
  measurement — an estimate of "~12 harvestable conflict resolutions" was
  actually 1, and an invariant that looked free fired on 2.9% of cases. Prefer a
  cheap experiment over a confident paragraph.
- **Never point `BASE_CLONE_DIR` at a repository anyone works in.** Stage 0
  checks out, resets, deletes branches, and force-pushes.
- **Report signals honestly.** If a signal cannot be computed, emit it as
  *unavailable* rather than zero — consumers must be able to tell "none" from
  "unknown".

## Indicating AI-generated code

Follow the upstream IfcOpenShell convention: mark AI-assisted files with a
comment at the top, and say so in the PR description.
