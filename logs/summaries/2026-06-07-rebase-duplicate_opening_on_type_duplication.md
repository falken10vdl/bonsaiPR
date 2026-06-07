# Rebase Summary: duplicate_opening_on_type_duplication onto v0.8.0

**Date:** 2026-06-07  
**Branch:** [`duplicate_opening_on_type_duplication`](https://github.com/IfcOpenShell/IfcOpenShell/tree/duplicate_opening_on_type_duplication)  
**Base:** `v0.8.0` @ [`93c6350e0f`](https://github.com/IfcOpenShell/IfcOpenShell/commit/93c6350e0f)  
**Result tip:** [`a0381a9de9`](https://github.com/IfcOpenShell/IfcOpenShell/commit/a0381a9de9)  
**Outcome:** `conflicts-resolved`  
**Prior rebase:** This branch was previously rebased onto the old v0.8.0 tip (`7e96692764`). This rebase adds 131 new v0.8.0 commits on top of that.

---

## Commits on branch not in v0.8.0

47 commits:

| Short hash | Message |
|------------|---------|
| `b93ae22829` | Doors are now placed on the side of the wall that was snapped to |
| `4e3931b6c0` | Flip tool now moves windows / doors to the other side of a wall |
| `04ecd52ff8` | Fixed door / window preview and made preview of other objects not rotate with wall |
| `00b2ac8354` | Fixed preview for rotated walls |
| `72e0561458` | Made door / window preview both simpler and more intuitive |
| `43ff41dfa5` | Added ChangeSwingDirection operator for parametric doors |
| `0bd0bae08b` | Added ShapeBuilder support for mirroring 3d curves, IfcPolygonalFaceSet and IfcGeometricSet |
| `3db5f95c87` | Added bim.mirror_geometry() operator for truly mirroring products / types |
| `36fae6c998` | changed hotkey to ctrl + f, added icon |
| `5709b664cb` | fixed directly flipping a product type throwing an exception |
| `1abfec86dd` | Inverted type name is now xxx.Mirror |
| `9fd608437d` | Door materials are now synced to mirrored types |
| `a3af4bbcb4` | Geometry for arbitrary objects is now synced for mirrored objects |
| `b61e8fc9f0` | Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type |
| `7917143151` | ShapeBuilder: added support for IndexedPolygonalFaceWithVoids |
| `c63b320960` | Implemented material syncing for mirrored types |
| `27ed53f773` | extended Root.copy_representation to also copy shape aspects |
| `05dfc89fae` | Root.copy_representation() now also copies shape aspects of product types |
| `d4f9cad5a5` | Simplified shape aspect duplication in copy_representation() |
| `e7e9e77647` | Mirrored objects now stay in place correctly |
| `235f7b50a1` | copy_representation now properly copies explicitly assigned IfcStyledItems |
| `c5de78c066` | Applied formatting |
| `df34beffee` | Fixed missing length unit conversion in FilledOpeningGenerator |
| `ea18962239` | Fixed double mirroring when two IfcPolygonalFaceSets reuse the same coordinate list entity |
| `d57de73cca` | Mirroring should now support IfcBoundingBox |
| `5219c1bcc9` | Fix NoneType error and missing argument in mirror_geometry operator |
| `56d0d373f3` | Use active object as mirror plane when other objects are selected |
| `bf131a86e9` | Shift+click or Shift+Ctrl+F duplicates and mirrors, keeping original |
| `acce2e3e06` | Fix mirror axis mismatch when ref object is rotated |
| `5a8d9fd5de` | Add Z-axis mirror support |
| `83d2c8e189` | copy_representation: preserve MappedRepresentation structure for IfcTypeProduct |
| `d899e22a6b` | Add LAYER3 (slab) mirror geometry support |
| `0aa3b67990` | Fix IfcOpeningElement mirror on LAYER3 slabs |
| `a63f496da0` | Fix BRep and opening element mirroring |
| `3281c2fbdc` | Fix void mirroring on assign_type path |
| `358d7ed723` | Add LAYER2 wall mirror support |
| `c87b1dc73a` | Fix extruded void mirror in LAYER2 walls |
| `988b86f272` | Fix #6392: duplicate window/door now copies IfcOpenElement |
| `eb42784b1e` | ifcpatch: fix MergeProjects context deduplication |
| `c4b1a5e56d` | ci: add test coverage for ifc5d, ifcquery, ifcedit, ifcmcp |
| `18aa168a3f` | CI: An ifc5d test needs odfpy |
| `f565da9020` | tests: mathutils tests need python 3.12+ |
| `23a153be34` | ifc5d: fix two csv2ifc bugs found by round-trip test |
| `7ea3c591ba` | CI: and ifc5d test needs xlsxwriter |
| `ff132b84db` | bsdd: fix tests for rate limiting, wrong API call, and assertion bugs |
| `c6b9694dba` | bsdd: retry on HTTP 429 rate-limit responses in Client.get() |
| `a0381a9de9` | bonsai: fix failing test_copy_with_new_geometry_copied_from_the_old |

---

## Conflict 1: `src/bonsai/bonsai/tool/blender.py`

**Replaying commit:** [`b61e8fc9f0`](https://github.com/IfcOpenShell/IfcOpenShell/commit/b61e8fc9f0) (original: `361955428c`) — "Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type."

**Key v0.8.0 commit:** [`a30546f1f2`](https://github.com/IfcOpenShell/IfcOpenShell/commit/a30546f1f2) — "Bbox dimensions key, DRY array operators, drop dead code"

### What v0.8.0 changed

The new v0.8.0 commits executed a major refactoring of the `Modifier` class in `tool.Blender`. The methods `is_window`, `is_door`, `is_stair`, and `is_wall` were **removed** from `Modifier` and moved to `tool.Parametric`. A new `is_array_child` method was added (with a detailed docstring), and `is_slab` was added as well.

### What the branch commit intended

The branch added `has_mirrored_type` and `set_mirrored_type` to `Modifier`. The patch context expected `is_stair` immediately before `is_wall` — but in v0.8.0, neither of those methods exist in `Modifier` anymore, and the new `is_array_child` appeared in their place.

### Resolution

1. Kept HEAD's `is_array_child` with its extended docstring unchanged.
2. Discarded `is_window`, `is_door`, `is_stair`, `is_wall` from the conflict "theirs" block — these are now in `tool.Parametric` and don't belong in `Modifier`.
3. Added `has_mirrored_type` and `set_mirrored_type` after `is_array_child` and before `is_slab`.

A follow-up commit `dc5a88d290` ("Applied formatting") tried to clean up trailing spaces around `has_mirrored_type`/`set_mirrored_type` and also re-add `is_door`/`is_stair` context lines. The `is_door`/`is_stair` conflict was resolved by discarding them again; the `edit_pset` multi-line formatting was kept (branch's version).

---

## Conflict 2: `src/bonsai/bonsai/core/root.py`

**Replaying commit:** [`235f7b50a1`](https://github.com/IfcOpenShell/IfcOpenShell/commit/235f7b50a1) (original: `c937a5e3bb`) — "copy_representation now properly copies explicitly assigned IfcStyledItems"

**Key v0.8.0 commit:** [`e764559133`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e764559133) — "Route _has_material_styles through tool.Root.has_material_styles"

### What v0.8.0 changed

v0.8.0 commit `e764559133` updated the conditional in `copy_class` from the private `_has_material_styles(ifc, new)` to `root.has_material_styles(new)` (routing through the tool layer). So HEAD has:
```python
if not root.has_material_styles(new):
    root.assign_body_styles(new, obj)
```

### What the branch commit intended

The branch commit removed the conditional entirely, replacing it with a comment:
```python
# not sure what the purpose of this is, but removing it fixes wrong IfcStyledItems...
# root.assign_body_styles(new, obj)
```
This is because `copy_representation` was updated to directly copy IfcStyledItems, making the separate `assign_body_styles` call redundant.

### Resolution

Kept the branch's commented-out version. The branch's intent (not calling `assign_body_styles` at all) is correct — it was superseded by the more direct approach in `copy_representation`. The `root.has_material_styles` wrapper in HEAD is a cleaner API, but since we're no longer calling `assign_body_styles`, it's not needed here.

---

## Conflict 3: `src/ifcgeom/kernels/opencascade/sweep_along_curve.cpp`

**Replaying commit:** branched as [`23a153be34`](https://github.com/IfcOpenShell/IfcOpenShell/commit/23a153be34) (original: `d70b15ead0`) — "ifcgeom: fix sweep restore translation sign in sweep_along_curve"

**Key v0.8.0 commit:** [`a433f56337`](https://github.com/IfcOpenShell/IfcOpenShell/commit/a433f56337) — "Fix sign of temporary offset restore in sweep_along_curve"

### What happened

Both v0.8.0 and the branch commit fix the same bug: the translation sign was negated twice, placing swept geometry at `original - 2*mean`. Both sides change the line to use positive mean:
```cpp
trsf.SetTranslation(gp_Vec(mean.x(), mean.y(), mean.z()));
```

v0.8.0's version added an explanatory comment; the branch commit's version has no comment.

### Resolution

Kept HEAD's version (with the comment). The fix itself was already subsumed by the v0.8.0 commit — only the comment was the difference.

---

## Final branch tip

[`a0381a9de9`](https://github.com/IfcOpenShell/IfcOpenShell/commit/a0381a9de9)
