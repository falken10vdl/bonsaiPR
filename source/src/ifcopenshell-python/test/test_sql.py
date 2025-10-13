# IfcOpenShell - IFC toolkit and geometry engine
# Copyright (C) 2021 Thomas Krijnen <thomas@aecgeeks.com>
#
# This file is part of IfcOpenShell.
#
# IfcOpenShell is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IfcOpenShell is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with IfcOpenShell.  If not, see <http://www.gnu.org/licenses/>.

import tempfile
import ifcpatch
import ifcopenshell
from pathlib import Path
from ifcpatch.recipes import Ifc2Sql

TEST_FILE = Path(__file__).parent / "files" / "basic.ifc"
SQLITE_PATH = None


def get_ifc_sqlite() -> ifcopenshell.sqlite:
    global SQLITE_PATH
    if SQLITE_PATH is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ifcsqlite")
        ifc_file = ifcopenshell.open(TEST_FILE)
        assert isinstance(ifc_file, ifcopenshell.file)
        patcher = Ifc2Sql.Patcher(ifc_file, database=tmp.name)
        patcher.patch()
        SQLITE_PATH = tmp.name
    ifc_sqlite = ifcopenshell.open(SQLITE_PATH)
    assert isinstance(ifc_sqlite, ifcopenshell.sqlite)
    return ifc_sqlite


class TestFile:
    def test_run(self):
        ifc_sqlite = get_ifc_sqlite()
        assert ifc_sqlite.schema == "IFC4"

    def test_by_id(self):
        ifc_sqlite = get_ifc_sqlite()
        assert (element := ifc_sqlite.by_id(1))
        assert str(element) == "#1=IFCPROJECT('3kv235yMjDO9tHiTzD8QuS',$,'My Project',$,$,$,$,(#14,#26),#9);"

    def test_by_type(self):
        ifc_sqlite = get_ifc_sqlite()
        assert (elements := ifc_sqlite.by_type("IfcProject"))
        assert str(elements[0]) == "#1=IFCPROJECT('3kv235yMjDO9tHiTzD8QuS',$,'My Project',$,$,$,$,(#14,#26),#9);"


class TestEntity:
    def test_getattr(self):
        ifc_sqlite = get_ifc_sqlite()
        assert (element := ifc_sqlite.by_id(1))
        assert element.Name == "My Project"

    def test_setattr(self):
        ifc_sqlite = get_ifc_sqlite()
        assert (element := ifc_sqlite.by_id(1))
        assert element.Name == "My Project"
        element.Name = "Foo"
        assert element.Name == "Foo"
        element.Name = "My Project"
        assert element.Name == "My Project"
