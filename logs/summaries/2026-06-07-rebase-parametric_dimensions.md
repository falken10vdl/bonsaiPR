# Rebase Summary: parametric_dimensions onto v0.8.0

**Date:** 2026-06-07 17:54:02
**Branch:** [parametric_dimensions](https://github.com/IfcOpenShell/IfcOpenShell/tree/parametric_dimensions)
**Base:** v0.8.0 @ [93c6350e0f](https://github.com/IfcOpenShell/IfcOpenShell/commit/93c6350e0f25557d15debb29a515fc62b16f49de)
**Outcome:** clean (no conflicts)
**Result commit:** [76e390f820](https://github.com/IfcOpenShell/IfcOpenShell/commit/76e390f820)

---

## Commits on `parametric_dimensions` not in `v0.8.0` (16 unique, after skips)

| Hash | Message |
|------|---------|
| [76e390f820](https://github.com/IfcOpenShell/IfcOpenShell/commit/76e390f820) | Improve SetDimensionAnchor snap: hover indicator, visibility, face outline |
| [631881932d](https://github.com/IfcOpenShell/IfcOpenShell/commit/631881932d) | Fix coplanar face snap: correct bbox check, on-edge detection, and ForcePerpendicularToFace |
| [a08679ed5d](https://github.com/IfcOpenShell/IfcOpenShell/commit/a08679ed5d) | Snap coplanar edge-on faces in FACE/LAYER mode for DrawParametricDimension |
| [f55c86aa6f](https://github.com/IfcOpenShell/IfcOpenShell/commit/f55c86aa6f) | Optimize DrawParametricDimension startup and MOUSEMOVE performance |
| [6a2cd1d976](https://github.com/IfcOpenShell/IfcOpenShell/commit/6a2cd1d976) | spread out gizmo arrows |
| [0753be2186](https://github.com/IfcOpenShell/IfcOpenShell/commit/0753be2186) | Add TAB snap cycling, snap decorators, and fix anchor dot activation for DrawParametricDimension |
| [a58e4d3b72](https://github.com/IfcOpenShell/IfcOpenShell/commit/a58e4d3b72) | Fix anchor click, undo, layer regen, and ForcePerpendicularToFace for layer anchors |
| [1a9332c00e](https://github.com/IfcOpenShell/IfcOpenShell/commit/1a9332c00e) | Add anchor gizmo dots, keymap click handler, and auto-sync for parametric dimensions |
| [c03afd33fa](https://github.com/IfcOpenShell/IfcOpenShell/commit/c03afd33fa) | Add LinePosition: absolute dimension line placement gated on ForcePerpendicularToFace |
| [eb77db9c7a](https://github.com/IfcOpenShell/IfcOpenShell/commit/eb77db9c7a) | Move dimension anchor/regen buttons to annotation tool; ForcePerpendicularToFace toggle updates selection |
| [a6435fb9bf](https://github.com/IfcOpenShell/IfcOpenShell/commit/a6435fb9bf) | Add ForcePerpendicularToFace + hover-cycle UX for parametric dimensions |
| [6caf5b9382](https://github.com/IfcOpenShell/IfcOpenShell/commit/6caf5b9382) | Add bim.draw_parametric_dimension: snap-based polyline operator for dimensions |
| [389ab31862](https://github.com/IfcOpenShell/IfcOpenShell/commit/389ab31862) | Add BBIM_DimensionTarget: parametric dimensions anchored to element geometry |
| [d9ec775650](https://github.com/IfcOpenShell/IfcOpenShell/commit/d9ec775650) | Closes #8063: ordinate dimensioning |
| [e65952d5d2](https://github.com/IfcOpenShell/IfcOpenShell/commit/e65952d5d2) | Closes #7775: BBIM_Dimension.SuppressZeroFeet |
| [80b0cf617b](https://github.com/IfcOpenShell/IfcOpenShell/commit/80b0cf617b) | closes #8060: add multiple custom units to the dimensions string |

### Skipped commits (19 — already present in v0.8.0)

These were cherry-picks or commits that had already landed upstream and were auto-detected by git rebase:

`c348fba7e0`, `2dc715163f`, `5c72222897`, `38a06819e0`, `1d86c8b5ab`, `26082d7712`, `aab6123f82`, `043ca70e07`, `d0b46507f9`, `c58579cab2`, `2738a62447`, `d393955dba`, `db53f7c062`, `4ce94e2ee7`, `3fefa49e92`, `a0086e59c2`, `8a4d267e2f`, `2d1971d08d`, `f00f3cf6ae`

---

## Conflicts

**None.** The rebase applied all 16 unique commits without conflict, despite 52 files being touched on both sides. Git's patch-application correctly identified that each changed region was independent between the branch and upstream.

---

## Syntax check

Key files verified with `python -m py_compile` after rebase:
- `src/bonsai/bonsai/bim/module/drawing/operator.py` — OK
- `src/bonsai/bonsai/bim/module/drawing/gizmos.py` — OK
- `src/bonsai/bonsai/bim/parametric_lifecycle.py` — OK
- `src/bonsai/bonsai/tool/parametric.py` — OK
