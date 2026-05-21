# Rebase Summary: general-mirroring onto v0.8.0

**Date:** 2026-05-21
**Branch:** `general-mirroring`
**Rebased onto:** `v0.8.0` ([7e96692764](https://github.com/IfcOpenShell/IfcOpenShell/commit/7e96692764))
**Result tip:** [2ab8d7d499](https://github.com/IfcOpenShell/IfcOpenShell/commit/2ab8d7d499)
**Outcome:** conflicts-resolved

---

## Branch commits (not in v0.8.0 at fork point)

37 commits were replayed onto v0.8.0:

| Hash | Message |
|------|---------|
| `2ab8d7d499` | Fix extruded void mirror in LAYER2 walls |
| `46f25f3c67` | Add LAYER2 wall mirror support |
| `469260b9d7` | Fix void mirroring on assign_type path |
| `8777b4e908` | Fix BRep and opening element mirroring |
| `287f0212f7` | Fix IfcOpeningElement mirror on LAYER3 slabs |
| `581805b233` | Add LAYER3 (slab) mirror geometry support |
| `34d768930f` | copy_representation: preserve MappedRepresentation structure for IfcTypeProduct |
| `507e9ddfd2` | Add Z-axis mirror support |
| `7343a68457` | Fix mirror axis mismatch when ref object is rotated |
| `4be597835d` | Shift+click duplicates and mirrors; show Mirror Geometry button for any IFC element |
| `fb75f50f07` | Use active object as mirror plane when other objects are selected |
| `e7534959b3` | Fix NoneType error and missing argument in mirror_geometry operator |
| `7a0c027016` | Mirroring should now support IfcBoundingBox |
| `c59af0065e` | Fixed double mirroring when two IfcPolygonalFaceSets reuse the same coordinate list |
| `64d2ce104f` | Fixed missing length unit conversion in FilledOpeningGenerator |
| `3cb779474c` | Applied formatting |
| `6f4b4283e0` | copy_representation now properly copies explicitly assigned IfcStyledItems |
| `8ef93721e3` | Mirrored objects now stay in place correctly; editing doors no longer switches reps |
| `f14fc495e1` | Simplified shape aspect duplication in copy_representation() |
| `60e4dd2870` | Root.copy_representation() now also copies shape aspects of product types |
| `5aed75f1fb` | Extended Root.copy_representation to also copy shape aspects |
| `b801098822` | Implemented material syncing for mirrored types |
| `08b3a639fa` | ShapeBuilder: added IndexedPolygonalFaceWithVoids support, fixed winding order |
| `bd1d114f17` | Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type |
| `1958b381fd` | Geometry for arbitrary objects is now synced for mirrored objects |
| `0bc60f927b` | Door materials are now synced to mirrored types |
| `2b6485578d` | Inverted type name is now xxx.Mirror |
| `370d505a04` | Fixed directly flipping a product type throwing an exception |
| `0357b47ed8` | Changed hotkey to ctrl+f, added icon |
| `5438190731` | Added bim.mirror_geometry() operator for truly mirroring products/types |
| `4b1fb89b23` | Added ShapeBuilder support for mirroring 3D curves, IfcPolygonalFaceSet, IfcGeometricSet |
| `ff0a7eab32` | Added ChangeSwingDirection operator for parametric doors |
| `916fac092f` | Made door/window preview both simpler and more intuitive |
| `b60bb72778` | Fixed preview for rotated walls |
| `5286a4beb1` | Fixed door/window preview and made preview of other objects not rotate with wall |
| `63333d27bf` | Flip tool now moves windows/doors to the other side of a wall |
| `17e79f12ee` | Doors are now placed on the side of the wall that was snapped to |

---

## Conflicts

### 1. `src/bonsai/bonsai/bim/module/model/workspace.py`

**Conflicting commit on branch:** `46f25f3c67` — "Add LAYER2 wall mirror support"

**v0.8.0 commit that caused the conflict:** [`1a849395c2`](https://github.com/IfcOpenShell/IfcOpenShell/commit/1a849395c2) — "Typo crashing edit tools panel when non-wall with wall selected"

**What each side did:**

- **v0.8.0 (`1a849395c2`):** Fixed a crash in the wall tool panel by correcting a typo in the operator name — calling `bpy.ops.bim.extend_walls_to_underside.__doc__` directly (the operator is properly registered under this name in v0.8.0).

- **Branch (`46f25f3c67`):** When this commit was written, the operator was not yet registered in the branch's codebase under any name. A `try/except AttributeError` guard was added around `bpy.ops.bim.extend_to_underside.__doc__` (an older/wrong name) to prevent a crash in the tool header draw.

**Conflict (3-way view):**
```python
# v0.8.0 (HEAD):
add_layout_hotkey_operator(
    cls.layout, "Extend To Underside", "S_E", bpy.ops.bim.extend_walls_to_underside.__doc__, ui_context
)

# Branch (theirs):
try:
    doc = bpy.ops.bim.extend_to_underside.__doc__
except AttributeError:
    doc = ""
add_layout_hotkey_operator(
    cls.layout, "Extend To Underside", "S_E", doc, ui_context
)
```

**Resolution:** Took v0.8.0's version verbatim. The try/except guard on the branch was a workaround for an operator that didn't exist at branch-fork time; v0.8.0 properly registered the operator as `extend_walls_to_underside` and fixed the typo crash simultaneously. The branch's intent (avoid a crash) is already satisfied by v0.8.0's fix.

---

## Files with potential overlap that did NOT conflict

The following files were touched by both sides but Git resolved them automatically:

- `src/bonsai/bonsai/bim/module/model/product.py` — auto-merged cleanly
- `src/bonsai/bonsai/bim/module/geometry/operator.py` — no overlap in touched lines
- `src/bonsai/bonsai/bim/module/material/operator.py` — no overlap in touched lines
- `src/bonsai/bonsai/bim/module/model/opening.py` — no overlap in touched lines
- `src/bonsai/bonsai/bim/module/model/polyline.py` — no overlap in touched lines
- `src/ifcopenshell-python/ifcopenshell/util/shape_builder.py` — no overlap in touched lines
