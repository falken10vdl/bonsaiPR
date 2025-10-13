# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2022 Dion Moult <dion@thinkmoult.com>
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
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import bpy
    import ifcopenshell
    import bonsai.tool as tool


def parse_express(debug: type[tool.Debug], filename: str) -> None:
    debug.add_schema_identifier(debug.load_express(filename))


def purge_hdf5_cache(debug: type[tool.Debug]) -> None:
    debug.purge_hdf5_cache()


def purge_unused_elements(ifc: type[tool.Ifc], debug: type[tool.Debug], ifc_class: str) -> int:
    ifc_file = ifc.get()
    unused_elements = [i for i in ifc_file.by_type(ifc_class) if ifc_file.get_total_inverses(i) == 0]
    unused_elements_amount = len(unused_elements)
    if ifc_class == "IfcApplication":
        for element in unused_elements:
            ifc.run("owner.remove_application", application=element)
    elif ifc_class == "IfcPerson":
        for element in unused_elements:
            ifc.run("owner.remove_person", person=element)
    elif ifc_class == "IfcPersonAndOrganization":
        for element in unused_elements:
            ifc.run("owner.remove_person_and_organisation", person_and_organisation=element)
    else:
        debug.remove_unused_elements(unused_elements)
    return unused_elements_amount
