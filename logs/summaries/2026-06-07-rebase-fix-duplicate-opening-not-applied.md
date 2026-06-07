# Rebase Summary — fix/duplicate-opening-not-applied onto v0.8.0

**Date:** 2026-06-07 18:10:24
**Branch:** [fix/duplicate-opening-not-applied](https://github.com/IfcOpenShell/IfcOpenShell/tree/fix/duplicate-opening-not-applied)
**Base:** `v0.8.0` @ [93c6350e0f](https://github.com/IfcOpenShell/IfcOpenShell/commit/93c6350e0f25557d15debb29a515fc62b16f49de)
**Result tip:** [bd934d9b8e](https://github.com/IfcOpenShell/IfcOpenShell/commit/bd934d9b8e)
**Outcome:** conflicts-resolved (1 conflict, 1 file)

> No GitHub PR was found for this branch (`gh` CLI unavailable on this machine), so the branch
> name links to the branch tree on GitHub. The commit message references issue **#7948**.

## Commits on the branch not in v0.8.0

A single commit was rebased:

- [bd934d9b8e](https://github.com/IfcOpenShell/IfcOpenShell/commit/bd934d9b8e) — *Fix #7948: Fix duplicate not applying openings to geometry*
  (was `73da47ece2` before the rebase)

The merge-base with `v0.8.0` was [32a7de66de](https://github.com/IfcOpenShell/IfcOpenShell/commit/32a7de66de41dae1891f018e345f19b1c9b07906).

### What the branch commit does

When duplicating an element that has `HasOpenings`, `copy_class` (API) correctly copies the
`IfcRelVoidsElement` into IFC, but the new object's Blender mesh was never regenerated — it was
just a data-block copy of the original, so the opening void was not subtracted from the duplicate's
geometry. The fix adds a loop after decomposition recreation that calls
`tool.Model.reload_body_representation` on any newly-created element that has **unfilled** openings
(filled openings are already handled by `recreate_decompositions`), forcing the opening boolean to
be computed for the duplicated geometry.

## Conflicts

### `src/bonsai/bonsai/tool/geometry.py`

One conflict, in `Geometry.duplicate_objects` (around the "Recreate decompositions" block).

**Why it conflicted:** Both sides edited the same line. At the merge-base the code read:

```python
tool.Root.recreate_decompositions(decomposition_relationships, old_to_new)
```

- **`v0.8.0` side (HEAD):** commit
  [3483683cb4](https://github.com/IfcOpenShell/IfcOpenShell/commit/3483683cb4)
  *("Add tool.Geometry helpers for body representation + placement")* renamed the call's namespace
  from `tool.Root` to `tool.Duplicate`:
  ```python
  tool.Duplicate.recreate_decompositions(decomposition_relationships, old_to_new)
  ```
  This is consistent with the neighbouring `tool.Duplicate.recreate_connections(...)` and
  `tool.Duplicate.recreate_port_connections(...)` calls already present just above.

- **Branch side (theirs):** the commit was authored against the older `tool.Root` namespace and
  *appended* the new unfilled-opening reload loop immediately after that line.

Because both sides touched the same line (rename vs. append-after), git could not auto-merge.

**Resolution:** Keep `v0.8.0`'s renamed call `tool.Duplicate.recreate_decompositions(...)` (the
namespace move is the current, correct API — `tool.Duplicate.recreate_decompositions` exists and is
the convention used by adjacent calls) **and** keep the branch's new opening-reload loop appended
after it. The stale `tool.Root.recreate_decompositions` form from the branch was discarded; its
intent (recreate decompositions) is fully preserved by the `tool.Duplicate` equivalent.

The final resolved block:

```python
tool.Duplicate.recreate_decompositions(decomposition_relationships, old_to_new)

# Reload geometry for duplicated elements that have unfilled openings.
# copy_class (API) copies HasOpenings in IFC, but the mesh geometry is
# just a data-block copy of the original — switch_representation must be
# called so the opening boolean is actually computed for the new element.
for new_els in old_to_new.values():
    for new_el in new_els:
        has_openings = getattr(new_el, "HasOpenings", None)
        if not has_openings:
            continue
        # Only reload for openings that have no filling (filled openings
        # are already handled by recreate_decompositions).
        unfilled = [rel for rel in has_openings if not rel.RelatedOpeningElement.HasFillings]
        if not unfilled:
            continue
        new_obj_final = tool.Ifc.get_object(new_el)
        if new_obj_final:
            tool.Model.reload_body_representation(new_obj_final)
```

## Verification

- `git log --oneline v0.8.0..HEAD` shows exactly the single expected commit (`bd934d9b8e`).
- `python -m py_compile src/bonsai/bonsai/tool/geometry.py` passed (the only overlap file).
- Working tree clean after rebase.
- The rebased commit diff is a clean +19-line addition (the reload loop); no namespace change
  leaks into the diff because the resolved call already matches `v0.8.0`.
