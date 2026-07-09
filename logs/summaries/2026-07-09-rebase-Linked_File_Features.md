<!-- This file was generated with the assistance of an AI coding tool. -->

# Rebase summary: `Linked_File_Features` onto `v0.8.0` (2026-07-09)

**Branch:** [`Linked_File_Features`](https://github.com/IfcOpenShell/IfcOpenShell/pull/8242) (PR #8242)
**Base:** `v0.8.0` at [9ae79b42dd](https://github.com/IfcOpenShell/IfcOpenShell/commit/9ae79b42dd)
**Pre-rebase tip:** [fa274ac07f](https://github.com/IfcOpenShell/IfcOpenShell/commit/fa274ac07f) · **Result tip:** [403308a923](https://github.com/IfcOpenShell/IfcOpenShell/commit/403308a923)
**Outcome:** conflicts-resolved (1 conflicting commit, 1 file hand-resolved)

## Branch commits replayed (9, no merges)

| old | new | subject |
|-----|-----|---------|
| 40db55e52d | a97276b8b1 | external styles + layerset slicing for linked models |
| d210d4c814 | 42a05cf976 | full Reload Link dialog |
| 3dc161f0f2 | 028e593939 | per-row lock toggle with auto-saved link transforms |
| 0571d22855 | cdb594b5c2 | Explore tool highlight + append placement fixes |
| c14592ec0a | 6d90048acd | per-query caches / multi-linking |
| f6cec0c9a5 | 5ea11817ad | dev-notes |
| ee43ed5526 | cf58c675db | match linked documents by resolved path |
| 1669cbcd43 | 236da3c75a | draw moved and multi-linked models (CONFLICT) |
| fa274ac07f | 403308a923 | keep linked models cut linework in BISECT cut mode |

The merge-base was the branch's own first commit (`0096c0f6a2`, the reload_link query
fix), which had already landed in upstream `v0.8.0`. The base advanced 45 commits since.
The branch is linear (no merge commits), so nothing was flattened or dropped.

## Overlap files (both sides changed since merge-base)

- `src/bonsai/bonsai/bim/module/drawing/operator.py` — **conflicted**, hand-resolved
- `src/bonsai/bonsai/bim/module/project/operator.py` — auto-merged (different regions)
- `src/bonsai/bonsai/tool/loader.py` — auto-merged (different regions)

## The conflict: two independent implementations of moved-link drawing

Upstream [5db955d40c](https://github.com/IfcOpenShell/IfcOpenShell/commit/5db955d40c)
("Apply link matrix when serialising linked drawings", Bruno Postle, 2026-07-03)
independently implemented the same feature as the branch's
[1669cbcd43 → 236da3c75a](https://github.com/IfcOpenShell/IfcOpenShell/commit/236da3c75a):
baking a linked model's transformation into the SVG serializer via
`model-offset`/`model-rotation`. The two collided in `serialize_contexts_elements`
(signature + offset/rotation block) and in `CreateDrawing`'s file loop.

**Resolution: the branch version supersedes upstream's**, for three reasons:

1. **Coordinate space.** Upstream feeds `tool.Project.calculate_link_matrix(link)` —
   the link empty's *Blender-world* matrix (`inv(L) @ T @ G`), additionally divided by
   `unit_scale` — into `model-offset`. The serializer applies the offset in model-space
   SI meters (the pre-existing 2mm Z-offset passes `0.002` unscaled), so the correct
   input is the raw stored transformation `T` (model-space delta, already SI), which is
   what the branch's `tool.Project.get_link_transformation_matrix(link)` provides.
   Upstream's version conflates the host's Blender offset/georeferencing into the
   geometry offset and double-converts units on non-metric projects.
2. **Same-file multi-links.** Upstream keys files in a dict by `link.filepath`,
   collapsing several links of the same file into one pass with one matrix. The branch
   iterates one entry per link (`(path, file, transform, query)` tuples).
3. **Per-link queries.** The branch intersects each link's drawing elements with its
   selector query, so drawings show what each link displays in the viewport.

Upstream's second change to the file,
[1614791775](https://github.com/IfcOpenShell/IfcOpenShell/commit/1614791775)
("Fix SHAPELY fill mode dropping surface fills for all but the last linked file"),
is orthogonal and was **kept**: its cross-file `raycast_objs`/`elements_with_faces`
accumulators (initialised before the file loop, consumed by the post-loop SHAPELY fill
pass) were combined with the branch's per-link loop header. Its in-loop fill collection
now also benefits from the branch's per-link query filtering.

Region-by-region resolution in `drawing/operator.py`:

| region | resolution |
|--------|------------|
| `serialize_contexts_elements` signature | branch (`link_transform: Optional[np.ndarray]`) |
| offset/rotation block | branch (numpy offset accumulation; z-offset adds onto translation) |
| `files` dict init | branch (removed; `file_entries` list follows) |
| link collection loop | branch (`file_entries.append(...)` with transform + query) |
| file loop header | **combined**: upstream's SHAPELY accumulators + branch's `for ifc_path, ifc, link_transform, link_query in file_entries:` |
| serialize calls | branch (pass `link_transform`) |

## Auto-merged overlaps (verified)

- `project/operator.py`: upstream [e0a1988044](https://github.com/IfcOpenShell/IfcOpenShell/commit/e0a1988044)
  (IfcRelAdheresToElement / IfcSurfaceFeature import, +5 lines) merged beside the
  branch's link work; both verified present.
- `tool/loader.py`: upstream texture commits (6dafb7a5c2 `check_existing=True`,
  4cedeec813, 9bbd2b1854) merged beside the branch's `slice_layerset_mesh`
  `style_to_material` refactor; both verified present.

## Verification

- 3-way classification of every file differing from the pre-rebase tip: all matched
  the `v0.8.0` version (upstream advancement picked up by the rebase) except exactly
  the three overlap files, which combine both sides as intended.
- `python -m py_compile` passed on every changed `.py` file.
- Branch diff vs base spans exactly the branch's 8 feature files.

## Result

New tip: [403308a923](https://github.com/IfcOpenShell/IfcOpenShell/commit/403308a923).
**Not yet force-pushed** — `origin/Linked_File_Features` still points at the pre-rebase
tip `fa274ac07f`; commit links above go live once the branch is published
(`git push --force-with-lease origin Linked_File_Features`).
