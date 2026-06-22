# Rebase Summary — duplicate_opening_on_type_duplication onto v0.8.0

**Date:** 2026-06-22 13:27:03
**Branch:** [duplicate_opening_on_type_duplication](https://github.com/IfcOpenShell/IfcOpenShell/tree/duplicate_opening_on_type_duplication)
**Base:** `v0.8.0` @ [3c9ee4a71f](https://github.com/IfcOpenShell/IfcOpenShell/commit/3c9ee4a71f)
**Result tip:** [ba4a94dfea](https://github.com/IfcOpenShell/IfcOpenShell/commit/ba4a94dfea)
**Outcome:** conflicts-resolved (large, heavily-duplicated history)

> No GitHub PR was found for this branch (`gh` CLI unavailable on this machine), so the
> branch name links to the branch tree on GitHub.

## Overview

This is a large feature branch (general-mirroring + the #6392 "duplicate opening on type
duplication" fix) whose history is **heavily tangled**: it repeatedly absorbed the
upstream `general-mirroring` work via `git merge` "absorb" commits, so the same logical
commits (e.g. *"Added tool.Blender.Modifier.has_mirrored_type"*, *"Doors are now placed on
the side of the wall that was snapped to"*) appear **5–6 times** across the branch.

- Merge-base with `v0.8.0`: [855de34d22](https://github.com/IfcOpenShell/IfcOpenShell/commit/855de34d22)
- Commits ahead of merge-base: **145**
- Commits git tried to replay: **143** (2 immediately recognised as already-applied)
- Commits in the final rebased range (`v0.8.0..HEAD`): **100** (43 dropped during replay as
  duplicate/empty)

## Key insight that drove the resolution strategy

The branch touches 295 files vs. merge-base, but only **24** of those are also touched by
`v0.8.0` since the merge-base (the true *overlap* set — the only files where v0.8.0's work
and the branch's work genuinely collide). Crucially:

- **Non-overlap files** (`v0.8.0` never changed them since the fork): a correct rebase must
  reproduce the **branch tip** content exactly, because the base content for those files is
  identical to the merge-base. The conflicts on these files arise purely from the branch's
  *internal* duplicated history, not from v0.8.0.
- The branch's absorb-merges pulled in a lot of **incidental cross-feature / C++ content**
  (ifcgeom, serializers, ifcparse, tests, `core/tool.py` stubs like `Connection`,
  `recreate_wall`). `git rebase` flattens history and **drops merge commits**, so this
  absorbed content correctly reverts to `v0.8.0` — which is exactly what we want for a
  v0.8.0 rebase. 251 files ended at v0.8.0's version for this reason.

So the resolution rule was:
1. **Overlap files** → hand-resolve to combine v0.8.0 + branch intent.
2. **Non-overlap files that conflicted** → resolve to the branch-tip version (the provably
   correct clean-rebase target).

## Conflicts and resolutions

### Overlap files (hand-resolved)

| File | Resolution |
|------|------------|
| [`src/bonsai/bonsai/tool/blender.py`](https://github.com/IfcOpenShell/IfcOpenShell/blob/ba4a94dfea/src/bonsai/bonsai/tool/blender.py) | `v0.8.0` commit [e0ceda6856](https://github.com/IfcOpenShell/IfcOpenShell/commit/e0ceda6856) *("Hide wall topology gizmos on array children")* added `any_selected_is_array_child` + `_any_selected_array_child_memo` to `tool.Blender.Modifier` at the exact spot the branch inserts `has_mirrored_type`/`set_mirrored_type`. **Kept both** — v0.8.0's array-child gizmo gate and the branch's mirror-type accessors. (Hit twice, in duplicate generations; resolved identically.) |
| [`src/bonsai/bonsai/tool/model.py`](https://github.com/IfcOpenShell/IfcOpenShell/blob/ba4a94dfea/src/bonsai/bonsai/tool/model.py) | A branch commit added `should_reload=True, is_global=False, should_sync_changes_first=False` kwargs to a `switch_representation(...)` call. The **branch tip itself no longer has these kwargs** (a later branch commit reverted them — intra-branch supersession), so kept HEAD's kwarg-free call, which matches both v0.8.0 and the branch tip. |

The other 22 overlap files (clip_box module, handler.py, wall.py, slab.py, project/*, etc.)
auto-merged cleanly — git combined v0.8.0 and branch changes with no markers.

### Non-overlap files (resolved to branch-tip)

These conflicted only because of the branch's duplicated internal history. Each was
resolved to its branch-tip content, which is the correct clean-rebase target:
`opening.py`, `polyline.py`, `workspace.py`, `product.py`, `door.py`, `shape_builder.py`,
`tool/root.py`, `geometry/operator.py`, `material/operator.py`.

Representative supersession cases that confirmed "resolve to tip" was right:
- **polyline.py** — an early generation added an `invert_x` door-preview correction; a later
  *"Made door / window preview both simpler and more intuitive"* commit removed it. Tip has
  no `invert_x`.
- **workspace.py** — an intermediate *ChangeSwingDirection* feature (`S_C_F` hotkey +
  `change_swing_direction()`) was added then **fully removed** by later branch commits; the
  tip has neither the keymap entry, the handler, nor the operator. Confirmed `git grep` on
  HEAD finds no `ChangeSwingDirection`/`change_swing_direction`.
- **door.py** — an intermediate `_finish_one`/`_finish_targets` classmethod approach was
  superseded by the `finish_editing_door_on_object` instance-method approach in the tip.

### Post-rebase reconciliation

Because the non-overlap conflicts were initially resolved by checking out the tip version
*mid-rebase*, three feature files (`opening.py`, `product.py`, `workspace.py`) were left in a
broken intermediate state after subsequent duplicate commits re-applied patches on top
(e.g. workspace.py ended up with a **duplicated `draw_mirror_geometry` method** and a lost
`keep_original` argument; product.py deviated by 113 lines). Since `git log --merges`
confirmed **no merge commit touches these three files** (their entire delta is linear
feature work), the branch tip is the definitive correct content. They were reset to the
branch-tip version and folded into the final commit via `--amend`.

`core/tool.py` was **left as the rebase produced it** (it was never hand-touched): its only
v0.8.0→HEAD delta is the legitimate `def has_material_styles(...)` interface stub, while the
tip's extra `Connection`/`recreate_wall`/`strip_underside_booleans` stubs are absorbed
cross-feature content the rebase correctly dropped.

## Verification

- `git log --oneline v0.8.0..HEAD` → 100 commits; the #6392 fix commit
  [6441c39c4e](https://github.com/IfcOpenShell/IfcOpenShell/commit/6441c39c4e) is present.
- No conflict markers remain in any tracked file.
- `python -m py_compile` passed on all 21 changed `.py` files.
- Structural tree analysis (HEAD vs `v0.8.0` vs branch-tip):
  - Files differing from tip where `HEAD != v0.8.0` reduce to exactly the 4 overlap files
    (`blender.py`, `tool/model.py`, `model/__init__.py`, `project/operator.py`) + the
    legitimate `core/tool.py` linear delta. Everything else either matches the tip (feature
    work intact) or matches `v0.8.0` (absorbed merge content correctly dropped).
  - `mirror_geometry` operator present (`product.py`); `ChangeSwingDirection` correctly
    absent (superseded in branch).
- Working tree clean apart from untracked `bonsai_clipboard.{ifc,json}` runtime files.

## Final branch tip

[ba4a94dfea](https://github.com/IfcOpenShell/IfcOpenShell/commit/ba4a94dfea)
