# Rebase: `regenerate_wall_to_underside` onto `v0.8.0` (2026-05-21)

## Summary

Branch [`regenerate_wall_to_underside`](https://github.com/IfcOpenShell/IfcOpenShell/pull/7943)
was rebased onto `v0.8.0` tip [`7e96692764`](https://github.com/IfcOpenShell/IfcOpenShell/commit/7e96692764).
One file conflict arose and was resolved cleanly. The branch tip is now
[`26bd75df31`](https://github.com/IfcOpenShell/IfcOpenShell/commit/26bd75df31).

---

## Branch Commits (7 total)

| Hash | Message |
|------|---------|
| [`26bd75df31`](https://github.com/IfcOpenShell/IfcOpenShell/commit/26bd75df31) | Add has_underside_connection method to Model class and update wall regeneration logic |
| [`268a1c68ad`](https://github.com/IfcOpenShell/IfcOpenShell/commit/268a1c68ad) | Fix validate_type corruption; remove debug prints |
| [`ff16295523`](https://github.com/IfcOpenShell/IfcOpenShell/commit/ff16295523) | Fix duplicate booleans in extend_walls_to_underside |
| [`5ca0ec7545`](https://github.com/IfcOpenShell/IfcOpenShell/commit/5ca0ec7545) | Regenerate connected walls when recalculating a slab |
| [`72f19e15be`](https://github.com/IfcOpenShell/IfcOpenShell/commit/72f19e15be) | Add extend/regenerate walls to multiple undersides |
| [`c74b4d0f91`](https://github.com/IfcOpenShell/IfcOpenShell/commit/c74b4d0f91) | Closes #7943: Add regenerate_wall_to_underside operator |
| [`06e364377d`](https://github.com/IfcOpenShell/IfcOpenShell/commit/06e364377d) | Fix extend_walls_to_underside ridge artifact |

---

## Conflict

### File: `src/bonsai/bonsai/bim/module/model/wall.py`

**Conflicting commit from `v0.8.0`:** [`26eef20eb5`](https://github.com/IfcOpenShell/IfcOpenShell/commit/26eef20eb5)
("Add wall parametric editing and gizmos") — introduced
`_commit_pending_wall_edits_for_selection(context)` at the top of
`ExtendWallsToUnderside._execute`, followed by `slab = None`.

**Branch commit that conflicted:** [`72f19e15be`](https://github.com/IfcOpenShell/IfcOpenShell/commit/72f19e15be)
("Add extend/regenerate walls to multiple undersides") — replaced `slab = None` with
`slabs: list[bpy.types.Object] = []` to support multiple slab targets.

**Common ancestor state:**
```python
def _execute(self, context):
    slab = None
    walls: list[bpy.types.Object] = []
```

**`v0.8.0` side (ours):**
```python
def _execute(self, context):
    # Match the sibling ops (UnjoinWalls / MergeWall / ExtendWallsToWall): if any
    # of the selected walls has an in-progress parametric draft, commit it before
    # extending, so the slab clip operates on the just-finalised IFC state.
    _commit_pending_wall_edits_for_selection(context)
    slab = None
    walls: list[bpy.types.Object] = []
```

**Branch side (theirs):**
```python
def _execute(self, context):
    slabs: list[bpy.types.Object] = []
    walls: list[bpy.types.Object] = []
```

**Resolution:** Both changes are independent — `v0.8.0` adds a pre-flight commit of
pending wall edits; the branch changes the slab variable from a single object to a list.
The resolved version keeps both:

```python
def _execute(self, context):
    # Match the sibling ops (UnjoinWalls / MergeWall / ExtendWallsToWall): if any
    # of the selected walls has an in-progress parametric draft, commit it before
    # extending, so the slab clip operates on the just-finalised IFC state.
    _commit_pending_wall_edits_for_selection(context)
    slabs: list[bpy.types.Object] = []
    walls: list[bpy.types.Object] = []
```

---

## Result

- **Branch tip after rebase:** [`26bd75df31`](https://github.com/IfcOpenShell/IfcOpenShell/commit/26bd75df31)
- **Conflicts:** 1 file, resolved cleanly
- **Stash:** none required (only `simple_spf` submodule was dirty; `git stash` found nothing to save)
