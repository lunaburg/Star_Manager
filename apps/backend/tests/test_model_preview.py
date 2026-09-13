import json
import sqlite3
import struct
from types import SimpleNamespace
import zipfile
from pathlib import Path

import UnityPy
import pytest
from PIL import Image

from star_manager.services import model_preview
from star_manager.services.mod_database_core import init_db
from star_manager.services.model_preview import (
    _build_glb,
    _clone_unity_value,
    _unique_unity_object_name,
    _find_selected_game_object,
    _find_half_model_game_objects,
    _normalize_preview_material_color,
    _select_half_model_meshes,
    _select_main_data_meshes,
    list_unity3d_main_data_candidates,
    export_item_unity3d_file,
    import_texture2d_into_unity3d,
    preprocess_unity3d_asset,
    prepare_item_unity3d_file,
    prepare_item_model_preview,
    prepare_workbench_model_preview,
)


class FakeMesh:
    m_Vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    m_Normals = [(0, 0, 1)] * 3
    m_UV0 = [(0, 0), (1, 0), (0, 1)]

    def get_triangles(self):
        return [[(0, 1, 2)]]


class FakeObject:
    def __init__(self, path_id, type_name, value):
        self.path_id = path_id
        self.type = SimpleNamespace(name=type_name)
        self.value = value

    def read(self):
        return self.value

    def read_typetree(self):
        return self.value


def pointer(path_id):
    return SimpleNamespace(path_id=path_id)


def test_selected_object_is_resolved_from_main_data_name_before_stale_path_id():
    first = FakeObject(1, "GameObject", SimpleNamespace(m_Name="First"))
    second = FakeObject(2, "GameObject", SimpleNamespace(m_Name="T001_10"))
    environment = SimpleNamespace(objects=[first, second])

    selected = _find_selected_game_object(environment, 1, selected_name="T001_10")

    assert selected is second


def test_duplicate_object_name_is_unique_case_insensitively():
    assert _unique_unity_object_name("T001_10", {"t001_10_copy", "T001_10_copy_2"}) == "T001_10_copy_3"


def test_asset_bundle_container_exposes_cloned_root_and_preloads():
    asset_file = SimpleNamespace(name="CAB-test")
    source_key = (id(asset_file), 10)
    asset_bundle_data = SimpleNamespace(
        m_Container=[
            (
                "source_obj",
                model_preview.AssetInfo(
                    asset=model_preview.PPtr(m_FileID=0, m_PathID=10, assetsfile=asset_file),
                    preloadIndex=0,
                    preloadSize=1,
                ),
            ),
        ],
        m_PreloadTable=[model_preview.PPtr(m_FileID=0, m_PathID=11, assetsfile=asset_file)],
        save=lambda: None,
    )
    asset_bundle_object = SimpleNamespace(
        type=SimpleNamespace(name="AssetBundle"),
        assets_file=asset_file,
        read=lambda: asset_bundle_data,
    )
    cloned_reader = SimpleNamespace(path_id=20, assets_file=asset_file)

    model_preview._append_asset_bundle_duplicate_entry(
        {"objects": [asset_bundle_object]},
        source_key,
        "Copied_Object",
        {(id(asset_file), 11): (id(asset_file), 21)},
        {source_key: cloned_reader},
        {},
    )

    copied_entry = next(entry for entry in asset_bundle_data.m_Container if entry[0] == "copied_object")
    assert copied_entry[1].asset.m_PathID == 20
    assert copied_entry[1].preloadIndex == 1
    assert copied_entry[1].preloadSize == 2
    assert [pointer.m_PathID for pointer in asset_bundle_data.m_PreloadTable] == [11, 21, 20]


def test_clone_unity_value_remaps_dynamic_serialized_fields():
    class FakeSerializedValue:
        __attrs_attrs__ = (SimpleNamespace(name="m_GameObject"),)

        def __init__(self, asset_file):
            self.m_GameObject = model_preview.PPtr(m_FileID=0, m_PathID=1, assetsfile=asset_file)
            self.rendCheckVisible = [model_preview.PPtr(m_FileID=0, m_PathID=2, assetsfile=asset_file)]
            self.rendNormal01 = [model_preview.PPtr(m_FileID=0, m_PathID=3, assetsfile=asset_file)]
            self.objTopDef = model_preview.PPtr(m_FileID=0, m_PathID=4, assetsfile=asset_file)
            self.objTopHalf = model_preview.PPtr(m_FileID=0, m_PathID=5, assetsfile=asset_file)
            self.objBotDef = model_preview.PPtr(m_FileID=0, m_PathID=6, assetsfile=asset_file)
            self.objBotHalf = model_preview.PPtr(m_FileID=0, m_PathID=7, assetsfile=asset_file)
            self.custom_color = "preserve"

    asset_file = SimpleNamespace()
    source = FakeSerializedValue(asset_file)
    cloned = _clone_unity_value(
        source,
        {
            (id(asset_file), 1): (id(asset_file), 11),
            (id(asset_file), 2): (id(asset_file), 12),
            (id(asset_file), 3): (id(asset_file), 13),
            (id(asset_file), 4): (id(asset_file), 14),
            (id(asset_file), 5): (id(asset_file), 15),
            (id(asset_file), 6): (id(asset_file), 16),
            (id(asset_file), 7): (id(asset_file), 17),
        },
        asset_file,
    )

    assert cloned is not source
    assert cloned.m_GameObject.m_PathID == 11
    assert cloned.rendCheckVisible[0].m_PathID == 12
    assert cloned.rendNormal01[0].m_PathID == 13
    assert cloned.objTopDef.m_PathID == 14
    assert cloned.objTopHalf.m_PathID == 15
    assert cloned.objBotDef.m_PathID == 16
    assert cloned.objBotHalf.m_PathID == 17
    assert cloned.custom_color == "preserve"
    assert source.rendCheckVisible[0].m_PathID == 2
    assert source.rendNormal01[0].m_PathID == 3
    assert source.objTopDef.m_PathID == 4
    assert source.objTopHalf.m_PathID == 5
    assert source.objBotDef.m_PathID == 6
    assert source.objBotHalf.m_PathID == 7


def test_unity_value_pointer_scan_includes_dynamic_fields():
    class FakeSerializedValue:
        __attrs_attrs__ = (SimpleNamespace(name="m_GameObject"),)

        def __init__(self, asset_file):
            self.m_GameObject = model_preview.PPtr(m_FileID=0, m_PathID=1, assetsfile=asset_file)
            self.rendNormal01 = [model_preview.PPtr(m_FileID=0, m_PathID=2, assetsfile=asset_file)]

    asset_file = SimpleNamespace()
    pointers = list(model_preview._iter_unity_value_pointers(FakeSerializedValue(asset_file)))

    assert [pointer.m_PathID for pointer in pointers] == [1, 2]


def test_duplicate_selected_preprocess_returns_the_new_main_data_identity(tmp_path, monkeypatch):
    source = tmp_path / "template.unity3d"
    source.write_bytes(b"unity3d")
    selected_data = SimpleNamespace(m_Name="T001_10")
    selected = FakeObject(10, "GameObject", selected_data)
    environment = SimpleNamespace(objects=[selected])
    monkeypatch.setattr(model_preview.UnityPy, "load", lambda _: environment)
    monkeypatch.setattr(
        model_preview,
        "_duplicate_selected_unity3d_object",
        lambda _environment, _selected: {
            "name": "T001_10_copy",
            "path_id": 99,
            "asset_file": "CAB-template",
            "object_count": 4,
            "game_object_count": 2,
        },
    )
    monkeypatch.setattr(model_preview, "_save_workbench_derived_unity3d_environment", lambda _environment, _path: [])
    monkeypatch.setattr(
        model_preview,
        "list_unity3d_main_data_candidates",
        lambda _path: {
            "ok": True,
            "candidates": [{
                "value": "T001_10_copy",
                "label": "T001_10_copy",
                "kind": "GameObject",
                "path_id": 100,
                "asset_file": "CAB-derived",
            }],
            "game_object_candidates": [{
                "value": "T001_10_copy",
                "label": "T001_10_copy",
                "kind": "GameObject",
                "path_id": 99,
                "asset_file": "CAB-derived",
            }],
            "default": "T001_10_copy",
            "object_count": 8,
            "game_object_count": 4,
        },
    )

    result = preprocess_unity3d_asset(
        str(source),
        "duplicate_selected",
        selected_path_id=10,
        selected_asset_file="",
        selected_name="T001_10",
    )

    assert result["ok"] is True
    assert result["operation"] == "duplicate_selected"
    assert result["main_data"] == "T001_10_copy"
    assert result["selected_path_id"] == 99
    assert result["selected_asset_file"] == "CAB-derived"
    assert result["game_object_candidates"][0]["path_id"] == 99
    assert result["duplicated_object_count"] == 4
    assert result["duplicated_game_object_count"] == 2


def test_build_glb_contains_renderable_mesh():
    payload = _build_glb([("Triangle", FakeMesh())])
    assert payload[:4] == b"glTF"
    version, total_length = struct.unpack_from("<II", payload, 4)
    assert version == 2
    assert total_length == len(payload)
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    assert document["meshes"][0]["name"] == "Triangle"
    assert document["meshes"][0]["primitives"][0]["attributes"]["POSITION"] == 0
    assert document["buffers"][0]["byteLength"] > 0


def test_build_glb_embeds_material_textures():
    png_header = b"\x89PNG\r\n\x1a\npreview"
    payload = _build_glb(
        [("Triangle", FakeMesh(), [1])],
        [
            {"name": "Fallback", "color": [1, 1, 1, 1]},
            {"name": "Fabric", "color": [0.8, 0.7, 0.6, 1], "base_color_png": png_header, "transparent": True},
        ],
    )
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    assert document["meshes"][0]["primitives"][0]["material"] == 1
    assert document["materials"][0]["doubleSided"] is False
    assert document["materials"][1]["doubleSided"] is False
    assert document["materials"][1]["alphaMode"] == "MASK"
    assert document["materials"][1]["alphaCutoff"] == 0.5
    assert document["materials"][1]["pbrMetallicRoughness"]["baseColorTexture"] == {"index": 0}
    assert document["images"][0]["mimeType"] == "image/png"


def test_textured_material_does_not_become_fully_transparent_from_zero_shader_color_alpha():
    assert _normalize_preview_material_color([1.1, 1.1, 1.145, 0], True) == [1.0, 1.0, 1.0, 1.0]
    assert _normalize_preview_material_color([1, 1, 1, 0], False) == [1.0, 1.0, 1.0, 0.0]


def test_build_glb_preserves_skin_weights_and_bind_poses():
    skin = {
        "bone_names": ["cf_N_height"],
        "fallback_bone_names": [[]],
        "inverse_bind_matrices": [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]],
        "indices": [(0, 0, 0, 0)] * 3,
        "weights": [(1, 0, 0, 0)] * 3,
    }
    payload = _build_glb([("SkinnedTriangle", FakeMesh(), [0], skin)])
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    attributes = document["meshes"][0]["primitives"][0]["attributes"]
    assert "JOINTS_0" in attributes
    assert "WEIGHTS_0" in attributes
    assert document["nodes"][0]["skin"] == 0
    assert document["nodes"][1]["name"] == "cf_N_height"
    assert document["skins"][0]["joints"] == [1]


def test_build_glb_preserves_joint_transform_matrix():
    joint_matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, 3, 4, 1]
    skin = {
        "bone_names": ["cf_J_Legsk_01_00"],
        "fallback_bone_names": [["cf_J_Kosi01_s"]],
        "bone_matrices": [joint_matrix],
        "inverse_bind_matrices": [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]],
        "indices": [(0, 0, 0, 0)] * 3,
        "weights": [(1, 0, 0, 0)] * 3,
    }
    payload = _build_glb([("Skirt", FakeMesh(), [0], skin)])
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    joint_node = document["nodes"][document["skins"][0]["joints"][0]]

    assert joint_node["name"] == "cf_J_Legsk_01_00"
    assert joint_node["matrix"] == joint_matrix


def test_build_glb_reuses_joint_nodes_between_skinned_meshes():
    skin = {
        "bone_names": ["cf_N_height"],
        "fallback_bone_names": [[]],
        "inverse_bind_matrices": [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]],
        "indices": [(0, 0, 0, 0)] * 3,
        "weights": [(1, 0, 0, 0)] * 3,
    }
    payload = _build_glb([
        ("First", FakeMesh(), [0], skin),
        ("Second", FakeMesh(), [0], skin),
    ])
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    assert document["skins"][0]["joints"] == document["skins"][1]["joints"]
    assert [node["name"] for node in document["nodes"]].count("cf_N_height") == 1


def test_build_glb_preserves_renderer_node_matrix():
    matrix = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]
    payload = _build_glb([("Rotated", FakeMesh(), [0], None, matrix)])
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    assert document["nodes"][0]["matrix"] == matrix


def test_prepare_preview_opens_database_path(tmp_path):
    result = prepare_item_model_preview(999, db_path=tmp_path / "preview.sqlite")
    assert result == {"ok": False, "error": "物品不存在"}


def test_export_item_unity3d_copies_archive_member_without_modifying_source(tmp_path):
    db_path = tmp_path / "mod_database.sqlite"
    zipmod_path = tmp_path / "mods" / "author" / "sample.zipmod"
    zipmod_path.parent.mkdir(parents=True)
    payload = b"unity3d-source"
    with zipfile.ZipFile(zipmod_path, "w") as archive:
        archive.writestr("abdata/chara/01/sample.unity3d", payload)

    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        init_db(conn)
        now = "2026-09-05T00:00:00+00:00"
        zipmod_id = conn.execute(
            """INSERT INTO zipmods (
                guid, name, file_path, relative_path, file_name, scan_status,
                last_scanned_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'ok', ?, ?, ?)""",
            ("sample.guid", "Sample", str(zipmod_path), "author/sample.zipmod", zipmod_path.name, now, now, now),
        ).lastrowid
        item_id = conn.execute(
            """INSERT INTO mod_items (
                zipmod_id, zipmod_guid, item_id, kind, name, main_manifest, main_ab,
                parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?)""",
            (zipmod_id, "sample.guid", "100", "240", "Sample Item", "abdata", "chara/01/sample.unity3d", now, now),
        ).lastrowid
        conn.commit()
    finally:
        conn.close()

    output_path = tmp_path / "exports" / "sample.unity3d"
    result = export_item_unity3d_file(item_id, str(output_path), db_path=db_path)

    assert result["ok"] is True
    assert output_path.read_bytes() == payload
    with zipfile.ZipFile(zipmod_path) as archive:
        assert archive.read("abdata/chara/01/sample.unity3d") == payload


def test_prepare_workbench_preview_uses_project_unity3d_and_main_data(tmp_path, monkeypatch):
    source = tmp_path / "project-item.unity3d"
    source.write_bytes(b"unity3d")
    preview_dir = tmp_path / "previews"
    environment = SimpleNamespace(objects=[])

    monkeypatch.setattr(model_preview, "DEFAULT_MODEL_PREVIEW_DIR", preview_dir)
    monkeypatch.setattr(model_preview.UnityPy, "load", lambda path: environment)
    monkeypatch.setattr(model_preview, "_select_main_data_meshes", lambda *_args, **_kwargs: ({31}, "main_data"))
    monkeypatch.setattr(model_preview, "_select_half_model_meshes", lambda *_args, **_kwargs: (set(), []))
    monkeypatch.setattr(model_preview, "_select_variant_game_objects", lambda *_args, **_kwargs: {7})

    def write_preview(_environment, _mesh_ids, output, **_kwargs):
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"glb")
        return 1

    monkeypatch.setattr(model_preview, "_write_preview_model", write_preview)
    monkeypatch.setattr(model_preview, "_dispose_unity_environment", lambda _environment: None)

    result = prepare_workbench_model_preview(str(source), "B004_base_obj", "1")

    assert result["ok"] is True
    assert result["selection"] == "main_data"
    assert result["mesh_count"] == 1
    assert result["source"] == str(source.resolve())
    assert result["url"].startswith("/mods/models/")
    preview_name = result["url"].split("/")[-1]
    assert (preview_dir / preview_name[:2] / preview_name).is_file()


def test_main_data_selects_only_descendant_renderer_meshes():
    environment = SimpleNamespace(objects=[
        FakeObject(1, "GameObject", SimpleNamespace(m_Name="Target")),
        FakeObject(2, "GameObject", SimpleNamespace(m_Name="Child")),
        FakeObject(3, "GameObject", SimpleNamespace(m_Name="Other")),
        FakeObject(10, "Transform", SimpleNamespace(m_GameObject=pointer(1), m_Children=[pointer(20)])),
        FakeObject(20, "Transform", SimpleNamespace(m_GameObject=pointer(2), m_Children=[])),
        FakeObject(30, "Transform", SimpleNamespace(m_GameObject=pointer(3), m_Children=[])),
        FakeObject(40, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(2), m_Mesh=pointer(100))),
        FakeObject(50, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(3), m_Mesh=pointer(200))),
    ])
    mesh_ids, mode = _select_main_data_meshes(environment, "target")
    assert mode == "main_data"
    assert mesh_ids == {100}


def test_missing_main_data_name_uses_explicit_fallback():
    environment = SimpleNamespace(objects=[])
    mesh_ids, mode = _select_main_data_meshes(environment, "missing")
    assert mesh_ids is None
    assert mode == "all_meshes_main_data_not_found"


def test_half_model_references_are_found_and_excluded_from_main_data_meshes():
    environment = SimpleNamespace(objects=[
        FakeObject(1, "GameObject", SimpleNamespace(m_Name="n_top")),
        FakeObject(2, "GameObject", SimpleNamespace(m_Name="n_top_a")),
        FakeObject(3, "GameObject", SimpleNamespace(m_Name="n_top_b")),
        FakeObject(4, "GameObject", SimpleNamespace(m_Name="half_child")),
        FakeObject(10, "Transform", SimpleNamespace(m_GameObject=pointer(1), m_Children=[pointer(20), pointer(30)])),
        FakeObject(20, "Transform", SimpleNamespace(m_GameObject=pointer(2), m_Children=[])),
        FakeObject(30, "Transform", SimpleNamespace(m_GameObject=pointer(3), m_Children=[pointer(40)])),
        FakeObject(40, "Transform", SimpleNamespace(m_GameObject=pointer(4), m_Children=[])),
        FakeObject(50, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(2), m_Mesh=pointer(100))),
        FakeObject(60, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(4), m_Mesh=pointer(200))),
        FakeObject(70, "MonoBehaviour", {
            "m_GameObject": {"m_FileID": 0, "m_PathID": 1},
            "objTopDef": {"m_FileID": 0, "m_PathID": 2},
            "objTopHalf": {"m_FileID": 0, "m_PathID": 3},
            "objBotHalf": {"m_FileID": 0, "m_PathID": 0},
        }),
    ])

    half_ids, references = _find_half_model_game_objects(environment, {1, 2, 3, 4})
    assert half_ids == {3}
    assert references == [{"field": "objTopHalf", "path_id": 3, "mono_behaviour_path_id": 70}]
    mesh_ids, mode = _select_main_data_meshes(environment, "n_top", exclude_half_models=True)
    assert mode == "main_data"
    assert mesh_ids == {100}
    half_mesh_ids, half_references = _select_half_model_meshes(environment, "n_top")
    assert half_mesh_ids == {200}
    assert half_references == references


def test_normal_renderer_is_kept_when_half_variant_reuses_the_same_mesh():
    environment = SimpleNamespace(objects=[
        FakeObject(1, "GameObject", SimpleNamespace(m_Name="clothmesh")),
        FakeObject(2, "GameObject", SimpleNamespace(m_Name="top_a")),
        FakeObject(3, "GameObject", SimpleNamespace(m_Name="top_b")),
        FakeObject(10, "Transform", SimpleNamespace(m_GameObject=pointer(1), m_Children=[pointer(20), pointer(30)])),
        FakeObject(20, "Transform", SimpleNamespace(m_GameObject=pointer(2), m_Children=[])),
        FakeObject(30, "Transform", SimpleNamespace(m_GameObject=pointer(3), m_Children=[])),
        FakeObject(40, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(2), m_Mesh=pointer(100))),
        FakeObject(50, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(3), m_Mesh=pointer(100))),
        FakeObject(60, "MonoBehaviour", {
            "m_GameObject": {"m_PathID": 1},
            "objTopHalf": {"m_PathID": 3},
        }),
    ])

    mesh_ids, mode = _select_main_data_meshes(environment, "clothmesh", exclude_half_models=True)

    assert mode == "main_data"
    assert mesh_ids == {100}


def test_half_model_fields_on_another_item_are_ignored():
    environment = SimpleNamespace(objects=[
        FakeObject(1, "GameObject", SimpleNamespace(m_Name="Target")),
        FakeObject(2, "GameObject", SimpleNamespace(m_Name="Other")),
        FakeObject(10, "Transform", SimpleNamespace(m_GameObject=pointer(1), m_Children=[])),
        FakeObject(20, "Transform", SimpleNamespace(m_GameObject=pointer(2), m_Children=[])),
        FakeObject(30, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(1), m_Mesh=pointer(100))),
        FakeObject(40, "MonoBehaviour", {
            "m_GameObject": {"m_PathID": 2},
            "objBothHalf": {"m_PathID": 1},
        }),
    ])
    mesh_ids, mode = _select_main_data_meshes(environment, "Target")
    assert mode == "main_data"
    assert mesh_ids == {100}


def test_prepare_item_unity3d_file_extracts_zipmod_member(tmp_path, monkeypatch):
    zipmod_path = tmp_path / "mods" / "sample.zipmod"
    zipmod_path.parent.mkdir()
    unity3d_payload = b"UnityFS test payload"
    with zipfile.ZipFile(zipmod_path, "w") as archive:
        archive.writestr("abdata/sample.unity3d", unity3d_payload)

    db_path = tmp_path / "runtime.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        init_db(conn)
        now = "2026-08-01T00:00:00+00:00"
        cursor = conn.execute(
            """INSERT INTO zipmods (
                guid, file_path, relative_path, file_name, scan_status,
                last_scanned_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("sample-guid", str(zipmod_path), "sample.zipmod", zipmod_path.name, "ok", now, now, now),
        )
        conn.execute(
            """INSERT INTO mod_items (
                zipmod_id, zipmod_guid, item_id, main_manifest, main_ab,
                parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cursor.lastrowid, "sample-guid", "1", "abdata", "abdata/sample.unity3d", "ok", now, now),
        )

    monkeypatch.setattr(model_preview, "DEFAULT_UNITY3D_OPEN_DIR", tmp_path / "unity3d_open")
    result = prepare_item_unity3d_file(1, db_path=db_path)

    assert result["ok"] is True
    assert result["extracted"] is True
    output_path = tmp_path / "unity3d_open" / Path(result["unity3d_path"]).relative_to(tmp_path / "unity3d_open")
    assert output_path.is_file()
    assert output_path.read_bytes() == unity3d_payload


def test_save_unity3d_environment_preserves_original_bundle_packing(tmp_path):
    calls = []

    class FakeEnvironment:
        def save(self, *, pack, out_path):
            calls.append(pack)
            Path(out_path, "asset.unity3d").write_bytes(b"UnityFS")

    output_path = tmp_path / "processed.unity3d"
    model_preview._save_unity3d_environment(FakeEnvironment(), output_path)

    assert calls == ["original"]
    assert output_path.read_bytes() == b"UnityFS"


def test_unique_cab_save_preserves_bundle_child_payloads(tmp_path, monkeypatch):
    old_cab = "CAB-a7fe78e221cfdc3e09eb7c10b4449ac0"
    resource_name = "CAB-26486298020695ec446accc3b402b4d7.resS"
    serialized_payload = b"serialized-file-with-original-object-offsets"
    resource_payload = b"streamed-resource-payload"
    saved_entries = []

    class FakeSerializedFile:
        def __init__(self, name):
            self.name = old_cab
            self.reader = SimpleNamespace(bytes=serialized_payload)
            self.flags = 4

    class FakeBundle:
        def __init__(self):
            self.signature = "UnityFS"
            self.asset_file = FakeSerializedFile(old_cab)
            self.resource_file = SimpleNamespace(
                name=resource_name,
                bytes=resource_payload,
                flags=0,
            )
            self.files = {
                resource_name: self.resource_file,
                old_cab: self.asset_file,
            }

        def save(self, *, packer):
            assert packer == "original"
            entries = [
                (name, bytes(child.bytes), child.flags)
                for name, child in self.files.items()
            ]
            assert all(isinstance(child, model_preview.EndianBinaryReader) for child in self.files.values())
            saved_entries.append(entries)
            return b"UnityFS-rebuilt"

    class FakeEnvironment:
        def __init__(self):
            self.bundle = FakeBundle()
            self.files = {"template.unity3d": self.bundle}

    def load_saved_bundle(payload):
        assert payload == b"UnityFS-rebuilt"
        files = {
            name: SimpleNamespace(bytes=raw_bytes, flags=flags)
            for name, raw_bytes, flags in saved_entries[-1]
        }
        return SimpleNamespace(
            files={"verified.unity3d": SimpleNamespace(signature="UnityFS", files=files)},
        )

    monkeypatch.setattr(model_preview.UnityPy, "load", load_saved_bundle)

    first = FakeEnvironment()
    second = FakeEnvironment()
    first_cabs = model_preview._save_unity3d_environment_with_unique_cabs(
        first,
        tmp_path / "first.unity3d",
    )
    second_cabs = model_preview._save_unity3d_environment_with_unique_cabs(
        second,
        tmp_path / "second.unity3d",
    )

    assert len(first_cabs) == 1
    assert len(second_cabs) == 1
    assert first_cabs[0] != second_cabs[0]
    assert model_preview.CAB_FILE_NAME_PATTERN.fullmatch(first_cabs[0])
    assert model_preview.CAB_FILE_NAME_PATTERN.fullmatch(second_cabs[0])
    assert old_cab in first.bundle.files
    assert old_cab in second.bundle.files
    assert resource_name in first.bundle.files
    assert resource_name in second.bundle.files
    assert first.bundle.asset_file.name == old_cab
    assert second.bundle.asset_file.name == old_cab
    assert saved_entries[0] == [
        (resource_name, resource_payload, 0),
        (first_cabs[0], serialized_payload, 4),
    ]
    assert saved_entries[1] == [
        (resource_name, resource_payload, 0),
        (second_cabs[0], serialized_payload, 4),
    ]
    assert (tmp_path / "first.unity3d").read_bytes() == b"UnityFS-rebuilt"
    assert (tmp_path / "second.unity3d").read_bytes() == b"UnityFS-rebuilt"


def test_workbench_derived_save_serializes_changes_before_raw_cab_rename(tmp_path, monkeypatch):
    output_path = tmp_path / "derived.unity3d"
    source_environment = SimpleNamespace()
    serialized_environment = SimpleNamespace(marker="serialized")
    calls = []

    def save_changed_environment(environment, path):
        calls.append(("serialize", environment))
        path.write_bytes(b"changed-content")

    def load_changed_environment(payload):
        calls.append(("reload", payload))
        return serialized_environment

    def save_unique_cab(environment, path):
        calls.append(("rename", environment))
        path.write_bytes(b"final")
        return ["unused"]

    monkeypatch.setattr(
        model_preview,
        "_save_unity3d_environment",
        save_changed_environment,
    )
    monkeypatch.setattr(
        model_preview.UnityPy,
        "load",
        load_changed_environment,
    )
    monkeypatch.setattr(
        model_preview,
        "_save_unity3d_environment_with_unique_cabs",
        save_unique_cab,
    )
    monkeypatch.setattr(
        model_preview,
        "_dispose_unity_environment",
        lambda environment: calls.append(("dispose", environment)),
    )

    cab_names = model_preview._save_workbench_derived_unity3d_environment(source_environment, output_path)

    assert cab_names == ["unused"]
    assert output_path.read_bytes() == b"final"
    assert calls == [
        ("serialize", source_environment),
        ("reload", b"changed-content"),
        ("rename", serialized_environment),
        ("dispose", serialized_environment),
    ]


def test_regenerate_workbench_unity3d_cab_replaces_source_after_verification(tmp_path, monkeypatch):
    source = tmp_path / "project-resource.unity3d"
    source.write_bytes(b"original")
    generated_cab = "CAB-0123456789abcdef0123456789abcdef"
    source_environment = SimpleNamespace(files={})
    verified_environment = SimpleNamespace(
        files={
            "project-resource.unity3d": SimpleNamespace(
                files={generated_cab: SimpleNamespace(name=generated_cab)},
            ),
        },
    )

    monkeypatch.setattr(
        model_preview.UnityPy,
        "load",
        lambda payload: source_environment if payload == b"original" else verified_environment,
    )
    monkeypatch.setattr(
        model_preview,
        "_save_unity3d_environment_with_unique_cabs",
        lambda _environment, output_path: Path(output_path).write_bytes(b"derived") and [generated_cab],
    )
    monkeypatch.setattr(model_preview, "_dispose_unity_environment", lambda _environment: None)

    result = model_preview.regenerate_workbench_unity3d_cab(str(source))

    assert result == {
        "ok": True,
        "path": str(source.resolve()),
        "cab_names": [generated_cab],
    }
    assert source.read_bytes() == b"derived"


def test_list_unity3d_main_data_candidates_only_includes_animator_objects(tmp_path, monkeypatch):
    source = tmp_path / "template.unity3d"
    source.write_bytes(b"unity3d")
    asset_file = SimpleNamespace(name="CAB-template")
    root = FakeObject(1, "GameObject", SimpleNamespace(m_Name="Root"))
    child = FakeObject(2, "GameObject", SimpleNamespace(m_Name="Child"))
    root_transform = FakeObject(
        10,
        "Transform",
        SimpleNamespace(m_GameObject=pointer(1), m_Father=pointer(0)),
    )
    child_transform = FakeObject(
        20,
        "Transform",
        SimpleNamespace(m_GameObject=pointer(2), m_Father=pointer(10)),
    )
    renderer = FakeObject(30, "MeshRenderer", SimpleNamespace(m_GameObject=pointer(2)))
    animator = FakeObject(40, "Animator", SimpleNamespace(m_GameObject=pointer(1)))
    for item in (root, child, root_transform, child_transform, renderer, animator):
        item.assets_file = asset_file
    environment = SimpleNamespace(objects=[root, child, root_transform, child_transform, renderer, animator], container={})
    monkeypatch.setattr(model_preview.UnityPy, "load", lambda _: environment)

    result = list_unity3d_main_data_candidates(str(source))

    assert result["ok"] is True
    assert result["game_object_count"] == 2
    assert result["game_object_names"] == ["Child", "Root"]
    assert result["candidates"] == [
        {"value": "Root", "label": "Root", "kind": "GameObject", "path_id": 1, "asset_file": "CAB-template", "component_index": 0, "is_animator": True},
    ]
    assert result["game_object_candidates"] == [
        {"value": "Root", "label": "Root", "kind": "GameObject", "path_id": 1, "asset_file": "CAB-template", "component_index": 0, "is_renderer_root": True, "is_animator": True},
    ]


def test_list_unity3d_main_data_candidates_falls_back_to_renderer_roots_without_native_animator(tmp_path, monkeypatch):
    source = tmp_path / "legacy.unity3d"
    source.write_bytes(b"unity3d")
    asset_file = SimpleNamespace(name="CAB-legacy")
    root = FakeObject(1, "GameObject", SimpleNamespace(m_Name="Root"))
    child = FakeObject(2, "GameObject", SimpleNamespace(m_Name="Bone"))
    root_transform = FakeObject(
        10,
        "Transform",
        SimpleNamespace(m_GameObject=pointer(1), m_Father=pointer(0)),
    )
    child_transform = FakeObject(
        20,
        "Transform",
        SimpleNamespace(m_GameObject=pointer(2), m_Father=pointer(10)),
    )
    renderer = FakeObject(30, "SkinnedMeshRenderer", SimpleNamespace(m_GameObject=pointer(2)))
    for item in (root, child, root_transform, child_transform, renderer):
        item.assets_file = asset_file
    environment = SimpleNamespace(objects=[root, child, root_transform, child_transform, renderer], container={})
    monkeypatch.setattr(model_preview.UnityPy, "load", lambda _: environment)

    result = list_unity3d_main_data_candidates(str(source))

    assert result["ok"] is True
    assert [candidate["value"] for candidate in result["candidates"]] == ["Root"]
    assert [candidate["value"] for candidate in result["game_object_candidates"]] == ["Root"]


def test_list_unity3d_main_data_candidates_includes_texture2d_names(tmp_path, monkeypatch):
    source = tmp_path / "template.unity3d"
    source.write_bytes(b"unity3d")
    asset_file = SimpleNamespace(name="CAB-template")
    color_mask = FakeObject(41, "Texture2D", SimpleNamespace(m_Name="mc_1"))
    main_texture = FakeObject(42, "Texture2D", SimpleNamespace(m_Name="body_diffuse"))
    color_mask.assets_file = asset_file
    main_texture.assets_file = asset_file
    environment = SimpleNamespace(objects=[main_texture, color_mask], container={})
    monkeypatch.setattr(model_preview.UnityPy, "load", lambda _: environment)

    result = list_unity3d_main_data_candidates(str(source))

    assert result["ok"] is True
    assert result["texture_count"] == 2
    assert result["texture_candidates"] == [
        {"value": "body_diffuse", "label": "body_diffuse", "kind": "Texture2D", "path_id": 42, "asset_file": "CAB-template", "component_index": 0},
        {"value": "mc_1", "label": "mc_1", "kind": "Texture2D", "path_id": 41, "asset_file": "CAB-template", "component_index": 1},
    ]


def test_import_texture2d_into_unity3d_adds_named_texture_and_container_entry(tmp_path):
    template_path = Path(__file__).parents[2] / "build-resources" / "workbench-templates" / "workbench-template.unity3d"
    if not template_path.is_file():
        pytest.skip("workbench Unity3D template is not available in this checkout")
    target_path = tmp_path / "main.unity3d"
    image_path = tmp_path / "external.png"
    target_path.write_bytes(template_path.read_bytes())
    Image.new("RGBA", (8, 8), (200, 40, 70, 255)).save(image_path)

    result = import_texture2d_into_unity3d(
        str(target_path),
        str(image_path),
        "test_external_diffuse",
    )

    assert result["ok"] is True
    assert result["texture_name"] == "test_external_diffuse"

    environment = UnityPy.load(str(target_path))
    texture_names = {
        str(getattr(obj.read(), "m_Name", ""))
        for obj in environment.objects
        if getattr(getattr(obj, "type", None), "name", "") == "Texture2D"
    }
    asset_bundle = next(
        obj.read()
        for obj in environment.objects
        if getattr(getattr(obj, "type", None), "name", "") == "AssetBundle"
    )
    container_names = {
        str(entry[0])
        for entry in (getattr(asset_bundle, "m_Container", None) or [])
    }

    assert "test_external_diffuse" in texture_names
    assert "test_external_diffuse" in container_names


def test_import_texture2d_into_unity3d_replaces_existing_texture_in_place(tmp_path, monkeypatch):
    source = tmp_path / "main.unity3d"
    image_path = tmp_path / "replacement.png"
    source.write_bytes(b"original")
    Image.new("RGBA", (6, 4), (20, 90, 220, 255)).save(image_path)

    class FakeTextureData:
        m_Name = "body_diffuse"
        m_TextureFormat = 4

        def __init__(self):
            self.replacement_size = None
            self.replacement_pixel = None

        def set_image(self, image, target_format, mipmap_count):
            assert target_format == 4
            assert mipmap_count == 1
            self.replacement_size = image.size
            self.replacement_pixel = image.getpixel((0, 0))

    texture_data = FakeTextureData()
    asset_file = SimpleNamespace(mark_changed=lambda: None)
    texture = FakeObject(42, "Texture2D", texture_data)
    texture.assets_file = asset_file
    texture.save_typetree = lambda value: setattr(texture, "saved_value", value)
    environment = SimpleNamespace(objects=[texture])

    monkeypatch.setattr(model_preview.UnityPy, "load", lambda _: environment)
    monkeypatch.setattr(
        model_preview,
        "_save_workbench_derived_unity3d_environment",
        lambda _environment, output_path: Path(output_path).write_bytes(b"replaced") or [],
    )
    monkeypatch.setattr(model_preview, "_dispose_unity_environment", lambda _environment: None)

    result = import_texture2d_into_unity3d(
        str(source),
        str(image_path),
        "body_diffuse",
        replace_existing=True,
    )

    assert result == {
        "ok": True,
        "path": str(source.resolve()),
        "texture_name": "body_diffuse",
        "texture_path_id": 42,
        "replaced": True,
    }
    assert source.read_bytes() == b"replaced"
    assert texture.saved_value is texture_data
    assert texture_data.replacement_size == (6, 4)
    assert texture_data.replacement_pixel == (20, 90, 220, 255)
