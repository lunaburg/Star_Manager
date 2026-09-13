from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _load_extractor():
    try:
        from extract_ts4_package_fbx import (  # type: ignore
            GeomFormatError,
            PackageFormatError,
            extract_lod0_fbx,
            safe_stem,
        )
    except ImportError:
        app_root = Path(__file__).resolve().parents[3]
        scripts_root = app_root / "scripts"
        if str(scripts_root) not in sys.path:
            sys.path.insert(0, str(scripts_root))
        from extract_ts4_package_fbx import (  # type: ignore
            GeomFormatError,
            PackageFormatError,
            extract_lod0_fbx,
            safe_stem,
        )
    return GeomFormatError, PackageFormatError, extract_lod0_fbx, safe_stem


def _next_output_directory(target_root: Path, package_stem: str) -> Path:
    base_name = f"{package_stem}_lod0_fbx"
    candidate = target_root / base_name
    suffix = 2
    while candidate.exists():
        candidate = target_root / f"{base_name}_{suffix}"
        suffix += 1
    return candidate


def _sims4_resource_file(file_name: str) -> Path:
    candidates = []
    pyinstaller_root = getattr(sys, "_MEIPASS", "")
    if pyinstaller_root:
        candidates.append(Path(pyinstaller_root) / "sims4" / file_name)
    candidates.append(
        Path(__file__).resolve().parents[3] / "resources" / "sims4" / file_name
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"找不到 Sims 4 骨架资源：{file_name}")


def _bake_t_pose_with_blender(
    blender_executable: Path,
    output_dir: Path,
    manifest: dict,
) -> None:
    exports = manifest.get("exports") or []
    jobs = []
    for item in exports:
        relative_skin_path = str(item.get("skin_data_relative_path") or "")
        if not relative_skin_path:
            continue
        jobs.append(
            {
                "fbx_path": str(output_dir / str(item.get("file") or "")),
                "skin_path": str(output_dir / relative_skin_path),
            }
        )
    if not jobs:
        _finalize_static_export(output_dir, manifest)
        return

    ts4_template_path = _sims4_resource_file("ts4_reference_rig.fbx")
    script_path = _sims4_resource_file("attach_ts4_skin_blender.py")
    work_dir = output_dir / ".skin_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    jobs_path = work_dir / "tpose_jobs.json"
    result_path = work_dir / "tpose_results.json"
    jobs_path.write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                str(blender_executable),
                "--background",
                "--python",
                str(script_path),
                "--",
                "--ts4-template",
                str(ts4_template_path),
                "--jobs",
                str(jobs_path),
                "--result",
                str(result_path),
            ],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            creationflags=creation_flags,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Blender 固化 T-Pose 超时") from error

    result_data = {}
    if result_path.is_file():
        result_data = json.loads(result_path.read_text(encoding="utf-8"))
    results = result_data.get("results") or []
    failures = [item for item in results if not item.get("ok")]
    if completed.returncode != 0 or failures:
        failure_message = "; ".join(
            str(item.get("error") or "未知 T-Pose 固化错误") for item in failures
        )
        if not failure_message:
            output = (completed.stderr or completed.stdout or "").strip()
            failure_message = output[-1200:] or f"Blender 返回代码 {completed.returncode}"
        raise RuntimeError(f"T-Pose 纯网格导出失败：{failure_message}")
    if len(results) != len(jobs):
        raise RuntimeError("Blender 没有返回完整的 T-Pose 导出结果")

    results_by_path = {
        str(Path(item["fbx_path"]).resolve()).casefold(): item for item in results
    }
    for item in exports:
        fbx_path = (output_dir / str(item.get("file") or "")).resolve()
        processing = results_by_path.get(str(fbx_path).casefold())
        item.pop("skin_data_relative_path", None)
        if not processing:
            item["rigged"] = False
            item["t_pose_baked"] = False
            continue
        source_has_skinning_data = bool(item.get("has_skinning_data"))
        source_bone_palette_size = int(item.get("bone_palette_size") or 0)
        item.update(
            {
                "rigged": False,
                "t_pose_baked": bool(processing.get("t_pose_baked")),
                "skin_data_removed": bool(processing.get("skin_data_removed")),
                "source_has_skinning_data": source_has_skinning_data,
                "source_bone_palette_size": source_bone_palette_size,
                "has_skinning_data": False,
                "bone_palette_size": 0,
                "bytes": int(processing.get("bytes") or fbx_path.stat().st_size),
                "skeleton_bones": int(processing.get("bone_count") or 0),
                "weighted_bones": int(processing.get("weighted_bone_count") or 0),
                "weighted_vertices": int(processing.get("weighted_vertex_count") or 0),
                "source_skeleton_bones": int(
                    processing.get("source_bone_count") or 0
                ),
                "source_weighted_bones": int(
                    processing.get("source_weighted_bone_count") or 0
                ),
                "removed_vertex_group_count": int(
                    processing.get("removed_vertex_group_count") or 0
                ),
                "rest_pose": str(processing.get("rest_pose") or ""),
                "pose_reference": str(processing.get("pose_reference") or ""),
                "source_arm_drop_degrees": float(
                    processing.get("source_arm_drop_degrees") or 0
                ),
                "target_arm_drop_degrees": float(
                    processing.get("target_arm_drop_degrees") or 0
                ),
                "arm_inward_offset_ratio": float(
                    processing.get("arm_inward_offset_ratio") or 0
                ),
                "arm_inward_offset": float(
                    processing.get("arm_inward_offset") or 0
                ),
                "vertices": int(
                    processing.get("vertices_after_reverse_cleanup")
                    or item.get("vertices")
                    or 0
                ),
                "triangles": int(
                    processing.get("triangles_after_reverse_cleanup")
                    or item.get("triangles")
                    or 0
                ),
                "reverse_duplicate_groups_detected": int(
                    processing.get("reverse_duplicate_groups_detected") or 0
                ),
                "reverse_duplicate_faces_removed": int(
                    processing.get("reverse_duplicate_faces_removed") or 0
                ),
                "reverse_duplicate_ambiguous_groups": int(
                    processing.get("reverse_duplicate_ambiguous_groups") or 0
                ),
                "reverse_duplicate_material_mismatch_groups": int(
                    processing.get("reverse_duplicate_material_mismatch_groups") or 0
                ),
                "reverse_duplicate_multi_face_groups": int(
                    processing.get("reverse_duplicate_multi_face_groups") or 0
                ),
            }
        )
    manifest["rigged_model_count"] = 0
    manifest["t_pose_model_count"] = sum(
        bool(item.get("t_pose_baked")) for item in exports
    )
    manifest.pop("skeleton_template", None)
    manifest["t_pose_bake"] = {
        "source_file": ts4_template_path.name,
        "source_bones": 165,
        "final_bones": 0,
        "final_skin_weights": 0,
        "scale": "HS2-aligned scale and coordinate system",
        "source_rest_pose": "A-pose",
        "export_rest_pose": "T-pose",
        "pose_reference": "HS2 horizontal shoulder-elbow-wrist alignment with 6% upper-arm-length inward offset",
        "arm_inward_offset_ratio": 0.06,
    }
    manifest["limitations"] = [
        "The final FBX contains a baked T-pose mesh only; skeletons, skin weights, animation, and blend shapes are not included.",
        *[
            limitation
            for limitation in manifest.get("limitations") or []
            if "WorkBench rigging stage" not in limitation
            and "WorkBench" not in limitation
            and "bone indices" not in limitation
            and "Blend shapes" not in limitation
        ],
    ]
    (output_dir / "extraction_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.rmtree(work_dir, ignore_errors=True)


def _finalize_static_export(output_dir: Path, manifest: dict) -> None:
    for item in manifest.get("exports") or []:
        item.pop("skin_data_relative_path", None)
        item["source_has_skinning_data"] = bool(item.get("has_skinning_data"))
        item["source_bone_palette_size"] = int(item.get("bone_palette_size") or 0)
        item["has_skinning_data"] = False
        item["bone_palette_size"] = 0
        item["rigged"] = False
        item["t_pose_baked"] = False
        item["skin_data_removed"] = True
        item["skeleton_bones"] = 0
        item["weighted_bones"] = 0
        item["weighted_vertices"] = 0
    manifest["rigged_model_count"] = 0
    manifest["t_pose_model_count"] = 0
    shutil.rmtree(output_dir / ".skin_work", ignore_errors=True)
    (output_dir / "extraction_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def export_sims4_package_lod0_fbx(
    package_path: str,
    target_dir: str,
    blender_executable_path: str = "",
) -> dict:
    source = Path(str(package_path or "")).expanduser()
    target_root = Path(str(target_dir or "")).expanduser()
    blender_executable = Path(str(blender_executable_path or "")).expanduser()

    if not source.is_file():
        return {"ok": False, "error": "请选择有效的 Sims 4 .package 文件"}
    if source.suffix.lower() != ".package":
        return {"ok": False, "error": "源文件必须使用 .package 扩展名"}
    if not target_root.is_dir():
        return {"ok": False, "error": "请选择已存在的输出目录"}
    if blender_executable_path and not blender_executable.is_file():
        return {"ok": False, "error": "设置中的 Blender 可执行文件不存在"}

    source = source.resolve()
    target_root = target_root.resolve()
    GeomFormatError, PackageFormatError, extract_lod0_fbx, safe_stem = _load_extractor()
    output_dir = _next_output_directory(target_root, safe_stem(source.stem))

    try:
        manifest = extract_lod0_fbx(source, output_dir)
        if blender_executable_path:
            _bake_t_pose_with_blender(
                blender_executable.resolve(), output_dir, manifest
            )
        else:
            _finalize_static_export(output_dir, manifest)
    except (
        OSError,
        PackageFormatError,
        GeomFormatError,
        RuntimeError,
        ValueError,
    ) as error:
        return {"ok": False, "error": str(error)}

    exports = manifest.get("exports") or []
    textures = manifest.get("textures") or []

    def resolve_texture(item: dict | None) -> dict | None:
        if not item:
            return None
        relative_path = str(item.get("relative_path") or item.get("file") or "")
        return {
            **item,
            "path": str(output_dir / relative_path),
        }

    export_items = []
    for item in exports:
        export_items.append(
            {
                **item,
                "path": str(output_dir / str(item.get("file") or "")),
                "default_texture": resolve_texture(item.get("default_texture")),
            }
        )
    texture_items = [resolve_texture(item) for item in textures]
    removed_untextured_triangle_count = sum(
        int(item.get("removed_untextured_triangles") or 0)
        for item in exports
    )
    reverse_duplicate_groups_detected = sum(
        int(item.get("reverse_duplicate_groups_detected") or 0) for item in exports
    )
    reverse_duplicate_faces_removed = sum(
        int(item.get("reverse_duplicate_faces_removed") or 0) for item in exports
    )
    reverse_duplicate_ambiguous_groups = sum(
        int(item.get("reverse_duplicate_ambiguous_groups") or 0) for item in exports
    )
    reverse_cleanup_message = (
        f"，清理 {reverse_duplicate_faces_removed} 个反向重合三角面"
        if reverse_duplicate_faces_removed
        else ""
    )
    reverse_skip_message = (
        f"，跳过 {reverse_duplicate_ambiguous_groups} 组无法安全判定的重合面"
        if reverse_duplicate_ambiguous_groups
        else ""
    )
    removal_message = (
        f"，裁剪 {removed_untextured_triangle_count} 个无贴图三角面"
        if removed_untextured_triangle_count
        else ""
    )
    rigged_model_count = 0
    t_pose_model_count = sum(bool(item.get("t_pose_baked")) for item in exports)
    t_pose_message = (
        f"，其中 {t_pose_model_count} 个已固化为无骨骼蒙皮的 T-Pose 纯网格"
        if t_pose_model_count
        else ""
    )
    return {
        "ok": True,
        "message": (
            f"已导出 {len(exports)} 个 LOD0 FBX 模型和 "
            f"{len(texture_items)} 张贴图{t_pose_message}{removal_message}"
            f"{reverse_cleanup_message}{reverse_skip_message}"
        ),
        "data": {
            "package_path": str(source),
            "output_dir": str(output_dir),
            "manifest_path": str(output_dir / "extraction_manifest.json"),
            "exported_model_count": len(exports),
            "rigged_model_count": rigged_model_count,
            "t_pose_model_count": t_pose_model_count,
            "texture_count": len(texture_items),
            "rle2_resource_count": int(manifest.get("rle2_resource_count") or 0),
            "geom_resource_count": int(manifest.get("geom_resource_count") or 0),
            "skipped_non_lod0_count": int(manifest.get("skipped_non_lod0_count") or 0),
            "removed_untextured_triangle_count": removed_untextured_triangle_count,
            "reverse_duplicate_groups_detected": reverse_duplicate_groups_detected,
            "reverse_duplicate_faces_removed": reverse_duplicate_faces_removed,
            "reverse_duplicate_ambiguous_groups": reverse_duplicate_ambiguous_groups,
            "exports": export_items,
            "textures": texture_items,
        },
    }
