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

import bpy
from . import ui, prop, operator

classes = (
    operator.AddBSDDProperties,
    operator.ImportBSDDClasses,
    operator.LoadBSDDDictionaries,
    operator.SearchBSDDClassifications,
    operator.SearchBSDDProperties,
    operator.BIM_OT_show_bsdd_description,
    prop.BSDDDictionary,
    prop.BSDDClassification,
    prop.BSDDProperty,
    prop.BSDDPset,
    prop.BIMBSDDProperties,
    ui.BIM_UL_bsdd_classifications,
    ui.BIM_UL_bsdd_dictionaries,
    ui.BIM_UL_bsdd_classes,
    ui.BIM_UL_bsdd_properties,
    ui.BIM_PT_bsdd,
)


def register():
    bpy.types.Scene.BIMBSDDProperties = bpy.props.PointerProperty(type=prop.BIMBSDDProperties)


def unregister():
    del bpy.types.Scene.BIMBSDDProperties
