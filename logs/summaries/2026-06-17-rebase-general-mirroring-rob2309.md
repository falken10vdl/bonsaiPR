# Rebase Summary: Rob2309/general-mirroring onto v0.8.0

**Date:** 2026-06-17 13:28:01
**Branch:** [`general-mirroring` (Rob2309 — PR #7003)](https://github.com/IfcOpenShell/IfcOpenShell/pull/7003)
**Rebased onto:** `v0.8.0` ([855de34d22](https://github.com/IfcOpenShell/IfcOpenShell/commit/855de34d22))
**Result tip:** [22b6d6b759](https://github.com/IfcOpenShell/IfcOpenShell/commit/22b6d6b759)
**Outcome:** conflicts-resolved
**Pushed to:** `Rob2309` remote (`Rob2309/IfcOpenShell:general-mirroring`) — pending Step 9

> **Context:** Previous rebase (2026-06-07) was onto `93c6350e0f`. v0.8.0 has since advanced
> to `855de34d22`. The branch's merge-base was still `93c6350e0f`, so the new rebase replayed
> 48 commits. Only 1 conflict this session vs 16 in the previous session — the new v0.8.0
> commits added `any_selected_is_array_child` in `blender.py`, which landed in the same
> insertion point as the branch's `has_mirrored_type`/`set_mirrored_type`.

---

## Conflict 1 — `blender.py` @ `3d6e5860bd`

**Commit:** "Added tool.Blender.Modifier.has_mirrored_type and set_mirrored_type."

**What conflicted:** v0.8.0 added a new `any_selected_is_array_child` classmethod (with a
detailed docstring and memo cache) and `_any_selected_array_child_memo` class variable
immediately after `is_array_child`. The branch's commit inserted `has_mirrored_type` and
`set_mirrored_type` at the same location.

**Resolution:** Kept HEAD's `any_selected_is_array_child` + `_any_selected_array_child_memo`
in full, then appended `has_mirrored_type` and `set_mirrored_type` after the memo variable
(as independent additions). Applied multi-line formatting to `edit_pset` call in
`set_mirrored_type` for readability:

```python
        _any_selected_array_child_memo: tuple[frozenset[int], int, bool] | None = None

        @classmethod
        def has_mirrored_type(cls, element: entity_instance, inherit: bool = True) -> entity_instance | None:
            pset = ifcopenshell.util.element.get_pset(element, "BBIM_MirroredType", "Data", should_inherit=inherit)
            if pset and (parsed := json.loads(pset)) and "mirrored_type" in parsed:
                return tool.Ifc.get_entity_by_id(int(parsed["mirrored_type"]))
            return None

        @classmethod
        def set_mirrored_type(cls, element: entity_instance, mirrored_type: entity_instance):
            pset = tool.Pset.get_element_pset(element, "BBIM_MirroredType")
            if not pset:
                pset = ifcopenshell.api.pset.add_pset(tool.Ifc.get(), element, "BBIM_MirroredType")
            ifcopenshell.api.pset.edit_pset(
                tool.Ifc.get(), pset, properties={"Data": json.dumps({"mirrored_type": mirrored_type.id()})}
            )
```

**Why correct:** `any_selected_is_array_child` is unrelated to mirroring — it gates wall
topology gizmos. `has_mirrored_type`/`set_mirrored_type` are the mirroring pset API. Both
sets of additions are independent and must coexist.
