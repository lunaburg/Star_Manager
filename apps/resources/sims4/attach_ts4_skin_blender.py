from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import sys
import traceback

import bmesh
import bpy
from mathutils import Matrix, Vector


# Move each complete arm chain toward the torso by a small amount while
# preserving the horizontal T-pose direction.  Scaling the offset from the
# upper-arm length keeps the adjustment consistent across different bodies.
ARM_INWARD_OFFSET_RATIO = 0.06
REVERSE_FACE_POSITION_TOLERANCE = 1.0e-6
REVERSE_FACE_NORMAL_DOT = -0.999
REVERSE_FACE_SCORE_EPSILON = 1.0e-6


def fnv32_lower(value: str) -> int:
    result = 0x811C9DC5
    for byte in value.lower().encode("utf-8"):
        result = ((result * 0x01000193) & 0xFFFFFFFF) ^ byte
    return result


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for data_collection in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
        for data_block in list(data_collection):
            if data_block.users == 0:
                data_collection.remove(data_block)


def load_template(template_path: Path) -> bpy.types.Object:
    existing = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(
        filepath=str(template_path),
        use_anim=False,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    armatures = [
        obj
        for obj in bpy.context.scene.objects
        if obj not in existing and obj.type == "ARMATURE"
    ]
    if len(armatures) != 1:
        raise RuntimeError(
            f"骨架模板应包含 1 个 Armature，实际找到 {len(armatures)} 个"
        )
    return armatures[0]


def load_mesh(fbx_path: Path, armature: bpy.types.Object) -> bpy.types.Object:
    existing = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False)
    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj not in existing and obj.type == "MESH"
    ]
    imported_armatures = [
        obj
        for obj in bpy.context.scene.objects
        if obj not in existing and obj.type == "ARMATURE" and obj != armature
    ]
    for imported_armature in imported_armatures:
        bpy.data.objects.remove(imported_armature, do_unlink=True)
    if len(meshes) != 1:
        raise RuntimeError(f"待绑定 FBX 应包含 1 个网格，实际找到 {len(meshes)} 个")
    return meshes[0]


def apply_skin(
    mesh: bpy.types.Object,
    armature: bpy.types.Object,
    skin_data: dict,
) -> dict:
    vertex_count = int(skin_data.get("vertex_count") or 0)
    bone_hashes = [int(value) & 0xFFFFFFFF for value in skin_data["bone_hashes"]]
    bone_indices = [int(value) for value in skin_data["bone_indices"]]
    bone_weights = [int(value) for value in skin_data["bone_weights"]]
    if len(mesh.data.vertices) != vertex_count:
        raise RuntimeError(
            f"网格顶点数 {len(mesh.data.vertices)} 与蒙皮数据 {vertex_count} 不一致"
        )
    if len(bone_indices) != vertex_count * 4 or len(bone_weights) != vertex_count * 4:
        raise RuntimeError("蒙皮数据不是每顶点四骨骼格式")

    bones_by_hash: dict[int, str] = {}
    for bone in armature.data.bones:
        bone_hash = fnv32_lower(bone.name)
        if bone_hash in bones_by_hash:
            raise RuntimeError(f"骨架模板存在重复骨骼哈希 0x{bone_hash:08X}")
        bones_by_hash[bone_hash] = bone.name

    used_hashes = set()
    for offset, weight in enumerate(bone_weights):
        if weight <= 0:
            continue
        local_bone_index = bone_indices[offset]
        if not 0 <= local_bone_index < len(bone_hashes):
            raise RuntimeError("蒙皮数据引用了不存在的骨骼索引")
        used_hashes.add(bone_hashes[local_bone_index])
    missing_hashes = sorted(used_hashes - set(bones_by_hash))
    if missing_hashes:
        formatted = ", ".join(f"0x{value:08X}" for value in missing_hashes)
        raise RuntimeError(f"骨架模板缺少 GEOM 使用的骨骼：{formatted}")

    grouped_vertices: dict[tuple[str, int], list[int]] = defaultdict(list)
    for vertex_index in range(vertex_count):
        start = vertex_index * 4
        for local_bone_index, weight_byte in zip(
            bone_indices[start : start + 4],
            bone_weights[start : start + 4],
        ):
            if weight_byte <= 0:
                continue
            if local_bone_index >= len(bone_hashes):
                raise RuntimeError(f"顶点 {vertex_index} 引用了不存在的骨骼索引")
            bone_name = bones_by_hash[bone_hashes[local_bone_index]]
            grouped_vertices[(bone_name, weight_byte)].append(vertex_index)

    for group in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(group)
    groups = {
        bone_name: mesh.vertex_groups.new(name=bone_name)
        for bone_name in sorted({key[0] for key in grouped_vertices})
    }
    for (bone_name, weight_byte), vertex_indices in grouped_vertices.items():
        groups[bone_name].add(vertex_indices, weight_byte / 255.0, "REPLACE")

    for modifier in list(mesh.modifiers):
        if modifier.type == "ARMATURE":
            mesh.modifiers.remove(modifier)
    modifier = mesh.modifiers.new(name="TS4 Armature", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    mesh.parent = None
    return {
        "bone_count": len(armature.data.bones),
        "weighted_bone_count": len(groups),
        "weighted_vertex_count": vertex_count,
        "missing_bone_hashes": [],
    }


def _arm_drop_angle_degrees(
    armature: bpy.types.Object,
    upper_arm_name: str,
    forearm_name: str,
) -> float:
    upper_arm = armature.data.bones[upper_arm_name]
    forearm = armature.data.bones[forearm_name]
    direction = forearm.head_local - upper_arm.head_local
    horizontal = max(abs(direction.x), 0.0000001)
    return abs(math.degrees(math.atan2(direction.z, horizontal)))


def convert_to_t_pose(
    mesh: bpy.types.Object,
    armature: bpy.types.Object,
) -> dict:
    arm_chains = (
        ("b__L_UpperArm__", "b__L_Forearm__", 1.0),
        ("b__R_UpperArm__", "b__R_Forearm__", -1.0),
    )
    missing = [
        name
        for upper_arm, forearm, _side in arm_chains
        for name in (upper_arm, forearm)
        if armature.data.bones.get(name) is None
    ]
    if missing:
        raise RuntimeError(f"骨架模板缺少 T-Pose 手臂骨骼：{', '.join(missing)}")

    source_angles = {}
    inward_offsets = {}
    for upper_arm_name, forearm_name, side in arm_chains:
        upper_arm = armature.data.bones[upper_arm_name]
        forearm = armature.data.bones[forearm_name]
        current_direction = forearm.head_local - upper_arm.head_local
        target_direction = Vector((side * current_direction.length, 0.0, 0.0))
        rotation = current_direction.rotation_difference(target_direction)
        pivot = Matrix.Translation(upper_arm.head_local)
        inward_offset = current_direction.length * ARM_INWARD_OFFSET_RATIO
        inward_translation = Matrix.Translation(
            Vector((-side * inward_offset, 0.0, 0.0))
        )
        pose_bone = armature.pose.bones[upper_arm_name]
        pose_bone.matrix = (
            inward_translation
            @ pivot
            @ rotation.to_matrix().to_4x4()
            @ pivot.inverted()
            @ pose_bone.matrix
        )
        inward_offsets[upper_arm_name] = inward_offset
        source_angles[upper_arm_name] = _arm_drop_angle_degrees(
            armature, upper_arm_name, forearm_name
        )

    bpy.context.view_layer.update()
    source_vertex_count = len(mesh.data.vertices)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_mesh = mesh.evaluated_get(depsgraph)
    baked_mesh = bpy.data.meshes.new_from_object(
        evaluated_mesh,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    if len(baked_mesh.vertices) != source_vertex_count:
        bpy.data.meshes.remove(baked_mesh)
        raise RuntimeError("T-Pose 固化改变了网格拓扑，已停止导出")

    old_mesh = mesh.data
    for modifier in list(mesh.modifiers):
        if modifier.type == "ARMATURE":
            mesh.modifiers.remove(modifier)
    mesh.data = baked_mesh
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)

    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    modifier = mesh.modifiers.new(name="TS4 Armature", type="ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    bpy.context.view_layer.update()
    target_angles = {
        upper_arm_name: _arm_drop_angle_degrees(
            armature, upper_arm_name, forearm_name
        )
        for upper_arm_name, forearm_name, _side in arm_chains
    }
    return {
        "rest_pose": "T-pose",
        "pose_reference": (
            "HS2 horizontal shoulder-elbow-wrist alignment with "
            f"{ARM_INWARD_OFFSET_RATIO:.0%} upper-arm-length inward offset"
        ),
        "arm_inward_offset_ratio": ARM_INWARD_OFFSET_RATIO,
        "arm_inward_offset": round(
            sum(inward_offsets.values()) / len(inward_offsets), 6
        ),
        "source_arm_drop_degrees": round(
            sum(source_angles.values()) / len(source_angles), 3
        ),
        "target_arm_drop_degrees": round(
            sum(target_angles.values()) / len(target_angles), 3
        ),
    }


def remove_rigging_data(
    mesh: bpy.types.Object,
    armature: bpy.types.Object,
) -> dict:
    source_bone_count = len(armature.data.bones)
    source_weighted_bone_count = len(mesh.vertex_groups)
    for group in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(group)
    for modifier in list(mesh.modifiers):
        if modifier.type == "ARMATURE":
            mesh.modifiers.remove(modifier)
    mesh.parent = None
    armature_data = armature.data
    bpy.data.objects.remove(armature, do_unlink=True)
    if armature_data.users == 0:
        bpy.data.armatures.remove(armature_data)
    bpy.context.view_layer.update()
    return {
        "rigged": False,
        "t_pose_baked": True,
        "skin_data_removed": True,
        "bone_count": 0,
        "weighted_bone_count": 0,
        "weighted_vertex_count": 0,
        "source_bone_count": source_bone_count,
        "source_weighted_bone_count": source_weighted_bone_count,
        "removed_vertex_group_count": source_weighted_bone_count,
    }


def _position_key(co: Vector) -> tuple[int, int, int]:
    return tuple(
        round(float(axis) / REVERSE_FACE_POSITION_TOLERANCE) for axis in co
    )


def _face_key(face: bmesh.types.BMFace) -> tuple:
    return (
        len(face.verts),
        tuple(sorted(_position_key(vertex.co) for vertex in face.verts)),
    )


def _mesh_center(bm: bmesh.types.BMesh) -> Vector:
    if not bm.verts:
        return Vector((0.0, 0.0, 0.0))
    minimum = Vector((float("inf"),) * 3)
    maximum = Vector((float("-inf"),) * 3)
    for vertex in bm.verts:
        for axis in range(3):
            minimum[axis] = min(minimum[axis], vertex.co[axis])
            maximum[axis] = max(maximum[axis], vertex.co[axis])
    return (minimum + maximum) * 0.5


def _corner_normal_alignment(mesh: bpy.types.Mesh) -> dict[int, float]:
    """Measure whether each face winding agrees with imported split normals."""

    try:
        corner_normals = mesh.corner_normals
        if len(corner_normals) != len(mesh.loops):
            return {}
        result = {}
        for polygon in mesh.polygons:
            average = Vector((0.0, 0.0, 0.0))
            for loop_index in polygon.loop_indices:
                average += corner_normals[loop_index].vector
            result[polygon.index] = (
                polygon.normal.dot(average.normalized())
                if average.length_squared > 0.0
                else 0.0
            )
        return result
    except (AttributeError, RuntimeError):
        return {}


def cleanup_reverse_duplicate_triangles(mesh_object: bpy.types.Object) -> dict:
    """Remove only unambiguous, coincident, opposite-facing triangle copies."""

    mesh = mesh_object.data
    custom_alignment = _corner_normal_alignment(mesh)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        center = _mesh_center(bm)
        groups = defaultdict(list)
        for face in bm.faces:
            groups[_face_key(face)].append(face)

        removal = set()
        statistics = {
            "reverse_duplicate_groups_detected": 0,
            "reverse_duplicate_faces_removed": 0,
            "reverse_duplicate_ambiguous_groups": 0,
            "reverse_duplicate_material_mismatch_groups": 0,
            "reverse_duplicate_multi_face_groups": 0,
            "reverse_duplicate_custom_normal_decisions": 0,
            "reverse_duplicate_center_direction_decisions": 0,
        }
        for faces in groups.values():
            if len(faces) < 2:
                continue
            if len(faces) != 2:
                statistics["reverse_duplicate_multi_face_groups"] += 1
                continue
            first, second = faces
            if len(first.verts) != 3 or len(second.verts) != 3:
                continue
            if first.normal.dot(second.normal) > REVERSE_FACE_NORMAL_DOT:
                continue
            statistics["reverse_duplicate_groups_detected"] += 1
            if first.material_index != second.material_index:
                statistics["reverse_duplicate_material_mismatch_groups"] += 1
                continue

            first_alignment = custom_alignment.get(first.index, 0.0)
            second_alignment = custom_alignment.get(second.index, 0.0)
            if abs(first_alignment - second_alignment) > REVERSE_FACE_SCORE_EPSILON:
                removal.add(second if first_alignment > second_alignment else first)
                statistics["reverse_duplicate_custom_normal_decisions"] += 1
                continue

            first_outward = first.normal.dot(first.calc_center_median() - center)
            second_outward = second.normal.dot(second.calc_center_median() - center)
            if abs(first_outward - second_outward) > REVERSE_FACE_SCORE_EPSILON:
                removal.add(second if first_outward > second_outward else first)
                statistics["reverse_duplicate_center_direction_decisions"] += 1
            else:
                statistics["reverse_duplicate_ambiguous_groups"] += 1

        statistics["reverse_duplicate_faces_removed"] = len(removal)
        if removal:
            # FACES also removes edges/vertices used only by the rejected copy.
            bmesh.ops.delete(bm, geom=list(removal), context="FACES")
            bm.normal_update()
            bm.to_mesh(mesh)
            mesh.update(calc_edges=True)
        statistics["vertices_after_reverse_cleanup"] = len(mesh.vertices)
        statistics["triangles_after_reverse_cleanup"] = len(mesh.polygons)
        return statistics
    finally:
        bm.free()


def export_static_fbx(output_path: Path) -> None:
    temporary_path = output_path.with_name(f"{output_path.stem}.tpose.tmp.fbx")
    bpy.ops.export_scene.fbx(
        filepath=str(temporary_path),
        use_selection=False,
        object_types={"MESH"},
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        axis_forward="Z",
        axis_up="Y",
        use_space_transform=True,
        bake_space_transform=False,
        use_mesh_modifiers=False,
        bake_anim=False,
        path_mode="RELATIVE",
        embed_textures=False,
    )
    os.replace(temporary_path, output_path)


def process_job(ts4_template_path: Path, job: dict) -> dict:
    fbx_path = Path(job["fbx_path"]).resolve()
    skin_path = Path(job["skin_path"]).resolve()
    clear_scene()
    ts4_armature = load_template(ts4_template_path)
    mesh = load_mesh(fbx_path, ts4_armature)
    skin_data = json.loads(skin_path.read_text(encoding="utf-8"))
    statistics = apply_skin(mesh, ts4_armature, skin_data)
    statistics.update(convert_to_t_pose(mesh, ts4_armature))
    statistics.update(remove_rigging_data(mesh, ts4_armature))
    statistics.update(cleanup_reverse_duplicate_triangles(mesh))
    export_static_fbx(fbx_path)
    return {
        "ok": True,
        "fbx_path": str(fbx_path),
        "bytes": fbx_path.stat().st_size,
        **statistics,
    }


def parse_arguments() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--ts4-template", required=True)
    parser.add_argument("--jobs", required=True)
    parser.add_argument("--result", required=True)
    return parser.parse_args(arguments)


def main() -> None:
    args = parse_arguments()
    ts4_template_path = Path(args.ts4_template).resolve()
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    results = []
    for job in jobs:
        try:
            results.append(process_job(ts4_template_path, job))
        except Exception as error:
            results.append(
                {
                    "ok": False,
                    "fbx_path": str(job.get("fbx_path") or ""),
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
    Path(args.result).write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if any(not item["ok"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
