# Rebase: extend-profiles-and-extrusions onto v0.8.0

**Date:** 2026-06-07  
**Branch:** [`extend-profiles-and-extrusions`](https://github.com/IfcOpenShell/IfcOpenShell/tree/extend-profiles-and-extrusions)  
**Base (v0.8.0 tip):** [`93c6350e0f`](https://github.com/IfcOpenShell/IfcOpenShell/commit/93c6350e0f)  
**Result commit:** [`e9ebba9050`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e9ebba9050)  
**Outcome:** `conflicts-resolved`

---

## Commits on `extend-profiles-and-extrusions` not in `v0.8.0`

| Commit | Message |
|--------|---------|
| [`28913afc12`](https://github.com/IfcOpenShell/IfcOpenShell/commit/28913afc12) | closes #3565 - extend profiles and basic extrusions to 3D cursor with Ctrl+E |
| [`9013dd2c35`](https://github.com/IfcOpenShell/IfcOpenShell/commit/9013dd2c35) | Add "E" to ExtendProfile join_type enum |
| [`e9ebba9050`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e9ebba9050) | Add Extend to Cursor button to active tool panel |

---

## Overlap files (touched by both sides since merge-base)

- `src/bonsai/bonsai/bim/module/model/profile.py`
- `src/bonsai/bonsai/bim/module/model/workspace.py`

---

## Conflicts

### 1. `src/bonsai/bonsai/bim/module/model/profile.py`

**Conflict occurred during:** applying commit `9013dd2c35` ("Add 'E' to ExtendProfile join_type enum")

**v0.8.0 commit that caused the conflict:** [`8eb0060d4a`](https://github.com/IfcOpenShell/IfcOpenShell/commit/8eb0060d4a) — "Get rid of pyright ignore reportRedeclaration noise"

**What v0.8.0 changed:** Added `# pyright: ignore[reportRedeclaration]` to the `join_type` property declaration in `ExtendProfile` to suppress a Pyright static analysis warning about the redeclaration pattern used by Blender's `bpy.props` annotations.

**What the feature branch changed:** Added `("E", "Extend to Cursor", "")` as a new enum item to the `join_type` `EnumProperty`, enabling the new Ctrl+E "extend to cursor" mode.

**Resolution:** Both changes are independent — the pyright comment annotates the line itself, while the new enum item expands the list. The resolved form keeps the `# pyright: ignore[reportRedeclaration]` comment on the declaration line and adds the `"E"` item to the enum list:

```python
join_type: bpy.props.EnumProperty(  # pyright: ignore[reportRedeclaration]
    items=[("-", "Unjoin", ""), ("L", "L", ""), ("V", "V", ""), ("T", "T", ""), ("E", "Extend to Cursor", "")],
    default="-",
)
```

**Why this is correct:** Both changes are purely additive and non-overlapping. Dropping either change would be wrong — omitting the pyright comment re-introduces the suppressed noise, and omitting `"E"` breaks the extend-to-cursor feature entirely.

### No conflict in `workspace.py`

Although `workspace.py` was touched by both sides, git merged it automatically without a conflict. The v0.8.0 changes (operator panel plumbing, hotkey display improvements) and the feature branch's addition of the Extend to Cursor button were in different regions of the file.

---

## Syntax verification

Both overlap files were verified with `python -m py_compile`:

- `src/bonsai/bonsai/bim/module/model/profile.py` — OK
- `src/bonsai/bonsai/bim/module/model/workspace.py` — OK

---

## Final state

```
e9ebba9050 Add Extend to Cursor button to active tool panel
9013dd2c35 Add "E" to ExtendProfile join_type enum
28913afc12 closes #3565 - extend profiles and basic extrusions to 3D cursor with Ctrl+E
```

Branch tip: [`e9ebba9050`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e9ebba9050)  
Force-push to `origin/extend-profiles-and-extrusions` required (branch history was rewritten).
