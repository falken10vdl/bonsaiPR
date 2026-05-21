# Rebase Summary: general-mirroring onto v0.8.0 (2nd rebase)

**Date:** 2026-05-21
**Branch:** [`general-mirroring`](https://github.com/IfcOpenShell/IfcOpenShell/tree/general-mirroring)
**Rebased onto:** `v0.8.0` ([7e96692764](https://github.com/IfcOpenShell/IfcOpenShell/commit/7e96692764))
**Result tip:** [7762668b7c](https://github.com/IfcOpenShell/IfcOpenShell/commit/7762668b7c)
**Outcome:** conflicts-resolved

> **Note:** This is the second rebase of this branch onto v0.8.0 in the same day.
> The first rebase (see `2026-05-21-rebase-general-mirroring.md`) was against an earlier
> v0.8.0 tip (`cb3253b57c`). A subsequent `git fetch` revealed 32 additional commits on
> v0.8.0, requiring this second pass.

---

## Conflict 1: `src/bonsai/bonsai/bim/module/model/door.py`

**Conflicting branch commit:** `5438190731` — "Added bim.mirror_geometry() operator for truly mirroring products / types"

**v0.8.0 commit that caused the conflict:** [`233cc344fa`](https://github.com/IfcOpenShell/IfcOpenShell/commit/233cc344fa) — "Add tool.Parametric registry and lifecycle mixins"

**What each side did:**

- **v0.8.0 (`233cc344fa`):** Introduced `FeatureModifierEditMixin` in `parametric_lifecycle.py` with a generalized `_finish_one` classmethod handling the full door-editing lifecycle (gather props → update representation → mark thumbnail → write pset → clear `is_editing`). `FinishEditingDoor._execute` was simplified to call `self._finish_targets(context)`.

- **Branch (`5438190731`):** `FinishEditingDoor` had its own `finish_editing_door_on_object` method that duplicated the base lifecycle logic and added mirror sync via `BBIM_InvertedSwingType` pset lookup. `_execute` looped over objects manually.

**Resolution:** Override `_finish_one` as a classmethod in `FinishEditingDoor` to call `super()._finish_one(obj, context)` then perform mirror sync. Keep `_execute` calling `_finish_targets` (v0.8.0's clean mixin approach). Read `door_data` from the pset after the super-call rather than re-gathering from props.

---

## Conflict 2: `src/bonsai/bonsai/bim/module/model/door.py` (same file, next commit)

**Conflicting branch commit:** `0bc60f927b` — "Door materials are now synced to mirrored types."

**v0.8.0 commit (same):** [`233cc344fa`](https://github.com/IfcOpenShell/IfcOpenShell/commit/233cc344fa)

**What changed:** The branch added `from_elem` as a second parameter to `copy_door_params` and changed `get_constituents_props_data(to_elem)` → `get_constituents_props_data(from_elem)` (correct: constituents come from the source element, not the target).

**Resolution:** Updated `copy_door_params` signature to `(cls, from_data, from_elem, to_elem)` and updated the call site in `_finish_one` accordingly.

---

## Conflict 3: `src/bonsai/bonsai/bim/module/model/door.py` (same file, next commit)

**Conflicting branch commit:** `bd1d114f17` — "Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type."

**v0.8.0 commit (same):** [`233cc344fa`](https://github.com/IfcOpenShell/IfcOpenShell/commit/233cc344fa)

**What changed:** The branch replaced the `BBIM_InvertedSwingType` pset lookup with the new `tool.Blender.Modifier.has_mirrored_type(element)` API for finding the mirrored type.

**Resolution:** Adopted the cleaner `has_mirrored_type` API, keeping the classmethod structure from the prior resolution.

---

## Files with overlap that did NOT conflict

- `src/bonsai/bonsai/bim/module/geometry/operator.py` — auto-merged
- `src/bonsai/bonsai/bim/module/model/__init__.py` — auto-merged
- `src/bonsai/bonsai/bim/module/model/ui.py` — auto-merged
- `src/bonsai/bonsai/tool/blender.py` — auto-merged
- `src/bonsai/bonsai/tool/model.py` — auto-merged
