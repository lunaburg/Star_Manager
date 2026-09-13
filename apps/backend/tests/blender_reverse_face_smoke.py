from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import bpy


script_path = (
    Path(__file__).resolve().parents[2]
    / "resources"
    / "sims4"
    / "attach_ts4_skin_blender.py"
)
spec = importlib.util.spec_from_file_location("attach_ts4_skin_blender", script_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

def create_object(name, vertices, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


bpy.ops.wm.read_factory_settings(use_empty=True)
# The first two faces overlap with opposite winding.  The unrelated lower face
# gives the object a meaningful inside/outside direction for the upper shell.
decidable = create_object(
    "reverse-face-decidable",
    [
        (-2.0, -1.0, 1.0),
        (0.0, -1.0, 1.0),
        (-1.0, 1.0, 1.0),
        (-2.0, -1.0, 1.0),
        (-1.0, 1.0, 1.0),
        (0.0, -1.0, 1.0),
        (1.0, -1.0, -1.0),
        (3.0, -1.0, -1.0),
        (2.0, 1.0, -1.0),
    ],
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)],
)

result = module.cleanup_reverse_duplicate_triangles(decidable)
assert result["reverse_duplicate_groups_detected"] == 1, result
assert result["reverse_duplicate_faces_removed"] == 1, result
assert result["reverse_duplicate_ambiguous_groups"] == 0, result
assert len(decidable.data.polygons) == 2, result
assert len(decidable.data.vertices) == 6, result

# A planar isolated pair has no defensible outward side and must remain intact.
ambiguous = create_object(
    "reverse-face-ambiguous",
    [
        (-1.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (0.0, 1.0, 0.0),
        (-1.0, -1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, -1.0, 0.0),
    ],
    [(0, 1, 2), (3, 4, 5)],
)
ambiguous_result = module.cleanup_reverse_duplicate_triangles(ambiguous)
assert ambiguous_result["reverse_duplicate_groups_detected"] == 1, ambiguous_result
assert ambiguous_result["reverse_duplicate_faces_removed"] == 0, ambiguous_result
assert ambiguous_result["reverse_duplicate_ambiguous_groups"] == 1, ambiguous_result
assert len(ambiguous.data.polygons) == 2, ambiguous_result
print(json.dumps({"decidable": result, "ambiguous": ambiguous_result}, ensure_ascii=False, sort_keys=True))
