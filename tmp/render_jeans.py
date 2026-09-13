import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--face", type=int, default=-1)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])

bpy.ops.wm.read_factory_settings(use_empty=True)
result = bpy.ops.import_scene.fbx(
    filepath=str(args.input.resolve()),
    use_anim=False,
    use_custom_normals=True,
    ignore_leaf_bones=False,
    automatic_bone_orientation=False,
)
if "FINISHED" not in result:
    raise RuntimeError(result)

meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
for obj in bpy.data.objects:
    if obj.type == "ARMATURE":
        obj.hide_render = True
    if obj.type == "MESH":
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                # Keep the rig intact; disable only for this diagnostic render
                # because the imported rig's unit scale is not the mesh scale.
                modifier.show_render = False

minimum = Vector((float("inf"), float("inf"), float("inf")))
maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
for obj in meshes:
    for vertex in obj.data.vertices:
        position = obj.matrix_world @ vertex.co
        minimum = Vector((min(minimum[i], position[i]) for i in range(3)))
        maximum = Vector((max(maximum[i], position[i]) for i in range(3)))
target = (minimum + maximum) * 0.5
extent = max((maximum - minimum).length, 1.0)
if args.face >= 0:
    mesh_obj = meshes[0]
    polygon = mesh_obj.data.polygons[args.face]
    target = mesh_obj.matrix_world @ (
        sum((mesh_obj.data.vertices[index].co for index in polygon.vertices), Vector())
        / len(polygon.vertices)
    )

camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera)
bpy.context.scene.camera = camera
if args.face >= 0:
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.025
    camera.location = target + Vector((0.0, 0.0, -0.2))
else:
    camera.location = target + Vector((0.0, 0.0, -extent * 2.4))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.lens = 55

for name, location, energy, size in (
    ("Key", target + Vector((4.0, 7.0, -8.0)), 1000.0, 5.0),
    ("Fill", target + Vector((-5.0, 4.0, -4.0)), 700.0, 4.0),
    ("Rim", target + Vector((0.0, 4.0, 8.0)), 500.0, 3.0),
):
    light_data = bpy.data.lights.new(name, type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(args.output.resolve())
scene.world = bpy.data.worlds.new("World")
scene.world.color = (0.035, 0.035, 0.035)
scene.render.film_transparent = False
bpy.ops.render.render(write_still=True)
print(f"rendered {args.output}")
