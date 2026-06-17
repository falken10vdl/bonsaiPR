# Rebase summary — drawing_render_overrides onto v0.8.0

**Branch:** [`drawing_render_overrides`](https://github.com/IfcOpenShell/IfcOpenShell/pull/8171)
**Date:** 2026-06-17 12:49:53
**Base (`v0.8.0`) tip at rebase:** [`855de34d22`](https://github.com/IfcOpenShell/IfcOpenShell/commit/855de34d22) — *Introduce unique error codes* line
**Merge-base before rebase:** [`a751fb956d`](https://github.com/IfcOpenShell/IfcOpenShell/commit/a751fb956d) — *Introduce unique error codes* (an ancestor of `v0.8.0`)
**Result tip:** [`f9ac17e759`](https://github.com/IfcOpenShell/IfcOpenShell/commit/f9ac17e759)
**Outcome:** conflicts-resolved (1 conflict, 1 file)

## Commits on the branch (not in v0.8.0)

The branch was 2 commits ahead of the merge-base; both replayed onto `v0.8.0`:

1. [`847bb90886`](https://github.com/IfcOpenShell/IfcOpenShell/commit/847bb90886) — **Add per-drawing render overrides (status_render module)**
   New `bim/module/status_render/` module (per-drawing render-override rules:
   filter-selected elements get exposure/gamma via a Cryptomatte-masked compositor
   graph, and transparency via a live Transparent-BSDF material). Also edits:
   `bim/__init__.py` (register module), `bim/data/pset/EPset_Drawing.ifc`
   (`RenderOverrides` pset template), `tool/search.py` and `module/search/operator.py`
   (per-rule filter resolver + `on_filter_query_edited` dispatch + empty-query handling).
2. [`f9ac17e759`](https://github.com/IfcOpenShell/IfcOpenShell/commit/f9ac17e759) — **Group Active Drawing controls into a collapsible "Drawing Settings" section**
   Wraps the `BIM_PT_camera` controls in a collapsible `layout.panel`. Touches only
   `bim/module/drawing/ui.py`.

## Pre-rebase overlap analysis

Files touched by the branch since the merge-base intersected with files touched by
`v0.8.0` since the merge-base = **only** `src/bonsai/bonsai/bim/__init__.py`. That was
the sole conflict candidate, and the sole actual conflict.

## Conflict and resolution

### `src/bonsai/bonsai/bim/__init__.py` (in commit `847bb90886`)

- **v0.8.0 change that caused it:** [`6147a58d7a`](https://github.com/IfcOpenShell/IfcOpenShell/commit/6147a58d7a) *"Add viewport clip-box feature"* added `"clip_box": None` to the `modules` dict immediately after `"alignment": None`.
- **Branch change:** the status_render commit added `"status_render": None` in that same spot (its base lacked `clip_box`, so the added line landed right after `"alignment"`).
- **3-way picture:** ancestor had `"alignment"` directly followed by the `# Uncomment … demo` comment; `v0.8.0` (ours) inserted `clip_box` there; the branch (theirs) inserted `status_render` there → both sides added a different line at the same location.
- **Resolution:** kept **both** entries, in order:
  ```python
      "alignment": None,
      "clip_box": None,
      "status_render": None,
      # Uncomment this line to enable loading of the demo module. …
  ```
  Correct because the two additions are independent module registrations; neither
  supersedes the other, and both modules must load. (Note: `v0.8.0` had also dropped
  `clipboard`, `cadsketcher`, and `license` from this dict relative to the old base —
  those are absorbed automatically by rebasing onto `v0.8.0` and were not part of the
  conflict.)

The second commit (`f9ac17e759`, drawing UI) applied cleanly — `v0.8.0` had not touched
`bim/module/drawing/ui.py` since the merge-base.

## Verification

- `git log --oneline v0.8.0..HEAD` shows exactly the two expected commits.
- Working tree clean (only untracked runtime files `bonsai_clipboard.*`).
- `python -m py_compile` passed for `bim/__init__.py` (the overlap file) plus all changed
  files: `bim/module/drawing/ui.py`, `tool/search.py`, `bim/module/search/operator.py`,
  and the `status_render` module.

## Final branch tip

[`f9ac17e759`](https://github.com/IfcOpenShell/IfcOpenShell/commit/f9ac17e759)
(not yet force-pushed — Step 9 pending explicit confirmation).
