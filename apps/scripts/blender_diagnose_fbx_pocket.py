"""Dump local geometry, normals, UVs, and material data for a suspected FBX region.

Run through Blender:
    blender.exe --background --factory-startup --python this_file.py -- \
      --input source.fbx --output report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--x-max", type=float, default=1.2)
    parser.add_argument("--y-min", type=float, default=10.0)
    parser.add_argument("--y-max", type=float, default=11.6)
    parser.add_argument("--z-max", type=float, default=1.4)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def vector(value: Vector) -> list[float]:
    return [round(float(component), 8) for component in value]


def main() -> int:
    parsed = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(
        filepath=str(parsed.input.resolve()),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX import failed: {sorted(result)}")

    report: dict[str, object] = {
        "input": str(parsed.input.resolve()),
        "objects": [],
        "candidate_faces": [],
    }
    candidates: list[dict[str, object]] = []
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        mesh = obj.data
        mesh.update(calc_edges=True)
        object_info = {
            "name": obj.name,
            "mesh": mesh.name,
            "vertices": len(mesh.vertices),
            "polygons": len(mesh.polygons),
            "loops": len(mesh.loops),
            "uv_layers": list(mesh.uv_layers.keys()),
            "materials": [material.name if material else None for material in mesh.materials],
            "matrix_world": [list(row) for row in obj.matrix_world],
            "bounds_min": vector(min((obj.matrix_world @ v.co for v in mesh.vertices), key=lambda v: v.x + v.y + v.z)),
            "bounds_max": vector(max((obj.matrix_world @ v.co for v in mesh.vertices), key=lambda v: v.x + v.y + v.z)),
        }
        report["objects"].append(object_info)

        for polygon in mesh.polygons:
            center = sum((mesh.vertices[index].co for index in polygon.vertices), Vector()) / len(polygon.vertices)
            if abs(center.x) > parsed.x_max or not (parsed.y_min <= center.y <= parsed.y_max) or center.z > parsed.z_max:
                continue
            average_corner = sum((mesh.corner_normals[index].vector for index in polygon.loop_indices), Vector())
            local_face_normal = polygon.normal.normalized() if polygon.normal.length else Vector()
            corner_average_normal = average_corner.normalized() if average_corner.length else Vector()
            loops: list[dict[str, object]] = []
            for loop_index in polygon.loop_indices:
                loop = mesh.loops[loop_index]
                loop_info: dict[str, object] = {
                    "loop": loop_index,
                    "vertex": loop.vertex_index,
                    "normal": vector(mesh.corner_normals[loop_index].vector),
                }
                for uv_layer in mesh.uv_layers:
                    uv = uv_layer.data[loop_index].uv
                    loop_info[uv_layer.name] = [round(float(uv.x), 8), round(float(uv.y), 8)]
                loops.append(loop_info)
            candidates.append(
                {
                    "object": obj.name,
                    "face": polygon.index,
                    "center": vector(center),
                    "vertices": list(polygon.vertices),
                    "normal": vector(local_face_normal),
                    "corner_average_normal": vector(corner_average_normal),
                    "normal_alignment": round(float(local_face_normal.dot(corner_average_normal)), 8),
                    "material_index": polygon.material_index,
                    "loops": loops,
                }
            )
    report["candidate_faces"] = sorted(candidates, key=lambda item: (str(item["object"]), int(item["face"])))
    parsed.output.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "objects": len(report["objects"]), "candidate_faces": len(candidates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
