"""Convert an HS2 Studio female FK pose .dat into a Kind=501 zipmod.

The generated resource reuses a static female pose AnimatorController/clip
template.  The template's canonical local positions are retained for the
character rig; FK rotations and scales come from the Studio pose file.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import struct
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / ".vendor"))

import UnityPy


FK_BONE_NAMES = [
    "cf_J_Hips",
    "cf_J_Head",
    "cf_J_Neck",
    "cf_J_Spine02",
    "cf_J_Spine01",
    "cf_J_Kosi01",
    "cf_J_LegUp00_R",
    "cf_J_LegLow01_R",
    "cf_J_Foot01_R",
    "cf_J_Toes01_R",
    "cf_J_LegUp00_L",
    "cf_J_LegLow01_L",
    "cf_J_Foot01_L",
    "cf_J_Toes01_L",
    "cf_J_Shoulder_R",
    "cf_J_ArmUp00_R",
    "cf_J_ArmLow01_R",
    "cf_J_Hand_R",
    "cf_J_Shoulder_L",
    "cf_J_ArmUp00_L",
    "cf_J_ArmLow01_L",
    "cf_J_Hand_L",
    "cf_J_Hand_Thumb01_R",
    "cf_J_Hand_Thumb02_R",
    "cf_J_Hand_Thumb03_R",
    "cf_J_Hand_Index01_R",
    "cf_J_Hand_Index02_R",
    "cf_J_Hand_Index03_R",
    "cf_J_Hand_Middle01_R",
    "cf_J_Hand_Middle02_R",
    "cf_J_Hand_Middle03_R",
    "cf_J_Hand_Ring01_R",
    "cf_J_Hand_Ring02_R",
    "cf_J_Hand_Ring03_R",
    "cf_J_Hand_Little01_R",
    "cf_J_Hand_Little02_R",
    "cf_J_Hand_Little03_R",
    "cf_J_Hand_Thumb01_L",
    "cf_J_Hand_Thumb02_L",
    "cf_J_Hand_Thumb03_L",
    "cf_J_Hand_Index01_L",
    "cf_J_Hand_Index02_L",
    "cf_J_Hand_Index03_L",
    "cf_J_Hand_Middle01_L",
    "cf_J_Hand_Middle02_L",
    "cf_J_Hand_Middle03_L",
    "cf_J_Hand_Ring01_L",
    "cf_J_Hand_Ring02_L",
    "cf_J_Hand_Ring03_L",
    "cf_J_Hand_Little01_L",
    "cf_J_Hand_Little02_L",
    "cf_J_Hand_Little03_L",
]


def read_varint_string(reader: io.BytesIO) -> str:
    length = 0
    shift = 0
    while True:
        raw = reader.read(1)
        if len(raw) != 1:
            raise ValueError("pose file ended while reading a string length")
        byte = raw[0]
        length |= (byte & 0x7F) << shift
        if byte < 0x80:
            data = reader.read(length)
            if len(data) != length:
                raise ValueError("pose file ended while reading a string")
            return data.decode("utf-8")
        shift += 7
        if shift > 35:
            raise ValueError("invalid pose string length")


def read_vec3(reader: io.BytesIO) -> tuple[float, float, float]:
    data = reader.read(12)
    if len(data) != 12:
        raise ValueError("pose file ended while reading a vector")
    return struct.unpack("<3f", data)


def read_bool(reader: io.BytesIO) -> bool:
    data = reader.read(1)
    if len(data) != 1:
        raise ValueError("pose file ended while reading a boolean")
    return bool(data[0])


def read_pose(path: Path) -> dict:
    reader = io.BytesIO(path.read_bytes())
    marker = read_varint_string(reader)
    version, sex = struct.unpack("<2i", reader.read(8))
    name = read_varint_string(reader)
    group, category, number = struct.unpack("<3i", reader.read(12))
    normalized = struct.unpack("<f", reader.read(4))[0] if version >= 101 else 0.0

    enable_ik = read_bool(reader)
    active_ik = [read_bool(reader) for _ in range(5)]
    ik_count = struct.unpack("<i", reader.read(4))[0]
    ik = {}
    for _ in range(ik_count):
        index = struct.unpack("<i", reader.read(4))[0]
        ik[index] = (read_vec3(reader), read_vec3(reader), read_vec3(reader))

    enable_fk = read_bool(reader)
    active_fk = [read_bool(reader) for _ in range(7)]
    fk_count = struct.unpack("<i", reader.read(4))[0]
    fk = {}
    for _ in range(fk_count):
        index = struct.unpack("<i", reader.read(4))[0]
        fk[index] = (read_vec3(reader), read_vec3(reader), read_vec3(reader))

    expression = [read_bool(reader) for _ in range(4)]
    remaining = reader.read()
    if remaining:
        raise ValueError(f"unexpected trailing pose data: {len(remaining)} bytes")
    if marker != "【pose】":
        raise ValueError(f"unsupported pose marker: {marker!r}")
    if sex != 1:
        raise ValueError(f"the input pose is not female (sex={sex})")
    if not enable_fk:
        raise ValueError("the input pose does not contain enabled FK data")
    missing = [index for index in range(len(FK_BONE_NAMES)) if index not in fk]
    if missing:
        raise ValueError(f"pose is missing required FK records: {missing}")

    return {
        "marker": marker,
        "version": version,
        "sex": sex,
        "name": name,
        "group": group,
        "category": category,
        "number": number,
        "normalized": normalized,
        "enable_ik": enable_ik,
        "active_ik": active_ik,
        "ik": ik,
        "enable_fk": enable_fk,
        "active_fk": active_fk,
        "fk": fk,
        "expression": expression,
    }


def transform_name_map(environment: UnityPy.Environment) -> tuple[dict[int, str], dict[str, object]]:
    transforms = {}
    names = {}
    for obj in environment.objects:
        if obj.type.name != "Transform":
            continue
        data = obj.read()
        transforms[obj.path_id] = data
        game_object = data.m_GameObject.deref()
        names[obj.path_id] = game_object.read().m_Name if game_object else ""

    def full_path(transform_id: int) -> str:
        parts = []
        seen = set()
        while transform_id and transform_id in transforms and transform_id not in seen:
            seen.add(transform_id)
            parts.append(names.get(transform_id, ""))
            father = transforms[transform_id].m_Father
            transform_id = father.path_id if father else 0
        return "/".join(reversed([part for part in parts if part]))

    paths_by_hash = {}
    transforms_by_path = {}
    for transform_id in transforms:
        path = full_path(transform_id)
        transforms_by_path[path] = transforms[transform_id]
        pieces = path.split("/")
        for start in range(len(pieces)):
            suffix = "/".join(pieces[start:])
            paths_by_hash[zlib.crc32(suffix.encode("utf-8")) & 0xFFFFFFFF] = suffix
    return paths_by_hash, transforms_by_path


def euler_to_unity_quaternion(euler_degrees: tuple[float, float, float]) -> tuple[float, float, float, float]:
    """Match Unity's Quaternion.Euler(Vector3) Z-X-Y rotation order."""
    x, y, z = (math.radians(value) * 0.5 for value in euler_degrees)
    sx, cx = math.sin(x), math.cos(x)
    sy, cy = math.sin(y), math.cos(y)
    sz, cz = math.sin(z), math.cos(z)
    quaternion = (
        sx * cy * cz - cx * sy * sz,
        cx * sy * cz + sx * cy * sz,
        cx * sy * sz + sx * cy * cz,
        cx * cy * cz - sx * sy * sz,
    )
    length = math.sqrt(sum(value * value for value in quaternion))
    return tuple(value / length for value in quaternion)


def set_vec3(values: list[float], offset: int, value: tuple[float, float, float]) -> None:
    values[offset : offset + 3] = list(value)


def set_quaternion(values: list[float], offset: int, value: tuple[float, float, float, float]) -> None:
    values[offset : offset + 4] = list(value)


def set_xform(value: object, quaternion: tuple[float, float, float, float], translation: tuple[float, float, float], scale: tuple[float, float, float]) -> None:
    for component, number in zip(("x", "y", "z", "w"), quaternion):
        setattr(value.q, component, number)
    for component, number in zip(("x", "y", "z"), translation):
        setattr(value.t, component, number)
    for component, number in zip(("x", "y", "z"), scale):
        setattr(value.s, component, number)


def update_value_deltas(deltas: list[object], values: list[float]) -> None:
    if len(deltas) != len(values):
        raise ValueError(f"constant/delta array length mismatch: {len(values)} vs {len(deltas)}")
    for delta, value in zip(deltas, values):
        delta.m_Start = value
        delta.m_Stop = value


def modify_template_clip(reference_bundle: Path, skeleton_bundle: Path, pose: dict, output_bundle: Path) -> dict:
    environment = UnityPy.load(str(reference_bundle))
    skeleton_environment = UnityPy.load(str(skeleton_bundle))
    clip_obj = next(
        obj
        for obj in environment.objects
        if obj.type.name == "AnimationClip" and obj.read().m_Name == "f_manekin"
    )
    clip = clip_obj.read()
    bindings = clip.m_ClipBindingConstant.genericBindings
    binding_groups = {
        attribute: [binding for binding in bindings if int(binding.typeID) == 4 and int(binding.attribute) == attribute]
        for attribute in (1, 2, 3)
    }
    counts = {attribute: len(group) for attribute, group in binding_groups.items()}
    if len(set(counts.values())) != 1 or not counts[1]:
        raise ValueError(f"unexpected AnimationClip transform binding groups: {counts}")
    transform_count = counts[1]

    values = clip.m_MuscleClip.m_Clip.data.m_ConstantClip.data
    if len(values) < transform_count * 10:
        raise ValueError("the static template does not contain complete position/rotation/scale constants")
    if clip.m_MuscleClip.m_Clip.data.m_DenseClip.m_CurveCount:
        raise ValueError("the selected template is not static")

    paths_by_hash, transforms_by_path = transform_name_map(skeleton_environment)
    clip_hashes = {int(binding.path) for group in binding_groups.values() for binding in group}
    paths_by_leaf = {}
    for path in paths_by_hash.values():
        if zlib.crc32(path.encode("utf-8")) & 0xFFFFFFFF in clip_hashes:
            paths_by_leaf.setdefault(path.rsplit("/", 1)[-1], []).append(path)

    index_by_attribute_and_hash = {
        attribute: {int(binding.path): index for index, binding in enumerate(group)}
        for attribute, group in binding_groups.items()
    }
    mapping = {}
    for pose_index, bone_name in enumerate(FK_BONE_NAMES):
        candidates = [
            path
            for path in paths_by_leaf.get(bone_name, [])
            if zlib.crc32(path.encode("utf-8")) & 0xFFFFFFFF in index_by_attribute_and_hash[1]
        ]
        if len(candidates) != 1:
            raise ValueError(f"could not uniquely map FK {pose_index} {bone_name!r}: {candidates}")
        path = candidates[0]
        path_hash = zlib.crc32(path.encode("utf-8")) & 0xFFFFFFFF
        indices = {attribute: index_by_attribute_and_hash[attribute][path_hash] for attribute in (1, 2, 3)}
        if len(set(indices.values())) != 1:
            raise ValueError(f"binding group order differs for {bone_name}: {indices}")
        mapping[pose_index] = {"bone": bone_name, "path": path, "path_hash": path_hash, "clip_index": indices[1]}

    for pose_index, info in mapping.items():
        position, euler, scale = pose["fk"][pose_index]
        clip_index = info["clip_index"]
        rotation_offset = transform_count * 3 + clip_index * 4
        scale_offset = transform_count * 7 + clip_index * 3
        set_quaternion(values, rotation_offset, euler_to_unity_quaternion(euler))
        set_vec3(values, scale_offset, scale)
        if pose_index == 0:
            # FK positions in Studio are offsets.  Non-root constants are rig
            # rest positions and must remain intact for Animator playback.
            set_vec3(values, clip_index * 3, position)

    root = pose["fk"][0]
    root_quaternion = euler_to_unity_quaternion(root[1])
    root_translation = root[0]
    root_scale = root[2]
    set_xform(clip.m_MuscleClip.m_StartX, root_quaternion, root_translation, root_scale)
    set_xform(clip.m_MuscleClip.m_StopX, root_quaternion, root_translation, root_scale)
    update_value_deltas(clip.m_MuscleClip.m_ValueArrayDelta, values)
    clip_obj.save_typetree(clip)

    output_bundle.parent.mkdir(parents=True, exist_ok=True)
    environment.save(pack="lz4", out_path=str(output_bundle.parent))
    if not output_bundle.is_file():
        saved_candidates = [
            path
            for path in output_bundle.parent.glob("*.unity3d")
            if path.is_file() and path != output_bundle
        ]
        if len(saved_candidates) != 1:
            raise RuntimeError(
                f"UnityPy did not write {output_bundle}; candidates={saved_candidates}"
            )
        saved_candidates[0].replace(output_bundle)

    return {
        "clip_name": clip.m_Name,
        "clip_path_id": clip_obj.path_id,
        "transform_binding_count": transform_count,
        "constant_value_count": len(values),
        "fk_record_count": len(pose["fk"]),
        "mapped_fk_count": len(mapping),
        "mapping": mapping,
        "root_euler_degrees": list(root[1]),
        "root_quaternion": list(root_quaternion),
    }


def make_manifest(guid: str, display_name: str) -> bytes:
    safe_name = xml_escape(display_name)
    return (
        '<manifest schema-ver="1">\n'
        f"  <guid>{xml_escape(guid)}</guid>\n"
        f"  <name>{safe_name}</name>\n"
        "  <version>1.0.0</version>\n"
        "  <author>Star_Manager</author>\n"
        f"  <description>Converted female Studio pose: {safe_name}</description>\n"
        "  <game>Honey Select 2</game>\n"
        "</manifest>\n"
    ).encode("utf-8")


def make_csv(display_name: str, main_ab: str, ik_ab: str, item_id: int, list_token: str) -> bytes:
    rows = [
        "501",
        "0",
        list_token,
        "ID,Kind,Possess,Name,EN_US,ZH_CN,ZH_TW,MainManifest,MainAB,MainData,Clip,IKAB,IKData",
        f"{item_id},1,1,{display_name},0,0,0,abdata,{main_ab},edit_F,mannequin,{ik_ab},edit_F",
        "",
    ]
    return "\n".join(rows).encode("utf-8")


def verify_bundle(path: Path) -> dict:
    environment = UnityPy.load(str(path))
    controller = next(
        obj
        for obj in environment.objects
        if obj.type.name == "AnimatorController" and obj.read().m_Name == "edit_F"
    )
    clip = next(
        obj
        for obj in environment.objects
        if obj.type.name == "AnimationClip" and obj.read().m_Name == "f_manekin"
    )
    controller_data = controller.read()
    clip_data = clip.read()
    state_names = [name for _, name in controller_data.m_TOS]
    if "mannequin" not in state_names:
        raise ValueError("generated controller has no mannequin state")
    values = clip_data.m_MuscleClip.m_Clip.data.m_ConstantClip.data
    deltas = clip_data.m_MuscleClip.m_ValueArrayDelta
    if len(values) != 3527 or len(deltas) != 3527:
        raise ValueError(f"unexpected static clip arrays: values={len(values)}, deltas={len(deltas)}")
    return {
        "controller": controller_data.m_Name,
        "controller_path_id": controller.path_id,
        "clip": clip_data.m_Name,
        "clip_path_id": clip.path_id,
        "state_names": state_names,
        "constant_value_count": len(values),
        "delta_value_count": len(deltas),
        "unityfs_size": path.stat().st_size,
    }


def build_zipmod(args: argparse.Namespace) -> tuple[Path, dict]:
    pose_path = args.pose.resolve()
    reference_bundle = args.reference_bundle.resolve()
    skeleton_bundle = args.skeleton_bundle.resolve()
    ik_bundle = args.ik_bundle.resolve() if args.ik_bundle else None
    external_ik_zipmod = args.external_ik_zipmod.resolve() if args.external_ik_zipmod else None
    output_path = args.output.resolve()
    if not pose_path.is_file() or not reference_bundle.is_file() or not skeleton_bundle.is_file():
        raise FileNotFoundError("pose, reference bundle, and skeleton bundle must all exist")
    if ik_bundle is None and external_ik_zipmod is None:
        raise ValueError("provide either --ik-bundle or --external-ik-zipmod")
    if ik_bundle is not None and not ik_bundle.is_file():
        raise FileNotFoundError(f"IK bundle does not exist: {ik_bundle}")
    if external_ik_zipmod is not None and not external_ik_zipmod.is_file():
        raise FileNotFoundError(f"external IK zipmod does not exist: {external_ik_zipmod}")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output already exists; pass --force to replace it: {output_path}")

    pose = read_pose(pose_path)
    display_name = args.name or pose["name"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pose-build-", dir=str(output_path.parent)) as temp:
        temp_dir = Path(temp)
        generated_bundle = temp_dir / "anim_f_33.unity3d"
        conversion = modify_template_clip(reference_bundle, skeleton_bundle, pose, generated_bundle)
        verification = verify_bundle(generated_bundle)

        main_ab = "custom/LD_33_CuteyNip/anim_f_00.unity3d"
        archive_main_ab = f"abdata/{main_ab}"
        ik_ab = args.ik_ab.strip().replace("\\", "/").strip("/")
        archive_ik = f"abdata/{ik_ab}.unity3d"
        csv_path = "abdata/list/characustom/00/custom_pose_f_ld33.csv"
        manifest = make_manifest("com.star_manager.ld33cuteynip", display_name)
        csv = make_csv(display_name, main_ab, ik_ab, args.item_id, args.list_token)
        if external_ik_zipmod is not None:
            with zipfile.ZipFile(external_ik_zipmod) as source_archive:
                if archive_ik not in source_archive.namelist():
                    raise ValueError(f"external IK zipmod does not contain {archive_ik}")
                external_ik_data = source_archive.read(archive_ik)
            external_ik_environment = UnityPy.load(external_ik_data)
            if not any(
                obj.type.name == "TextAsset" and obj.read().m_Name == "edit_F"
                for obj in external_ik_environment.objects
            ):
                raise ValueError("external IK bundle has no edit_F TextAsset")
        else:
            external_ik_data = ik_bundle.read_bytes()
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("manifest.xml", manifest)
            archive.writestr(csv_path, csv)
            archive.write(generated_bundle, archive_main_ab)
            if not args.external_ik_zipmod:
                archive.writestr(archive_ik, external_ik_data)

        with zipfile.ZipFile(output_path) as archive:
            names = set(archive.namelist())
            expected = {"manifest.xml", csv_path, archive_main_ab}
            if not args.external_ik_zipmod:
                expected.add(archive_ik)
            # ZIP names are normalized to forward slashes by the reader.
            if not expected.issubset(names):
                raise ValueError(f"zipmod entries missing: {sorted(expected - names)}")
            archive.testzip()

    report = {
        "source_pose": str(pose_path),
        "source_name": pose["name"],
        "source_sex": pose["sex"],
        "source_fk_record_count": len(pose["fk"]),
        "source_ik_record_count": len(pose["ik"]),
        "display_name": display_name,
        "item_id": args.item_id,
        "main_ab": main_ab,
        "archive_main_ab": archive_main_ab,
        "ik_ab": ik_ab,
        "archive_ik": archive_ik,
        "external_ik_zipmod": str(external_ik_zipmod) if external_ik_zipmod else "",
        "ik_included_in_output": not bool(external_ik_zipmod),
        "csv_path": csv_path,
        "conversion": conversion,
        "verification": verification,
        "output": str(output_path),
        "output_size": output_path.stat().st_size,
    }
    report_path = output_path.with_suffix(output_path.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", type=Path, required=True)
    parser.add_argument("--reference-bundle", type=Path, required=True)
    parser.add_argument("--skeleton-bundle", type=Path, required=True)
    parser.add_argument("--ik-bundle", type=Path)
    parser.add_argument("--external-ik-zipmod", type=Path, help="zipmod that supplies the IKAB resource")
    parser.add_argument("--ik-ab", default="custom/LD_33_CuteyNip/ik_f_00", help="IKAB path without .unity3d")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--item-id", type=int, default=33001)
    parser.add_argument("--list-token", default="73c8de55fb8d473a855d8abbcd978f17")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    output, report = build_zipmod(parse_args())
    print(json.dumps({"output": str(output), "size": output.stat().st_size, "report": str(output.with_suffix(output.suffix + ".report.json")), "mapped_fk_count": report["conversion"]["mapped_fk_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
