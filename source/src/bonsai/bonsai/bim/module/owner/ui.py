# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
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

import bpy
import bonsai.bim.helper
import bonsai.tool as tool
from typing import Any
from bonsai.bim.module.owner.data import (
    PeopleData,
    OrganisationsData,
    OwnerData,
    ActorData,
    ObjectActorData,
    ApplicationsData,
)


def draw_roles(box: bpy.types.UILayout, parent: dict[str, Any]) -> None:
    props = tool.Owner.get_owner_props()
    row = box.row(align=True)
    row.label(text="Roles")
    op = row.operator("bim.add_role", icon="ADD", text="")
    op.parent = parent["id"]

    for role in parent["roles"]:
        if props.active_role_id == role["id"]:
            row = box.row(align=True)
            row.operator("bim.edit_role", icon="CHECKMARK")
            row.operator("bim.disable_editing_role", icon="CANCEL", text="")
            bonsai.bim.helper.draw_attributes(props.role_attributes, box)
        else:
            row = box.row(align=True)
            row.label(text=role["label"])
            row.operator("bim.enable_editing_role", icon="GREASEPENCIL", text="").role = role["id"]
            row.operator("bim.remove_role", icon="X", text="").role = role["id"]


def draw_addresses(box: bpy.types.UILayout, parent: dict[str, Any]) -> None:
    props = tool.Owner.get_owner_props()
    row = box.row(align=True)
    row.label(text="Addresses")

    assert (wm := bpy.context.window_manager)
    row.prop(wm.operator_properties_last(bpy.ops.bim.add_address.idname()), "ifc_class", text="")
    op = row.operator("bim.add_address", icon="ADD", text="")
    op.parent = parent["id"]

    for address in parent["addresses"]:
        if props.active_address_id == address["id"]:
            row = box.row(align=True)
            row.operator("bim.edit_address", icon="CHECKMARK")
            row.operator("bim.disable_editing_address", icon="CANCEL", text="")
            bonsai.bim.helper.draw_attributes(props.address_attributes, box)
            attributes: list[str] = address["list_attributes"]
            for attribute_name in attributes:
                row = box.row(align=True)
                row.label(text=attribute_name)
                op = row.operator("bim.add_address_attribute", icon="ADD", text="")
                op.name = attribute_name

                collection = tool.Owner.get_address_collection(attribute_name)
                for i, item in enumerate(collection):
                    row = box.row(align=True)
                    row.prop(item, "name", text="")
                    op = row.operator("bim.remove_address_attribute", icon="REMOVE", text="")
                    op.name = attribute_name
                    op.id = i
        else:
            row = box.row(align=True)
            row.label(text=address["label"])
            row.operator("bim.enable_editing_address", icon="GREASEPENCIL", text="").address = address["id"]
            row.operator("bim.remove_address", icon="X", text="").address = address["id"]


class BIM_PT_people(bpy.types.Panel):
    bl_label = "People"
    bl_idname = "BIM_PT_people"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_stakeholders"

    @classmethod
    def poll(cls, context):
        return bool(tool.Ifc.get())

    def draw(self, context):
        if not PeopleData.is_loaded:
            PeopleData.load()

        assert self.layout
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        row = self.layout.row()
        row.operator("bim.add_person", icon="ADD")

        for person in PeopleData.data["people"]:
            self.draw_person(person)

    def draw_person(self, person: dict[str, Any]) -> None:
        assert self.layout
        props = tool.Owner.get_owner_props()

        if props.active_person_id == person["id"]:
            box = self.layout.box()
            row = box.row(align=True)
            row.operator("bim.edit_person", icon="CHECKMARK")
            row.operator("bim.disable_editing_person", icon="CANCEL", text="")
            bonsai.bim.helper.draw_attributes(props.person_attributes, box)

            for attribute_name in tool.Owner.PERSON_ATTRIBUTE_TYPES:
                row = box.row(align=True)
                row.label(text=attribute_name)
                op = row.operator("bim.add_person_attribute", icon="ADD", text="")
                op.name = attribute_name

                collection = tool.Owner.get_names_collection(attribute_name)
                for i, item in enumerate(collection):
                    row = box.row(align=True)
                    row.prop(item, "name", text="")
                    op = row.operator("bim.remove_person_attribute", icon="REMOVE", text="")
                    op.name = attribute_name
                    op.id = i

            draw_roles(box, person)
            draw_addresses(box, person)
        else:
            row = self.layout.row(align=True)
            row.label(text=person["name"], icon="OUTLINER_OB_ARMATURE")
            if person["roles_label"]:
                row.label(text=person["roles_label"])
            row.operator("bim.enable_editing_person", icon="GREASEPENCIL", text="").person = person["id"]
            if not person["is_engaged"]:
                row.operator("bim.remove_person", icon="X", text="").person = person["id"]


class BIM_PT_organisations(bpy.types.Panel):
    bl_label = "Organisations"
    bl_idname = "BIM_PT_organisations"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_stakeholders"

    @classmethod
    def poll(cls, context):
        return bool(tool.Ifc.get())

    def draw(self, context):
        if not OrganisationsData.is_loaded:
            OrganisationsData.load()

        assert self.layout
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        row = self.layout.row()
        row.operator("bim.add_organisation", icon="ADD")

        for organisation in OrganisationsData.data["organisations"]:
            self.draw_organisation(organisation)

    def draw_organisation(self, organisation: dict[str, Any]) -> None:
        assert self.layout
        props = tool.Owner.get_owner_props()
        if props.active_organisation_id == organisation["id"]:
            box = self.layout.box()
            row = box.row(align=True)
            row.operator("bim.edit_organisation", icon="CHECKMARK")
            row.operator("bim.disable_editing_organisation", icon="CANCEL", text="")
            bonsai.bim.helper.draw_attributes(props.organisation_attributes, box)

            draw_roles(box, organisation)
            draw_addresses(box, organisation)
        else:
            row = self.layout.row(align=True)
            row.label(text=organisation["name"], icon="COMMUNITY")
            if organisation["roles_label"]:
                row.label(text=organisation["roles_label"])
            op = row.operator("bim.enable_editing_organisation", icon="GREASEPENCIL", text="")
            op.organisation = organisation["id"]
            if not organisation["is_engaged"]:
                row.operator("bim.remove_organisation", icon="X", text="").organisation = organisation["id"]


class BIM_PT_owner(bpy.types.Panel):
    bl_label = "Owner History"
    bl_idname = "BIM_PT_owner"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_stakeholders"

    @classmethod
    def poll(cls, context):
        return bool(tool.Ifc.get())

    def draw(self, context):
        if not OwnerData.is_loaded:
            OwnerData.load()

        assert self.layout
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        props = tool.Owner.get_owner_props()

        if not OwnerData.data["user_person"]:
            self.layout.label(text="No people found.")
        else:
            row = self.layout.row()
            row.prop(props, "user_person")

        if not OwnerData.data["user_organisation"]:
            self.layout.label(text="No organisations found.")
        else:
            row = self.layout.row()
            row.prop(props, "user_organisation")

        if OwnerData.data["user_organisation"] and OwnerData.data["user_person"]:
            row = self.layout.row()
            op = row.operator("bim.add_person_and_organisation", icon="ADD")
            op.person = int(props.user_person)
            op.organisation = int(props.user_organisation)

        for user in OwnerData.data["users"]:
            row = self.layout.row(align=True)
            if props.active_user_id == user["id"]:
                row.label(text=user["label"], icon="USER")
                row.operator("bim.clear_user", icon="KEYFRAME", text="").user = user["id"]
            else:
                row.label(text=user["label"])
                row.operator("bim.set_user", icon="KEYFRAME_HLT", text="").user = user["id"]
            op = row.operator("bim.remove_person_and_organisation", icon="X", text="")
            op.person_and_organisation = user["id"]


class BIM_PT_actor(bpy.types.Panel):
    bl_label = "Actors"
    bl_idname = "BIM_PT_actor"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_stakeholders"

    @classmethod
    def poll(cls, context):
        return bool(tool.Ifc.get())

    def draw(self, context):
        if not ActorData.is_loaded:
            ActorData.load()

        assert self.layout
        self.props = tool.Owner.get_owner_props()

        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

        row = self.layout.row(align=True)
        row.prop(self.props, "actor_class", text="")
        row.prop(self.props, "actor_type", text="")
        if ActorData.data["the_actor"]:
            row = self.layout.row(align=True)
            row.prop(self.props, "the_actor", text="")
            row.operator("bim.add_actor", icon="ADD", text="")
        else:
            self.layout.label(text="No users found.")

        for actor in ActorData.data["actors"]:
            self.draw_actor(actor)

    def draw_actor(self, actor: dict[str, Any]) -> None:
        assert self.layout
        props = tool.Owner.get_owner_props()

        if props.active_actor_id == actor["id"]:
            box = self.layout.box()
            row = box.row(align=True)
            row.operator("bim.edit_actor", icon="CHECKMARK")
            row.operator("bim.disable_editing_actor", icon="CANCEL", text="")
            bonsai.bim.helper.draw_attributes(props.actor_attributes, box)
        else:
            row = self.layout.row(align=True)
            row.label(text=actor["name"], icon="USER")
            row.label(text=actor["the_actor"])
            row.operator("bim.enable_editing_actor", icon="GREASEPENCIL", text="").actor = actor["id"]
            row.operator("bim.remove_actor", icon="X", text="").actor = actor["id"]


class BIM_PT_object_actor(bpy.types.Panel):
    bl_label = "Actor"
    bl_idname = "BIM_PT_object_actor"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_order = 1
    bl_parent_id = "BIM_PT_tab_misc"

    @classmethod
    def poll(cls, context):
        return bool(tool.Ifc.get())

    def draw(self, context):
        if not ObjectActorData.is_loaded:
            ObjectActorData.load()

        assert self.layout
        self.props = tool.Owner.get_owner_props()

        if not ObjectActorData.data["actor"]:
            row = self.layout.row(align=True)
            row.label(text="No Actors Found", icon="USER")
            return

        row = self.layout.row(align=True)
        row.prop(self.props, "actor", text="")
        row.operator("bim.assign_actor", icon="ADD", text="").actor = int(self.props.actor)

        for actor in ObjectActorData.data["actors"]:
            row = self.layout.row(align=True)
            row.label(text=actor["name"], icon="USER")
            row.label(text=actor["role"])
            row.operator("bim.unassign_actor", icon="X", text="").actor = actor["id"]


class BIM_PT_applications(bpy.types.Panel):
    bl_label = "Applications"
    bl_idname = "BIM_PT_applications"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_stakeholders"

    @classmethod
    def poll(cls, context) -> bool:
        return bool(tool.Ifc.get())

    def draw(self, context):
        if not ApplicationsData.is_loaded:
            ApplicationsData.load()

        assert (layout := self.layout)
        props = tool.Owner.get_owner_props()

        row = self.layout.row()
        row.operator("bim.add_application", icon="ADD")

        apps_data: list[dict[str, Any]] = ApplicationsData.data["applications"]
        if not apps_data:
            layout.label(text="No Applications Found")
            return

        for app_data in apps_data:
            if props.active_application_id == app_data["id"]:
                box = self.layout.box()
                row = box.row(align=True)
                row.operator("bim.edit_application", icon="CHECKMARK")
                row.operator("bim.disable_editing_application", icon="CANCEL", text="")
                bonsai.bim.helper.draw_attributes(props.application_attributes, box)
            else:
                row = layout.row(align=True)
                row.label(text=app_data["name"])
                op = row.operator("bim.enable_editing_application", icon="GREASEPENCIL", text="")
                op.application_id = app_data["id"]
                row.operator("bim.remove_application", icon="X", text="").application_id = app_data["id"]
