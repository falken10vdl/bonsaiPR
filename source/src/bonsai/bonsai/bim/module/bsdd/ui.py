# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2023 Dion Moult <dion@thinkmoult.com>
#
# This file is part of Bonsai.
#
# Bonsai is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bonsai is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bonsai.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations
import bpy
import bonsai.tool as tool
from bonsai.bim.module.bsdd.data import BSDDData
from bpy.types import Panel, UIList
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bonsai.bim.module.bsdd.prop import BIMBSDDProperties, BSDDDictionary, BSDDClassification, BSDDProperty


class BIM_PT_bsdd(Panel):
    bl_label = "buildingSMART Data Dictionary"
    bl_idname = "BIM_PT_bsdd"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_project_setup"

    def draw(self, context):
        if not BSDDData.is_loaded:
            BSDDData.load()
        props = tool.Bsdd.get_bsdd_props()
        assert self.layout
        layout = self.layout
        if len(props.dictionaries):
            row = self.layout.row()
            row.operator("bim.load_bsdd_dictionaries", icon="FILE_REFRESH")

        if len(props.dictionaries):
            self.layout.template_list(
                "BIM_UL_bsdd_dictionaries",
                "",
                props,
                "dictionaries",
                props,
                "active_dictionary_index",
            )
            if 0 <= props.active_dictionary_index < len(props.dictionaries):
                selected_dictionary = props.dictionaries[props.active_dictionary_index]
            else:
                selected_dictionary = None

            if selected_dictionary:
                layout.label(text="Selected Dictionary:")
                box = layout.box()
                row = box.row(align=True)
                row.label(text="Language")
                row.label(text=selected_dictionary.default_language_code)
                row = box.row(align=True)
                row.label(text="Version")
                row.label(text=selected_dictionary.version)
                box.operator("bim.open_uri", text="Open bSDD In Browser", icon="URL").uri = selected_dictionary.uri

        else:
            row = self.layout.row()
            row.operator("bim.load_bsdd_dictionaries")


class BIM_UL_bsdd_dictionaries(UIList):
    def draw_item(
        self,
        context,
        layout: bpy.types.UILayout,
        data: BIMBSDDProperties,
        item: BSDDDictionary,
        icon,
        active_data,
        active_propname,
    ) -> None:
        if item:
            row = layout.row(align=True)
            if item.status != "Active":
                row.label(
                    text=f"{item.name} ({item.organization_name_owner}) v{item.version} - {item.status}", icon="ERROR"
                )
            else:
                row.label(text=f"{item.name} ({item.organization_name_owner}) v{item.version}")
            row.prop(
                item, "is_active", icon="CHECKBOX_HLT" if item.is_active else "CHECKBOX_DEHLT", text="", emboss=False
            )


class BIM_UL_bsdd_classifications(UIList):
    def draw_item(
        self,
        context,
        layout: bpy.types.UILayout,
        data: BIMBSDDProperties,
        item: BSDDClassification,
        icon,
        active_data,
        active_propname,
    ) -> None:
        if item:
            row = layout.row(align=True)
            row.label(text=item.reference_code)
            row.label(text=item.name)
            row.operator("bim.open_uri", text="", icon="URL").uri = item.uri


class BIM_UL_bsdd_classes(UIList):
    def draw_item(
        self,
        context,
        layout: bpy.types.UILayout,
        data: BIMBSDDProperties,
        item: BSDDClassification,
        icon,
        active_data,
        active_propname,
    ) -> None:
        if item:
            row = layout.row(align=True)
            row.label(text=item.name)
            row.operator("bim.open_uri", text="", icon="URL").uri = item.uri


class BIM_UL_bsdd_properties(UIList):
    def draw_item(
        self,
        context,
        layout: bpy.types.UILayout,
        data: BIMBSDDProperties,
        item: BSDDProperty,
        icon,
        active_data,
        active_propname,
    ) -> None:
        if item:
            layout.context_pointer_set("active_bsdd_property", item)  # used for context menu
            row = layout.row(align=True)
            name = item.name
            if name != item.code:
                name += f" ({item.code})"
            row.label(text=name)
            if item.pset:
                row.label(text=item.pset)
            row.operator("bim.open_uri", text="", icon="URL").uri = item.uri
            row.prop(
                item,
                "is_selected",
                icon="CHECKBOX_HLT" if item.is_selected else "CHECKBOX_DEHLT",
                text="",
                emboss=False,
            )
