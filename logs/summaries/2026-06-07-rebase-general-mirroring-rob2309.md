# Rebase Summary: Rob2309/general-mirroring onto v0.8.0

**Date:** 2026-06-07 19:28:50
**Branch:** [`general-mirroring`](https://github.com/Rob2309/IfcOpenShell/tree/general-mirroring) (Rob2309's fork)
**Rebased onto:** `v0.8.0` ([93c6350e0f](https://github.com/IfcOpenShell/IfcOpenShell/commit/93c6350e0f))
**Result tip:** [c654e58ca3](https://github.com/IfcOpenShell/IfcOpenShell/commit/c654e58ca3)
**Outcome:** conflicts-resolved
**Pushed to:** `Rob2309` remote (`Rob2309/IfcOpenShell:general-mirroring`)

> **Context:** The branch's merge-base with v0.8.0 was `7e96692764`; v0.8.0 had since advanced
> 32+ commits to `93c6350e0f`. The rebase replayed 51 branch commits (48 unique after skips),
> yielding 16 conflict hunks across 14 commits in 8 files.

---

## Recurring pattern: `_finish_one` / `_finish_targets` classmethod (door.py)

Several commits re-conflicted on `FinishEditingDoor` because v0.8.0 introduced
`FeatureModifierEditMixin` with `_finish_one`/`_finish_targets` classmethods
([233cc344fa](https://github.com/IfcOpenShell/IfcOpenShell/commit/233cc344fa)), while the
branch still used the older instance-method `finish_editing_door_on_object` + `copy_door_params(self, ...)`.

**Resolution applied consistently:** Keep HEAD's classmethod structure throughout:
- `_finish_one` calls `super()._finish_one(obj, context)` then mirror-syncs via `has_mirrored_type`
- `copy_door_params(cls, from_data, from_elem, to_elem)` — `from_elem` for correct constituent lookup
- `_execute` delegates to `_finish_targets(context)`

---

## Conflict 1 — `blender.py` @ `12161e90c1`

**Commit:** "Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type."

v0.8.0 extended the `is_array_child` docstring ("This sits on a different axis from
`tool.Parametric.is_array`…"). The branch inserted `is_window`, `is_door`, `is_stair`,
`has_mirrored_type`, `set_mirrored_type`, `is_wall` between the docstring end and the method body.

**Resolution:** Kept v0.8.0's docstring extension; added only `has_mirrored_type` +
`set_mirrored_type` after `is_array_child` closes; dropped `is_window`, `is_door`,
`is_stair`, `is_wall` (all moved to `tool.Parametric` in v0.8.0).

---

## Conflict 2 — `root.py` @ `bbb7cee2d4`

**Commit:** "copy_representation now properly copies explicitly assigned IfcStyledItems"

v0.8.0 guards `assign_body_styles` with `if not root.has_material_styles(new)`.
Branch comments it out entirely — `copy_representation` now copies `IfcStyledItem`s directly.

**Resolution:** Kept branch's commented-out version. Consistent with the same resolution
applied to `duplicate_opening_on_type_duplication` rebase.

---

## Conflict 3 — `blender.py` @ `b4bb5e7e9b`

**Commit:** "Applied formatting"

Branch re-inserted `is_door` + `is_stair` before `has_mirrored_type`; also reformatted
the `edit_pset` call to multi-line.

**Resolution:** Dropped `is_door`/`is_stair` re-insertion; kept multi-line `edit_pset` formatting.

---

## Conflicts 4 & 5 — `opening.py` @ `7b12dc8a32` and `2cefe24b14`

**Commits:** "Doors are now placed on the side of the wall that was snapped to" /
"Flip tool now moves windows / doors to the other side of a wall"

Conflict 4: Branch adds `filling_opposite_x` offset calculation so a door placed on the
side axis occupies the same X extents after 180° rotation. v0.8.0 simply translated to
`point_on_side_axis`. Kept branch's fuller logic.

Conflict 5: v0.8.0 had an extra blank line before `return {"FINISHED"}`. Branch removes it.
Kept branch version.

---

## Conflicts 6 & 7 — `polyline.py` @ `178d1e1f1e` and `3bbd2aa747`

**Commits:** "Fixed door/window preview and made preview of other objects not rotate with wall" /
"Made door/window preview both simpler and more intuitive"

Commit `178d1e1f1e` added `invert_x = False` / `invert_x = True` + `offset_x` correction
for the door/window preview when snapped to the side axis.
Commit `3bbd2aa747` then simplified by removing `invert_x = False` (and the offset logic
was auto-merged away).

**Resolution:** Kept all branch additions for `178d1e1f1e`; for `3bbd2aa747` removed
`invert_x = False` init (no longer needed after the simplification).

---

## Conflict 8 — `workspace.py` @ `8cda4cf6b1`

**Commit:** "Added ChangeSwingDirection operator for parametric doors"

Branch adds `S_C_F` (Shift+Ctrl+F) hotkey → `change_swing_direction`. HEAD has `C_F` →
`mirror_geometry`. Both are independent operations.

**Resolution:** Kept both hotkeys and both handler methods.

---

## Conflict 9 — `shape_builder.py` @ `7885a5dc02`

**Commit:** "Added ShapeBuilder support for mirroring 3d curves, IfcPolygonalFaceSet and IfcGeometricSet"

Two sub-conflicts:

**A:** v0.8.0 added a guard: if `Coordinates` is shared (total inverses > 1), clone before
mutating to avoid corrupting other representation items. Branch didn't have this guard.
Kept v0.8.0's guard.

**B:** v0.8.0 conditionally reverses face winding only when `(axis_flip_count % 2) != 0`
(a double mirror preserves orientation). Also includes `IfcBoundingBox` handling.
Branch always reverses winding and lacks `IfcBoundingBox`. Kept v0.8.0's correct
conditional + bounding-box branch.

---

## Conflict 10 — `door.py` @ `3a3f615d8a`

**Commit:** "Added bim.mirror_geometry() operator for truly mirroring products / types"

First introduction of the mirror operator. Branch uses old instance-method pattern
(`finish_editing_door_on_object` + `BBIM_InvertedSwingType` pset lookup).

**Resolution:** Kept HEAD's `_finish_one`/`_finish_targets` classmethod approach.
Kept `from_elem` for `get_constituents_props_data` (correct: constituents come from
source, not target).

---

## Conflict 11 — `workspace.py` @ `174aa5256a`

**Commit:** "changed hotkey to ctrl + f, added icon"

This commit supersedes `8cda4cf6b1` — it removes `S_C_F` and changes `C_F` to call
`mirror_geometry()` directly (without the `keep_original=shift` argument).

**Resolution:** Removed `S_C_F` from keymap (following branch intent); simplified
`hotkey_C_F` to `mirror_geometry()` without arguments.

---

## Conflict 12 — `door.py` @ `c82424c90c`

**Commit:** "Door materials are now synced to mirrored types."

Branch adds `from_elem` to `copy_door_params` (still instance-method style). HEAD already
has this as a classmethod from prior resolution.

**Resolution:** Kept HEAD's classmethod; discarded branch's re-introduction of the
instance-method lifecycle body.

---

## Conflict 13 — `geometry/operator.py` @ `267719aa1f`

**Commit:** "Geometry for arbitrary objects is now synced for mirrored objects"

Branch uses old `BBIM_InvertedSwingType` pset lookup to find the mirrored type. HEAD uses
the cleaner `tool.Blender.Modifier.has_mirrored_type(type_elem)` API.

**Resolution:** Kept HEAD's `has_mirrored_type` API.

---

## Conflicts 14–16 — `operator.py`, `door.py`, `blender.py` @ `361955428c`

**Commit:** "Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type."

This is the commit that *introduced* `has_mirrored_type` in the branch, but v0.8.0
already had it from our earlier conflict resolutions. Taking the branch's additions would
have duplicated `has_mirrored_type`/`set_mirrored_type` in `blender.py`, and duplicated
swap+reload logic in `operator.py`.

**Resolution:** Took HEAD throughout in all three files to avoid duplication.
