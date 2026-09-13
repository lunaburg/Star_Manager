from __future__ import annotations

import copy
import base64
import gc
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import shutil
import struct
import tempfile
import uuid
import zipfile
from pathlib import Path

import UnityPy
from PIL import Image
from UnityPy.classes import AssetInfo, PPtr
from UnityPy.export.MeshExporter import MeshHandler
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.streams import EndianBinaryReader

from star_manager.core.runtime_paths import runtime_root
from star_manager.services.mod_database_core import DEFAULT_DB_PATH, init_db
from star_manager.services.mod_database_queries import (
    normalize_abdata_path,
    normalize_zip_path,
    resolve_game_abdata_path,
    resolve_game_dir_from_zipmod,
)


DEFAULT_MODEL_PREVIEW_DIR = runtime_root() / "model_previews"
DEFAULT_UNITY3D_OPEN_DIR = runtime_root() / "unity3d_open"
DEFAULT_UNITY3D_PREPROCESS_DIR = runtime_root() / "unity3d_preprocessed"
CAB_FILE_NAME_PATTERN = re.compile(r"^CAB-[0-9a-f]{32}$", re.IGNORECASE)
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
                        joint_node = {
                            "name": bone_name,
                            "extras": {"fallbackBoneNames": skin_spec["fallback_bone_names"][bone_index]},
                        }
                        bone_matrices = skin_spec.get("bone_matrices") or []
                        if bone_index < len(bone_matrices) and bone_matrices[bone_index] is not None:
                            joint_node["matrix"] = bone_matrices[bone_index]
                        nodes.append(joint_node)
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
            "doubleSided": False,
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
            # Texture atlases use transparent pixels for the unused canvas and
            # clothing cutouts.  Blending makes every partially covered mesh
            # triangle translucent and exposes rear geometry; use an alpha mask
            # so accepted pixels remain opaque and write depth normally.
            material["alphaMode"] = "MASK"
            material["alphaCutoff"] = 0.5
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


def _png_has_transparency(data: bytes | None) -> bool:
    if not data:
        return False
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.mode in {"RGBA", "LA"}:
                return image.getchannel("A").getextrema()[0] < 255
            return "transparency" in image.info
    except (OSError, ValueError):
        return False


def _normalize_preview_material_color(color: list[float], has_base_texture: bool) -> list[float]:
    normalized = [max(0.0, min(1.0, float(value))) for value in color]
    if has_base_texture and normalized[3] <= 0.001:
        normalized[3] = 1.0
    return normalized


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
    half_roots, _references = _find_half_model_game_objects(environment, descendant_game_objects) if exclude_half_models else (set(), [])
    half_game_objects = _game_object_descendants(environment, half_roots) if half_roots else set()
    mesh_ids = {
        mesh_id
        for mesh_id, renderer in _renderer_mesh_links(environment)
        if _pointer_id(renderer.m_GameObject) in descendant_game_objects
        and _pointer_id(renderer.m_GameObject) not in half_game_objects
    }
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
        base_color_png = _texture_png(base_texture, texture_cache) if base_texture else None
        color = _normalize_preview_material_color(color, bool(base_color_png))
        smoothness = floats.get("_Glossiness", floats.get("_Smoothness", 0.32))
        spec = {
            "name": str(getattr(material, "m_Name", "Material")),
            "color": color,
            "metallic": max(0.0, min(1.0, floats.get("_Metallic", 0.0))),
            "roughness": 1.0 - max(0.0, min(1.0, smoothness)),
            "base_color_png": base_color_png,
            "normal_png": _texture_png(normal_texture, texture_cache) if normal_texture else None,
            "transparent": color[3] < 0.999 or _png_has_transparency(base_color_png),
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


def prepare_item_unity3d_file(mod_item_id: int, db_path: Path = DEFAULT_DB_PATH) -> dict:
    try:
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
            raise ValueError("Item not found")

        reference = normalize_abdata_path(str(item["main_manifest"] or ""), str(item["main_ab"] or ""))
        if not reference.lower().endswith(".unity3d"):
            raise ValueError("The item has no usable MainAB Unity3D resource")

        zipmod_path = Path(str(item["file_path"])).resolve()
        if not zipmod_path.is_file():
            raise FileNotFoundError(f"Zipmod file not found: {zipmod_path}")

        member_name = normalize_zip_path(reference)
        with zipfile.ZipFile(zipmod_path) as archive:
            members = {normalize_zip_path(name).lower(): name for name in archive.namelist()}
            matched = members.get(member_name.lower())
            if matched:
                cache_key = hashlib.sha1(
                    f"{zipmod_path}:{zipmod_path.stat().st_mtime_ns}:{zipmod_path.stat().st_size}:{matched}".encode("utf-8")
                ).hexdigest()
                output_dir = DEFAULT_UNITY3D_OPEN_DIR / cache_key[:2]
                safe_name = _safe_export_name(Path(matched).name, f"item_{mod_item_id}.unity3d")
                output_path = output_dir / f"{cache_key}-{safe_name}"
                output_dir.mkdir(parents=True, exist_ok=True)
                if not output_path.is_file():
                    output_path.write_bytes(archive.read(matched))
                return {
                    "ok": True,
                    "item_id": int(mod_item_id),
                    "unity3d_path": str(output_path),
                    "source": f"{zipmod_path}:{matched}",
                    "extracted": True,
                    "message": "Prepared a temporary Unity3D copy",
                }

        game_dir = resolve_game_dir_from_zipmod(str(zipmod_path), str(item["relative_path"] or ""))
        external = resolve_game_abdata_path(game_dir, reference).resolve()
        abdata_root = (game_dir / "abdata").resolve()
        if abdata_root not in external.parents or not external.is_file():
            raise FileNotFoundError(f"Unity3D resource not found: {reference}")
        return {
            "ok": True,
            "item_id": int(mod_item_id),
            "unity3d_path": str(external),
            "source": str(external),
            "extracted": False,
            "message": "Found the Unity3D file",
        }
    except Exception as error:
        return {"ok": False, "error": str(error)}


def export_item_unity3d_file(
    mod_item_id: int,
    target_path: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    """Copy one item's MainAB Unity3D resource to a user-selected file."""
    raw_target = str(target_path or "").strip()
    if not raw_target:
        return {"ok": False, "error": "请选择 Unity3D 导出位置"}

    destination = Path(raw_target).expanduser().resolve()
    if destination.suffix.lower() != ".unity3d":
        return {"ok": False, "error": "导出文件必须使用 .unity3d 扩展名"}
    if destination.exists() and destination.is_dir():
        return {"ok": False, "error": "导出位置是一个文件夹"}

    temporary_path: Path | None = None
    try:
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

        reference = normalize_abdata_path(str(item["main_manifest"] or ""), str(item["main_ab"] or ""))
        if not reference.lower().endswith(".unity3d"):
            raise ValueError("该物品没有可用的 Unity3D 主资源")

        zipmod_path = Path(str(item["file_path"])).resolve()
        if not zipmod_path.is_file():
            raise FileNotFoundError(f"找不到 zipmod 文件：{zipmod_path}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=str(destination.parent),
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            member_name = normalize_zip_path(reference)
            with zipfile.ZipFile(zipmod_path) as archive:
                members = {normalize_zip_path(name).lower(): name for name in archive.namelist()}
                matched = members.get(member_name.lower())
                if matched:
                    with archive.open(matched, "r") as source:
                        shutil.copyfileobj(source, temporary_file)
                    source_label = f"{zipmod_path}:{matched}"
                else:
                    game_dir = resolve_game_dir_from_zipmod(str(zipmod_path), str(item["relative_path"] or ""))
                    external = resolve_game_abdata_path(game_dir, reference).resolve()
                    abdata_root = (game_dir / "abdata").resolve()
                    if abdata_root not in external.parents or not external.is_file():
                        raise FileNotFoundError(f"找不到 Unity3D 资源：{reference}")
                    if external == destination:
                        raise ValueError("导出位置不能与源 Unity3D 文件相同")
                    temporary_file.flush()
                    with external.open("rb") as source:
                        shutil.copyfileobj(source, temporary_file)
                    source_label = str(external)

        os.replace(temporary_path, destination)
        temporary_path = None
        return {
            "ok": True,
            "item_id": int(mod_item_id),
            "source_path": source_label,
            "target_path": str(destination),
            "message": "Unity3D 已复制导出，源文件未修改",
        }
    except Exception as error:
        return {"ok": False, "error": str(error)}
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


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
                bone_matrices = []
                for original_index in used_bone_indices:
                    transform_id = _pointer_id(bone_pointers[original_index])
                    bone_matrices.append(
                        _gltf_matrix_from_unity(_transform_world_matrix(transform_id, transforms, transform_matrix_cache))
                        if transform_id in transforms
                        else None
                    )
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
                    "bone_matrices": bone_matrices,
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
            f"main-data-v16-alpha-mask-front-face:{mod_item_id}:{item['modified_at']}:{item['main_ab']}:{item['main_data']}".encode("utf-8")
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
                selected_game_object_ids=normal_game_object_ids or None,
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


def prepare_workbench_model_preview(file_path: str, main_data: str, item_kind: str = "") -> dict:
    """Generate a cached GLB preview for one project-local Workbench Unity3D."""
    environment = None
    try:
        source = Path(str(file_path or "")).expanduser().resolve()
        normalized_main_data = str(main_data or "").strip()
        normalized_kind = str(item_kind or "").strip()
        if source.suffix.lower() != ".unity3d" or not source.is_file():
            return {"ok": False, "error": "Unity3D 文件不存在"}
        if not normalized_main_data:
            return {"ok": False, "error": "MainData 不能为空"}

        source_stat = source.stat()
        cache_key = hashlib.sha1(
            (
                "workbench-main-data-v2-alpha-mask-front-face:"
                f"{source}:{source_stat.st_mtime_ns}:{source_stat.st_size}:"
                f"{normalized_main_data}:{normalized_kind}"
            ).encode("utf-8")
        ).hexdigest()
        output = DEFAULT_MODEL_PREVIEW_DIR / cache_key[:2] / f"{cache_key}.glb"
        half_output = output.with_name(f"{cache_key}-half.glb")
        environment = UnityPy.load(str(source))
        selected_mesh_ids, selection_mode = _select_main_data_meshes(
            environment,
            normalized_main_data,
            exclude_half_models=True,
        )
        if selection_mode == "main_data_no_renderable_mesh":
            raise ValueError(f"MainData“{normalized_main_data}”下没有可显示的网格")

        half_mesh_ids, half_references = _select_half_model_meshes(environment, normalized_main_data)
        normal_game_object_ids = _select_variant_game_objects(environment, normalized_main_data)
        half_game_object_ids = _select_variant_game_objects(environment, normalized_main_data, half=True)
        include_skin = normalized_kind in MANNEQUIN_ITEM_KINDS
        mesh_count = None
        if not output.is_file():
            mesh_count = _write_preview_model(
                environment,
                selected_mesh_ids,
                output,
                include_skin=include_skin,
                selected_game_object_ids=normal_game_object_ids or None,
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
            if include_skin and resolve_mannequin_model_file()
            else None,
            "mesh_count": mesh_count,
            "selection": selection_mode,
            "source": str(source),
        }
    except Exception as error:
        return {"ok": False, "error": str(error)}
    finally:
        _dispose_unity_environment(environment)


def _workbench_thumbnail_lookup_keys(value: object) -> set[str]:
    normalized = str(value or "").replace("\\", "/").strip().lower().strip("/")
    if not normalized:
        return set()
    name = normalized.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return {normalized, name, stem}


def _workbench_thumbnail_rank(value: object) -> int:
    normalized = str(value or "").replace("\\", "/").strip().lower().strip("/")
    name = normalized.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return {"icon": 1, "thumb": 2, "thumbnail": 3, "preview": 4, "prev": 5}.get(stem, 0)


def prepare_workbench_thumbnail_preview(file_path: str, texture_name: str = "") -> dict:
    """Read one project-local Unity3D thumbnail without changing the project."""
    environment = None
    try:
        source = Path(str(file_path or "")).expanduser().resolve()
        if source.suffix.lower() != ".unity3d" or not source.is_file():
            return {"ok": False, "error": "缩略图 Unity3D 文件不存在"}

        environment = UnityPy.load(str(source))
        images: dict[str, object] = {}
        fallback_images: list[tuple[int, object]] = []

        def remember(name: object, image: object) -> None:
            keys = _workbench_thumbnail_lookup_keys(name)
            for key in keys:
                images.setdefault(key, image)
            rank = _workbench_thumbnail_rank(name)
            if rank:
                fallback_images.append((rank, image))

        for container_path, obj in environment.container.items():
            try:
                image = getattr(obj.read(), "image", None)
            except Exception:  # noqa: BLE001 - skip unreadable thumbnail objects.
                continue
            if image is not None:
                remember(container_path, image)

        for obj in environment.objects:
            if getattr(obj.type, "name", "") not in {"Texture2D", "Sprite"}:
                continue
            try:
                data = obj.read()
                image = getattr(data, "image", None)
                name = getattr(data, "name", "") or ""
            except Exception:  # noqa: BLE001 - skip unreadable thumbnail objects.
                continue
            if image is not None:
                remember(name, image)

        image = next((images[key] for key in _workbench_thumbnail_lookup_keys(texture_name) if key in images), None)
        if image is None and fallback_images:
            image = sorted(fallback_images, key=lambda entry: entry[0])[0][1]
        if image is None:
            return {"ok": False, "error": "缩略图 Unity3D 中未找到对应图片"}

        output = io.BytesIO()
        image.save(output, format="PNG")
        encoded = output.getvalue()
        if len(encoded) > 2_000_000:
            return {"ok": False, "error": "缩略图超过 2 MB，无法预览"}
        return {
            "ok": True,
            "data_url": f"data:image/png;base64,{base64.b64encode(encoded).decode('ascii')}",
            "source_path": str(source)
        }
    except Exception as error:  # noqa: BLE001 - preview failures stay local to the workbench slot.
        return {"ok": False, "error": str(error)}
    finally:
        _dispose_unity_environment(environment)


def list_unity3d_main_data_candidates(file_path: str) -> dict:
    """Return likely MainData GameObject names for one local Unity3D file."""
    environment = None
    try:
        source = Path(str(file_path or "")).expanduser().resolve()
        if source.suffix.lower() != ".unity3d" or not source.is_file():
            return {"ok": False, "error": "Unity3D 文件不存在"}

        environment = UnityPy.load(str(source))
        game_objects = {}
        texture_candidates: list[dict] = []
        seen_textures: set[tuple[str, int]] = set()
        transforms = {}
        renderer_game_objects: set[int] = set()
        animator_game_objects: set[int] = set()
        objects_by_key = {_object_key(obj): obj for obj in environment.objects}

        def is_animator_component(obj: object) -> bool:
            object_type = getattr(getattr(obj, "type", None), "name", "")
            try:
                class_id = int(getattr(obj, "class_id", 0) or 0)
            except (TypeError, ValueError):
                class_id = 0
            return object_type == "Animator" or class_id == 95
        component_indexes = {
            _object_key(obj): index
            for index, obj in enumerate(environment.objects)
        }
        for obj in environment.objects:
            object_type = getattr(obj.type, "name", "")
            if object_type == "GameObject":
                try:
                    value = obj.read()
                    name = str(getattr(value, "m_Name", "") or "").strip()
                    if name:
                        game_objects[obj.path_id] = (name, obj)
                    components = getattr(value, "m_Component", None)
                    if components is None:
                        components = getattr(value, "m_Components", None)
                    for component_pair in components or []:
                        component_pointer = _component_pointer(component_pair)
                        component_key = _local_pointer_key(component_pointer, getattr(obj, "assets_file", None))
                        component_obj = objects_by_key.get(component_key) if component_key else None
                        if component_obj is not None and is_animator_component(component_obj):
                            animator_game_objects.add(int(obj.path_id))
                            break
                except Exception:
                    continue
            elif object_type == "Texture2D":
                try:
                    value = obj.read()
                    name = str(getattr(value, "m_Name", "") or "").strip()
                    asset_file = str(getattr(getattr(obj, "assets_file", None), "name", "") or "")
                    key = (asset_file, int(getattr(obj, "path_id", 0) or 0))
                    if name and key not in seen_textures:
                        seen_textures.add(key)
                        texture_candidates.append({
                            "value": name,
                            "label": name,
                            "kind": "Texture2D",
                            "path_id": key[1],
                            "asset_file": asset_file,
                            "component_index": int(component_indexes.get(_object_key(obj), 0)),
                        })
                except Exception:
                    continue
            elif object_type in {"Transform", "RectTransform"}:
                try:
                    value = obj.read()
                    transforms[obj.path_id] = value
                except Exception:
                    continue
            elif object_type in {"MeshRenderer", "SkinnedMeshRenderer"}:
                try:
                    value = obj.read()
                    game_object_id = _pointer_id(getattr(value, "m_GameObject", None))
                    if game_object_id:
                        renderer_game_objects.add(game_object_id)
                except Exception:
                    continue
            elif is_animator_component(obj):
                try:
                    value = obj.read()
                    game_object_id = _pointer_id(getattr(value, "m_GameObject", None))
                    if game_object_id:
                        animator_game_objects.add(game_object_id)
                except Exception:
                    continue

        transform_by_game_object = {
            _pointer_id(transform.m_GameObject): path_id
            for path_id, transform in transforms.items()
            if _pointer_id(getattr(transform, "m_GameObject", None))
        }
        parent_by_game_object: dict[int, int] = {}
        for game_object_id, transform_id in transform_by_game_object.items():
            transform = transforms.get(transform_id)
            parent_transform_id = _pointer_id(getattr(transform, "m_Father", None)) if transform else 0
            parent_game_object_id = _pointer_id(
                getattr(transforms.get(parent_transform_id), "m_GameObject", None)
            ) if parent_transform_id in transforms else 0
            parent_by_game_object[game_object_id] = parent_game_object_id

        root_ids: list[int] = []
        for game_object_id in sorted(renderer_game_objects):
            current = game_object_id
            visited: set[int] = set()
            while current and current not in visited:
                visited.add(current)
                parent = parent_by_game_object.get(current, 0)
                if not parent:
                    break
                current = parent
            if current and current not in root_ids:
                root_ids.append(current)

        animator_candidate_ids = {
            game_object_id
            for game_object_id in animator_game_objects
            if game_object_id in game_objects
        }
        if not animator_candidate_ids:
            # Some older Unity3D files do not expose the native Animator
            # component through UnityPy. In that case the renderer hierarchy
            # roots are the safe Animator/MainData candidates; never fall
            # back to every GameObject, which would expose all bone nodes.
            animator_candidate_ids = {
                game_object_id
                for game_object_id in root_ids
                if game_object_id in game_objects
            }

        game_object_candidates: list[dict] = []
        for game_object_id in sorted(animator_candidate_ids):
            game_object = game_objects[game_object_id]
            name = str(game_object[0] or "").strip()
            asset_file = str(getattr(getattr(game_object[1], "assets_file", None), "name", "") or "")
            if not name:
                continue
            game_object_candidates.append({
                "value": name,
                "label": name,
                "kind": "GameObject",
                "path_id": int(game_object_id),
                "asset_file": asset_file,
                "component_index": int(component_indexes.get(_object_key(game_object[1]), 0)),
                "is_renderer_root": game_object_id in root_ids,
                "is_animator": True,
            })

        candidates: list[dict] = []
        seen: set[tuple[str, int] | str] = set()

        def add_candidate(game_object_id: int, kind: str) -> None:
            if game_object_id not in animator_candidate_ids:
                return
            game_object = game_objects.get(game_object_id)
            if not game_object:
                return
            name = game_object[0] if game_object else ""
            normalized = str(name or "").strip()
            key = (str(getattr(getattr(game_object[1], "assets_file", None), "name", "") or ""), game_object_id)
            if not normalized or key in seen:
                return
            seen.add(key)
            candidates.append({
                "value": normalized,
                "label": normalized,
                "kind": kind,
                "path_id": int(game_object_id),
                "asset_file": key[0],
                "component_index": int(component_indexes.get(_object_key(game_object[1]), 0)),
                "is_animator": True,
            })

        for game_object_id in sorted(
            animator_candidate_ids,
            key=lambda value: game_objects.get(value, ("", None))[0].casefold(),
        ):
            add_candidate(game_object_id, "GameObject")
        return {
            "ok": True,
            "path": str(source),
            "candidates": candidates[:200],
            "game_object_candidates": game_object_candidates[:1000],
            "game_object_names": sorted(
                {game_object[0] for game_object in game_objects.values()},
                key=str.casefold,
            )[:500],
            "texture_candidates": sorted(
                texture_candidates,
                key=lambda candidate: (candidate["value"].casefold(), candidate["asset_file"].casefold()),
            )[:500],
            "default": candidates[0]["value"] if candidates else "",
            "object_count": len(environment.objects),
            "game_object_count": sum(
                1 for obj in environment.objects
                if getattr(getattr(obj, "type", None), "name", "") == "GameObject"
            ),
            "texture_count": len(texture_candidates),
        }
    except Exception as error:
        return {"ok": False, "error": f"Unity3D 读取失败：{error}"}
    finally:
        _dispose_unity_environment(environment)


def _pointer_file_id(pointer: object) -> int:
    if isinstance(pointer, dict):
        return int(pointer.get("m_FileID", pointer.get("file_id", 0)) or 0)
    return int(getattr(pointer, "m_FileID", getattr(pointer, "file_id", 0)) or 0)


def _asset_file_name(value: object) -> str:
    asset_file = getattr(value, "assets_file", value)
    return str(getattr(asset_file, "name", "") or "")


def _object_key(obj: object) -> tuple[int, int]:
    return (id(getattr(obj, "assets_file", None)), int(getattr(obj, "path_id", 0)))


def _local_pointer_key(pointer: object, asset_file: object) -> tuple[int, int] | None:
    path_id = _pointer_id(pointer)
    if not path_id or _pointer_file_id(pointer) != 0:
        return None
    return (id(asset_file), path_id)


def _component_pointer(component_pair: object) -> object | None:
    pointer = getattr(component_pair, "component", None)
    if pointer is not None:
        return pointer
    if isinstance(component_pair, (list, tuple)) and len(component_pair) >= 2:
        return component_pair[1]
    return None


def _find_selected_game_object(
    environment: object,
    path_id: int,
    asset_file_name: str = "",
    selected_name: str = "",
) -> object:
    # MainData is the authoritative selection. The path ID remains only as a
    # fallback for older callers that do not provide the input value.
    normalized_name = str(selected_name or "").strip()
    if normalized_name:
        matches = []
        for obj in environment.objects:
            if getattr(getattr(obj, "type", None), "name", "") != "GameObject":
                continue
            if asset_file_name and _asset_file_name(obj) != asset_file_name:
                continue
            try:
                object_name = str(getattr(obj.read(), "m_Name", "") or "").strip()
            except Exception:
                continue
            if object_name == normalized_name:
                matches.append(obj)
        if not matches:
            raise ValueError(f"找不到名称为“{normalized_name}”的 GameObject，请检查 MainData")
        if len(matches) == 1:
            return matches[0]
        path_matches = [obj for obj in matches if int(getattr(obj, "path_id", 0)) == int(path_id or 0)]
        if len(path_matches) == 1:
            return path_matches[0]
        raise ValueError(f"名称为“{normalized_name}”的 GameObject 不唯一，请检查 MainData")

    if path_id <= 0:
        raise ValueError("请选择一个有效的 GameObject")
    matches = [
        obj for obj in environment.objects
        if getattr(getattr(obj, "type", None), "name", "") == "GameObject"
        and int(getattr(obj, "path_id", 0)) == path_id
    ]
    if asset_file_name:
        matches = [obj for obj in matches if _asset_file_name(obj) == asset_file_name]
    if not matches:
        raise ValueError("找不到所选的 GameObject，请重新选择 MainData")
    if len(matches) > 1:
        raise ValueError("所选 GameObject 的资源文件标识不明确，请重新选择 MainData")
    return matches[0]


def _collect_unity3d_object_graph(environment: object) -> dict:
    objects = list(environment.objects)
    objects_by_key = {_object_key(obj): obj for obj in objects}
    game_objects: dict[tuple[int, int], object] = {}
    transforms: dict[tuple[int, int], object] = {}
    transform_game_objects: dict[tuple[int, int], tuple[int, int]] = {}
    component_keys_by_game_object: dict[tuple[int, int], set[tuple[int, int]]] = {}

    for obj in objects:
        object_type = getattr(getattr(obj, "type", None), "name", "")
        key = _object_key(obj)
        if object_type == "GameObject":
            game_objects[key] = obj
            try:
                data = obj.read()
                components = getattr(data, "m_Component", None)
                if components is None:
                    components = getattr(data, "m_Components", None)
                for component_pair in components or []:
                    pointer = _component_pointer(component_pair)
                    component_key = _local_pointer_key(pointer, getattr(obj, "assets_file", None))
                    if component_key in objects_by_key:
                        component_keys_by_game_object.setdefault(key, set()).add(component_key)
            except Exception:
                continue
        elif object_type in {"Transform", "RectTransform"}:
            transforms[key] = obj
            try:
                data = obj.read()
                game_object_key = _local_pointer_key(
                    getattr(data, "m_GameObject", None),
                    getattr(obj, "assets_file", None),
                )
                if game_object_key in game_objects or game_object_key:
                    transform_game_objects[key] = game_object_key
            except Exception:
                continue

    parent_by_game_object: dict[tuple[int, int], tuple[int, int]] = {}
    for transform_key, transform in transforms.items():
        game_object_key = transform_game_objects.get(transform_key)
        if not game_object_key:
            continue
        try:
            data = transform.read()
            parent_transform_key = _local_pointer_key(
                getattr(data, "m_Father", None),
                getattr(transform, "assets_file", None),
            )
            parent_game_object_key = transform_game_objects.get(parent_transform_key)
            if parent_game_object_key:
                parent_by_game_object[game_object_key] = parent_game_object_key
        except Exception:
            continue

    return {
        "objects": objects,
        "objects_by_key": objects_by_key,
        "game_objects": game_objects,
        "transforms": transforms,
        "transform_game_objects": transform_game_objects,
        "component_keys_by_game_object": component_keys_by_game_object,
        "parent_by_game_object": parent_by_game_object,
    }


def _clear_pointer(pointer: object) -> None:
    if isinstance(pointer, dict):
        pointer["m_FileID"] = 0
        pointer["m_PathID"] = 0
        return
    if hasattr(pointer, "m_FileID"):
        pointer.m_FileID = 0
    if hasattr(pointer, "m_PathID"):
        pointer.m_PathID = 0


def _rewrite_transform_hierarchy(graph: dict, keep_game_objects: set[tuple[int, int]]) -> None:
    transforms = graph["transforms"]
    transform_game_objects = graph["transform_game_objects"]
    keep_transform_keys = {
        transform_key
        for transform_key, game_object_key in transform_game_objects.items()
        if game_object_key in keep_game_objects
    }
    for transform_key in keep_transform_keys:
        transform = transforms[transform_key]
        data = transform.read()
        changed = False
        parent_pointer = getattr(data, "m_Father", None)
        parent_transform_key = _local_pointer_key(parent_pointer, getattr(transform, "assets_file", None))
        parent_game_object_key = transform_game_objects.get(parent_transform_key)
        if parent_pointer is not None and parent_game_object_key not in keep_game_objects:
            _clear_pointer(parent_pointer)
            changed = True

        children = getattr(data, "m_Children", None)
        if children is not None:
            filtered_children = []
            for child_pointer in children:
                child_key = _local_pointer_key(child_pointer, getattr(transform, "assets_file", None))
                if child_key is None or child_key in keep_transform_keys:
                    filtered_children.append(child_pointer)
            if len(filtered_children) != len(children):
                data.m_Children = filtered_children
                changed = True
        if changed:
            data.save()


def _pointer_is_deleted(pointer: object, asset_file: object, deleted_keys: set[tuple[int, int]]) -> bool:
    key = _local_pointer_key(pointer, asset_file)
    return key in deleted_keys if key else False


def _rewrite_asset_bundle_metadata(graph: dict, deleted_keys: set[tuple[int, int]]) -> None:
    for obj in graph["objects"]:
        if getattr(getattr(obj, "type", None), "name", "") != "AssetBundle":
            continue
        data = obj.read()
        asset_file = getattr(obj, "assets_file", None)
        container = getattr(data, "m_Container", None)
        preload_table = list(getattr(data, "m_PreloadTable", None) or [])
        changed = False
        if container is not None:
            rebuilt_container = []
            rebuilt_preload_table = []
            for entry in container:
                if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                    rebuilt_container.append(entry)
                    continue
                asset_info = entry[1]
                asset_pointer = getattr(asset_info, "asset", None)
                if _pointer_is_deleted(asset_pointer, asset_file, deleted_keys):
                    changed = True
                    continue
                start = max(0, int(getattr(asset_info, "preloadIndex", 0) or 0))
                end = min(len(preload_table), start + max(0, int(getattr(asset_info, "preloadSize", 0) or 0)))
                preloads = [
                    pointer for pointer in preload_table[start:end]
                    if not _pointer_is_deleted(pointer, asset_file, deleted_keys)
                ]
                new_start = len(rebuilt_preload_table)
                rebuilt_preload_table.extend(preloads)
                if (
                    new_start != int(getattr(asset_info, "preloadIndex", 0) or 0)
                    or len(preloads) != int(getattr(asset_info, "preloadSize", 0) or 0)
                ):
                    asset_info.preloadIndex = new_start
                    asset_info.preloadSize = len(preloads)
                    changed = True
                rebuilt_container.append(entry)
            if len(rebuilt_container) != len(container):
                data.m_Container = rebuilt_container
                changed = True
            if hasattr(data, "m_PreloadTable") and rebuilt_preload_table != preload_table:
                data.m_PreloadTable = rebuilt_preload_table
                changed = True
        elif hasattr(data, "m_PreloadTable"):
            filtered_preload_table = [
                pointer for pointer in preload_table
                if not _pointer_is_deleted(pointer, asset_file, deleted_keys)
            ]
            if filtered_preload_table != preload_table:
                data.m_PreloadTable = filtered_preload_table
                changed = True
        if changed:
            data.save()


def _append_asset_bundle_duplicate_entry(
    graph: dict,
    source_key: tuple[int, int],
    duplicate_name: str,
    pointer_map: dict[tuple[int, int], tuple[int, int]],
    cloned_readers: dict[tuple[int, int], object],
    cloned_data_by_key: dict[tuple[int, int], object],
) -> None:
    """Expose a newly cloned root GameObject through the AssetBundle container."""
    for asset_bundle_object in graph["objects"]:
        if getattr(getattr(asset_bundle_object, "type", None), "name", "") != "AssetBundle":
            continue

        asset_file = getattr(asset_bundle_object, "assets_file", None)
        duplicate_reader = cloned_readers.get(source_key)
        if duplicate_reader is None or getattr(duplicate_reader, "assets_file", None) is not asset_file:
            continue

        asset_bundle_data = asset_bundle_object.read()
        container = list(getattr(asset_bundle_data, "m_Container", None) or [])
        container_name = str(duplicate_name).casefold()
        existing_entry = next(
            (
                entry
                for entry in container
                if isinstance(entry, (list, tuple))
                and len(entry) >= 2
                and str(entry[0]).casefold() == container_name
            ),
            None,
        )
        duplicate_path_id = int(getattr(duplicate_reader, "path_id", 0) or 0)
        if existing_entry is not None:
            existing_asset = getattr(existing_entry[1], "asset", None)
            if _pointer_file_id(existing_asset) == 0 and _pointer_id(existing_asset) == duplicate_path_id:
                return
            raise ValueError(f"AssetBundle 中已存在同名资源入口：{duplicate_name}")

        preload_table = list(getattr(asset_bundle_data, "m_PreloadTable", None) or [])
        duplicate_preloads: list[object] = []
        seen_preloads: set[tuple[object, ...]] = set()

        def preload_key(pointer: object) -> tuple[object, ...] | None:
            path_id = _pointer_id(pointer)
            if not path_id:
                return None
            file_id = _pointer_file_id(pointer)
            if file_id == 0:
                pointer_asset_file = getattr(pointer, "assetsfile", None) or asset_file
                return (0, id(pointer_asset_file), path_id)
            return (file_id, path_id)

        def append_preload(pointer: object) -> None:
            remapped_pointer = (
                _clone_unity_value(pointer, pointer_map, asset_file)
                if isinstance(pointer, PPtr)
                else pointer
            )
            key = preload_key(remapped_pointer)
            if key is None or key in seen_preloads:
                return
            seen_preloads.add(key)
            duplicate_preloads.append(remapped_pointer)

        source_preloads: list[object] = []
        for entry in container:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue
            asset_info = entry[1]
            asset_pointer = getattr(asset_info, "asset", None)
            if (
                _pointer_file_id(asset_pointer) == 0
                and _pointer_id(asset_pointer) == source_key[1]
                and _local_pointer_key(asset_pointer, asset_file) == source_key
            ):
                start = max(0, int(getattr(asset_info, "preloadIndex", 0) or 0))
                end = min(
                    len(preload_table),
                    start + max(0, int(getattr(asset_info, "preloadSize", 0) or 0)),
                )
                source_preloads = preload_table[start:end]
                break

        # Preserve the original root's dependency order when it already has a
        # container entry. This includes shared shaders/bones that are not
        # cloned, while local pointers are remapped to the cloned resources.
        for pointer in source_preloads:
            append_preload(pointer)

        # A renderer-root candidate may not have had its own container entry.
        # Include dependencies found in the cloned typetrees in that case (and
        # as a safety net for resources added by a newer Unity serialization).
        for cloned_data in cloned_data_by_key.values():
            for pointer in _iter_unity_value_pointers(cloned_data):
                append_preload(pointer)

        # The preload table must also contain every object created for the
        # duplicate, including objects that are not reachable through a
        # serialized pointer from another cloned object.
        for source_object_key in sorted(cloned_readers, key=lambda key: (key[0], key[1])):
            cloned_reader = cloned_readers[source_object_key]
            append_preload(
                PPtr(
                    m_FileID=0,
                    m_PathID=int(getattr(cloned_reader, "path_id", 0) or 0),
                    assetsfile=getattr(cloned_reader, "assets_file", None),
                )
            )

        asset_bundle_data.m_PreloadTable = [*preload_table, *duplicate_preloads]
        container.append(
            (
                container_name,
                AssetInfo(
                    asset=PPtr(
                        m_FileID=0,
                        m_PathID=duplicate_path_id,
                        assetsfile=asset_file,
                    ),
                    preloadIndex=len(preload_table),
                    preloadSize=len(duplicate_preloads),
                ),
            )
        )
        asset_bundle_data.m_Container = container
        asset_bundle_data.save()
        return


def _clone_unity_value(
    value: object,
    pointer_map: dict[tuple[int, int], tuple[int, int]],
    asset_file: object,
    memo: dict[int, object] | None = None,
) -> object:
    """Clone serialized data while remapping local pointers to duplicates."""
    memo = memo if memo is not None else {}
    if isinstance(value, PPtr):
        pointer_asset_file = value.assetsfile or asset_file
        source_key = (id(pointer_asset_file), int(value.m_PathID or 0))
        mapped_key = pointer_map.get(source_key) if int(value.m_FileID or 0) == 0 else None
        target_path_id = mapped_key[1] if mapped_key else int(value.m_PathID or 0)
        return PPtr(
            m_FileID=int(value.m_FileID or 0),
            m_PathID=target_path_id,
            assetsfile=pointer_asset_file,
        )
    if value is None or isinstance(value, (str, bytes, bytearray, int, float, bool)):
        return value
    value_id = id(value)
    if value_id in memo:
        return memo[value_id]
    if isinstance(value, list):
        cloned_list: list[object] = []
        memo[value_id] = cloned_list
        cloned_list.extend(_clone_unity_value(item, pointer_map, asset_file, memo) for item in value)
        return cloned_list
    if isinstance(value, tuple):
        cloned_tuple = tuple(_clone_unity_value(item, pointer_map, asset_file, memo) for item in value)
        memo[value_id] = cloned_tuple
        return cloned_tuple
    if isinstance(value, dict):
        cloned_dict: dict[object, object] = {}
        memo[value_id] = cloned_dict
        cloned_dict.update(
            (_clone_unity_value(key, pointer_map, asset_file, memo), _clone_unity_value(item, pointer_map, asset_file, memo))
            for key, item in value.items()
        )
        return cloned_dict

    field_names = [field.name for field in getattr(type(value), "__attrs_attrs__", ())]
    if hasattr(value, "__dict__"):
        field_names.extend(
            name
            for name in vars(value)
            if name != "object_reader" and name not in field_names
        )
    if not field_names:
        return value
    cloned = copy.copy(value)
    memo[value_id] = cloned
    for field_name in field_names:
        try:
            setattr(cloned, field_name, _clone_unity_value(getattr(value, field_name), pointer_map, asset_file, memo))
        except AttributeError:
            continue
    if hasattr(cloned, "object_reader"):
        cloned.object_reader = None
    return cloned


def _unique_unity_object_name(base_name: str, existing_names: set[str]) -> str:
    base = str(base_name or "Object").strip() or "Object"
    normalized_existing_names = {str(name).casefold() for name in existing_names}
    candidate = f"{base}_copy"
    index = 2
    while candidate.casefold() in normalized_existing_names:
        candidate = f"{base}_copy_{index}"
        index += 1
    return candidate


def _iter_unity_value_pointers(value: object, visited: set[int] | None = None):
    """Yield PPtrs nested in a UnityPy typetree value."""
    visited = visited if visited is not None else set()
    if isinstance(value, PPtr):
        yield value
        return
    if value is None or isinstance(value, (str, bytes, bytearray, int, float, bool)):
        return
    value_id = id(value)
    if value_id in visited:
        return
    visited.add(value_id)
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_unity_value_pointers(key, visited)
            yield from _iter_unity_value_pointers(item, visited)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_unity_value_pointers(item, visited)
        return

    field_names = [field.name for field in getattr(type(value), "__attrs_attrs__", ())]
    if hasattr(value, "__dict__"):
        field_names.extend(
            name
            for name in vars(value)
            if name != "object_reader" and name not in field_names
        )
    for field_name in field_names:
        try:
            yield from _iter_unity_value_pointers(getattr(value, field_name), visited)
        except AttributeError:
            continue


def _duplicate_selected_unity3d_object(
    environment: object,
    selected_game_object: object,
    new_name: str = "",
) -> dict:
    graph = _collect_unity3d_object_graph(environment)
    selected_key = _object_key(selected_game_object)
    if selected_key not in graph["game_objects"]:
        raise ValueError("所选对象不属于当前 Unity3D 资源")

    children_by_parent: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for child_key, parent_key in graph["parent_by_game_object"].items():
        children_by_parent.setdefault(parent_key, set()).add(child_key)
    source_game_objects = {selected_key}
    pending = [selected_key]
    while pending:
        current = pending.pop()
        for child_key in children_by_parent.get(current, set()):
            if child_key not in source_game_objects:
                source_game_objects.add(child_key)
                pending.append(child_key)

    source_transform_keys = {
        transform_key
        for transform_key, game_object_key in graph["transform_game_objects"].items()
        if game_object_key in source_game_objects
    }
    source_component_keys = {
        component_key
        for game_object_key in source_game_objects
        for component_key in graph["component_keys_by_game_object"].get(game_object_key, set())
    }
    source_keys = source_game_objects | source_transform_keys | source_component_keys

    # AddFrame-style hierarchy cloning is not enough for a standalone copy:
    # renderers would still point at the original Mesh/Material/Texture2D
    # assets. Walk the serialized component and material typetrees and clone
    # the local render resources they reference, while leaving shared bones
    # and shaders untouched.
    resource_types = {"Mesh", "Material", "Texture2D", "Texture3D", "Cubemap"}
    pending_keys = list(source_keys)
    resource_keys: set[tuple[int, int]] = set()
    while pending_keys:
        current_key = pending_keys.pop()
        source_obj = graph["objects_by_key"].get(current_key)
        if source_obj is None:
            continue
        try:
            serialized = source_obj.read()
        except Exception:
            continue
        for pointer in _iter_unity_value_pointers(serialized):
            if _pointer_file_id(pointer) != 0:
                continue
            pointer_asset_file = getattr(pointer, "assetsfile", None) or getattr(source_obj, "assets_file", None)
            pointer_id = _pointer_id(pointer)
            dependency_key = (id(pointer_asset_file), pointer_id) if pointer_id else None
            dependency_obj = graph["objects_by_key"].get(dependency_key) if dependency_key else None
            dependency_type = getattr(getattr(dependency_obj, "type", None), "name", "")
            if dependency_key and dependency_obj and dependency_type in resource_types and dependency_key not in source_keys:
                source_keys.add(dependency_key)
                resource_keys.add(dependency_key)
                pending_keys.append(dependency_key)
    if not source_transform_keys:
        raise ValueError("所选 GameObject 没有可复制的 Transform")

    existing_names: set[str] = set()
    for game_object in graph["game_objects"].values():
        try:
            name = str(getattr(game_object.read(), "m_Name", "") or "").strip()
        except Exception:
            continue
        if name:
            existing_names.add(name.casefold())
    original_data = selected_game_object.read()
    requested_name = str(new_name or "").strip()
    duplicate_name = requested_name or _unique_unity_object_name(
        getattr(original_data, "m_Name", ""),
        existing_names,
    )
    asset_bundle_container_names = {
        str(entry[0]).casefold()
        for asset_bundle_object in graph["objects"]
        if getattr(getattr(asset_bundle_object, "type", None), "name", "") == "AssetBundle"
        for entry in (getattr(asset_bundle_object.read(), "m_Container", None) or [])
        if isinstance(entry, (list, tuple)) and len(entry) >= 2
    }
    if duplicate_name.casefold() in asset_bundle_container_names:
        duplicate_name = _unique_unity_object_name(
            duplicate_name,
            existing_names | asset_bundle_container_names,
        )

    max_path_by_asset: dict[int, int] = {}
    for obj in graph["objects"]:
        asset_file = getattr(obj, "assets_file", None)
        if asset_file is not None:
            max_path_by_asset[id(asset_file)] = max(
                max_path_by_asset.get(id(asset_file), 0),
                int(getattr(obj, "path_id", 0)),
            )
    pointer_map: dict[tuple[int, int], tuple[int, int]] = {}
    next_path_by_asset = dict(max_path_by_asset)
    for source_key in sorted(source_keys, key=lambda key: (key[0], key[1])):
        source_obj = graph["objects_by_key"][source_key]
        asset_file = getattr(source_obj, "assets_file", None)
        asset_id = id(asset_file)
        next_path_by_asset[asset_id] = next_path_by_asset.get(asset_id, 0) + 1
        pointer_map[source_key] = (asset_id, next_path_by_asset[asset_id])

    cloned_readers: dict[tuple[int, int], object] = {}
    for source_key in sorted(source_keys, key=lambda key: (key[0], key[1])):
        source_obj = graph["objects_by_key"][source_key]
        asset_file = getattr(source_obj, "assets_file", None)
        new_path_id = pointer_map[source_key][1]
        cloned_reader = ObjectReader(
            assets_file=asset_file,
            reader=source_obj.reader,
            path_id=new_path_id,
            type_id=source_obj.type_id,
            serialized_type=source_obj.serialized_type,
            class_id=source_obj.class_id,
            type=source_obj.type,
            byte_start=0,
            byte_size=0,
            is_destroyed=source_obj.is_destroyed,
            is_stripped=source_obj.is_stripped,
            data=None,
            read_until=None,
        )
        asset_file.objects[new_path_id] = cloned_reader
        cloned_readers[source_key] = cloned_reader

    selected_duplicate_reader = None
    cloned_data_by_key: dict[tuple[int, int], object] = {}
    for source_key in sorted(source_keys, key=lambda key: (key[0], key[1])):
        source_obj = graph["objects_by_key"][source_key]
        cloned_reader = cloned_readers[source_key]
        cloned_data = _clone_unity_value(source_obj.read(), pointer_map, source_obj.assets_file)
        cloned_data_by_key[source_key] = cloned_data
        if source_key == selected_key:
            cloned_data.m_Name = duplicate_name
            selected_duplicate_reader = cloned_reader
        cloned_data.set_object_reader(cloned_reader)
        cloned_reader.save_typetree(cloned_data)

    root_transform_key = next(
        transform_key
        for transform_key in source_transform_keys
        if graph["transform_game_objects"].get(transform_key) == selected_key
    )
    root_transform = graph["transforms"][root_transform_key]
    root_transform_data = root_transform.read()
    parent_transform_key = _local_pointer_key(
        getattr(root_transform_data, "m_Father", None),
        getattr(root_transform, "assets_file", None),
    )
    if parent_transform_key and parent_transform_key in graph["transforms"]:
        parent_data = graph["transforms"][parent_transform_key].read()
        children = list(getattr(parent_data, "m_Children", None) or [])
        new_root_path_id = pointer_map[root_transform_key][1]
        if not any(
            _pointer_id(child) == new_root_path_id and _pointer_file_id(child) == 0
            for child in children
        ):
            children.append(PPtr(m_FileID=0, m_PathID=new_root_path_id, assetsfile=root_transform.assets_file))
            parent_data.m_Children = children
            parent_data.save()

    _append_asset_bundle_duplicate_entry(
        graph,
        selected_key,
        duplicate_name,
        pointer_map,
        cloned_readers,
        cloned_data_by_key,
    )

    if selected_duplicate_reader is None:
        raise ValueError("复制所选 GameObject 失败")
    return {
        "name": duplicate_name,
        "path_id": int(selected_duplicate_reader.path_id),
        "asset_file": _asset_file_name(selected_duplicate_reader),
        "object_count": len(source_keys),
        "game_object_count": len(source_game_objects),
        "resource_count": len(resource_keys),
    }


def _remove_unselected_unity3d_objects(environment: object, selected_game_object: object) -> dict:
    graph = _collect_unity3d_object_graph(environment)
    selected_key = _object_key(selected_game_object)
    if selected_key not in graph["game_objects"]:
        raise ValueError("所选对象不属于当前 Unity3D 资源")

    children_by_parent: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for child_key, parent_key in graph["parent_by_game_object"].items():
        children_by_parent.setdefault(parent_key, set()).add(child_key)
    keep_game_objects = {selected_key}
    pending = [selected_key]
    while pending:
        current = pending.pop()
        for child_key in children_by_parent.get(current, set()):
            if child_key not in keep_game_objects:
                keep_game_objects.add(child_key)
                pending.append(child_key)

    keep_transform_keys = {
        transform_key
        for transform_key, game_object_key in graph["transform_game_objects"].items()
        if game_object_key in keep_game_objects
    }
    deleted_game_object_keys = {
        key for key in graph["game_objects"]
        if key not in keep_game_objects
    }
    deleted_keys: set[tuple[int, int]] = set()
    for key, obj in graph["objects_by_key"].items():
        object_type = getattr(getattr(obj, "type", None), "name", "")
        if object_type == "GameObject" and key not in keep_game_objects:
            deleted_keys.add(key)
        elif object_type in {"Transform", "RectTransform"} and key not in keep_transform_keys:
            deleted_keys.add(key)
        elif key in {
            component_key
            for game_object_key in deleted_game_object_keys
            for component_key in graph["component_keys_by_game_object"].get(game_object_key, set())
        }:
            deleted_keys.add(key)

    _rewrite_transform_hierarchy(graph, keep_game_objects)
    _rewrite_asset_bundle_metadata(graph, deleted_keys)
    changed_asset_files: set[int] = set()
    for key in deleted_keys:
        obj = graph["objects_by_key"].get(key)
        if obj is None:
            continue
        asset_file = getattr(obj, "assets_file", None)
        objects = getattr(asset_file, "objects", None)
        if isinstance(objects, dict) and int(getattr(obj, "path_id", 0)) in objects:
            del objects[int(getattr(obj, "path_id", 0))]
            if id(asset_file) not in changed_asset_files:
                asset_file.mark_changed()
                changed_asset_files.add(id(asset_file))
    return {
        "object_count": len(deleted_keys),
        "game_object_count": len(deleted_game_object_keys),
    }


def _save_unity3d_environment(environment: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="star-manager-unity3d-") as temporary_dir:
        # Keep the source UnityFS block compression/layout.  SB3Utility and
        # some Unity asset tools reject the otherwise valid uncompressed
        # UnityFS that UnityPy produces with pack="none".
        environment.save(pack="original", out_path=temporary_dir)
        saved_files = [path for path in Path(temporary_dir).iterdir() if path.is_file()]
        if not saved_files:
            raise ValueError("Unity3D 处理后没有生成可保存的资源文件")
        output_path.write_bytes(saved_files[0].read_bytes())


def _unity3d_cab_names(environment: object) -> list[str]:
    names: list[str] = []
    for bundle in getattr(environment, "files", {}).values():
        files = getattr(bundle, "files", None)
        if not isinstance(files, dict):
            continue
        names.extend(
            str(name)
            for name in files
            if CAB_FILE_NAME_PATTERN.fullmatch(str(name))
        )
    return sorted(names, key=str.casefold)


def _unity3d_bundle(environment: object) -> object:
    bundles = [
        value
        for value in getattr(environment, "files", {}).values()
        if isinstance(getattr(value, "files", None), dict)
        and str(getattr(value, "signature", "")) in {"UnityFS", "UnityWeb", "UnityRaw"}
    ]
    if len(bundles) != 1:
        raise ValueError("工作台 CAB 重写仅支持包含一个 UnityFS Bundle 的 Unity3D")
    return bundles[0]


def _raw_bundle_child_bytes(child: object) -> bytes:
    """Return one Bundle directory child's bytes without serializing it again."""
    child_reader = getattr(child, "reader", None)
    if child_reader is not None:
        reader_bytes = getattr(child_reader, "bytes", None)
        if reader_bytes is not None:
            return bytes(reader_bytes)
    child_bytes = getattr(child, "bytes", None)
    if child_bytes is not None:
        return bytes(child_bytes)
    raise ValueError("UnityFS 子文件不支持原始字节读取")


def _save_unity3d_environment_with_unique_cabs(environment: object, output_path: Path) -> list[str]:
    """Rename CAB directory entries while preserving every child payload byte-for-byte."""
    bundle = _unity3d_bundle(environment)
    original_files = bundle.files
    used_names = {str(name).casefold() for name in original_files}
    rebuilt_files: dict[str, EndianBinaryReader] = {}
    expected_entries: dict[str, tuple[bytes, int]] = {}
    generated: list[str] = []

    for current_name, child in original_files.items():
        output_name = str(current_name)
        if CAB_FILE_NAME_PATTERN.fullmatch(output_name):
            while True:
                output_name = f"CAB-{uuid.uuid4().hex}"
                if output_name.casefold() not in used_names:
                    break
            used_names.add(output_name.casefold())
            generated.append(output_name)

        raw_bytes = _raw_bundle_child_bytes(child)
        flags = int(getattr(child, "flags", 0) or 0)
        raw_reader = EndianBinaryReader(raw_bytes)
        raw_reader.flags = flags
        raw_reader.name = output_name
        rebuilt_files[output_name] = raw_reader
        expected_entries[output_name] = (raw_bytes, flags)

    if not generated:
        raise ValueError("Unity3D 中没有可重写的 CAB 标识")

    bundle.files = rebuilt_files
    try:
        saved_bytes = bundle.save(packer="original")
    finally:
        bundle.files = original_files

    verification_environment = None
    try:
        verification_environment = UnityPy.load(saved_bytes)
        verification_files = _unity3d_bundle(verification_environment).files
        if list(verification_files) != list(expected_entries):
            raise ValueError("唯一 CAB 写入后 UnityFS 子文件目录验证失败")
        for name, child in verification_files.items():
            expected_bytes, expected_flags = expected_entries[name]
            actual_bytes = _raw_bundle_child_bytes(child)
            actual_flags = int(getattr(child, "flags", 0) or 0)
            if actual_flags != expected_flags:
                raise ValueError(f"唯一 CAB 写入后子文件 flags 发生变化：{name}")
            if len(actual_bytes) != len(expected_bytes) or hashlib.sha256(actual_bytes).digest() != hashlib.sha256(expected_bytes).digest():
                raise ValueError(f"唯一 CAB 写入后子文件内容发生变化：{name}")
        if _unity3d_cab_names(verification_environment) != sorted(generated, key=str.casefold):
            raise ValueError("唯一 CAB 写入后标识验证失败")
    finally:
        _dispose_unity_environment(verification_environment)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(saved_bytes)
    return generated


def _save_workbench_derived_unity3d_environment(environment: object, output_path: Path) -> list[str]:
    """Save object changes, then rename CAB without a second SerializedFile rewrite."""
    derived_environment = None
    try:
        with tempfile.TemporaryDirectory(prefix="star-manager-derived-unity3d-") as temporary_dir:
            content_path = Path(temporary_dir) / output_path.name
            _save_unity3d_environment(environment, content_path)
            derived_environment = UnityPy.load(content_path.read_bytes())
            return _save_unity3d_environment_with_unique_cabs(derived_environment, output_path)
    finally:
        _dispose_unity_environment(derived_environment)


def _dispose_unity_environment(environment: object | None) -> None:
    """Release UnityPy readers so Windows can remove the source Unity3D file."""
    if environment is None:
        return

    visited: set[int] = set()

    def dispose(value: object | None) -> None:
        if value is None or id(value) in visited:
            return
        visited.add(id(value))

        reader = getattr(value, "reader", None)
        close_reader = getattr(reader, "dispose", None)
        if callable(close_reader):
            try:
                close_reader()
            except Exception:
                pass

        decryptor = getattr(value, "decryptor", None)
        decryptor_reader = getattr(decryptor, "reader", None)
        close_decryptor_reader = getattr(decryptor_reader, "dispose", None)
        if callable(close_decryptor_reader):
            try:
                close_decryptor_reader()
            except Exception:
                pass

        children = getattr(value, "files", None)
        if isinstance(children, dict):
            for child in children.values():
                dispose(child)

    for collection_name in ("files", "cabs"):
        collection = getattr(environment, collection_name, None)
        if isinstance(collection, dict):
            for value in collection.values():
                dispose(value)
    gc.collect()


def regenerate_workbench_unity3d_cab(file_path: str) -> dict:
    """Atomically assign fresh CAB identities to one project-local Unity3D."""
    environment = None
    verification_environment = None
    replacement_path: Path | None = None
    try:
        source = Path(str(file_path or "")).expanduser().resolve()
        if source.suffix.lower() != ".unity3d" or not source.is_file():
            return {"ok": False, "error": "Unity3D 文件不存在"}

        with tempfile.TemporaryDirectory(prefix="star-manager-cab-") as temporary_dir:
            temporary_path = Path(temporary_dir) / source.name
            environment = UnityPy.load(source.read_bytes())
            cab_names = _save_unity3d_environment_with_unique_cabs(environment, temporary_path)
            saved_bytes = temporary_path.read_bytes()
            _dispose_unity_environment(environment)
            environment = None

            with tempfile.NamedTemporaryFile(
                prefix=f".{source.stem}-",
                suffix=source.suffix,
                dir=source.parent,
                delete=False,
            ) as replacement_file:
                replacement_file.write(saved_bytes)
                replacement_file.flush()
                os.fsync(replacement_file.fileno())
                replacement_path = Path(replacement_file.name)

            verification_environment = UnityPy.load(saved_bytes)
            verified_cab_names = _unity3d_cab_names(verification_environment)
            if sorted(cab_names, key=str.casefold) != verified_cab_names:
                raise ValueError("唯一 CAB 写入后验证失败")
            _dispose_unity_environment(verification_environment)
            verification_environment = None
            os.replace(replacement_path, source)
            replacement_path = None

        return {
            "ok": True,
            "path": str(source),
            "cab_names": verified_cab_names,
        }
    except Exception as error:
        return {"ok": False, "error": f"Unity3D CAB 重写失败：{error}"}
    finally:
        _dispose_unity_environment(verification_environment)
        _dispose_unity_environment(environment)
        if replacement_path is not None:
            replacement_path.unlink(missing_ok=True)


def import_texture2d_into_unity3d(
    file_path: str,
    image_path: str,
    texture_name: str,
    replace_existing: bool = False,
) -> dict:
    """Import a named Texture2D or replace the pixels of an existing named texture."""
    environment = None
    try:
        source = Path(str(file_path or "")).expanduser().resolve()
        image_source = Path(str(image_path or "")).expanduser().resolve()
        normalized_name = str(texture_name or "").strip()
        if source.suffix.lower() != ".unity3d" or not source.is_file():
            return {"ok": False, "error": "Unity3D 文件不存在"}
        if image_source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} or not image_source.is_file():
            return {"ok": False, "error": "外部贴图文件不存在或格式不受支持"}
        if not normalized_name:
            return {"ok": False, "error": "贴图资源名不能为空"}
        if len(normalized_name) > 160 or any(ord(char) < 32 for char in normalized_name):
            return {"ok": False, "error": "贴图资源名过长或包含不可用字符"}
        if image_source.stat().st_size > 50 * 1024 * 1024:
            return {"ok": False, "error": "外部贴图不能超过 50 MB"}

        environment = UnityPy.load(str(source))
        texture_objects = [
            obj for obj in environment.objects
            if getattr(getattr(obj, "type", None), "name", "") == "Texture2D"
        ]
        matching_textures = [
            obj
            for obj in texture_objects
            if str(getattr(obj.read(), "m_Name", "") or "").strip().casefold() == normalized_name.casefold()
        ]
        if matching_textures and not replace_existing:
            return {"ok": False, "error": f"Unity3D 中已存在贴图资源：{normalized_name}"}
        if replace_existing and not matching_textures:
            return {"ok": False, "error": f"Unity3D 中找不到要替换的贴图资源：{normalized_name}"}
        if not texture_objects:
            return {"ok": False, "error": "Unity3D 中没有可用的 Texture2D 模板"}

        target_reader = matching_textures[0] if replace_existing else None
        asset_file = target_reader.assets_file if target_reader is not None else texture_objects[0].assets_file
        texture_path_id = int(getattr(target_reader, "path_id", 0) or 0)
        texture_data = target_reader.read() if target_reader is not None else None

        if target_reader is None:
            template = texture_objects[0]
            texture_path_id = max(
                (int(path_id) for path_id in getattr(asset_file, "objects", {}).keys()),
                default=0,
            ) + 1
            while texture_path_id in asset_file.objects:
                texture_path_id += 1
            target_reader = ObjectReader(
                assets_file=asset_file,
                reader=template.reader,
                path_id=texture_path_id,
                type_id=template.type_id,
                serialized_type=template.serialized_type,
                class_id=template.class_id,
                type=template.type,
                byte_start=0,
                byte_size=0,
                is_destroyed=template.is_destroyed,
                is_stripped=template.is_stripped,
                data=None,
                read_until=None,
            )
            asset_file.objects[texture_path_id] = target_reader
            texture_data = _clone_unity_value(template.read(), {}, asset_file)
            texture_data.set_object_reader(target_reader)
            texture_data.m_Name = normalized_name

        with Image.open(image_source) as image:
            prepared_image = image.convert("RGBA")
            target_format = int(getattr(texture_data, "m_TextureFormat", 4) or 4)
            try:
                texture_data.set_image(prepared_image, target_format=target_format, mipmap_count=1)
            except Exception:
                texture_data.set_image(prepared_image, target_format=4, mipmap_count=1)
        target_reader.save_typetree(texture_data)
        asset_file.mark_changed()

        if not replace_existing:
            asset_bundle_object = next(
                (
                    obj for obj in environment.objects
                    if getattr(getattr(obj, "type", None), "name", "") == "AssetBundle"
                ),
                None,
            )
            if asset_bundle_object is not None:
                asset_bundle_data = asset_bundle_object.read()
                container = list(getattr(asset_bundle_data, "m_Container", None) or [])
                container.append((
                    normalized_name,
                    AssetInfo(
                        asset=PPtr(m_FileID=0, m_PathID=texture_path_id, assetsfile=asset_file),
                        preloadIndex=0,
                        preloadSize=0,
                    ),
                ))
                asset_bundle_data.m_Container = container
                asset_bundle_data.save()

        with tempfile.TemporaryDirectory(prefix="star-manager-texture-") as temporary_dir:
            temporary_path = Path(temporary_dir) / source.name
            _save_workbench_derived_unity3d_environment(environment, temporary_path)
            saved_bytes = temporary_path.read_bytes()
            _dispose_unity_environment(environment)
            environment = None
            replacement_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    prefix=f".{source.stem}-",
                    suffix=source.suffix,
                    dir=source.parent,
                    delete=False,
                ) as replacement_file:
                    replacement_file.write(saved_bytes)
                    replacement_file.flush()
                    os.fsync(replacement_file.fileno())
                    replacement_path = Path(replacement_file.name)
                os.replace(replacement_path, source)
                replacement_path = None
            finally:
                if replacement_path is not None:
                    replacement_path.unlink(missing_ok=True)

        return {
            "ok": True,
            "path": str(source),
            "texture_name": normalized_name,
            "texture_path_id": texture_path_id,
            "replaced": bool(replace_existing),
        }
    except Exception as error:
        action = "替换" if replace_existing else "导入"
        return {"ok": False, "error": f"贴图{action}失败：{error}"}
    finally:
        _dispose_unity_environment(environment)


def preprocess_unity3d_asset(
    file_path: str,
    operation: str,
    selected_path_id: int,
    selected_asset_file: str = "",
    new_name: str = "",
    selected_name: str = "",
) -> dict:
    """Apply a non-destructive template preprocessing operation to a runtime copy."""
    try:
        source = Path(str(file_path or "")).expanduser().resolve()
        if source.suffix.lower() != ".unity3d" or not source.is_file():
            return {"ok": False, "error": "Unity3D 文件不存在"}
        normalized_operation = str(operation or "").strip().lower()
        if normalized_operation not in {"keep_selected", "rename_selected", "duplicate_selected"}:
            return {"ok": False, "error": "不支持的 Unity3D 预处理操作"}
        if normalized_operation in {"rename_selected", "duplicate_selected"}:
            normalized_name = str(new_name or "").strip()
            if normalized_operation == "rename_selected" and not normalized_name:
                return {"ok": False, "error": "请输入新的对象名称"}
            if len(normalized_name) > 160 or any(ord(char) < 32 for char in normalized_name):
                return {"ok": False, "error": "对象名称过长或包含不可用字符"}
        else:
            normalized_name = ""

        environment = UnityPy.load(str(source))
        selected_game_object = _find_selected_game_object(
            environment,
            int(selected_path_id or 0),
            str(selected_asset_file or "").strip(),
            str(selected_name or "").strip(),
        )
        selected_data = selected_game_object.read()
        duplicate_result: dict = {}
        if normalized_operation == "rename_selected":
            selected_data.m_Name = normalized_name
            selected_data.save()
        elif normalized_operation == "duplicate_selected":
            if normalized_name:
                duplicate_result = _duplicate_selected_unity3d_object(
                    environment,
                    selected_game_object,
                    normalized_name,
                )
            else:
                duplicate_result = _duplicate_selected_unity3d_object(environment, selected_game_object)
        removed_object_count = 0
        removed_game_object_count = 0
        if normalized_operation == "keep_selected":
            removal_counts = _remove_unselected_unity3d_objects(environment, selected_game_object)
            removed_object_count = int(removal_counts["object_count"])
            removed_game_object_count = int(removal_counts["game_object_count"])

        signature = hashlib.sha1(
            f"{source}:{source.stat().st_size}:{source.stat().st_mtime_ns}:{normalized_operation}:"
            f"{selected_name}:{selected_path_id}:{selected_asset_file}:{normalized_name}".encode("utf-8")
        ).hexdigest()
        output_dir = DEFAULT_UNITY3D_PREPROCESS_DIR / signature[:2]
        output_path = output_dir / f"{_safe_export_name(source.stem, 'unity3d')}-{normalized_operation}-{signature[2:14]}.unity3d"
        _save_workbench_derived_unity3d_environment(environment, output_path)
        candidates = list_unity3d_main_data_candidates(str(output_path))
        if not candidates.get("ok"):
            raise ValueError(candidates.get("error") or "无法重新读取处理后的 Unity3D")
        result_name = str(
            (
                duplicate_result.get("name")
                if normalized_operation == "duplicate_selected"
                else getattr(selected_data, "m_Name", "")
            )
            or ""
        ).strip()
        if not result_name:
            raise ValueError("所选对象没有有效的名称")
        result_path_id = int(
            (
                duplicate_result.get("path_id")
                if normalized_operation == "duplicate_selected"
                else getattr(selected_game_object, "path_id", 0)
            )
            or 0
        )
        result_asset_file = str(
            (
                duplicate_result.get("asset_file")
                if normalized_operation == "duplicate_selected"
                else _asset_file_name(selected_game_object)
            )
            or ""
        )
        named_candidates = [
            candidate
            for candidate in [
                *candidates.get("candidates", []),
                *candidates.get("game_object_candidates", []),
            ]
            if str(candidate.get("value") or "").strip() == result_name
        ]
        matching_candidate = next(
            (
                candidate
                for candidate in named_candidates
                if int(candidate.get("path_id") or 0) == result_path_id
            ),
            named_candidates[0] if len(named_candidates) == 1 else None,
        )
        if matching_candidate:
            result_path_id = int(matching_candidate.get("path_id") or result_path_id)
            result_asset_file = str(matching_candidate.get("asset_file") or result_asset_file)
        return {
            "ok": True,
            "path": str(output_path),
            "operation": normalized_operation,
            "main_data": result_name,
            "selected_path_id": result_path_id,
            "selected_asset_file": result_asset_file,
            "candidates": candidates.get("candidates", []),
            "game_object_candidates": candidates.get("game_object_candidates", []),
            "default": candidates.get("default", ""),
            "object_count": int(candidates.get("object_count", 0) or 0),
            "game_object_count": int(candidates.get("game_object_count", 0) or 0),
            "removed_object_count": removed_object_count,
            "removed_game_object_count": removed_game_object_count,
            "duplicated_object_count": int(duplicate_result.get("object_count", 0) or 0),
            "duplicated_game_object_count": int(duplicate_result.get("game_object_count", 0) or 0),
            "duplicated_resource_count": int(duplicate_result.get("resource_count", 0) or 0),
        }
    except Exception as error:
        return {"ok": False, "error": f"Unity3D 预处理失败：{error}"}


def resolve_model_preview_file(file_name: str) -> Path | None:
    if not file_name.endswith(".glb") or Path(file_name).name != file_name:
        return None
    candidates = list(DEFAULT_MODEL_PREVIEW_DIR.glob(f"??/{file_name}"))
    return candidates[0] if candidates and candidates[0].is_file() else None
