# Rebase Summary — `print_ifcspaces_in_projection` onto `v0.8.0`

- **Branch:** [`print_ifcspaces_in_projection`](https://github.com/IfcOpenShell/IfcOpenShell/pull/7858) (PR #7858 — "Fix #6602: Print IfcSpaces in projection.")
- **Base:** `v0.8.0` @ [`256d5a63f1`](https://github.com/IfcOpenShell/IfcOpenShell/commit/256d5a63f1)
- **Merge-base (before rebase):** `dae913e06a`
- **Pre-rebase tip (`ORIG`):** `3538a72de5`
- **Result tip:** [`f5c22d97e9`](https://github.com/IfcOpenShell/IfcOpenShell/commit/f5c22d97e9)
- **Date:** 2026-07-10 22:45:21
- **Outcome:** conflicts-resolved (1 conflict, 1 auto-merge)

## Commits on the branch (not in `v0.8.0`)

A single linear commit, no merge commits:

- `3538a72de5` — **Show IfcSpace in projection drawings**

  Previously `IfcSpace` was excluded from `get_drawing_elements()` and handled via a
  separate special-case path (`get_drawing_spaces()`). The commit removes that special case:
  spaces are folded into the standard element set and rendered in `generate_bisect_linework()`
  alongside other elements, with back-face-culled / crease-angle-filtered projected edges for
  spaces that don't intersect the cut plane. It also adds `.IfcSpace.projection` CSS rules to
  `default.css` and `sample.css` to override the existing `fill:none`.

  Files touched: `tool/drawing.py`, `bim/module/drawing/operator.py`,
  `bim/data/assets/default.css`, `bim/data/assets/sample.css`.

Replayed to `f5c22d97e9` (1 commit → 1 commit; nothing dropped).

## Overlap analysis

Files changed on **both** sides since the merge-base (the only candidates for a
judgment-requiring conflict):

- `src/bonsai/bonsai/tool/drawing.py` — **conflicted** (hand-resolved)
- `src/bonsai/bonsai/bim/module/drawing/operator.py` — **auto-merged** (disjoint regions)

The two CSS files are non-overlap (only the branch touched them); they carried through
identically (`git diff ORIG HEAD` shows no change), so they never appeared in the
end-state scrutiny set.

## The conflict — `tool/drawing.py`

### What each side did

`get_drawing_elements()` in the **merge-base** opened with:

```python
if ifc_file is None:
    ifc_file = tool.Ifc.get()
    elements = cls.get_elements_in_camera_view(tool.Ifc.get_object(drawing), bpy.data.objects)
else:
    # This can probably be smarter
    elements = set(ifc_file.by_type("IfcElement"))
...
    elements = {e for e in (elements & base_elements) if e.is_a() != "IfcSpace"}
```

**`v0.8.0` side** — commit [`315835063c`](https://github.com/IfcOpenShell/IfcOpenShell/commit/315835063c)
("Fix #8225: Respect camera boundary for Include filter") refactored the function: it
introduced `param_was_none = ifc_file is None`, hoisted the camera-view lookup into a
deferred `camera_view_elements` computed once (so an `Include` filter is also clipped to the
camera boundary), and **deleted the inline `elements = get_elements_in_camera_view(...)` +
`else` block**, moving the element-set selection further down into a new `if include: … else: …`
structure. It kept `elements = set(ifc_file.by_type("IfcElement"))` and the
`!= "IfcSpace"` filter unchanged.

**Branch side** — commit `3538a72de5` edited that *same original* if/else block: it made the
passed-`ifc_file` `elements` set schema-aware (adding `IfcSpatialElement` /
`IfcSpatialStructureElement`) and removed the `!= "IfcSpace"` filter, plus dropped
`| cls.get_drawing_spaces(drawing)` in the caller.

Because `v0.8.0` deleted/relocated the exact block the branch modified, git could not
auto-merge and produced one conflict hunk (the branch's version of the old block vs. `v0.8.0`'s
empty/relocated version).

### Resolution

Kept `v0.8.0`'s refactor wholesale (`param_was_none`, `camera_view_elements`, the
`Include`-filter camera-boundary intersection) and re-applied the branch's **intent** at the
new locations in that structure:

1. In the passed-`ifc_file` `else` branch, make the initial `elements` set schema-aware:
   ```python
   else:
       # This can probably be smarter
       if ifc_file.schema == "IFC2X3":
           elements = set(ifc_file.by_type("IfcElement") + ifc_file.by_type("IfcSpatialStructureElement"))
       else:
           elements = set(ifc_file.by_type("IfcElement") + ifc_file.by_type("IfcSpatialElement"))
   ```
   (Required: the set is subsequently intersected with `base_elements`, so if it only held
   `IfcElement`, spaces would still be filtered out.)
2. Drop the `IfcSpace` exclusion: `elements = elements & base_elements`.
3. The caller change (`filtered_elements = cls.get_drawing_elements(drawing)`, dropping
   `| cls.get_drawing_spaces(drawing)`) applied cleanly and was left as-is.

The `!= "IfcSpace"`→`&` change (2) and the caller change (3) actually applied without
conflict during the replay; only intent (1) had to be re-injected by hand because its
context lived in the deleted block.

### Why this is correct

`git diff v0.8.0 HEAD -- tool/drawing.py` reduces to exactly the three branch intents and
nothing else, confirming `v0.8.0`'s refactor is preserved intact while the branch's feature
(spaces in projection) is fully applied.

## The auto-merge — `drawing/operator.py`

`v0.8.0` changed `operator.py` (+76/−31) and the branch rewrote `generate_bisect_linework`
(+69/−26), but in **disjoint regions**, so git auto-merged. Verified by comparing
`git diff v0.8.0 HEAD` against `git diff <merge-base> ORIG` for the file: the two diffs are
identical apart from `@@` hunk-header offsets and index hashes — i.e. the branch's patch was
reproduced verbatim on top of `v0.8.0`'s changes, and both sides' edits are present.

## Verification

- No conflict markers anywhere in the tree.
- End-state 3-way classification: every file differing between `ORIG` and `HEAD` matches
  either the `v0.8.0` version (the release advancement) or is one of the two overlap files;
  the `SCRUTINIZE` set reduced to exactly `tool/drawing.py` and `drawing/operator.py`, both
  inspected above.
- `python -m py_compile` passes on both changed `.py` files.

## Final branch tip

`f5c22d97e9f49863ee4d592b769fd860dec95ffc`
