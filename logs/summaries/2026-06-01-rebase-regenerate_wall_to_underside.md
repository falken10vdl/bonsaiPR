# Rebase Summary — regenerate_wall_to_underside onto v0.8.0

- **Date:** 2026-06-01 07:20:04
- **Branch:** [regenerate_wall_to_underside](https://github.com/IfcOpenShell/IfcOpenShell/pull/7944) (PR #7944 — "Closes #7943: Regenerate wall to underside")
- **Base:** `v0.8.0` @ [431cf435ef](https://github.com/IfcOpenShell/IfcOpenShell/commit/431cf435ef)
- **Merge-base before rebase:** [7e96692764](https://github.com/IfcOpenShell/IfcOpenShell/commit/7e96692764)
- **New branch tip:** [bfb4312906](https://github.com/IfcOpenShell/IfcOpenShell/commit/bfb4312906)
- **Outcome:** conflicts-resolved (1 conflict, 1 file)

## Divergence

At the start, `regenerate_wall_to_underside` was **7 commits ahead** of its merge-base (`7e96692764`) with `v0.8.0`, and `v0.8.0` had landed **71 commits** since that merge-base. The local `v0.8.0` ref was stale (`c83b4eb69f`) and was fast-forwarded to the freshly fetched `origin/v0.8.0` tip (`431cf435ef`) before rebasing.

### Commits on the branch (replayed, oldest → newest)

| New hash | Subject |
|----------|---------|
| [94aaa5a6b2](https://github.com/IfcOpenShell/IfcOpenShell/commit/94aaa5a6b2) | Fix extend_walls_to_underside ridge artifact |
| [5217ff0dce](https://github.com/IfcOpenShell/IfcOpenShell/commit/5217ff0dce) | Closes #7943: Add regenerate_wall_to_underside operator |
| [2e85a11c82](https://github.com/IfcOpenShell/IfcOpenShell/commit/2e85a11c82) | Add extend/regenerate walls to multiple undersides ← **conflict resolved here** |
| [acd62c59d0](https://github.com/IfcOpenShell/IfcOpenShell/commit/acd62c59d0) | Regenerate connected walls when recalculating a slab |
| [4475111d0c](https://github.com/IfcOpenShell/IfcOpenShell/commit/4475111d0c) | Fix duplicate booleans in extend_walls_to_underside |
| [d6662e5c56](https://github.com/IfcOpenShell/IfcOpenShell/commit/d6662e5c56) | Fix validate_type corruption; remove debug prints |
| [bfb4312906](https://github.com/IfcOpenShell/IfcOpenShell/commit/bfb4312906) | Add has_underside_connection method to Model class and update wall regeneration logic |

### Files touched by the branch that also changed in v0.8.0 (conflict candidates)

Seven of the branch's eight touched files overlapped with v0.8.0 changes:

- `src/bonsai/bonsai/bim/module/model/__init__.py`
- `src/bonsai/bonsai/bim/module/model/wall.py` ← **only actual conflict**
- `src/bonsai/bonsai/bim/module/model/workspace.py`
- `src/bonsai/bonsai/core/model.py`
- `src/bonsai/bonsai/core/tool.py`
- `src/bonsai/bonsai/tool/geometry.py`
- `src/bonsai/bonsai/tool/model.py`

(`src/ifcopenshell-python/ifcopenshell/api/geometry/validate_type.py` was the only non-overlapping file.) Despite seven overlap candidates, only `wall.py` actually conflicted; the rest auto-merged.

## The conflict

**File:** [`src/bonsai/bonsai/bim/module/model/wall.py`](https://github.com/IfcOpenShell/IfcOpenShell/blob/bfb4312906/src/bonsai/bonsai/bim/module/model/wall.py) — inside `ExtendWallsToUnderside._execute`, raised while replaying [2e85a11c82](https://github.com/IfcOpenShell/IfcOpenShell/commit/2e85a11c82) ("Add extend/regenerate walls to multiple undersides").

### The v0.8.0 change that caused it

Commit [d7b5ac1453](https://github.com/IfcOpenShell/IfcOpenShell/commit/d7b5ac1453) ("Add wall draft-resync helper + wire 6 mutation operators") landed in `v0.8.0` after the merge-base. Among the six operators it wired up was `ExtendWallsToUnderside`: it added a `_resync_walls_after_mutation(walls)` call immediately after `core.extend_wall_to_slab(...)`, so that any in-progress parametric wall drafts are re-synced after the slab clip mutates the walls.

### The three versions

**Merge-base** (`2e85a11c82~1`, the singular-slab model the branch started from):
```python
slab = None
walls: list[bpy.types.Object] = []
if (obj := tool.Blender.get_active_object(is_selected=True)) and (element := tool.Ifc.get_entity(obj)):
    slab = obj
for obj in tool.Blender.get_selected_objects(include_active=False):
    element = tool.Ifc.get_entity(obj)
    usage = tool.Model.get_usage_type(element) if element else None
    if element and usage == "LAYER2":
        walls.append(obj)
if slab and walls:
    core.extend_wall_to_slab(tool.Ifc, tool.Geometry, tool.Model, slab, walls)
else:
    self.report({"ERROR"}, "Please select at least one LAYER2 element and an active element")
```

**Ours / HEAD (v0.8.0 + the two already-replayed branch commits):** identical to the merge-base **except** for the new resync call:
```python
if slab and walls:
    core.extend_wall_to_slab(tool.Ifc, tool.Geometry, tool.Model, slab, walls)
    _resync_walls_after_mutation(walls)   # ← added by v0.8.0 commit d7b5ac1453
```

**Theirs (branch commit 2e85a11c82):** generalized single underside → multiple undersides. Every selected non-LAYER2 object becomes a slab:
```python
slabs: list[bpy.types.Object] = []
walls: list[bpy.types.Object] = []
for obj in tool.Blender.get_selected_objects():
    element = tool.Ifc.get_entity(obj)
    if not element:
        continue
    if tool.Model.get_usage_type(element) == "LAYER2":
        walls.append(obj)
    else:
        slabs.append(obj)
if slabs and walls:
    core.extend_wall_to_slab(tool.Ifc, tool.Geometry, tool.Model, slabs, walls)
else:
    self.report({"ERROR"}, "Please select at least one LAYER2 element and at least one other IFC element")
```

## Resolution

The two sides expressed **independent intents**:

- The branch (theirs) restructured the selection loop to support **multiple** undersides (`slabs` list passed to `core.extend_wall_to_slab`).
- v0.8.0 (ours) appended a single new line — the **`_resync_walls_after_mutation(walls)`** post-mutation cleanup.

Neither supersedes the other, so I combined them: kept the branch's multi-slab loop and error message verbatim, and re-attached v0.8.0's resync call after the `core.extend_wall_to_slab(..., slabs, walls)` call. The resync helper takes the `walls` list, whose meaning is unchanged by the single→multiple-slab generalization, so it composes cleanly.

### Resolved `_execute`

```python
def _execute(self, context):
    # Match the sibling ops (UnjoinWalls / MergeWall / ExtendWallsToWall): if any
    # of the selected walls has an in-progress parametric draft, commit it before
    # extending, so the slab clip operates on the just-finalised IFC state.
    _commit_pending_wall_edits_for_selection(context)
    slabs: list[bpy.types.Object] = []
    walls: list[bpy.types.Object] = []
    for obj in tool.Blender.get_selected_objects():
        element = tool.Ifc.get_entity(obj)
        if not element:
            continue
        if tool.Model.get_usage_type(element) == "LAYER2":
            walls.append(obj)
        else:
            slabs.append(obj)
    if slabs and walls:
        core.extend_wall_to_slab(tool.Ifc, tool.Geometry, tool.Model, slabs, walls)
        _resync_walls_after_mutation(walls)
    else:
        self.report({"ERROR"}, "Please select at least one LAYER2 element and at least one other IFC element")
```

### Why this is correct

- **Branch intent preserved:** multiple undersides still work — all non-LAYER2 selected objects are collected into `slabs` and clipped against in one call.
- **v0.8.0 intent preserved:** walls are still re-synced after the mutation, exactly as `d7b5ac1453` intended for all six wired operators.
- The later branch commits (`acd62c59d0`, `4475111d0c`, `d6662e5c56`, `bfb4312906`) replayed cleanly on top of this resolution, and `wall.py` passes `python -m py_compile`.

## Verification

- `git log --oneline v0.8.0..HEAD` shows all **7** expected commits with `v0.8.0` (`431cf435ef`) as the new base.
- No conflict markers remain anywhere under `src/bonsai` or `src/ifcopenshell-python`.
- Resolved `wall.py` compiles cleanly.
- No stash was created (working tree was clean; the unrelated `slab_issues` stash was left untouched).

**Final branch tip:** [bfb4312906](https://github.com/IfcOpenShell/IfcOpenShell/commit/bfb4312906)
