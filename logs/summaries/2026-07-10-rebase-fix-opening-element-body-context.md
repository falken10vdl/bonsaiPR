# Rebase: `fix/opening-element-body-context` onto `v0.8.0`

**Branch:** [`fix/opening-element-body-context`](https://github.com/IfcOpenShell/IfcOpenShell/pull/7898) (PR #7898)
**Date:** 2026-07-10 21:58:58
**Base (`v0.8.0`) tip at rebase:** [`256d5a63f1`](https://github.com/IfcOpenShell/IfcOpenShell/commit/256d5a63f1)
**Result tip:** [`b0246f7609`](https://github.com/IfcOpenShell/IfcOpenShell/commit/b0246f76097b89813f9e32eae2cb01607d6f9afe)
**Outcome:** conflicts-resolved (1 overlap file)

---

## Commits on the branch not in `v0.8.0`

A single linear commit (no merge commits):

- [`2b24ab2063`](https://github.com/IfcOpenShell/IfcOpenShell/commit/2b24ab2063) — *Fix IfcOpeningElement using wrong geometry context*

It touches two files:

- `src/bonsai/bonsai/bim/module/root/operator.py` — in `AddElement._execute`, when the class is
  `IfcOpeningElement`, resolve `Model/Body/MODEL_VIEW` (falling back to `Model/Body`) directly from
  the IFC file instead of trusting the `props.contexts` dropdown, which could be left on the
  top-level `Model` context. The boolean engine only searches subcontexts for opening geometry, so a
  top-level context silently produced a void that was never cut. A warning is reported if no
  `Model/Body` context exists.
- `src/bonsai/bonsai/bim/module/void/operator.py` — in `AddOpening._execute`, two diagnostic warnings:
  1. warn if the created opening has no `Model/Body` representation ("void will not be cut");
  2. warn if, after the host recut, the host's active representation contains no `IfcBooleanResult`
     ("no boolean cut was created").

The pre-rebase merge-base was `9d42f4c1ee`; the branch was 1 commit ahead of it.

## Rebase result

`git rebase v0.8.0` replayed the single commit. `root/operator.py` applied cleanly (it is a
**non-overlap** file — `v0.8.0` made no changes to it since the merge-base — so its correct end
state is the branch-tip version, verified identical). `void/operator.py` conflicted.

## The conflict — `void/operator.py`

### What each side changed

- **Merge-base:** the host recut in the `AddOpening` per-voided-object loop was an **inline** call:
  ```python
  bonsai.core.geometry.switch_representation(tool.Ifc, tool.Geometry, obj=voided_obj, representation=representation)
  ```

- **`v0.8.0`** — commit [`82dd1d94de`](https://github.com/IfcOpenShell/IfcOpenShell/commit/82dd1d94de)
  *"Bonsai: batch host recuts in array/opening paths"* replaced that inline call with a batched
  helper:
  ```python
  tool.Geometry.recut_host(voided_obj, representation)
  ```
  and wrapped the whole `AddOpening._execute` body in `with tool.Geometry.batch_host_recut():`.
  Inside that context, `recut_host` **does not** call `switch_representation` immediately — it
  enqueues the recut by voided-element id and only drains the queue (running
  `update_representation` then `switch_representation` for each host) when the outermost `with`
  block exits. This coalesces/deduplicates repeated host recuts for performance.

- **The branch** — commit `2b24ab2063` kept the inline `switch_representation(...)` and appended a
  diagnostic **immediately after it**:
  ```python
  updated_rep = tool.Geometry.get_active_representation(voided_obj)
  if updated_rep and not any(item.is_a("IfcBooleanResult") for item in updated_rep.Items):
      self.report({"WARNING"}, f"Opening was applied to '{voided_obj.name}' but no boolean cut was created. ...")
  ```

### Why it is a genuine (not just textual) conflict

The branch's diagnostic was written against the merge-base world where `switch_representation` fired
**inline** — so immediately afterwards the host's active representation already reflected the recut,
and the `IfcBooleanResult` check was meaningful. Under `v0.8.0`'s batching the recut is **deferred**
to the end of the `with` block, so reading `get_active_representation(voided_obj)` right after
`recut_host` returns the **pre-recut** representation. The diagnostic would therefore emit a spurious
"no boolean cut was created" warning on essentially **every** opening. Naively keeping both sides
compiles but is behaviourally broken.

### Resolution

Kept `v0.8.0`'s `tool.Geometry.recut_host(voided_obj, representation)` and **dropped** the inline
boolean-cut diagnostic.

```python
representation = tool.Geometry.get_active_representation(voided_obj)
assert representation
tool.Geometry.recut_host(voided_obj, representation)
```

### Why this resolution is correct

- The branch's **primary** fix — resolving the `Model/Body/MODEL_VIEW` context for
  `IfcOpeningElement` in `root/operator.py` — is fully preserved.
- The branch's **first** diagnostic (warn when the opening has no `Model/Body` representation) sits
  earlier in the method, outside the conflict region; it auto-merged and is intact. This is the more
  valuable of the two warnings and directly addresses the wrong-context symptom.
- The **second** diagnostic is fundamentally incompatible with `v0.8.0`'s deferred-recut
  architecture at that call site. Relocating it to run after the batch flushes would mean inventing
  new control structure the author never wrote and risking a batch-ordering bug — beyond the remit
  of a rebase. If the boolean-cut check is still wanted, it should be re-introduced deliberately as a
  follow-up that hooks the batch drain, not carried through a conflict resolution.

The user was consulted on this trade-off during the rebase and the "drop the diagnostic" resolution
was chosen.

## Verification

- `git log --oneline v0.8.0..HEAD` → exactly one commit (`b0246f7609`).
- **3-way tree check:** every file differing between the pre-rebase tip (`2b24ab2063`) and the rebased
  `HEAD` matched either the `v0.8.0` version (absorbed base advancement) or the branch-tip version —
  the only `SCRUTINIZE` result was the overlap file `void/operator.py`, as expected.
- Feature delta vs `v0.8.0` is exactly the two expected files (`root/operator.py`, `void/operator.py`).
- `root/operator.py` is byte-identical to the branch tip (non-overlap invariant holds).
- `python -m py_compile` passes on both changed `.py` files.

## Final branch tip

[`b0246f76097b89813f9e32eae2cb01607d6f9afe`](https://github.com/IfcOpenShell/IfcOpenShell/commit/b0246f76097b89813f9e32eae2cb01607d6f9afe)

> **Note:** the `void/operator.py` and result-commit links above go live only after the rebased
> branch is force-pushed (Step 9) — pending until then.
