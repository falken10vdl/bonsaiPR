# Rebase Summary — `fix/duplicate-assigns-to-product` onto `v0.8.0`

**Branch:** [`fix/duplicate-assigns-to-product`](https://github.com/IfcOpenShell/IfcOpenShell/pull/8032) (PR #8032)
**Base:** `v0.8.0` at [`256d5a63f1`](https://github.com/IfcOpenShell/IfcOpenShell/commit/256d5a63f1)
**Date:** 2026-07-10 22:12:49
**Result tip:** [`683b717348`](https://github.com/IfcOpenShell/IfcOpenShell/commit/683b717348)
**Outcome:** conflicts-resolved (1 conflict, 1 file)

---

## Commits on the branch (not in `v0.8.0`)

The branch was a single linear commit ahead of its merge-base (`cb3253b57c`), no merge commits:

- [`00900e1ace`](https://github.com/IfcOpenShell/IfcOpenShell/commit/00900e1ace) — *Closes #6621: Fix IfcRelAssignsToProduct on duplicate*

  When duplicating a product+annotation pair linked via `IfcRelAssignsToProduct`, `copy_class`'s
  generic else-branch appended the new annotation to every existing rel that referenced the
  original, leaving both old and new products sharing stale `RelatedObjects`. The commit adds
  `Geometry.fix_assigns_to_product_after_duplication`, called at the end of
  `duplicate_ifc_objects`, correcting three cases: new annotation left in the old product's rel
  (remove it), stale original left in the new product's rel (remove it), and annotation-only
  duplicate (build a fresh unique rel). Total change: **44 insertions** in
  `src/bonsai/bonsai/tool/geometry.py` (helper method + one call site).

After the rebase this replayed as [`683b717348`](https://github.com/IfcOpenShell/IfcOpenShell/commit/683b717348),
still a single commit, still +44 lines vs base — feature content carried through intact.

## Divergence analysis

- **Commits ahead of merge-base:** 1
- **Merge commits on branch:** none
- **Files touched by branch:** `src/bonsai/bonsai/tool/geometry.py` (only)
- **Overlap files** (changed on both sides since merge-base): `src/bonsai/bonsai/tool/geometry.py`

Since the branch's only file is also the only overlap file, the conflict required genuine
three-way judgment (no non-overlap shortcut files applied here).

## The conflict

**File:** [`src/bonsai/bonsai/tool/geometry.py`](https://github.com/IfcOpenShell/IfcOpenShell/blob/683b717348/src/bonsai/bonsai/tool/geometry.py)

Both sides inserted code at the **exact same point** — the tail of `Geometry.duplicate_ifc_objects`,
immediately after `cls.remove_linked_aggregate_data(old_to_new)` and immediately before
`bonsai.bim.handler.refresh_ui_data()`. In the merge-base that region held nothing between those
two lines, so both changes read as additions at the same anchor and git could not auto-merge them.

- **`v0.8.0` side (HEAD)** — introduced by [`8f3a1d7412`](https://github.com/IfcOpenShell/IfcOpenShell/commit/8f3a1d7412)
  ("Bonsai: batch array-duplicate + defensive guards"), which added:
  ```python
  # In-loop regenerate_wall runs before recreate_connections, so any new
  # walls that just received an IfcRelConnectsPathElements have stale
  # junction geometry — recalculate them now that their connection graph
  # is complete.
  cls._recalculate_walls_with_new_connections(old_to_new)
  ```
- **Branch side (theirs)** — introduced by [`00900e1ace`](https://github.com/IfcOpenShell/IfcOpenShell/commit/00900e1ace),
  which added:
  ```python
  cls.fix_assigns_to_product_after_duplication(old_to_new)
  ```

## Resolution

The two insertions are **independent** — one recalculates wall junction geometry after the
connection graph is rebuilt; the other repairs `IfcRelAssignsToProduct` relationships after the
copy. Neither supersedes or depends on the other, and there is no ordering constraint between
them (both run before the shared `refresh_ui_data()`). Kept **both**, base's walls-recalc block
first, then the branch's fix-assigns call:

```python
        cls.remove_linked_aggregate_data(old_to_new)

        # In-loop regenerate_wall runs before recreate_connections, so any new
        # walls that just received an IfcRelConnectsPathElements have stale
        # junction geometry — recalculate them now that their connection graph
        # is complete.
        cls._recalculate_walls_with_new_connections(old_to_new)

        cls.fix_assigns_to_product_after_duplication(old_to_new)
        bonsai.bim.handler.refresh_ui_data()
```

### Why this is correct

- The branch's helper method `fix_assigns_to_product_after_duplication` (defined elsewhere in the
  file) applied cleanly with no conflict; only its call site collided. Combining both call lines
  preserves the branch's full feature.
- `git diff v0.8.0 HEAD -- tool/geometry.py` is exactly **44 insertions** — identical in size to
  the branch's original standalone change — confirming the base's walls block was preserved (it's
  part of base, not the diff) and the branch's method + call were added without loss or
  duplication.
- 3-way tree verification: the only file differing from both base and the pre-rebase tip (`ORIG`
  = `00900e1ace`) is `tool/geometry.py`, the expected overlap file. Every other file matched the
  `v0.8.0` base version exactly (base advancing, correctly reproduced by the rebase).
- `python -m py_compile` on the sole changed `.py` file passed.

## Final state

- **Branch tip:** [`683b717348`](https://github.com/IfcOpenShell/IfcOpenShell/commit/683b717348)
- **Commits ahead of `v0.8.0`:** 1 (as expected)
- **Status:** rebase complete, working tree clean (only pre-existing untracked files remain)

> **Publish pending.** The `conflict_files` and `result_commit` links above point at the rebased
> commit `683b717348`, which does not exist on GitHub until the branch is force-pushed (Step 9,
> not yet performed). Those links go live only after publishing.
