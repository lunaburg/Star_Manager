from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import sqlite3
import struct
import zipfile
from pathlib import Path

import UnityPy
from UnityPy.export.MeshExporter import MeshHandler

from star_manager.core.runtime_paths import runtime_root
from star_manager.services.mod_database_core import DEFAULT_DB_PATH, init_db
from star_manager.services.mod_database_queries import (
    normalize_abdata_path,
    normalize_zip_path,
    resolve_game_abdata_path,
    resolve_game_dir_from_zipmod,
)


DEFAULT_MODEL_PREVIEW_DIR = runtime_root() / "model_previews"
DEFAULT_MANNEQUIN_MODEL_PATH = Path(
    os.environ.get("STAR_MANAGER_MANNEQUIN_FBX", r"D:\Workspace\blender_workspace\hs\body.fbx")
).resolve()
MANNEQUIN_ITEM_KINDS = {"240", "241", "242", "243", "244", "245", "246", "247"}


def resolve_mannequin_model_file() -> Path | None:
    return DEFAULT_MANNEQUIN_MODEL_PATH if DEFAULT_MANNEQUIN_MODEL_PATH.is_file() else None


def _safe_export_name(value: str, fallback: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip()).rstrip(" .")
    return name[:96] or fallback


def _pad(data: bytes, fill: bytes = b"\0") -> bytes:
    return data + fill * ((-len(data)) % 4)


def _finite(value: object) -> float:
    number = float(value)
    return number if math.isfinite(number) else 0.0


def _multiply_matrix(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [sum(left[row][offset] * right[offset][column] for offset in range(4)) for column in range(4)]
        for row in range(4)
    ]


def _transform_world_matrix(transform_id: int, transforms: dict[int, object], cache: dict[int, list[list[float]]]) -> list[list[float]]:
    if transform_id in cache:
        return cache[transform_id]
    transform = transforms[transform_id]
    position = transform.m_LocalPosition
    rotation = transform.m_LocalRotation
    scale = transform.m_LocalScale
    x, y, z, w = (_finite(getattr(rotation, channel)) for channel in "xyzw")
    sx, sy, sz = (_finite(getattr(scale, channel)) for channel in "xyz")
    local = [
        [(1 - 2 * (y * y + z * z)) * sx, (2 * (x * y - z * w)) * sy, (2 * (x * z + y * w)) * sz, _finite(position.x)],
        [(2 * (x * y + z * w)) * sx, (1 - 2 * (x * x + z * z)) * sy, (2 * (y * z - x * w)) * sz, _finite(position.y)],
        [(2 * (x * z - y * w)) * sx, (2 * (y * z + x * w)) * sy, (1 - 2 * (x * x + y * y)) * sz, _finite(position.z)],
        [0.0, 0.0, 0.0, 1.0],
    ]
    parent_id = _pointer_id(transform.m_Father)
    world = _multiply_matrix(_transform_world_matrix(parent_id, transforms, cache), local) if parent_id in transforms else local
    cache[transform_id] = world
    return world


def _gltf_matrix_from_unity(matrix: list[list[float]]) -> list[float]:
    axis_sign = (-1.0, 1.0, 1.0, 1.0)
    return [
        matrix[row][column] * axis_sign[row] * axis_sign[column]
        for column in range(4)
        for row in range(4)
    ]


def _build_glb(meshes: list[tuple], material_specs: list[dict] | None = None) -> bytes:
    binary = bytearray()
    views: list[dict] = []
    accessors: list[dict] = []
    gltf_meshes: list[dict] = []
    nodes: list[dict] = []
    skins: list[dict] = []
    joint_nodes_by_name: dict[str, int] = {}

    def add_view(payload: bytes, target: int | None = None) -> int:
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(payload)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        views.append(view)
        return len(views) - 1

    def add_accessor(view: int, component_type: int, count: int, kind: str, **extra: object) -> int:
        accessors.append({"bufferView": view, "componentType": component_type, "count": count, "type": kind, **extra})
        return len(accessors) - 1

    for mesh_entry in meshes:
        name, mesh = mesh_entry[:2]
        material_slots = mesh_entry[2] if len(mesh_entry) > 2 else []
        skin_spec = mesh_entry[3] if len(mesh_entry) > 3 else None
        node_matrix = mesh_entry[4] if len(mesh_entry) > 4 else None
        vertices = [[-_finite(v[0]), _finite(v[1]), _finite(v[2])] for v in mesh.m_Vertices]
        if not vertices:
            continue
        position_bytes = b"".join(struct.pack("<3f", *value) for value in vertices)
        position = add_accessor(
            add_view(position_bytes, 34962), 5126, len(vertices), "VEC3",
            min=[min(v[i] for v in vertices) for i in range(3)],
            max=[max(v[i] for v in vertices) for i in range(3)],
        )
        attributes: dict[str, int] = {"POSITION": position}
        if mesh.m_Normals and len(mesh.m_Normals) == len(vertices):
            normals = [[-_finite(v[0]), _finite(v[1]), _finite(v[2])] for v in mesh.m_Normals]
            attributes["NORMAL"] = add_accessor(
                add_view(b"".join(struct.pack("<3f", *value) for value in normals), 34962),
                5126, len(normals), "VEC3",
            )
        if mesh.m_UV0 and len(mesh.m_UV0) == len(vertices):
            uvs = [[_finite(v[0]), 1.0 - _finite(v[1])] for v in mesh.m_UV0]
            attributes["TEXCOORD_0"] = add_accessor(
                add_view(b"".join(struct.pack("<2f", *value) for value in uvs), 34962),
                5126, len(uvs), "VEC2",
            )
        if skin_spec and len(skin_spec["indices"]) == len(vertices) and len(skin_spec["weights"]) == len(vertices):
            attributes["JOINTS_0"] = add_accessor(
                add_view(b"".join(struct.pack("<4H", *(int(index) for index in value)) for value in skin_spec["indices"]), 34962),
                5123, len(vertices), "VEC4",
            )
            attributes["WEIGHTS_0"] = add_accessor(
                add_view(b"".join(struct.pack("<4f", *(_finite(weight) for weight in value)) for value in skin_spec["weights"]), 34962),
                5126, len(vertices), "VEC4",
            )

        primitives = []
        for submesh_index, triangles in enumerate(mesh.get_triangles()):
            indices = [index for triangle in triangles for index in (int(triangle[2]), int(triangle[1]), int(triangle[0]))]
            if not indices:
                continue
            component_type = 5123 if max(indices) <= 65535 else 5125
            pattern = "<H" if component_type == 5123 else "<I"
            accessor = add_accessor(
                add_view(b"".join(struct.pack(pattern, index) for index in indices), 34963),
                component_type, len(indices), "SCALAR", min=[min(indices)], max=[max(indices)],
            )
            material_index = material_slots[submesh_index] if submesh_index < len(material_slots) else 0
            primitives.append({"attributes": attributes, "indices": accessor, "material": material_index})
        if primitives:
            gltf_meshes.append({"name": name or "Mesh", "primitives": primitives})
            mesh_node = {"name": name or "Mesh", "mesh": len(gltf_meshes) - 1}
            if node_matrix:
                mesh_node["matrix"] = node_matrix
            nodes.append(mesh_node)
            if skin_spec:
                joint_nodes = []
                for bone_index, bone_name in enumerate(skin_spec["bone_names"]):
                    if bone_name not in joint_nodes_by_name:
                        joint_nodes_by_name[bone_name] = len(nodes)
                        nodes.append({
                            "name": bone_name,
                            "extras": {"fallbackBoneNames": skin_spec["fallback_bone_names"][bone_index]},
                        })
                    joint_nodes.append(joint_nodes_by_name[bone_name])
                bind_payload = b"".join(
                    struct.pack("<16f", *matrix)
                    for matrix in skin_spec["inverse_bind_matrices"]
                )
                inverse_bind_accessor = add_accessor(
                    add_view(bind_payload), 5126, len(joint_nodes), "MAT4",
                )
                skins.append({"joints": joint_nodes, "inverseBindMatrices": inverse_bind_accessor})
                mesh_node["skin"] = len(skins) - 1

    if not gltf_meshes:
        raise ValueError("资源中没有可显示的网格")
    materials = []
    images = []
    textures = []
    for spec in material_specs or [{}]:
        color = spec.get("color", [0.72, 0.78, 0.86, 1])
        material = {
            "name": spec.get("name", "预览材质"),
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": spec.get("metallic", 0.05),
                "roughnessFactor": spec.get("roughness", 0.68),
            },
            "doubleSided": True,
        }
        for image_key, texture_key in (("base_color_png", "baseColorTexture"), ("normal_png", "normalTexture")):
            payload = spec.get(image_key)
            if not payload:
                continue
            images.append({"bufferView": add_view(payload), "mimeType": "image/png", "name": spec.get("name", "Texture")})
            textures.append({"source": len(images) - 1, "sampler": 0})
            texture_ref = {"index": len(textures) - 1}
            if texture_key == "baseColorTexture":
                material["pbrMetallicRoughness"][texture_key] = texture_ref
            else:
                material[texture_key] = texture_ref
        if color[3] < 0.999 or spec.get("transparent"):
            material["alphaMode"] = "BLEND"
        materials.append(material)

    document = {
        "asset": {"version": "2.0", "generator": "Star Manager / UnityPy"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": materials,
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": views,
        "accessors": accessors,
    }
    if images:
        document["images"] = images
        document["textures"] = textures
        document["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
    if skins:
        document["skins"] = skins
    json_chunk = _pad(json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = _pad(bytes(binary))
    length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return b"glTF" + struct.pack("<II", 2, length) + struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk + struct.pack("<I4s", len(bin_chunk), b"BIN\0") + bin_chunk


def _fbx_array(values: list[object]) -> str:
    return ",".join(f"{value:.9g}" if isinstance(value, float) else str(value) for value in values)


def _build_fbx_ascii(meshes: list[tuple], material_specs: list[dict], texture_files: dict[int, tuple[str, str]]) -> str:
    object_lines: list[str] = []
    connection_lines: list[str] = []
    next_id = 100000
    material_ids: dict[int, int] = {}
    texture_ids: dict[int, tuple[int, int]] = {}

    for material_index, spec in enumerate(material_specs):
        material_id = next_id
        next_id += 1
        material_ids[material_index] = material_id
        color = spec.get("color", [0.72, 0.78, 0.86, 1])
        name = _safe_export_name(spec.get("name", "Material"), f"Material_{material_index}")
        object_lines.append(
            f'''    Material: {material_id}, "Material::{name}", "" {{
        Version: 102
        ShadingModel: "phong"
        MultiLayer: 0
        Properties70:  {{
            P: "DiffuseColor", "Color", "", "A",{color[0]},{color[1]},{color[2]}
            P: "DiffuseFactor", "Number", "", "A",1
            P: "TransparencyFactor", "Number", "", "A",{1.0 - float(color[3])}
            P: "Shininess", "double", "Number", "",{max(0.0, (1.0 - float(spec.get('roughness', 0.68))) * 100.0)}
        }}
    }}'''
        )
        if material_index in texture_files:
            absolute_path, relative_path = texture_files[material_index]
            absolute_fbx_path = absolute_path.replace("\\", "/")
            relative_fbx_path = relative_path.replace("\\", "/")
            texture_id, video_id = next_id, next_id + 1
            next_id += 2
            texture_ids[material_index] = (texture_id, video_id)
            object_lines.append(
                f'''    Video: {video_id}, "Video::{name}", "Clip" {{
        Type: "Clip"
        Filename: "{absolute_fbx_path}"
        RelativeFilename: "{relative_fbx_path}"
    }}
    Texture: {texture_id}, "Texture::{name}", "" {{
        Type: "TextureVideoClip"
        Version: 202
        TextureName: "Texture::{name}"
        Media: "Video::{name}"
        FileName: "{absolute_fbx_path}"
        RelativeFilename: "{relative_fbx_path}"
        ModelUVTranslation: 0,0
        ModelUVScaling: 1,1
        Texture_Alpha_Source: "None"
        Cropping: 0,0,0,0
    }}'''
            )
            connection_lines.extend([
                f'    C: "OO",{video_id},{texture_id}',
                f'    C: "OP",{texture_id},{material_id},"DiffuseColor"',
            ])

    exported_mesh_count = 0
    for mesh_entry in meshes:
        name, mesh = mesh_entry[:2]
        slots = mesh_entry[2] if len(mesh_entry) > 2 else []
        triangles_by_submesh = mesh.get_triangles()
        faces: list[tuple[int, int, int]] = []
        face_materials: list[int] = []
        used_materials: list[int] = []
        for submesh_index, triangles in enumerate(triangles_by_submesh):
            material_index = slots[submesh_index] if submesh_index < len(slots) else 0
            if material_index not in used_materials:
                used_materials.append(material_index)
            local_material = used_materials.index(material_index)
            for a, b, c in triangles:
                faces.append((int(c), int(b), int(a)))
                face_materials.append(local_material)
        if not faces or not mesh.m_Vertices:
            continue
        geometry_id, model_id = next_id, next_id + 1
        next_id += 2
        mesh_name = _safe_export_name(name, f"Mesh_{exported_mesh_count}")
        vertices = [component for vertex in mesh.m_Vertices for component in (-_finite(vertex[0]), _finite(vertex[1]), _finite(vertex[2]))]
        polygon_indices = [index for face in faces for index in (face[0], face[1], -face[2] - 1)]
        normal_values: list[float] = []
        uv_values: list[float] = []
        uv_indices: list[int] = []
        has_normals = bool(mesh.m_Normals and len(mesh.m_Normals) == len(mesh.m_Vertices))
        has_uvs = bool(mesh.m_UV0 and len(mesh.m_UV0) == len(mesh.m_Vertices))
        for face in faces:
            for vertex_index in face:
                if has_normals:
                    normal = mesh.m_Normals[vertex_index]
                    normal_values.extend((-_finite(normal[0]), _finite(normal[1]), _finite(normal[2])))
                if has_uvs:
                    uv = mesh.m_UV0[vertex_index]
                    uv_values.extend((_finite(uv[0]), _finite(uv[1])))
                    uv_indices.append(len(uv_indices))
        layers = []
        layer_refs = ['            Type: "LayerElementMaterial"\n            TypedIndex: 0']
        if has_normals:
            layers.append(f'''        LayerElementNormal: 0 {{
            Version: 101
            Name: ""
            MappingInformationType: "ByPolygonVertex"
            ReferenceInformationType: "Direct"
            Normals: *{len(normal_values)} {{ a: {_fbx_array(normal_values)} }}
        }}''')
            layer_refs.insert(0, '            Type: "LayerElementNormal"\n            TypedIndex: 0')
        if has_uvs:
            layers.append(f'''        LayerElementUV: 0 {{
            Version: 101
            Name: "UVChannel_1"
            MappingInformationType: "ByPolygonVertex"
            ReferenceInformationType: "IndexToDirect"
            UV: *{len(uv_values)} {{ a: {_fbx_array(uv_values)} }}
            UVIndex: *{len(uv_indices)} {{ a: {_fbx_array(uv_indices)} }}
        }}''')
            layer_refs.insert(-1, '            Type: "LayerElementUV"\n            TypedIndex: 0')
        layers.append(f'''        LayerElementMaterial: 0 {{
            Version: 101
            Name: ""
            MappingInformationType: "ByPolygon"
            ReferenceInformationType: "IndexToDirect"
            Materials: *{len(face_materials)} {{ a: {_fbx_array(face_materials)} }}
        }}''')
        object_lines.append(f'''    Geometry: {geometry_id}, "Geometry::{mesh_name}", "Mesh" {{
        Vertices: *{len(vertices)} {{ a: {_fbx_array(vertices)} }}
        PolygonVertexIndex: *{len(polygon_indices)} {{ a: {_fbx_array(polygon_indices)} }}
{chr(10).join(layers)}
        Layer: 0 {{
            Version: 100
{chr(10).join(layer_refs)}
        }}
    }}
    Model: {model_id}, "Model::{mesh_name}", "Mesh" {{
        Version: 232
        Properties70:  {{
            P: "Lcl Translation", "Lcl Translation", "", "A",0,0,0
            P: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0
            P: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1
        }}
        Shading: T
        Culling: "CullingOff"
    }}''')
        connection_lines.append(f'    C: "OO",{geometry_id},{model_id}')
        for material_index in used_materials:
            connection_lines.append(f'    C: "OO",{material_ids.get(material_index, material_ids[0])},{model_id}')
        exported_mesh_count += 1
    if not exported_mesh_count:
        raise ValueError("资源中没有可导出的网格")
    return f'''; FBX 7.4.0 project file
FBXHeaderExtension:  {{
    FBXHeaderVersion: 1003
    FBXVersion: 7400
    Creator: "Star Manager / UnityPy"
}}
GlobalSettings:  {{
    Version: 1000
    Properties70:  {{
        P: "UpAxis", "int", "Integer", "",1
        P: "UpAxisSign", "int", "Integer", "",1
        P: "FrontAxis", "int", "Integer", "",2
        P: "FrontAxisSign", "int", "Integer", "",-1
        P: "CoordAxis", "int", "Integer", "",0
        P: "CoordAxisSign", "int", "Integer", "",1
        P: "UnitScaleFactor", "double", "Number", "",100
    }}
}}
Objects:  {{
{chr(10).join(object_lines)}
}}
Connections:  {{
{chr(10).join(connection_lines)}
}}
'''


def _pointer_id(pointer: object) -> int:
    if isinstance(pointer, dict):
        return int(pointer.get("m_PathID", pointer.get("path_id", pointer.get("pathId", 0))) or 0)
    return int(getattr(pointer, "path_id", getattr(pointer, "m_PathID", 0)) or 0)


def _texture_png(pointer: object, cache: dict[int, bytes]) -> bytes | None:
    path_id = _pointer_id(pointer)
    if not path_id:
        return None
    if path_id in cache:
        return cache[path_id]
    try:
        texture = pointer.read()
        image = texture.image
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        cache[path_id] = output.getvalue()
        return cache[path_id]
    except Exception:
        return None


def _renderer_mesh_links(environment: object) -> list[tuple[int, object]]:
    mesh_by_game_object: dict[int, int] = {}
    renderers = []
    for obj in environment.objects:
        if obj.type.name == "MeshFilter":
            mesh_filter = obj.read()
            mesh_by_game_object[_pointer_id(mesh_filter.m_GameObject)] = _pointer_id(mesh_filter.m_Mesh)
        elif obj.type.name in {"MeshRenderer", "SkinnedMeshRenderer"}:
            renderers.append(obj.read())
    links = []
    for renderer in renderers:
        game_object_id = _pointer_id(renderer.m_GameObject)
        mesh_id = _pointer_id(getattr(renderer, "m_Mesh", None)) or mesh_by_game_object.get(game_object_id, 0)
        if mesh_id:
            links.append((mesh_id, renderer))
    return links


def _game_object_descendants(environment: object, root_game_objects: set[int]) -> set[int]:
    transforms = {
        obj.path_id: obj.read()
        for obj in environment.objects
        if obj.type.name in {"Transform", "RectTransform"}
    }
    transform_by_game_object = {
        _pointer_id(transform.m_GameObject): path_id
        for path_id, transform in transforms.items()
    }
    pending = [transform_by_game_object[path_id] for path_id in root_game_objects if path_id in transform_by_game_object]
    descendant_transforms: set[int] = set()
    while pending:
        transform_id = pending.pop()
        if transform_id in descendant_transforms or transform_id not in transforms:
            continue
        descendant_transforms.add(transform_id)
        pending.extend(_pointer_id(child) for child in (transforms[transform_id].m_Children or []))
    return {
        _pointer_id(transforms[path_id].m_GameObject)
        for path_id in descendant_transforms
    } | root_game_objects


_HALF_MODEL_FIELDS = {"objtophalf", "objbothalf", "objbothhalf", "objbottomhalf"}


def _find_pointer_fields(value: object) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in _HALF_MODEL_FIELDS:
                path_id = _pointer_id(child)
                if path_id:
                    found.append((str(key), path_id))
            found.extend(_find_pointer_fields(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.extend(_find_pointer_fields(child))
    return found


def _find_half_model_game_objects(environment: object, item_game_objects: set[int]) -> tuple[set[int], list[dict]]:
    half_game_objects: set[int] = set()
    references: list[dict] = []
    for obj in environment.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        owner_id = _pointer_id(tree.get("m_GameObject", {})) if isinstance(tree, dict) else 0
        if owner_id not in item_game_objects:
            continue
        for field, path_id in _find_pointer_fields(tree):
            half_game_objects.add(path_id)
            references.append({"field": field, "path_id": path_id, "mono_behaviour_path_id": obj.path_id})
    return half_game_objects, references


def _select_main_data_meshes(
    environment: object,
    main_data: str,
    *,
    exclude_half_models: bool = False,
) -> tuple[set[int] | None, str]:
    target = str(main_data or "").strip().lower()
    if not target:
        return None, "all_meshes_empty_main_data"
    game_objects = {
        obj.path_id: obj.read()
        for obj in environment.objects
        if obj.type.name == "GameObject"
    }
    root_game_objects = {
        path_id for path_id, game_object in game_objects.items()
        if str(getattr(game_object, "m_Name", "")).strip().lower() == target
    }
    if not root_game_objects:
        return None, "all_meshes_main_data_not_found"

    descendant_game_objects = _game_object_descendants(environment, root_game_objects)
    mesh_ids = {
        mesh_id
        for mesh_id, renderer in _renderer_mesh_links(environment)
        if _pointer_id(renderer.m_GameObject) in descendant_game_objects
    }
    half_roots, _references = _find_half_model_game_objects(environment, descendant_game_objects) if exclude_half_models else (set(), [])
    if half_roots:
        half_game_objects = _game_object_descendants(environment, half_roots)
        half_mesh_ids = {
            mesh_id
            for mesh_id, renderer in _renderer_mesh_links(environment)
            if _pointer_id(renderer.m_GameObject) in half_game_objects
        }
        mesh_ids.difference_update(half_mesh_ids)
    return mesh_ids, "main_data" if mesh_ids else "main_data_no_renderable_mesh"


def _select_half_model_meshes(environment: object, main_data: str) -> tuple[set[int], list[dict]]:
    target = str(main_data or "").strip().lower()
    game_objects = {
        obj.path_id: obj.read()
        for obj in environment.objects
        if obj.type.name == "GameObject"
    }
    root_game_objects = {
        path_id for path_id, game_object in game_objects.items()
        if str(getattr(game_object, "m_Name", "")).strip().lower() == target
    }
    if not root_game_objects:
        return set(), []
    item_game_objects = _game_object_descendants(environment, root_game_objects)
    half_roots, references = _find_half_model_game_objects(environment, item_game_objects)
    if not half_roots:
        return set(), []
    half_game_objects = _game_object_descendants(environment, half_roots)
    mesh_ids = {
        mesh_id
        for mesh_id, renderer in _renderer_mesh_links(environment)
        if _pointer_id(renderer.m_GameObject) in half_game_objects
    }
    return mesh_ids, references


def _select_variant_game_objects(environment: object, main_data: str, *, half: bool = False) -> set[int]:
    target = str(main_data or "").strip().lower()
    game_objects = {
        obj.path_id: obj.read()
        for obj in environment.objects
        if obj.type.name == "GameObject"
    }
    root_game_objects = {
        path_id for path_id, game_object in game_objects.items()
        if str(getattr(game_object, "m_Name", "")).strip().lower() == target
    }
    if not root_game_objects:
        return set()
    item_game_objects = _game_object_descendants(environment, root_game_objects)
    half_roots, _references = _find_half_model_game_objects(environment, item_game_objects)
    half_game_objects = _game_object_descendants(environment, half_roots) if half_roots else set()
    return half_game_objects if half else item_game_objects.difference(half_game_objects)


def _extract_materials(
    environment: object,
    selected_mesh_ids: set[int] | None = None,
    selected_game_object_ids: set[int] | None = None,
) -> tuple[list[dict], dict[int, list[int]]]:
    material_objects = {obj.path_id: obj.read() for obj in environment.objects if obj.type.name == "Material"}
    referenced_ids: list[int] = []
    mesh_material_ids: dict[int, list[int]] = {}
    for mesh_id, renderer in _renderer_mesh_links(environment):
        if selected_mesh_ids is not None and mesh_id not in selected_mesh_ids:
            continue
        if selected_game_object_ids is not None and _pointer_id(renderer.m_GameObject) not in selected_game_object_ids:
            continue
        material_ids = [_pointer_id(pointer) for pointer in getattr(renderer, "m_Materials", [])]
        material_ids = [path_id for path_id in material_ids if path_id in material_objects]
        if material_ids:
            mesh_material_ids[mesh_id] = material_ids
            for path_id in material_ids:
                if path_id not in referenced_ids:
                    referenced_ids.append(path_id)

    specs = [{"name": "预览材质", "color": [0.72, 0.78, 0.86, 1]}]
    material_indices: dict[int, int] = {}
    texture_cache: dict[int, bytes] = {}
    for path_id in referenced_ids:
        material = material_objects[path_id]
        properties = material.m_SavedProperties
        colors = {name: value for name, value in (properties.m_Colors or [])}
        floats = {name: float(value) for name, value in (properties.m_Floats or [])}
        textures = {name: value for name, value in (properties.m_TexEnvs or [])}
        color_value = colors.get("_Color") or colors.get("_BaseColor")
        color = [float(getattr(color_value, channel, 1.0)) for channel in ("r", "g", "b", "a")]
        base_texture = next((textures[name].m_Texture for name in ("_MainTex", "_BaseMap", "_BaseColorMap") if name in textures), None)
        normal_texture = next((textures[name].m_Texture for name in ("_BumpMap", "_NormalMap") if name in textures), None)
        smoothness = floats.get("_Glossiness", floats.get("_Smoothness", 0.32))
        spec = {
            "name": str(getattr(material, "m_Name", "Material")),
            "color": color,
            "metallic": max(0.0, min(1.0, floats.get("_Metallic", 0.0))),
            "roughness": 1.0 - max(0.0, min(1.0, smoothness)),
            "base_color_png": _texture_png(base_texture, texture_cache) if base_texture else None,
            "normal_png": _texture_png(normal_texture, texture_cache) if normal_texture else None,
            "transparent": color[3] < 0.999,
        }
        material_indices[path_id] = len(specs)
        specs.append(spec)

    slots = {
        mesh_id: [material_indices.get(material_id, 0) for material_id in material_ids]
        for mesh_id, material_ids in mesh_material_ids.items()
    }
    return specs, slots


def _read_main_asset(item: object) -> tuple[bytes, str]:
    reference = normalize_abdata_path(str(item["main_manifest"] or ""), str(item["main_ab"] or ""))
    if not reference.lower().endswith(".unity3d"):
        raise ValueError("该物品没有可用的 MainAB Unity3D 资源")
    zipmod_path = Path(str(item["file_path"])).resolve()
    member_name = normalize_zip_path(reference)
    with zipfile.ZipFile(zipmod_path) as archive:
        members = {normalize_zip_path(name).lower(): name for name in archive.namelist()}
        matched = members.get(member_name.lower())
        if matched:
            return archive.read(matched), f"{zipmod_path}:{matched}"
    game_dir = resolve_game_dir_from_zipmod(str(zipmod_path), str(item["relative_path"] or ""))
    external = resolve_game_abdata_path(game_dir, reference)
    if external.is_file():
        return external.read_bytes(), str(external)
    raise FileNotFoundError(f"找不到模型资源：{reference}")


def _write_preview_model(
    environment: object,
    selected_mesh_ids: set[int] | None,
    output: Path,
    *,
    include_skin: bool = False,
    selected_game_object_ids: set[int] | None = None,
) -> int:
    material_specs, material_slots = _extract_materials(environment, selected_mesh_ids, selected_game_object_ids)
    renderers_by_mesh = {
        mesh_id: renderer
        for mesh_id, renderer in _renderer_mesh_links(environment)
        if selected_mesh_ids is None or mesh_id in selected_mesh_ids
        if selected_game_object_ids is None or _pointer_id(renderer.m_GameObject) in selected_game_object_ids
    }
    game_objects = {
        obj.path_id: obj.read()
        for obj in environment.objects
        if obj.type.name == "GameObject"
    }
    transforms = {
        obj.path_id: obj.read()
        for obj in environment.objects
        if obj.type.name in {"Transform", "RectTransform"}
    }
    transform_names = {
        path_id: str(getattr(game_objects.get(_pointer_id(transform.m_GameObject)), "m_Name", ""))
        for path_id, transform in transforms.items()
    }
    transform_by_game_object = {
        _pointer_id(transform.m_GameObject): path_id
        for path_id, transform in transforms.items()
    }
    transform_matrix_cache: dict[int, list[list[float]]] = {}
    meshes: list[tuple] = []
    for obj in environment.objects:
        if obj.type.name != "Mesh":
            continue
        if selected_mesh_ids is not None and obj.path_id not in selected_mesh_ids:
            continue
        mesh = obj.read()
        handler = MeshHandler(mesh)
        handler.process()
        if handler.m_VertexCount > 0 and handler.m_Vertices:
            skin_spec = None
            renderer = renderers_by_mesh.get(obj.path_id)
            bone_pointers = list(getattr(renderer, "m_Bones", []) or []) if renderer else []
            bind_poses = list(getattr(mesh, "m_BindPose", []) or [])
            bone_indices = list(getattr(handler, "m_BoneIndices", []) or [])
            bone_weights = list(getattr(handler, "m_BoneWeights", []) or [])
            if (
                include_skin
                and bone_pointers
                and len(bind_poses) == len(bone_pointers)
                and len(bone_indices) == handler.m_VertexCount
                and len(bone_weights) == handler.m_VertexCount
                and any(float(weight) > 0.000001 for weights in bone_weights for weight in weights)
            ):
                used_bone_indices = sorted({
                    int(index)
                    for indices, weights in zip(bone_indices, bone_weights)
                    for index, weight in zip(indices, weights)
                    if float(weight) > 0.000001 and 0 <= int(index) < len(bone_pointers)
                })
                compact_index = {original: compact for compact, original in enumerate(used_bone_indices)}
                compact_indices = [
                    tuple(compact_index.get(int(index), 0) for index in indices)
                    for indices in bone_indices
                ]
                axis_sign = (-1.0, 1.0, 1.0, 1.0)
                inverse_bind_matrices = []
                for original_index in used_bone_indices:
                    matrix = bind_poses[original_index]
                    inverse_bind_matrices.append([
                        _finite(getattr(matrix, f"e{row}{column}")) * axis_sign[row] * axis_sign[column]
                        for column in range(4)
                        for row in range(4)
                    ])
                fallback_bone_names = []
                for original_index in used_bone_indices:
                    transform_id = _pointer_id(bone_pointers[original_index])
                    ancestors = []
                    visited: set[int] = set()
                    while transform_id in transforms and transform_id not in visited:
                        visited.add(transform_id)
                        transform_id = _pointer_id(transforms[transform_id].m_Father)
                        if transform_id in transforms:
                            name = transform_names.get(transform_id, "")
                            if name:
                                ancestors.append(name)
                    fallback_bone_names.append(ancestors)
                skin_spec = {
                    "bone_names": [
                        transform_names.get(_pointer_id(bone_pointers[index]), f"Bone_{index}")
                        for index in used_bone_indices
                    ],
                    "fallback_bone_names": fallback_bone_names,
                    "inverse_bind_matrices": inverse_bind_matrices,
                    "indices": compact_indices,
                    "weights": bone_weights,
                }
            renderer_transform_id = transform_by_game_object.get(_pointer_id(renderer.m_GameObject), 0) if renderer else 0
            node_matrix = (
                _gltf_matrix_from_unity(_transform_world_matrix(renderer_transform_id, transforms, transform_matrix_cache))
                if renderer_transform_id in transforms
                else None
            )
            meshes.append((
                str(getattr(mesh, "m_Name", "Mesh")),
                handler,
                material_slots.get(obj.path_id, []),
                skin_spec,
                node_matrix,
            ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_build_glb(meshes, material_specs))
    return len(meshes)


def prepare_item_model_preview(mod_item_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict:
    try:
        with sqlite3.connect(db_path.resolve()) as conn:
            conn.row_factory = sqlite3.Row
            init_db(conn)
            item = conn.execute(
                """SELECT mod_items.*, zipmods.file_path, zipmods.relative_path, zipmods.modified_at
                   FROM mod_items INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                   WHERE mod_items.id = ?""",
                (int(mod_item_id),),
            ).fetchone()
        if item is None:
            return {"ok": False, "error": "物品不存在"}
        asset_data, source = _read_main_asset(item)
        cache_key = hashlib.sha1(
            f"main-data-v11-renderer-transform:{mod_item_id}:{item['modified_at']}:{item['main_ab']}:{item['main_data']}".encode("utf-8")
        ).hexdigest()
        output = DEFAULT_MODEL_PREVIEW_DIR / cache_key[:2] / f"{cache_key}.glb"
        half_output = output.with_name(f"{cache_key}-half.glb")
        environment = UnityPy.load(asset_data)
        selected_mesh_ids, selection_mode = _select_main_data_meshes(
            environment,
            str(item["main_data"] or ""),
            exclude_half_models=True,
        )
        if selection_mode == "main_data_no_renderable_mesh":
            raise ValueError(f"MainData“{item['main_data']}”下没有可显示的网格")
        half_mesh_ids, half_references = _select_half_model_meshes(environment, str(item["main_data"] or ""))
        normal_game_object_ids = _select_variant_game_objects(environment, str(item["main_data"] or ""))
        half_game_object_ids = _select_variant_game_objects(environment, str(item["main_data"] or ""), half=True)
        include_skin = str(item["kind"] or "").strip() in MANNEQUIN_ITEM_KINDS
        mesh_count = None
        if not output.is_file():
            mesh_count = _write_preview_model(
                environment,
                selected_mesh_ids,
                output,
                include_skin=include_skin,
                selected_game_object_ids=normal_game_object_ids,
            )
        if half_mesh_ids and not half_output.is_file():
            _write_preview_model(
                environment,
                half_mesh_ids,
                half_output,
                include_skin=include_skin,
                selected_game_object_ids=half_game_object_ids,
            )
        return {
            "ok": True,
            "url": f"/mods/models/{output.name}",
            "half_url": f"/mods/models/{half_output.name}" if half_mesh_ids else None,
            "has_half_model": bool(half_mesh_ids),
            "half_model_references": half_references,
            "mannequin_url": "/mods/mannequin/body.fbx"
            if str(item["kind"] or "").strip() in MANNEQUIN_ITEM_KINDS and resolve_mannequin_model_file()
            else None,
            "mesh_count": mesh_count,
            "selection": selection_mode,
            "source": source,
        }
    except Exception as error:
        return {"ok": False, "error": str(error)}


def export_item_fbx(mod_item_id: int, target_dir: str, db_path: Path = DEFAULT_DB_PATH) -> dict:
    try:
        export_root = Path(str(target_dir or "")).resolve()
        if not export_root.is_dir():
            raise ValueError("请选择有效的导出目录")
        with sqlite3.connect(db_path.resolve()) as conn:
            conn.row_factory = sqlite3.Row
            init_db(conn)
            item = conn.execute(
                """SELECT mod_items.*, zipmods.file_path, zipmods.relative_path
                   FROM mod_items INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                   WHERE mod_items.id = ?""",
                (int(mod_item_id),),
            ).fetchone()
        if item is None:
            raise ValueError("物品不存在")
        asset_data, source = _read_main_asset(item)
        environment = UnityPy.load(asset_data)
        selected_mesh_ids, selection_mode = _select_main_data_meshes(environment, str(item["main_data"] or ""))
        if selection_mode == "main_data_no_renderable_mesh":
            raise ValueError(f"MainData“{item['main_data']}”下没有可导出的网格")
        material_specs, material_slots = _extract_materials(environment, selected_mesh_ids)
        meshes: list[tuple] = []
        for obj in environment.objects:
            if obj.type.name != "Mesh" or (selected_mesh_ids is not None and obj.path_id not in selected_mesh_ids):
                continue
            mesh = obj.read()
            handler = MeshHandler(mesh)
            handler.process()
            if handler.m_VertexCount > 0 and handler.m_Vertices:
                meshes.append((str(getattr(mesh, "m_Name", "Mesh")), handler, material_slots.get(obj.path_id, [])))
        if not meshes:
            raise ValueError("资源中没有可导出的网格")

        base_name = _safe_export_name(str(item["name"] or item["main_data"] or f"item_{mod_item_id}"), f"item_{mod_item_id}")
        output_dir = export_root / f"{base_name}_fbx"
        suffix = 2
        while output_dir.exists():
            output_dir = export_root / f"{base_name}_fbx_{suffix}"
            suffix += 1
        texture_dir = output_dir / "textures"
        texture_dir.mkdir(parents=True, exist_ok=False)
        texture_files: dict[int, tuple[str, str]] = {}
        exported_texture_count = 0
        for material_index, spec in enumerate(material_specs):
            material_name = _safe_export_name(str(spec.get("name") or "material"), f"material_{material_index}")
            base_png = spec.get("base_color_png")
            if base_png:
                file_name = f"{material_index:02d}_{material_name}_base.png"
                texture_path = texture_dir / file_name
                texture_path.write_bytes(base_png)
                texture_files[material_index] = (str(texture_path), f"textures/{file_name}")
                exported_texture_count += 1
            normal_png = spec.get("normal_png")
            if normal_png:
                normal_path = texture_dir / f"{material_index:02d}_{material_name}_normal.png"
                normal_path.write_bytes(normal_png)
                exported_texture_count += 1
        fbx_path = output_dir / f"{base_name}.fbx"
        fbx_path.write_text(_build_fbx_ascii(meshes, material_specs, texture_files), encoding="utf-8", newline="\n")
        return {
            "ok": True,
            "item_id": int(mod_item_id),
            "fbx_path": str(fbx_path),
            "output_dir": str(output_dir),
            "mesh_count": len(meshes),
            "texture_count": exported_texture_count,
            "selection": selection_mode,
            "source": source,
            "message": "FBX 模型已导出",
        }
    except Exception as error:
        return {"ok": False, "error": str(error)}


def resolve_model_preview_file(file_name: str) -> Path | None:
    if not file_name.endswith(".glb") or Path(file_name).name != file_name:
        return None
    candidates = list(DEFAULT_MODEL_PREVIEW_DIR.glob(f"??/{file_name}"))
    return candidates[0] if candidates and candidates[0].is_file() else None
