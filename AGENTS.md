# AGENTS.md

Guidelines for AI coding agents working on BonsaiPR. Intended to be read by any
agent regardless of platform, alongside tool-specific configuration.

## Read first

**Before touching a subsystem, read its note in
[`docs/dev-notes/`](docs/dev-notes/).** Those notes exist so a session starting
cold does not re-derive context, repeat a dead end, or re-discover a trap that
already cost someone a day. Keep the relevant note current as you work — that
upkeep is part of the change, not an optional extra.

Convention borrowed from IfcOpenShell/IfcOpenShell#8201, with one change. Notes
there are branch-scoped and deleted when their PR merges; here they are
**permanent engineering logs** for subsystems that keep evolving after the
original work lands. Each note marks which of its sections are volatile (status,
untested) and which are durable (traps, past defects), and carries a staleness
test — if its date is older than the newest commit touching the code it
describes, fix the note first.

## Where things live

| | |
|---|---|
| `proposals/` | design proposals (RFC-NNN), each with a plain-language companion. The argument and the evidence. |
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
- **A re-measured number has more than one home.** Figures quoted in an RFC are
  usually also quoted in its plain-language companion and sometimes in a dev
  note. Correcting one and not the others leaves the most-read document holding
  the wrong number — which has already happened once here.
- **Report signals honestly.** If a signal cannot be computed, emit it as
  *unavailable* rather than zero — consumers must be able to tell "none" from
  "unknown".

## Indicating AI-generated code

Follow the upstream IfcOpenShell convention: mark AI-assisted files with a
comment at the top, and say so in the PR description.
