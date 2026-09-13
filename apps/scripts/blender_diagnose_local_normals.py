"""Find face normals that disagree with nearby geometric faces.

This catches isolated/disconnected flipped triangles that shared-edge parity
cannot see, while leaving the source FBX untouched.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--neighbors", type=int, default=16)
    parser.add_argument("--radius", type=float, default=0.18)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def vec(value):
    return [round(float(component), 8) for component in value]


def main():
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(
        filepath=str(args.input.resolve()),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX import failed: {sorted(result)}")

    report = {"input": str(args.input.resolve()), "objects": []}
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        mesh = obj.data
        mesh.update(calc_edges=True)
        polygons = list(mesh.polygons)
        centers = [sum((mesh.vertices[index].co for index in polygon.vertices), Vector((0.0, 0.0, 0.0))) / len(polygon.vertices) for polygon in polygons]
        normals = [polygon.normal.normalized() if polygon.normal.length else Vector() for polygon in polygons]
        tree = KDTree(len(polygons))
        for index, center in enumerate(centers):
            tree.insert(center, index)
        tree.balance()

        faces = []
        for index, polygon in enumerate(polygons):
            neighbors = []
            for co, other_index, distance in tree.find_n(centers[index], args.neighbors + 1):
                if other_index == index or distance > args.radius:
                    continue
                neighbors.append((other_index, distance))
            if len(neighbors) < 3:
                continue
            weighted = Vector((0.0, 0.0, 0.0))
            for other_index, distance in neighbors:
                weighted += normals[other_index] / max(distance, 1.0e-5)
            if weighted.length == 0:
                continue
            alignment = float(normals[index].dot(weighted.normalized()))
            opposite_count = sum(1 for other_index, _ in neighbors if normals[index].dot(normals[other_index]) < -0.2)
            faces.append(
                {
                    "face": index,
                    "vertices": list(polygon.vertices),
                    "center": vec(centers[index]),
                    "normal": vec(normals[index]),
                    "area": round(float(polygon.area), 10),
                    "neighbor_count": len(neighbors),
                    "opposite_neighbor_count": opposite_count,
                    "local_alignment": round(alignment, 8),
                    "neighbors": [
                        {"face": other_index, "distance": round(float(distance), 8), "dot": round(float(normals[index].dot(normals[other_index])), 8)}
                        for other_index, distance in neighbors
                    ],
                }
            )

        faces.sort(key=lambda item: float(item["local_alignment"]))
        report["objects"].append(
            {
                "object": obj.name,
                "mesh": mesh.name,
                "vertices": len(mesh.vertices),
                "polygons": len(mesh.polygons),
                "radius": args.radius,
                "neighbors": args.neighbors,
                "lowest_alignment": faces[0]["local_alignment"] if faces else None,
                "faces": faces[:200],
            }
        )

    args.output.resolve().write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "objects": len(report["objects"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
