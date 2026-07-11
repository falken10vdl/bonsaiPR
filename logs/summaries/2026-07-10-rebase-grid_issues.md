# Rebase Summary — `grid_issues` onto `v0.8.0`

**Branch:** [`grid_issues`](https://github.com/IfcOpenShell/IfcOpenShell/pull/7833) (PR #7833)
**Date:** 2026-07-10 19:24:52
**Base (`v0.8.0`) tip at rebase:** [`256d5a63f1`](https://github.com/IfcOpenShell/IfcOpenShell/commit/256d5a63f1)
**Merge-base before rebase:** `c026dd3b6e`
**Pre-rebase branch tip (`ORIG`):** `ec0f47c6b7`
**New branch tip (result):** [`60063ac1c7`](https://github.com/IfcOpenShell/IfcOpenShell/commit/60063ac1c7)
**Outcome:** conflicts-resolved (1 conflict, 1 file)

## Commits on `grid_issues` not in `v0.8.0`

5 linear commits, no merge commits (nothing flattened/dropped). Replayed in order:

| New hash | Old hash | Subject |
|----------|----------|---------|
| [`e70ce17431`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e70ce17431) | `f005b8192c` | Fix grid decorations missing due to geolocation offset |
| [`e609f10559`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e609f10559) | `db329cebbe` | Fix grid axis annotation misalignment when axis is moved |
| [`c0889c7f10`](https://github.com/IfcOpenShell/IfcOpenShell/commit/c0889c7f10) | `e62ab1848e` | Fix IfcGridAxis duplication losing geometry on save |
| [`f2d3e226b4`](https://github.com/IfcOpenShell/IfcOpenShell/commit/f2d3e226b4) | `d5e4ac0dd0` | Fix IfcGridAxis unlock not working in IFC4X3 |
| [`60063ac1c7`](https://github.com/IfcOpenShell/IfcOpenShell/commit/60063ac1c7) | `ec0f47c6b7` | Add tests for IfcGridAxis fixes |

## Divergence analysis

- Branch was 5 commits ahead of the merge-base.
- **Overlap files** (changed on *both* sides since the merge-base): `core/drawing.py`, `tool/collector.py`, `tool/drawing.py`, `tool/geometry.py`.
- Three of the four overlap files auto-merged cleanly (edits landed in different regions). Only `tool/geometry.py` conflicted.

### Submodule note

The working tree carried an uncommitted `simple_spf` submodule pointer bump to `9400d243d8`. `git stash` cannot capture gitlink changes (it reported "No local changes to save"), so it was left in place. As it happens, `v0.8.0` itself bumps `simple_spf` to that exact commit (`9400d243d8`), so after the rebase the pointer is the committed base value and the working tree is clean — nothing needed restoring.

## The conflict — `src/bonsai/bonsai/tool/geometry.py`

**Conflicting branch commit:** `e62ab1848e` → replayed as [`c0889c7f10`](https://github.com/IfcOpenShell/IfcOpenShell/commit/c0889c7f10) — "Fix IfcGridAxis duplication losing geometry on save".

**Cause on the base side:** [`8f3a1d7412`](https://github.com/IfcOpenShell/IfcOpenShell/commit/8f3a1d7412) ("Bonsai: batch array-duplicate + defensive guards") refactored `Geometry.duplicate_ifc_objects`, extracting the entire per-object loop body into a new helper classmethod `_duplicate_ifc_object_once(...)`. The branch commit, written against the pre-refactor inline loop body, added its grid-axis fix *inside that loop body* — which no longer exists on the base side — so the two edits collided over the whole loop region.

**What the branch commit intended:** immediately after `copy_class`, give each duplicated `IfcGridAxis` its own `AxisCurve` so duplicates don't share the source axis's `IfcPolyline`:

```python
# Give each duplicated IfcGridAxis its own AxisCurve so it doesn't
# share geometry with the source axis.
if new and new.is_a("IfcGridAxis"):
    tool.Model.create_axis_curve(new_obj, new)
```

(The commit's companion `not new.is_a("IfcGridAxis")` guard on the temp-data cleanup was *already* present at the merge-base and carried into `v0.8.0`'s helper, so it was context, not a new addition.)

**Resolution:** Keep the base side's refactored structure — the `duplicate_ifc_objects` loop stays as the single call to `cls._duplicate_ifc_object_once(...)` — and inject the branch's grid-axis block into the helper `_duplicate_ifc_object_once`, right after the `copy_class` call and before the temp-data cleanup (matching the exact position the branch used relative to `copy_class`).

**Why correct:**
- The base refactor supersedes the branch's inline loop structure; carrying forward the old inline body would have reintroduced a whole method the base deliberately moved. The branch's *net intent* for this file is a single block addition, confirmed by patch-id: the branch delta (`merge-base..ORIG`) and the resolved delta (`v0.8.0..HEAD`) are identical.
- The resolved `HEAD` vs `v0.8.0` diff for `geometry.py` is **exactly** the four-line grid-axis block and nothing else.
- The commit's other two fixes (`create_axis_curve.py` inverse-count guard, `export_ifc.py` moving the `IfcGridAxis` branch before the `is_moved` gate) live in non-overlap files and replayed without conflict.
- Bonus correctness: because the fix now lives in the shared helper `_duplicate_ifc_object_once`, it also applies to the base's batched array-duplicate caller — a strict superset of the original inline behaviour.

## Verification

- All 5 commits present in `v0.8.0..HEAD`.
- 3-way tree check: every file differing between `ORIG` and `HEAD` matches either the `v0.8.0` version or the `ORIG` version, **except** the 4 overlap files (expected — they combine both sides). For all four overlap files the branch delta is intact (patch-id of `merge-base..ORIG` == `v0.8.0..HEAD`).
- `python -m py_compile` passes on all 8 changed `.py` files.
- Working tree clean (submodule pointer resolved to base value).

## Files changed on the branch (for reference)

`export_ifc.py`, `module/spatial/prop.py`, `core/drawing.py`, `tool/collector.py`, `tool/drawing.py`, `tool/geometry.py`, `test/bim/feature/project.feature`, `api/grid/create_axis_curve.py`, `test/api/grid/test_create_axis_curve.py`.
