# Rebase Summary: duplicate_opening_on_type_duplication onto v0.8.0

**Date:** 2026-05-21  
**Branch:** `duplicate_opening_on_type_duplication`  
**Base:** `v0.8.0` @ [`7e96692764`](https://github.com/IfcOpenShell/IfcOpenShell/commit/7e96692764)  
**Result tip:** [`5a9dd012da`](https://github.com/IfcOpenShell/IfcOpenShell/commit/5a9dd012da)  
**Outcome:** `conflicts-resolved`

---

## Commits on branch not in v0.8.0

47 commits (linearized; the original merge commit `bcb94d79bd` is not preserved after rebase):

| Short hash | Message |
|------------|---------|
| `7b12dc8a32` | Doors are now placed on the side of the wall that was snapped to |
| `2cefe24b14` | Flip tool now moves windows / doors to the other side of a wall |
| `178d1e1f1e` | Fixed door / window preview and made preview of other objects not rotate with wall |
| `9036308f44` | Fixed preview for rotated walls |
| `3bbd2aa747` | Made door / window preview both simpler and more intuitive |
| `8cda4cf6b1` | Added ChangeSwingDirection operator for parametric doors |
| `7885a5dc02` | Added ShapeBuilder support for mirroring 3d curves, IfcPolygonalFaceSet and IfcGeometricSet |
| `3a3f615d8a` | Added bim.mirror_geometry() operator for truly mirroring products / types |
| `174aa5256a` | changed hotkey to ctrl + f, added icon |
| `6e5b2bd080` | fixed directly flipping a product type throwing an exception |
| `1a7ec6c08e` | Inverted type name is now xxx.Mirror |
| `c82424c90c` | Door materials are now synced to mirrored types. Fixed door editing applying materials to product when modifying product type geometry. |
| `267719aa1f` | Geometry for arbitrary objects is now synced for mirrored objects |
| `361955428c` | Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type. |
| `cd3a11b5b8` | ShapeBuilder: added support for IndexedPolygonalFaceWithVoids, fixed winding order when mirroring on an even number of axes |
| `044af7d437` | Implemented material syncing for mirrored types |
| `90ca6f9419` | extended Root.copy_representation to also copy shape aspects |
| `0459485a31` | Root.copy_representation() now also copies shape aspects of product types |
| `f83b0cdd84` | Simplified shape aspect duplication in copy_representation() |
| `8c5f3f49b2` | Mirrored objects now stay in place correctly. Editing doors no longer results in switching representations. |
| `c937a5e3bb` | copy_representation now properly copies explicitly assigned IfcStyledItems |
| `dc5a88d290` | Applied formatting |
| `2a60e654d4` | Fixed missing length unit conversion in FilledOpeningGenerator |
| `1a7ab5b48e` | Fixed double mirroring when two IfcPolygonalFaceSets reuse the same coordinate list entity |
| `013b59a81a` | Mirroring should now support IfcBoundingBox |
| `3e0712f272` | Fix NoneType error and missing argument in mirror_geometry operator |
| `2313159df2` | - Use active object as mirror plane when other objects are selected, falling back to in-place X-axis flip |
| `885fc5ef17` | - Shift+click or Shift+Ctrl+F duplicates and mirrors, keeping original |
| `5cfcf87fd6` | Fix mirror axis mismatch when ref object is rotated |
| `1ffde7d6bf` | Add Z-axis mirror support |
| `2b46db0f3c` | copy_representation: preserve MappedRepresentation structure for IfcTypeProduct |
| `94bbb24599` | Add LAYER3 (slab) mirror geometry support |
| `e4510416ca` | Fix IfcOpeningElement mirror on LAYER3 slabs |
| `afbfe9e148` | Fix BRep and opening element mirroring |
| `ff56b2ec2f` | Fix void mirroring on assign_type path |
| `2079e78a5c` | Add LAYER2 wall mirror support |
| `3bc4b7e854` | Fix extruded void mirror in LAYER2 walls |
| `9c66dacd93` | Fix #6392: when duplicating a window/door/etc, the associated IfcOpenElement duplicates as well |
| `efe2d7c999` | ifcpatch: fix MergeProjects context deduplication and remove stale stub |
| `3a00be83a4` | ci: add test coverage for ifc5d, ifcquery, ifcedit, ifcmcp |
| `d173d9b9dc` | CI: An ifc5d test needs odfpy |
| `2689cc2fa2` | tests: mathutils tests need python 3.12+ |
| `cbc92c2f44` | ifc5d: fix two csv2ifc bugs found by round-trip test |
| `d70b15ead0` | ifcgeom: fix sweep restore translation sign in sweep_along_curve |
| `362457c2ef` | CI: and ifc5d test needs xlsxwriter |
| `b037b7de32` | bsdd: fix tests for rate limiting, wrong API call, and assertion bugs |
| `68f2ce54dd` | bsdd: retry on HTTP 429 rate-limit responses in Client.get() |
| `5a9dd012da` | bonsai: fix failing test_copy_with_new_geometry_copied_from_the_old |

---

## Conflict 1: `src/bonsai/bonsai/bim/module/model/door.py`

**Replaying commit:** [`3a3f615d8a`](https://github.com/IfcOpenShell/IfcOpenShell/commit/3a3f615d8a) — "Added bim.mirror_geometry() operator for truly mirroring products / types"

**v0.8.0 commit that caused the conflict:** [`233cc344fa`](https://github.com/IfcOpenShell/IfcOpenShell/commit/233cc344fa) — "Add tool.Parametric registry and lifecycle mixins"

### What v0.8.0 changed

`233cc344fa` refactored `FinishEditingDoor`, `CancelEditingDoor`, and `EnableEditingDoor` to inherit from `_DoorEditMixin(FeatureModifierEditMixin)`. `FinishEditingDoor._execute` became a one-liner: `return self._finish_targets(context)`, which delegates to the mixin to iterate all selected doors and call `_finish_one` on each.

The merge-base already had a manual multi-object loop in `_execute` with inline `finish_editing_door_on_object` logic.

### What the branch commit intended

The branch's commit `3a3f615d8a` was adding `bim.mirror_geometry()`. As part of that, it extended `FinishEditingDoor` to also sync door parameters to any mirrored/inverted type via `BBIM_InvertedSwingType` pset. It added:
- `finish_editing_door_on_object(self, obj)` — does the per-object finish work, plus syncs mirrored type
- `copy_door_params(self, from_data, to_elem)` — copies door params to the mirrored type with swing direction inverted
- `_execute` — iterates selected objects calling `finish_editing_door_on_object`

### Resolution

**Kept:** `_DoorEditMixin` inheritance from v0.8.0 (cleaner class hierarchy).  
**Added:** branch's `finish_editing_door_on_object`, `copy_door_params`, and `_execute` override on `FinishEditingDoor`.

This gives us: v0.8.0's mixin-structured class hierarchy + the branch's mirror-type sync logic. The `_execute` override calls `finish_editing_door_on_object` for each selected object, superseding the inherited `_finish_targets` for this class.

Later commits on the branch evolve `finish_editing_door_on_object` to use `tool.Blender.Modifier.has_mirrored_type(element)` instead of `BBIM_InvertedSwingType` pset, and update `copy_door_params` signature to `(from_data, from_elem, to_elem)` — those apply cleanly on top of this resolution.

---

## Conflict 2: `src/bonsai/bonsai/core/root.py`

**Replaying commit:** [`5a9dd012da`](https://github.com/IfcOpenShell/IfcOpenShell/commit/5a9dd012da) (original: `aa3e38aca8`) — "bonsai: fix failing test_copy_with_new_geometry_copied_from_the_old"

**Root cause:** An earlier branch commit (`c937a5e3bb` / original `6f4b4283e0` — "copy_representation now properly copies explicitly assigned IfcStyledItems") had already been replayed on top of v0.8.0, and it commented out the `assign_body_styles` call entirely. Then `aa3e38aca8` (written against the earlier branch state that still had `_has_material_styles`) tried to apply, but that code was already gone.

### What v0.8.0 had

`core/root.py` had a private `_has_material_styles(ifc, element)` function and a conditional call:
```python
if not _has_material_styles(ifc, new):
    root.assign_body_styles(new, obj)
```

### What the branch commit `aa3e38aca8` intended

Move `_has_material_styles` from a private function (that directly called `ifcopenshell.util.element`, bypassing the tool layer and crashing unit tests) into `root.has_material_styles(new)` via `core/tool.py` + `tool/root.py`.

### What HEAD had at the point of conflict

An earlier replayed branch commit (`c937a5e3bb`) had commented out the entire `assign_body_styles` call:
```python
# not sure what the purpose of this is, but removing it fixes wrong IfcStyledItems being assigned to
# a duplicated object. Instead, copy_representation now properly copies IfcStyledItems directly.
# root.assign_body_styles(new, obj)
```

So the code `aa3e38aca8` was trying to patch no longer existed.

### Resolution

**Kept:** HEAD's commented-out version (the desired final state — `assign_body_styles` not called at all).  
**Accepted:** The `core/tool.py` and `tool/root.py` additions from `aa3e38aca8` applied cleanly (adding `has_material_styles` to the tool interface and implementation). These are kept as they are valid additions regardless.

The `has_material_styles` method in the tool is now present (added by the commit) even though it is no longer called from `core/root.py`. This is benign — it remains a useful diagnostic tool method.

---

## Final branch tip

[`5a9dd012da`](https://github.com/IfcOpenShell/IfcOpenShell/commit/5a9dd012da)
