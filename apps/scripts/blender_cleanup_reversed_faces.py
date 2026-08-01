"""Safely find and remove exactly overlapping, opposite-facing mesh faces.

Run this file from Blender's Scripting workspace with the clothing mesh selected.

The default ACTION is ``SELECT``: the script only selects faces that it proposes
to remove. Inspect them with Overlays > Face Orientation. When the selection is
correct, change ACTION to ``DELETE`` and run the script again.

The deletion mode creates a hidden backup object before changing the mesh. This
script intentionally skips meshes with shape keys because deleting topology
would invalidate those keys.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import bmesh
import bpy
from mathutils import Vector


# ---------------------------------------------------------------------------
# User settings
# ---------------------------------------------------------------------------

# Use "SELECT" first. Change to "DELETE" only after inspecting the selection.
ACTION = "SELECT"

# Vertex positions closer than this value are considered identical. The value
# is in Blender object-local units. Increase only if the two layers are not
# mathematically identical.
POSITION_TOLERANCE = 1.0e-6

# Normals must be almost exactly opposite before a face is considered a reverse
# duplicate. -0.999 corresponds to roughly 2.6 degrees from perfectly opposite.
OPPOSITE_NORMAL_DOT = -0.999

# The outward-facing copy is chosen by comparing its normal with the direction
# from the object's bounding-box center to the face center.
OUTWARD_SCORE_EPSILON = 1.0e-8

CREATE_BACKUP_BEFORE_DELETE = True
BACKUP_COLLECTION_NAME = "__StarManager_ReversedFace_Backups"

# Blender/FBX normally calculates tangents from UVs during export. Enabling this
# also asks Blender to refresh them immediately after deletion when supported.
REFRESH_TANGENTS_AFTER_DELETE = True


def _position_key(co: Vector) -> tuple[int, int, int]:
    return tuple(round(float(axis) / POSITION_TOLERANCE) for axis in co)


def _face_key(face: bmesh.types.BMFace) -> tuple[int, tuple[tuple[int, int, int], ...]]:
    positions = tuple(sorted(_position_key(vertex.co) for vertex in face.verts))
    return len(face.verts), positions


def _bounding_box_center(bm: bmesh.types.BMesh) -> Vector:
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    for vertex in bm.verts:
        for axis in range(3):
            minimum[axis] = min(minimum[axis], vertex.co[axis])
            maximum[axis] = max(maximum[axis], vertex.co[axis])
    return (minimum + maximum) * 0.5


def _find_reverse_duplicates(
    bm: bmesh.types.BMesh,
) -> tuple[set[bmesh.types.BMFace], int, int]:
    """Return faces to remove, duplicate group count, and ambiguous group count."""

    bm.normal_update()
    center = _bounding_box_center(bm)
    groups: dict[tuple, list[bmesh.types.BMFace]] = defaultdict(list)
    for face in bm.faces:
        groups[_face_key(face)].append(face)

    proposed: set[bmesh.types.BMFace] = set()
    matched_groups = 0
    ambiguous_groups = 0

    for faces in groups.values():
        if len(faces) < 2:
            continue

        scores = {
            face: face.normal.dot(face.calc_center_median() - center)
            for face in faces
        }
        outward = max(faces, key=lambda face: scores[face])
        opposite_faces = [
            face
            for face in faces
            if face is not outward and face.normal.dot(outward.normal) <= OPPOSITE_NORMAL_DOT
        ]
        if not opposite_faces:
            continue

        opposite_best = max(scores[face] for face in opposite_faces)
        if scores[outward] - opposite_best <= OUTWARD_SCORE_EPSILON:
            ambiguous_groups += 1
            continue

        matched_groups += 1
        proposed.update(opposite_faces)

    return proposed, matched_groups, ambiguous_groups


def _backup_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.get(BACKUP_COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(BACKUP_COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    collection.hide_render = True
    collection.hide_select = True
    return collection


def _create_backup(obj: bpy.types.Object) -> bpy.types.Object:
    backup = obj.copy()
    backup.data = obj.data.copy()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup.name = f"{obj.name}__before_reverse_cleanup_{timestamp}"
    backup.data.name = f"{obj.data.name}__before_reverse_cleanup_{timestamp}"
    backup["star_manager_backup_of"] = obj.name
    _backup_collection().objects.link(backup)
    backup.hide_render = True
    backup.hide_set(True)
    return backup


def _refresh_tangents(mesh: bpy.types.Mesh) -> str:
    if not REFRESH_TANGENTS_AFTER_DELETE:
        return "disabled"
    if not mesh.uv_layers or mesh.uv_layers.active is None:
        return "skipped: no active UV map"
    try:
        mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
        return f"updated from UV map '{mesh.uv_layers.active.name}'"
    except (AttributeError, RuntimeError) as exc:
        return f"deferred to export: {exc}"


def _process_object(obj: bpy.types.Object, action: str) -> dict[str, object]:
    mesh = obj.data
    if mesh.shape_keys and mesh.shape_keys.key_blocks:
        return {
            "object": obj.name,
            "status": "skipped",
            "reason": "mesh has shape keys; topology deletion would invalidate them",
        }

    if action == "DELETE" and mesh.users > 1:
        obj.data = mesh.copy()
        mesh = obj.data

    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        proposed, group_count, ambiguous_count = _find_reverse_duplicates(bm)

        if action == "SELECT":
            for face in bm.faces:
                face.select = face in proposed
            bm.select_mode = {"FACE"}
            bm.select_flush_mode()
            bm.to_mesh(mesh)
            mesh.update()
            return {
                "object": obj.name,
                "status": "selected",
                "faces": len(proposed),
                "groups": group_count,
                "ambiguous_groups": ambiguous_count,
            }

        backup_name = None
        if proposed and CREATE_BACKUP_BEFORE_DELETE:
            backup_name = _create_backup(obj).name

        deleted_count = len(proposed)
        if proposed:
            bmesh.ops.delete(bm, geom=list(proposed), context="FACES")
            bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update(calc_edges=True)
        tangent_status = _refresh_tangents(mesh)
        return {
            "object": obj.name,
            "status": "cleaned",
            "faces": deleted_count,
            "groups": group_count,
            "ambiguous_groups": ambiguous_count,
            "backup": backup_name,
            "tangents": tangent_status,
        }
    finally:
        bm.free()


def main() -> None:
    action = ACTION.strip().upper()
    if action not in {"SELECT", "DELETE"}:
        raise ValueError('ACTION must be either "SELECT" or "DELETE"')
    if POSITION_TOLERANCE <= 0:
        raise ValueError("POSITION_TOLERANCE must be greater than zero")

    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    objects = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not objects:
        raise RuntimeError("Select at least one clothing mesh object before running the script")

    active = bpy.context.view_layer.objects.active
    results = [_process_object(obj, action) for obj in objects]

    print("\n=== Star Manager reverse-face cleanup ===")
    for result in results:
        print(result)

    if action == "SELECT":
        if active not in objects:
            active = objects[0]
        bpy.context.view_layer.objects.active = active
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        bpy.ops.object.mode_set(mode="EDIT")
        print(
            "Detection finished. Proposed reverse faces are selected. "
            "Inspect them with Overlays > Face Orientation; then set ACTION='DELETE' and run again."
        )
    else:
        print(
            f"Cleanup finished. Backups are stored in collection '{BACKUP_COLLECTION_NAME}'. "
            "Inspect Face Orientation before deleting the backup collection."
        )


if __name__ == "__main__":
    main()
