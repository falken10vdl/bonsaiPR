# Rebase Summary — `default_relative_path` onto `v0.8.0`

**Branch:** [`default_relative_path`](https://github.com/IfcOpenShell/IfcOpenShell/tree/default_relative_path)
**Date:** 2026-06-08 20:17:54
**Base (`v0.8.0`) tip at rebase:** [`93c6350e0f`](https://github.com/IfcOpenShell/IfcOpenShell/commit/93c6350e0f)
**New branch tip:** [`6b9dbebccc`](https://github.com/IfcOpenShell/IfcOpenShell/commit/6b9dbebccc)
**Outcome:** conflicts-resolved (1 file)

> No GitHub PR found for this branch (`gh` CLI unavailable locally); the branch link points to the branch tree. Issue [#7765](https://github.com/IfcOpenShell/IfcOpenShell/issues/7765) is the tracked issue, not the PR.

## Commits on `default_relative_path` not in `v0.8.0`

The branch was 3 commits ahead of its merge-base ([`e6258ab4a8`](https://github.com/IfcOpenShell/IfcOpenShell/commit/e6258ab4a8)). After the rebase, the three commits (new hashes) are:

1. [`1ccd74e78a`](https://github.com/IfcOpenShell/IfcOpenShell/commit/1ccd74e78a) — *Closes #7765: Default IFC file path to relative and auto-convert on blend save*
2. [`7bcbe1b908`](https://github.com/IfcOpenShell/IfcOpenShell/commit/7bcbe1b908) — *Fix relative path error when IFC not under blend dir*
3. [`6b9dbebccc`](https://github.com/IfcOpenShell/IfcOpenShell/commit/6b9dbebccc) — *Decouple should_start_fresh_session from use_relative_path so IFC files always open in a clean session*

### What the branch does
Defaults `use_relative_project_path` to `True` (relative paths become opt-out), and adds a `save_post` Blender handler that, after a `.blend` save, rewrites an absolute `bim_props.ifc_file` to a path relative to the blend directory while keeping `IfcStore.path` absolute internally. Later commits harden the relative-path conversion (handles IFC not under the blend dir) and decouple the fresh-session behaviour from the relative-path setting.

## Files touched by the branch vs. files changed in `v0.8.0` since merge-base (overlap)

Overlap (conflict candidates):
- `src/bonsai/bonsai/bim/__init__.py`
- `src/bonsai/bonsai/bim/handler.py`
- `src/bonsai/bonsai/bim/module/project/operator.py`
- `src/bonsai/bonsai/bim/ui.py`

Only **`handler.py`** actually conflicted; the other three auto-merged.

## The conflict

### File: `src/bonsai/bonsai/bim/handler.py`

**`v0.8.0` change that caused it:** commit [`5e23030a0f`](https://github.com/IfcOpenShell/IfcOpenShell/commit/5e23030a0f) — *"Decompose bim/handler.py load_post + install cache + discard hooks"*. In `v0.8.0`, the monolithic `load_post` body was decomposed into helper functions — `_apply_save_file_invariants(scene)`, `_apply_user_preferences()`, `_install_viewport_overlays()` — with a thin `@persistent load_post` at the bottom that calls them. The body that used to live directly under `@persistent def load_post(scene):` (msgbus subscription, IFC owner settings, parametric on-load state, multi-instance lock probe) now lives inside `_apply_save_file_invariants`.

**The branch change (commit 1):** inserted a new `@persistent def save_post(scene)` function immediately above the old `@persistent def load_post(scene):`. It made **no change** to the `load_post` body itself.

Because the branch's insertion point and the function header that `v0.8.0` rewrote were the same region of the file, git produced a conflict at the boundary:
- **HEAD (ours / `v0.8.0`):** `def _apply_save_file_invariants(scene): """..."""` followed by the shared body.
- **theirs (branch):** new `@persistent def save_post(...)` + `@persistent def load_post(scene):` followed by the same shared body.

### Resolution
Kept `v0.8.0`'s decomposition intact — `_apply_save_file_invariants(scene)` retains ownership of the shared body — and re-added the branch's brand-new `save_post` handler as a standalone `@persistent` function placed just above `_apply_save_file_invariants`:

```python
@persistent
def save_post(scene) -> None:
    """After saving the .blend file, convert the stored IFC path to relative if enabled."""
    pprops = tool.Project.get_project_props()
    if not pprops.use_relative_project_path:
        return
    bim_props = tool.Blender.get_bim_props()
    ifc_path = bim_props.ifc_file
    if not ifc_path or not os.path.isabs(ifc_path):
        return
    blend_dir = bpy.path.abspath("//")
    if not blend_dir:
        return
    from bonsai.bim.ifc import IfcStore
    rel_path = os.path.relpath(ifc_path, blend_dir)
    bim_props.ifc_file = rel_path
    IfcStore.set_path(ifc_path)  # keep IfcStore.path absolute for loading


def _apply_save_file_invariants(scene: bpy.types.Scene) -> None:
    """Invariants enforced on every load_post: ..."""
    global global_subscription_owner
    ...
```

**Why this is correct:**
- The branch never intended to modify `load_post`'s behaviour — it only *added* a new save-time handler. The conflict was purely positional (the new function was inserted at the exact line `v0.8.0` renamed). Combining both intents means: preserve `v0.8.0`'s refactor and keep the branch's new function.
- `save_post` is independent of the `load_post` decomposition; it does not need to participate in it. Keeping it a top-level `@persistent` handler matches both how the branch wrote it and how it is registered.
- Registration is unaffected: `__init__.py` (auto-merged) still contains `bpy.app.handlers.save_post.append(handler.save_post)` and the matching `remove`, so the function is wired up correctly.
- `os` is imported at the top of `handler.py`, so `os.path.isabs` / `os.path.relpath` resolve.

## Verification
- No conflict markers remain in `handler.py`.
- `python -m py_compile` passes for all overlap files: `__init__.py`, `handler.py`, `module/project/operator.py`, `ui.py`, plus the other branch-touched files `module/project/prop.py` and `operator.py`.
- `git log --oneline v0.8.0..HEAD` shows exactly the three expected commits; working tree clean.
