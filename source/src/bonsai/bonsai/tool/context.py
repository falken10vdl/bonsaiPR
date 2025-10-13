# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2021 Dion Moult <dion@thinkmoult.com>
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
import bonsai.bim.helper
import bonsai.tool as tool
import bonsai.core.tool
import ifcopenshell
from typing import Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from bonsai.bim.prop import Attribute
    from bonsai.bim.module.context.prop import BIMContextProperties


class Context(bonsai.core.tool.Context):
    @classmethod
    def get_context_props(cls) -> BIMContextProperties:
        assert bpy.context.scene
        return bpy.context.scene.BIMContextProperties  # pyright: ignore[reportAttributeAccessIssue]

    @classmethod
    def set_context(cls, context: ifcopenshell.entity_instance) -> None:
        props = cls.get_context_props()
        props.active_context_id = context.id()

    @classmethod
    def import_attributes(cls) -> None:
        props = cls.get_context_props()
        props.context_attributes.clear()
        context = cls.get_context()

        def callback(name: str, prop: Union[Attribute, None], data: dict[str, Any]) -> Union[bool, None]:
            if context.is_a("IfcGeometricRepresentationSubContext"):
                if name == "Precision":
                    props.context_attributes.remove(props.context_attributes.find("Precision"))
                    return True
                elif name == "CoordinateSpaceDimension":
                    props.context_attributes.remove(props.context_attributes.find("CoordinateSpaceDimension"))
                    return True
                elif name == "TargetScale":
                    props.context_attributes.remove(props.context_attributes.find("TargetScale"))
                    scale_denominator = None
                    value = data.get(name)
                    if value not in (None, 0):
                        scale_denominator = 1.0 / value
                    new_prop = props.context_attributes.add()
                    new_prop.name = "ScaleDenominator"
                    new_prop.data_type = "float"
                    if scale_denominator is not None:
                        new_prop.float_value = scale_denominator
                    return True
            else:  # IfcGeometricRepresentationContext
                # Import precision as a string because Blender has problem displaying 1e-7 and smaller numbers in UI.
                if name == "Precision":
                    assert prop
                    prop.data_type = "string"

        bonsai.bim.helper.import_attributes(context, props.context_attributes, callback)

    @classmethod
    def clear_context(cls) -> None:
        props = cls.get_context_props()
        props.active_context_id = 0

    @classmethod
    def get_context(cls) -> ifcopenshell.entity_instance:
        props = cls.get_context_props()
        return tool.Ifc.get().by_id(props.active_context_id)

    @classmethod
    def export_attributes(cls) -> dict[str, Any]:
        props = cls.get_context_props()

        def callback(attributes: dict[str, Any], blender_attribute: Attribute) -> bool:
            if blender_attribute.name == "Precision":
                attributes["Precision"] = float(blender_attribute.get_value())
                return True
            elif blender_attribute.name == "ScaleDenominator":
                scale_denominator = blender_attribute.get_value()
                if scale_denominator is not None and scale_denominator != 0:
                    attributes["TargetScale"] = 1.0 / scale_denominator
                else:
                    attributes["TargetScale"] = None
                return True
            return False

        return bonsai.bim.helper.export_attributes(props.context_attributes, callback=callback)
