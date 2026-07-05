# Rebase: opening-template-on-type onto v0.8.0

**Branch:** [opening-template-on-type](https://github.com/IfcOpenShell/IfcOpenShell/pull/8200) (PR #8200)
**Base:** `v0.8.0` @ [`b549e65ad9`](https://github.com/IfcOpenShell/IfcOpenShell/commit/b549e65ad9)
**Date:** 2026-07-05 18:52:06
**Result tip:** `4ec042595e` (local; GitHub links live after force-push)
**Outcome:** conflicts-resolved

## Commits replayed

Pre-rebase the branch had 4 non-merge commits + one merge (`93b80a615b`, the `#7916`
build-conflict ancestry-merge). `git rebase` flattened history and dropped the merge; its
second-parent content commit `f59942c453` (#7916) is linear in-range, so it **replayed** and
#7916's content is preserved. Rebased history (onto `b549e65ad9`):

1. `2e6f17ed0f` — Preserve custom opening geometry via a type-level Reference template
2. `1cd7e52c49` — Helps with #7853: Select objects by RepresentationType from panel (#7916)
3. `48f6e2908b` — Propagate edited void to all type occurrences
4. `4ec042595e` — Preserve adjusted extrusion openings on duplicate

## Overlap set

Files changed on **both** the branch and `v0.8.0` since the merge-base (`f60a3423d0`):
`geometry/ui.py`, `model/opening.py`, `project/operator.py`, `tool/geometry.py`,
`tool/model.py`. Of these, three produced real conflicts during replay; the other two
(`project/operator.py`, `tool/geometry.py`) auto-merged.

## Conflicts and resolutions

### `src/bonsai/bonsai/bim/module/model/opening.py` (commit 1)
- **v0.8.0 cause:** [`4d92a64206`](https://github.com/IfcOpenShell/IfcOpenShell/commit/4d92a64206)
  "skip sibling refresh on show/hide toggle" refactored `FilledOpeningGenerator.edit_openings`
  into a unified `opening_edited`/`opening_moved` block that only refreshes sibling walls when
  the opening's shape or placement actually changed.
- **Branch intent:** the feature commit added a call to `self.update_type_template_from_opening(opening_element)`
  after `run_geometry_update_representation` in the edit branch (the legacy write-back hook).
- **Resolution:** kept v0.8.0's new structure and inserted the write-back call inside its
  `if opening_edited:` branch. Independent concerns, both preserved.

### `src/bonsai/bonsai/tool/model.py` (commit 1)
- **v0.8.0 cause:** [`82dd1d94de`](https://github.com/IfcOpenShell/IfcOpenShell/commit/82dd1d94de)
  "batch host recuts in array/opening paths" replaced the old `update_simple_openings` inline
  loop (with `has_replaced_opening_representation`) with `regenerate_simple_opening_bodies`,
  which dedups by `seen_source_ids` via `get_body_representation` / `resolve_mapped_representation`
  / `regenerate_filling_opening_body`.
- **Branch intent:** the feature commit added a guard that skips regenerating a *custom*
  (non-extrusion) opening, to preserve user-authored void geometry during array propagation.
- **Resolution:** kept v0.8.0's new dedup loop and prepended the custom-skip guard
  (`if FilledOpeningGenerator().is_opening_representation_custom(opening): continue`), adding a
  local `from bonsai.bim.module.model.opening import FilledOpeningGenerator` import since the
  refactored method no longer had one in scope.

### `src/bonsai/bonsai/bim/module/geometry/ui.py` (commit 2, #7916)
- **Cause:** intra-branch — replaying #7916 (`f59942c453`) re-triggered the exact conflict the
  dropped merge `93b80a615b` had resolved: the feature commit adds a `RepresentationIdentifier`
  column + header to the `BIM_PT_representations` rows, while #7916 turns the `RepresentationType`
  label into a clickable `bim.select_by_representation_type` operator. (v0.8.0 only touched this
  file cosmetically — `5fba0026dd` ruff import-sort — which auto-merged.)
- **Resolution:** kept the `RepresentationIdentifier` label and #7916's clickable Type operator
  side by side — identical to the original merge resolution.

## Verification

- 3-way tree classification: every file differing between the pre-rebase tip (`aad4cbdfe1`)
  and the rebased `HEAD` matched either the `v0.8.0` version (advancement on files the branch
  never touched) or the branch-tip version (feature work intact); the "matches neither" set
  reduced to exactly the 5 overlap files.
- All changed `.py` files `py_compile` clean.
- Feature symbols confirmed present post-rebase: `should_preserve_opening`,
  `_is_adjusted_extrusion`, `update_type_template_from_opening`, `_remap_opening_to_template`,
  `promote_opening_to_type` (opening.py); the custom-skip guard (tool/model.py);
  `harvest_opening_template` (project/operator.py); the `base_representation` reimport fix
  (tool/geometry.py); both features in ui.py.

## Note — build ancestry-merge invalidated

The rebase changed all hashes, so the prior `#8200 vs #7916` ancestry-merge fix in the build
(logged 2026-06-24, `conflict-resolutions.md`) no longer applies. Because #7916's content is
now a *replayed* commit in #8200's linear history (not a merge), the build's LCA reverts to
`v0.8.0` and the `geometry/ui.py` conflict with #7916 will re-emerge — re-resolve via the
conflict-resolution prompt on the next build that includes both.
