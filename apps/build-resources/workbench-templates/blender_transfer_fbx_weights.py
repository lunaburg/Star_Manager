"""Transfer skin weights from a skinned FBX to a skeleton-only FBX.

The default method mirrors Maya's ``Copy Skin Weights`` much more closely than
nearest-vertex copying: each target vertex is projected onto the closest
triangle of the source surface and the three triangle-vertex weights are
interpolated with barycentric coordinates.  The result is normalized and, by
default, no arbitrary four-influence limit is applied.  ``--max-influences``
can be used for runtimes that require a fixed limit (for example ``4`` for a
strict game-export pipeline).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transfer FBX skin weights by closest-surface interpolation.")
    parser.add_argument("--source", required=True, type=Path, help="Skinned source FBX")
    parser.add_argument("--target", required=True, type=Path, help="Skeleton-only target FBX")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--method",
        choices=("surface", "vertices"),
        default="surface",
        help="surface = Maya-like closest triangle interpolation; vertices = legacy nearest-vertex mode",
    )
    parser.add_argument("--neighbors", type=int, default=4, help="Nearest source vertices in legacy vertices mode")
    parser.add_argument(
        "--max-influences",
        type=int,
        default=0,
        help="Maximum influences per vertex; 0 keeps all interpolated influences (Maya-like)",
    )
    parser.add_argument(
        "--weight-threshold",
        type=float,
        default=1e-6,
        help="Discard interpolated influences below this value",
    )
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def _validate_fbx(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.suffix.lower() != ".fbx":
        raise ValueError(f"{label} must be a valid .fbx file")
    return resolved


def _import_fbx(path: Path) -> None:
    result = bpy.ops.import_scene.fbx(
        filepath=str(path),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=True,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX import failed: {sorted(result)}")


def _canonical_bone_name(name: str) -> str:
    value = str(name or "").replace("\\", "/").split("/")[-1]
    value = value.split("|")[-1].split(":")[-1]
    return value.casefold()


def _source_vertex_weights(mesh: bpy.types.Object, source_bone_names: set[str]) -> list[dict[str, float]]:
    groups = []
    for group in mesh.vertex_groups:
        canonical = _canonical_bone_name(group.name)
        if canonical in source_bone_names:
            groups.append((canonical, group))
    result: list[dict[str, float]] = []
    for vertex in mesh.data.vertices:
        weights: dict[str, float] = {}
        for canonical, group in groups:
            try:
                weight = float(group.weight(vertex.index))
            except RuntimeError:
                continue
            if weight > 0:
                weights[canonical] = weight
        result.append(weights)
    return result


def _build_bone_mapping(source_mesh: bpy.types.Object, target_armature: bpy.types.Object) -> dict[str, str]:
    target_names = {}
    for bone in target_armature.data.bones:
        target_names.setdefault(_canonical_bone_name(bone.name), bone.name)
    mapping = {}
    for group in source_mesh.vertex_groups:
        canonical = _canonical_bone_name(group.name)
        if canonical in target_names:
            mapping[group.name] = target_names[canonical]
    return mapping


def _build_source_surface(source_mesh: bpy.types.Object):
    """Build a BVH over world-space source triangles and return triangle data."""
    source_mesh.data.calc_loop_triangles()
    world_vertices = [source_mesh.matrix_world @ vertex.co for vertex in source_mesh.data.vertices]
    triangles = [tuple(loop.vertices) for loop in source_mesh.data.loop_triangles]
    if not triangles:
        raise RuntimeError("Source Mesh does not contain any triangles")
    return world_vertices, triangles, BVHTree.FromPolygons(world_vertices, triangles, all_triangles=True)


def _barycentric_weights(point: Vector, a: Vector, b: Vector, c: Vector) -> tuple[float, float, float]:
    """Return stable barycentric coordinates, clamped for tiny BVH errors."""
    ab = b - a
    ac = c - a
    ap = point - a
    d00 = ab.dot(ab)
    d01 = ab.dot(ac)
    d11 = ac.dot(ac)
    d20 = ap.dot(ab)
    d21 = ap.dot(ac)
    denominator = d00 * d11 - d01 * d01
    if abs(denominator) <= 1e-12:
        return 1.0, 0.0, 0.0
    v = (d11 * d20 - d01 * d21) / denominator
    w = (d00 * d21 - d01 * d20) / denominator
    u = 1.0 - v - w
    values = [max(0.0, u), max(0.0, v), max(0.0, w)]
    total = sum(values)
    return tuple(value / total for value in values)


def _combined_weights(source_weights, indices_and_factors, threshold):
    combined: dict[str, float] = {}
    for source_index, factor in indices_and_factors:
        if factor <= 0:
            continue
        for canonical, weight in source_weights[source_index].items():
            combined[canonical] = combined.get(canonical, 0.0) + weight * factor
    total = sum(combined.values())
    if total <= 0:
        return {}
    return {
        canonical: weight / total
        for canonical, weight in combined.items()
        if weight / total > threshold
    }


def _nearest_weight_transfer(
    source_mesh: bpy.types.Object,
    target_mesh: bpy.types.Object,
    target_armature: bpy.types.Object,
    neighbors: int,
    method: str = "surface",
    max_influences: int = 0,
    weight_threshold: float = 1e-6,
) -> tuple[int, float, int]:
    source_bones = {_canonical_bone_name(bone.name) for bone in target_armature.data.bones}
    source_weights = _source_vertex_weights(source_mesh, source_bones)
    mapping = _build_bone_mapping(source_mesh, target_armature)
    if not mapping:
        raise RuntimeError("No source vertex groups match the target Armature bones")

    for group in list(target_mesh.vertex_groups):
        target_mesh.vertex_groups.remove(group)
    target_groups = {bone.name: target_mesh.vertex_groups.new(name=bone.name) for bone in target_armature.data.bones if bone.name in mapping.values()}
    if not target_groups:
        raise RuntimeError("No target vertex groups could be created from the source weights")

    source_world_vertices = []
    source_triangles = []
    surface_tree = None
    vertex_tree = None
    if method == "surface":
        source_world_vertices, source_triangles, surface_tree = _build_source_surface(source_mesh)
    else:
        from mathutils import kdtree

        vertex_tree = kdtree.KDTree(len(source_mesh.data.vertices))
        for vertex in source_mesh.data.vertices:
            vertex_tree.insert(source_mesh.matrix_world @ vertex.co, vertex.index)
        vertex_tree.balance()
        neighbor_count = max(1, min(int(neighbors), len(source_mesh.data.vertices)))

    weighted_vertices = 0
    distance_sum = 0.0
    for target_vertex in target_mesh.data.vertices:
        target_world = target_mesh.matrix_world @ target_vertex.co
        if method == "surface":
            location, _normal, triangle_index, distance = surface_tree.find_nearest(target_world)
            if triangle_index is None:
                continue
            a, b, c = source_triangles[triangle_index]
            factors = _barycentric_weights(
                location,
                source_world_vertices[a],
                source_world_vertices[b],
                source_world_vertices[c],
            )
            indices_and_factors = ((a, factors[0]), (b, factors[1]), (c, factors[2]))
            distance_sum += float(distance)
        else:
            nearest = vertex_tree.find_n(target_world, neighbor_count)
            indices_and_factors = []
            total_distance_weight = 0.0
            for _co, source_index, distance in nearest:
                distance_weight = 1.0 / max(float(distance) ** 2, 1e-12)
                total_distance_weight += distance_weight
                indices_and_factors.append((source_index, distance_weight))
                distance_sum += float(distance)
            if total_distance_weight > 0:
                indices_and_factors = [
                    (index, factor / total_distance_weight)
                    for index, factor in indices_and_factors
                ]
        combined = _combined_weights(source_weights, indices_and_factors, max(0.0, float(weight_threshold)))
        if max_influences > 0 and len(combined) > max_influences:
            combined = dict(sorted(combined.items(), key=lambda item: item[1], reverse=True)[:max_influences])
        total_weight = sum(combined.values())
        if total_weight <= 0:
            continue
        for canonical, weight in combined.items():
            target_name = next((name for name in target_groups if _canonical_bone_name(name) == canonical), "")
            if target_name:
                target_groups[target_name].add([target_vertex.index], weight / total_weight, "REPLACE")
        weighted_vertices += 1

    modifier = next((modifier for modifier in target_mesh.modifiers if modifier.type == "ARMATURE"), None)
    if modifier is None:
        modifier = target_mesh.modifiers.new(name="HS2 Armature", type="ARMATURE")
    modifier.object = target_armature
    distance_divisor = len(target_mesh.data.vertices)
    if method == "vertices":
        distance_divisor *= neighbor_count
    average_distance = distance_sum / max(1, distance_divisor)
    return len(target_groups), average_distance, weighted_vertices


def _normalize_mesh_transforms(target_meshes: list[bpy.types.Object]) -> None:
    """Bake FBX compensation so SB3Utility sees identity mesh transforms."""
    for index, mesh in enumerate(target_meshes):
        local_matrix = mesh.matrix_basis.copy()
        mesh.data.transform(local_matrix)
        mesh.location = (0.0, 0.0, 0.0)
        mesh.rotation_mode = "XYZ"
        mesh.rotation_euler = (0.0, 0.0, 0.0)
        mesh.scale = (1.0, 1.0, 1.0)
        safe_name = f"Mesh_{index}"
        mesh.name = safe_name
        mesh.data.name = safe_name


def _remove_source_objects(target_objects: set[bpy.types.Object]) -> None:
    for obj in list(bpy.context.scene.objects):
        if obj not in target_objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def _export(output_path: Path, target_meshes: list[bpy.types.Object], target_armature: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in target_meshes:
        mesh.select_set(True)
    target_armature.select_set(True)
    bpy.context.view_layer.objects.active = target_armature
    result = bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        object_types={"MESH", "ARMATURE"},
        use_mesh_modifiers=False,
        use_mesh_edges=False,
        use_tspace=True,
        use_custom_props=True,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
        axis_forward="-Z",
        axis_up="Y",
        apply_unit_scale=True,
        use_space_transform=True,
        bake_space_transform=False,
        apply_scale_options="FBX_SCALE_NONE",
    )
    if "FINISHED" not in result or not output_path.is_file():
        raise RuntimeError(f"FBX export failed: {sorted(result)}")


def main() -> int:
    args = _parse_args()
    source = _validate_fbx(args.source, "Source skinned FBX")
    target = _validate_fbx(args.target, "Target skeleton-only FBX")
    output = args.output.expanduser().resolve()
    if source == target:
        raise ValueError("Source and target FBX must be different files")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f".{output.stem}.tmp-{os.getpid()}{output.suffix}")
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _import_fbx(target)
        target_objects = set(bpy.context.scene.objects)
        target_meshes = [obj for obj in target_objects if obj.type == "MESH"]
        target_armatures = [obj for obj in target_objects if obj.type == "ARMATURE"]
        if not target_meshes or not target_armatures:
            raise RuntimeError("Target FBX must contain a Mesh and an Armature")
        target_armature = target_armatures[0]

        _import_fbx(source)
        source_objects = [obj for obj in bpy.context.scene.objects if obj not in target_objects]
        source_meshes = [obj for obj in source_objects if obj.type == "MESH"]
        if not source_meshes:
            raise RuntimeError("Source FBX does not contain a skinned Mesh")
        source_mesh = max(source_meshes, key=lambda obj: len(obj.data.vertices))
        if not source_mesh.vertex_groups:
            raise RuntimeError("Source Mesh does not contain vertex-group weights")

        total_groups = 0
        total_distance = 0.0
        total_weighted_vertices = 0
        for mesh in target_meshes:
            groups, distance, weighted_vertices = _nearest_weight_transfer(
                source_mesh,
                mesh,
                target_armature,
                args.neighbors,
                args.method,
                args.max_influences,
                args.weight_threshold,
            )
            total_groups = max(total_groups, groups)
            total_distance += distance
            total_weighted_vertices += weighted_vertices
        _normalize_mesh_transforms(target_meshes)
        _remove_source_objects(target_objects)
        _export(temp_output, target_meshes, target_armature)
        os.replace(temp_output, output)

        print(json.dumps({
            "ok": True,
            "source": str(source),
            "target": str(target),
            "output": str(output),
            "mesh_count": len(target_meshes),
            "bone_count": len(target_armature.data.bones),
            "mapped_group_count": total_groups,
            "weighted_vertex_count": total_weighted_vertices,
            "average_nearest_distance": total_distance / max(1, len(target_meshes)),
            "method": args.method,
            "max_influences": max(0, int(args.max_influences)),
            "armature_modifiers": sum(
                sum(1 for modifier in mesh.modifiers if modifier.type == "ARMATURE")
                for mesh in target_meshes
            ),
        }, ensure_ascii=False))
        return 0
    finally:
        if temp_output.exists():
            temp_output.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        raise
