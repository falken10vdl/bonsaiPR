# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Maxim Vasilyev <qwiglydee@gmail.com>
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
import os
import bpy
import math
import bmesh
import bonsai.tool as tool
import ifcopenshell.util.element
from pathlib import Path
from mathutils import Vector, Matrix
from typing import Optional


class Annotator:
    @staticmethod
    def add_line_to_annotation(
        obj: bpy.types.Object, co1: Optional[Vector] = None, co2: Optional[Vector] = None
    ) -> bpy.types.Object:
        if co1 is None:
            co1, co2, _, _ = Annotator.get_placeholder_coords()
        co1 = obj.matrix_world.inverted() @ co1
        co2 = obj.matrix_world.inverted() @ co2

        if isinstance(obj.data, bpy.types.Mesh):
            obj.data.vertices.add(2)
            obj.data.vertices[-2].co = co1
            obj.data.vertices[-1].co = co2
            obj.data.edges.add(1)
            obj.data.edges[-1].vertices = (obj.data.vertices[-2].index, obj.data.vertices[-1].index)

        if isinstance(obj.data, bpy.types.Curve):
            polyline = obj.data.splines.new("POLY")
            polyline.points.add(1)
            polyline.points[-2].co = list(co1) + [1]
            polyline.points[-1].co = list(co2) + [1]

        return obj

    @staticmethod
    def add_vertex_to_annotation(obj: bpy.types.Object) -> bpy.types.Object:
        verts_world_space = Annotator.get_placeholder_coords()
        vert_local = obj.matrix_world.inverted() @ verts_world_space[0]
        bm = tool.Blender.get_bmesh_for_mesh(obj.data, clean=True)
        bm.verts.new(vert_local)
        tool.Blender.apply_bmesh(obj.data, bm, obj)
        return obj

    @staticmethod
    def add_plane_to_annotation(obj: bpy.types.Object, remove_face: bool = False) -> bpy.types.Object:
        # default order = bot left, top left, bot right, top right
        # therefore we redefine the order
        face_verts = [0, 2, 3, 1]

        verts_world_space = Annotator.get_placeholder_coords()
        verts_local = [obj.matrix_world.inverted() @ v for v in verts_world_space]
        bm = tool.Blender.get_bmesh_for_mesh(obj.data, clean=True)
        new_verts = [bm.verts.new(v) for v in verts_local]

        face = bm.faces.new([new_verts[i] for i in face_verts])
        if remove_face:
            bmesh.ops.delete(bm, geom=[face], context="FACES_ONLY")
        tool.Blender.apply_bmesh(obj.data, bm, obj)
        return obj

    @staticmethod
    def get_annotation_obj(
        drawing: ifcopenshell.entity_instance, object_type: str, data_type: tool.Drawing.ANNOTATION_DATA_TYPE
    ) -> bpy.types.Object:
        assert bpy.context.scene
        camera = tool.Ifc.get_object(drawing)
        assert isinstance(camera, bpy.types.Object)
        # those annotations you want to obey the depth of the 3d cursor
        if object_type == "PLAN_LEVEL":
            co1 = bpy.context.scene.cursor.location.copy()
        else:
            co1, _, _, _ = Annotator.get_placeholder_coords(camera)
        matrix_world = tool.Drawing.get_camera_matrix(camera)
        matrix_world.translation = co1
        collection = tool.Blender.get_object_bim_props(camera).collection

        if object_type == "TEXT":
            obj = bpy.data.objects.new(object_type, None)
            obj.matrix_world = matrix_world
            collection.objects.link(obj)
            return obj

        elif object_type in ("TEXT_LEADER", "SECTION_LEVEL"):
            data = bpy.data.curves.new(object_type, type="CURVE")
            data.dimensions = "3D"
            data.resolution_u = 2
            obj = bpy.data.objects.new(object_type, data)
            obj.matrix_world = matrix_world
            collection.objects.link(obj)
            return obj

        # TODO: remove as outdated?
        # Is reusing the same objects preventing the creation of new annotations.
        # if object_type != "ANGLE":
        #     for obj in collection.objects:
        #         element = tool.Ifc.get_entity(obj)
        #         if (
        #             element
        #             and ifcopenshell.util.element.get_predefined_type(element) == object_type
        #             and obj.type == data_type.upper()
        #         ):
        #             return obj

        if data_type == "mesh":
            data = bpy.data.meshes.new(object_type)
        elif data_type == "curve":
            data = bpy.data.curves.new(object_type, type="CURVE")
            data.dimensions = "3D"
            data.resolution_u = 2
        elif data_type == "empty":
            data = None

        obj = bpy.data.objects.new(object_type, data)
        obj.matrix_world = matrix_world
        collection.objects.link(obj)
        return obj

    @staticmethod
    def get_placeholder_coords(camera: Optional[bpy.types.Object] = None) -> tuple[Vector, Vector, Vector, Vector]:
        if not camera:
            camera = bpy.context.scene.camera

        z_offset = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))

        if (
            ifcopenshell.util.element.get_pset(tool.Ifc.get_entity(camera), "EPset_Drawing", "TargetView")
            == "REFLECTED_PLAN_VIEW"
        ):
            z_offset *= -1

        y = camera.data.ortho_scale / 4

        res_x = bpy.context.scene.render.resolution_x
        res_y = bpy.context.scene.render.resolution_y
        if res_x > res_y:
            y *= res_y / res_x

        y_offset = camera.matrix_world.to_quaternion() @ Vector((0, y, 0))
        x_offset = camera.matrix_world.to_quaternion() @ Vector((y / 2, 0, 0))

        center = camera.matrix_world.inverted() @ bpy.context.scene.cursor.location
        center.z = 0
        center = camera.matrix_world @ center

        return (
            center + z_offset,
            center + z_offset + y_offset,
            center + z_offset + x_offset,
            center + z_offset + x_offset + y_offset,
        )
