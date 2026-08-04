# Rebase: parametric_dimensions → v0.8.0 (2026-08-04)

**Branch:** [parametric_dimensions](https://github.com/IfcOpenShell/IfcOpenShell/pull/8083)
**Base commit:** [6f3acc84ee](https://github.com/IfcOpenShell/IfcOpenShell/commit/6f3acc84ee) (`v0.8.0` tip at time of rebase)
**Pre-rebase tip:** `a26eb38f1c` (local; 6 commits ahead of `origin/parametric_dimensions`)
**Result commit:** `a27c9ef01c` *(links pending push)*
**Outcome:** conflicts-resolved

---

## Commits on branch not in v0.8.0 (52 linear, 3 merge commits dropped)

The branch had 55 commits beyond the merge-base (`93c6350e0f`). Three were merge commits (dropped by rebase):
- `456d2ae501` — ancestry-merge for PR #7965 (`inset_section_endpoints`)
- `23fd50eace` — ancestry-merge for PR #7798
- `738110bd7d` — ancestry-merge for `parametric_dimensions` itself (PR #8083)

One commit was auto-dropped as already upstream (`4ab04d4926 spread out gizmo arrows`).

**Replayed (44 commits in final log):**

The 52 linear commits fall into three groups:

1. **Manual drawing reference feature** (9 commits, `7ab7f02db2` – `c1d4494a64`): `IsManualDrawingReference`, annotation operator, `AssignManualDrawingReference`, integration, `ElevationDecorator` fix, non-plan-view fix, searchable drawing selector, external SVG support, Auto-snap SECTION endpoints.

2. **OLD duplicate parametric dimension commits** (13 commits, `e5116732d0` – `913c9c42ba`): These entered the branch via the `738110bd7d` ancestry-merge second parent. The rebase replays them as linear commits, causing all the conflicts (they patch against an old merge-base that no longer matches `v0.8.0`).

3. **NEW/unique parametric dimension commits** (30 commits): multi-units, SuppressZeroFeet, ordinate, BBIM_DimensionTarget, DrawParametricDimension operator, ForcePerpendicularToFace, LinePosition, gizmo dots, anchor click fixes, TAB snap cycling, optimizations, coplanar face snap, SetDimensionAnchor improvements, BakeParametricDimension, PLAN_LEVEL/SECTION_LEVEL annotation placement, bug fixes, camera-relative snapping, stale cache fix, LinePosition section fix.

---

## Conflict files and resolutions

### Overall strategy

The 13 OLD duplicate commits caused the vast majority of conflicts. Since each OLD commit has a newer counterpart (in group 3) that will be replayed later on top of a clean `v0.8.0` state, the correct strategy was:

- **Overlap files** during OLD duplicate commits → **`--ours` (keep HEAD)**: makes the OLD duplicate a no-op, letting the NEW version apply its patch correctly.
- **Non-overlap files** during OLD/NEW commits → **ORIG tip** (`a26eb38f1c`): `v0.8.0` didn't change them, so their correct state is exactly the branch tip.

### Hand-resolved conflicts (commit `e5116732d0` — closes #8060: multi-units)

**`src/bonsai/bonsai/bim/module/drawing/decoration.py`** (overlap)

Three conflict zones:
1. `ordinate_total` tracking block — HEAD (from v0.8.0 which merged an earlier branch version) had ordinate support; `e5116732d0` predated this. **Kept HEAD** (preserves ordinate logic).
2. `suppress_zero_feet=dimension_data["suppress_zero_feet"]` kwarg — HEAD had it; `e5116732d0` didn't. **Kept HEAD**.
3. Radius annotation `format_value` call — same pattern. **Kept HEAD**.

**`src/bonsai/bonsai/bim/module/drawing/svgwriter.py`** (overlap)

Five conflict zones — all the same pattern: HEAD had `distance_override` parameter, `suppress_zero_feet` kwarg, and `distance_override`-aware dimension calculation; `e5116732d0` predated all three. **Kept HEAD** in all zones.

**`src/bonsai/bonsai/bim/data/pset/Psets_BBIM_Annotation.ifc`** (non-overlap)

Conflicted in every OLD duplicate commit (14 times total) because each OLD commit patched the file to an intermediate state. `v0.8.0` didn't touch this file. **Used ORIG tip** (`a26eb38f1c`) each time.

**`src/bonsai/bonsai/bim/module/drawing/data.py`** (non-overlap)

Conflicted during SuppressZeroFeet OLD commit. **Used ORIG tip**.

### `--ours` overlap files (all OLD duplicate commits)

These files are in the overlap set (both `v0.8.0` and the branch changed them):

- `src/bonsai/bonsai/bim/module/drawing/__init__.py`
- `src/bonsai/bonsai/bim/module/drawing/handler.py`
- `src/bonsai/bonsai/bim/module/drawing/operator.py`
- `src/bonsai/bonsai/bim/module/drawing/prop.py`
- `src/bonsai/bonsai/bim/module/drawing/workspace.py`
- `src/bonsai/bonsai/bim/module/drawing/gizmos.py`
- `src/bonsai/bonsai/bim/module/pset/operator.py`
- `src/bonsai/bonsai/tool/drawing.py`

`v0.8.0` added `CopyAnnotationToDrawing`, edge-classification settings, category-level select-all, and other drawing UI improvements to these files. The branch added the entire `DrawParametricDimension` operator, anchor gizmos, `LinePosition` gizmo, depsgraph handler, etc.

The `--ours` (HEAD) strategy during OLD duplicates ensured `v0.8.0`'s state was preserved. The NEW version commits (group 3) then applied their complete patches cleanly on top of `v0.8.0`'s state, giving the correct combined result.

### Non-overlap NEW files (ORIG tip)

- `src/ifcopenshell-python/ifcopenshell/api/drawing/__init__.py`
- `src/ifcopenshell-python/ifcopenshell/api/drawing/regenerate_dimension.py`
- `src/ifcopenshell-python/ifcopenshell/api/drawing/resolve_anchor.py`

These were added by the branch and not present in `v0.8.0`. Add/add conflicts occurred because the OLD ordinate duplicate (`bea4f2c364`) replayed before BBIM_DimensionTarget (`d71b3de87c`) due to commit topology, adding these files first. **Used ORIG tip** to ensure the final camera-aware version of `regenerate_dimension.py` was used throughout.

---

## Step 6 verification

**Commit count:** 44 commits replayed on top of `v0.8.0` (from 52 linear: 1 auto-dropped as upstream-identical, 7 additional dropped as empty/duplicate).

**3-way tree check:** `SCRUTINIZE` set = exactly the 17 overlap files. All other changed files matched either `v0.8.0` tip (absorbed content correctly dropped) or ORIG tip (feature work intact). No unexpected artifacts.

**py_compile:** 22 changed `.py` files, 0 syntax errors.

**Spot-check:** `operator.py` has both `CopyAnnotationToDrawing` (v0.8.0 feature) and `camera_dir` threading (branch feature). `regenerate_dimension.py` has `camera_dir` parameter. `handler.py` has `cam_dir_tuple` computation.

---

## Key v0.8.0 commit

[`bc1fb2a88d`](https://github.com/IfcOpenShell/IfcOpenShell/commit/bc1fb2a88d) — add one-click copy of annotations to another drawing (#8719). Primary contributor to operator.py overlap conflicts.
