import json
import struct
from types import SimpleNamespace

from star_manager.services.model_preview import (
    _build_fbx_ascii,
    _build_glb,
    _find_half_model_game_objects,
    _select_half_model_meshes,
    _select_main_data_meshes,
    prepare_item_model_preview,
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
            {"name": "Fabric", "color": [0.8, 0.7, 0.6, 1], "base_color_png": png_header},
        ],
    )
    json_length = struct.unpack_from("<I", payload, 12)[0]
    document = json.loads(payload[20 : 20 + json_length])
    assert document["meshes"][0]["primitives"][0]["material"] == 1
    assert document["materials"][1]["pbrMetallicRoughness"]["baseColorTexture"] == {"index": 0}
    assert document["images"][0]["mimeType"] == "image/png"


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


def test_build_fbx_contains_mesh_material_uv_and_texture_connections():
    document = _build_fbx_ascii(
        [("Triangle", FakeMesh(), [1])],
        [
            {"name": "Fallback", "color": [1, 1, 1, 1]},
            {"name": "Fabric", "color": [0.8, 0.7, 0.6, 1], "roughness": 0.5},
        ],
        {1: ("D:/exports/textures/fabric.png", "textures/fabric.png")},
    )
    assert "FBXVersion: 7400" in document
    assert 'Geometry::Triangle' in document
    assert "PolygonVertexIndex: *3" in document
    assert 'LayerElementUV: 0' in document
    assert 'Material::Fabric' in document
    assert 'RelativeFilename: "textures/fabric.png"' in document
    assert '"DiffuseColor"' in document


def test_prepare_preview_opens_database_path(tmp_path):
    result = prepare_item_model_preview(999, db_path=tmp_path / "preview.sqlite")
    assert result == {"ok": False, "error": "物品不存在"}


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
