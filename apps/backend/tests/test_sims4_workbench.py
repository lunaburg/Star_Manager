from __future__ import annotations

import io
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from star_manager.services import sims4_workbench


SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from extract_ts4_package_fbx import (  # noqa: E402
    align_mesh_to_hs2,
    combine_alpha_coverage,
    decode_rle2,
    fbx_object_name,
    filter_mesh_by_alpha_coverage,
    parse_geom,
)


class FakePackageFormatError(RuntimeError):
    pass


class FakeGeomFormatError(RuntimeError):
    pass


def fake_extractor(source: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True)
    model_path = output_dir / "sample_model01_lod0.fbx"
    texture_dir = output_dir / "textures"
    texture_dir.mkdir()
    texture_path = texture_dir / "texture_01.png"
    model_path.write_bytes(b"fbx")
    texture_path.write_bytes(b"png")
    return {
        "geom_resource_count": 4,
        "rle2_resource_count": 2,
        "skipped_non_lod0_count": 3,
        "exports": [
            {
                "file": model_path.name,
                "vertices": 1200,
                "triangles": 2200,
                "uv_sets": 2,
                "removed_untextured_vertices": 300,
                "removed_untextured_triangles": 500,
                "default_texture": {
                    "file": texture_path.name,
                    "relative_path": "textures/texture_01.png",
                    "resource_index": 7,
                },
            }
        ],
        "textures": [
            {
                "file": texture_path.name,
                "relative_path": "textures/texture_01.png",
                "resource_index": 7,
                "width": 1024,
                "height": 2048,
            }
        ],
    }


def fake_safe_stem(value: str) -> str:
    return value.replace(" ", "_")


def test_export_sims4_package_lod0_fbx_uses_collision_safe_folder(tmp_path: Path) -> None:
    package_path = tmp_path / "Sample Dress.package"
    package_path.write_bytes(b"DBPF")
    target_dir = tmp_path / "exports"
    target_dir.mkdir()
    loader_result = (
        FakeGeomFormatError,
        FakePackageFormatError,
        fake_extractor,
        fake_safe_stem,
    )

    with patch.object(sims4_workbench, "_load_extractor", return_value=loader_result):
        first = sims4_workbench.export_sims4_package_lod0_fbx(
            str(package_path), str(target_dir)
        )
        second = sims4_workbench.export_sims4_package_lod0_fbx(
            str(package_path), str(target_dir)
        )

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["data"]["exported_model_count"] == 1
    assert first["data"]["texture_count"] == 1
    assert first["data"]["rle2_resource_count"] == 2
    assert first["data"]["skipped_non_lod0_count"] == 3
    assert first["data"]["removed_untextured_triangle_count"] == 500
    assert Path(first["data"]["output_dir"]).name == "Sample_Dress_lod0_fbx"
    assert Path(second["data"]["output_dir"]).name == "Sample_Dress_lod0_fbx_2"
    assert Path(first["data"]["exports"][0]["path"]).is_file()
    assert Path(first["data"]["textures"][0]["path"]).is_file()
    assert Path(
        first["data"]["exports"][0]["default_texture"]["path"]
    ).is_file()


def test_export_sims4_package_lod0_fbx_rejects_non_package(tmp_path: Path) -> None:
    source = tmp_path / "mesh.zip"
    source.write_bytes(b"data")

    result = sims4_workbench.export_sims4_package_lod0_fbx(
        str(source), str(tmp_path)
    )

    assert result["ok"] is False
    assert ".package" in result["error"]


def test_decode_rle2_produces_readable_rgba_dds() -> None:
    raw = (
        b"DXT5RLE2"
        + struct.pack("<HHHH", 4, 4, 1, 0)
        + struct.pack("<iiiii", 36, 38, 38, 38, 38)
        + struct.pack("<H", 4)
    )
    dds, width, height, mip_count = decode_rle2(raw)

    assert dds.startswith(b"DDS ")
    assert (width, height, mip_count) == (4, 4, 1)
    with Image.open(io.BytesIO(dds)) as image:
        image.load()
        assert image.size == (width, height)
        assert image.convert("RGBA").mode == "RGBA"


def test_fbx_binary_object_name_uses_blender_compatible_separator() -> None:
    assert fbx_object_name("Geometry", "Dress") == "Dress\x00\x01Geometry"


def test_align_mesh_to_hs2_scales_positions_without_changing_normals() -> None:
    source = {
        "positions": [(0.5, 1.25, -0.2)],
        "normals": [(0.0, 1.0, 0.0)],
        "faces": [(0, 0, 0)],
    }

    aligned = align_mesh_to_hs2(source)

    assert aligned["positions"] == [(5.0, 12.5, -2.0)]
    assert aligned["normals"] == source["normals"]
    assert aligned["faces"] == source["faces"]
    assert source["positions"] == [(0.5, 1.25, -0.2)]


def test_filter_mesh_by_alpha_coverage_removes_untextured_face() -> None:
    coverage = Image.new("L", (16, 16), 0)
    for y in range(0, 8):
        for x in range(0, 8):
            coverage.putpixel((x, y), 255)
    mesh = {
        "positions": [(float(index), 0.0, 0.0) for index in range(6)],
        "normals": [(0.0, 1.0, 0.0)] * 6,
        "uv_sets": [
            [(0.1, 0.1), (0.4, 0.1), (0.1, 0.4), (0.7, 0.7), (0.9, 0.7), (0.7, 0.9)],
            [(0.0, 0.0)] * 6,
        ],
        "bone_indices": [(0, 1, 2, 3)] * 6,
        "bone_weights": [(255, 0, 0, 0)] * 6,
        "bone_hashes": [1, 2, 3, 4],
        "faces": [(0, 1, 2), (3, 4, 5)],
        "vertex_count": 6,
        "triangle_count": 2,
    }

    filtered, statistics = filter_mesh_by_alpha_coverage(mesh, coverage)

    assert filtered["faces"] == [(0, 1, 2)]
    assert filtered["vertex_count"] == 3
    assert filtered["triangle_count"] == 1
    assert len(filtered["normals"]) == 3
    assert [len(uv_set) for uv_set in filtered["uv_sets"]] == [3, 3]
    assert filtered["bone_indices"] == [(0, 1, 2, 3)] * 3
    assert filtered["bone_weights"] == [(255, 0, 0, 0)] * 3
    assert statistics["removed_vertices"] == 3
    assert statistics["removed_triangles"] == 1


def test_combine_alpha_coverage_uses_union_of_swatches(tmp_path: Path) -> None:
    first = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    second = first.copy()
    first.putpixel((1, 1), (255, 255, 255, 255))
    second.putpixel((6, 6), (255, 255, 255, 255))
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first.save(first_path)
    second.save(second_path)

    coverage = combine_alpha_coverage([first_path, second_path])

    assert coverage is not None
    assert coverage.getpixel((1, 1)) == 255
    assert coverage.getpixel((6, 6)) == 255


def test_parse_geom_reads_panda_bone_palette_and_weights() -> None:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "extracted"
        / "panda_dress"
        / "raw_resources"
        / "panda_lod0_D9DAE30E1866ABF6.geom"
    )
    mesh = parse_geom(fixture.read_bytes())

    assert len(mesh["bone_hashes"]) == 58
    assert len(mesh["bone_indices"]) == mesh["vertex_count"]
    assert len(mesh["bone_weights"]) == mesh["vertex_count"]
    assert all(sum(weights) == 255 for weights in mesh["bone_weights"])


def test_bake_t_pose_with_blender_exports_mesh_without_skin(tmp_path: Path) -> None:
    output_dir = tmp_path / "result"
    work_dir = output_dir / ".skin_work"
    work_dir.mkdir(parents=True)
    fbx_path = output_dir / "sample.fbx"
    skin_path = work_dir / "sample.skin.json"
    fbx_path.write_bytes(b"fbx")
    skin_path.write_text("{}", encoding="utf-8")
    manifest = {
        "exports": [
            {
                "file": fbx_path.name,
                "skin_data_relative_path": ".skin_work/sample.skin.json",
            }
        ],
        "limitations": [],
    }

    def fake_run(command, **_kwargs):
        assert "--ts4-template" in command
        assert "--hs2-template" not in command
        jobs_path = Path(command[command.index("--jobs") + 1])
        result_path = Path(command[command.index("--result") + 1])
        jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
        result_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "ok": True,
                            "fbx_path": jobs[0]["fbx_path"],
                            "bytes": 123,
                            "rigged": False,
                            "t_pose_baked": True,
                            "skin_data_removed": True,
                            "bone_count": 0,
                            "weighted_bone_count": 0,
                            "weighted_vertex_count": 0,
                            "source_bone_count": 165,
                            "source_weighted_bone_count": 22,
                            "removed_vertex_group_count": 22,
                            "rest_pose": "T-pose",
                            "pose_reference": "HS2",
                            "source_arm_drop_degrees": 44.908,
                            "target_arm_drop_degrees": 0.0,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch.object(sims4_workbench.subprocess, "run", side_effect=fake_run):
        sims4_workbench._bake_t_pose_with_blender(
            tmp_path / "blender.exe",
            output_dir,
            manifest,
        )

    exported = manifest["exports"][0]
    assert exported["rigged"] is False
    assert exported["t_pose_baked"] is True
    assert exported["skin_data_removed"] is True
    assert exported["skeleton_bones"] == 0
    assert exported["weighted_bones"] == 0
    assert manifest["rigged_model_count"] == 0
    assert manifest["t_pose_model_count"] == 1
    assert manifest["t_pose_bake"]["final_bones"] == 0
    assert not work_dir.exists()
