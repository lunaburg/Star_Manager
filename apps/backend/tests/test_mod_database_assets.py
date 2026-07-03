import sys
import sqlite3
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.mod_database_core import CsvItem, PreparedModItem, ThumbnailResult  # noqa: E402
from star_manager.services.mod_database_core import ManifestData, ZipmodCandidate, init_db  # noqa: E402
from star_manager.services.mod_database_assets import (  # noqa: E402
    _duplicate_keep_sort_key,
    _duplicate_item_signature,
    _unity3d_average_modified,
    _version_sort_key,
    decode_csv_bytes_with_encoding,
    extract_thumbnail_from_zipmod,
    find_zip_directory,
    find_zip_member,
    find_zip_unity3d_or_directory,
    inspect_unity3d_status,
    normalize_abdata_path,
    preextract_zip_unity_thumbnails,
    read_manifest,
    read_items_from_csv,
    repair_zipmod_unity3d_from_game,
    resource_image_candidates,
    ThumbnailSourceCache,
    UnityThumbnailBundleCache,
    thumbnail_csv_reference_for_arcname,
    thumbnail_error_detail,
    unity3d_member_signatures,
    ZipMemberIndex,
)
from star_manager.services import mod_database_assets  # noqa: E402
from star_manager.services.mod_database import prepare_mod_items, summarize_prepared_unity3d, unity3d_retry_guids  # noqa: E402


class ManifestParsingTests(unittest.TestCase):
    def test_missing_author_is_warning_candidate_not_invalid_manifest(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "missing-author.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>sample.guid</guid><name>Sample</name><version>1</version></manifest>",
                )

            manifest = read_manifest(zipmod_path)

        self.assertEqual(manifest.guid, "sample.guid")
        self.assertEqual(manifest.author, "")
        self.assertEqual(manifest.scan_status, "ok")
        self.assertEqual(manifest.scan_error, "")


class ThumbnailDiagnosticTests(unittest.TestCase):
    def test_imported_direct_thumbnail_csv_reference_is_split(self):
        thumb_ab, thumb_tex = thumbnail_csv_reference_for_arcname(
            "abdata/thumbnail/star_manager/674_lxdb.png"
        )

        self.assertEqual(thumb_ab, "thumbnail/star_manager")
        self.assertEqual(thumb_tex, "674_lxdb")

    def test_unitypy_load_failure_is_distinct_from_missing_asset(self):
        detail = thumbnail_error_detail("UnityPy load failed: invalid bundle")

        self.assertIn("Unity3D", detail)
        self.assertIn("无法打开", detail)
        self.assertNotIn("ThumbTex", detail)


    def test_unitypy_empty_bundle_is_distinct_from_missing_asset(self):
        detail = thumbnail_error_detail("UnityPy loaded no objects")

        self.assertIn("Unity3D", detail)
        self.assertNotIn("ThumbTex", detail)

    def test_unitypy_empty_bundle_returns_error(self):
        class EmptyEnv:
            container = {}
            objects = []

        class EmptyUnityPy:
            @staticmethod
            def load(_bundle_bytes):
                return EmptyEnv()

        original = mod_database_assets.UnityPy
        try:
            mod_database_assets.UnityPy = EmptyUnityPy
            result = mod_database_assets.UnityThumbnailBundle.from_bytes(b"bundle")
        finally:
            mod_database_assets.UnityPy = original

        self.assertIsInstance(result, ThumbnailResult)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error, "UnityPy loaded no objects")

    def test_thumbnail_bundle_skips_bad_individual_assets(self):
        class ImageData:
            image = object()
            name = "prev"

        class BadObject:
            type = type("ObjType", (), {"name": "Sprite"})()

            def read(self):
                raise KeyError("bad sprite")

        class GoodObject:
            type = type("ObjType", (), {"name": "Texture2D"})()

            def read(self):
                return ImageData()

        class PartialEnv:
            container = {"bad": BadObject(), "prev": GoodObject()}
            objects = [BadObject(), GoodObject()]

        class PartialUnityPy:
            @staticmethod
            def load(_bundle_bytes):
                return PartialEnv()

        original = mod_database_assets.UnityPy
        try:
            mod_database_assets.UnityPy = PartialUnityPy
            result = mod_database_assets.UnityThumbnailBundle.from_bytes(b"bundle")
        finally:
            mod_database_assets.UnityPy = original

        self.assertIsInstance(result, mod_database_assets.UnityThumbnailBundle)
        self.assertIsNotNone(result.find_image("prev"))


class CsvEncodingTests(unittest.TestCase):
    def test_prefers_gb18030_when_cp932_decodes_chinese_filename_as_mojibake(self):
        csv_bytes = (
            "300,,,,,,,,,,,,,,\r\n"
            "0,,,,,,,,,,,,,,\r\n"
            "reddead,,,,,,,,,,,,,,\r\n"
            "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,"
            "TexManifest,TexAB,TexD,TexC,SetHair,ThumbAB,ThumbTex\r\n"
            "2402163,0,1,[YuDream]A01.5_hair,0,abdata,"
            "chara/YuDream/[YuDream]A01.5_hair.unity3d,"
            "[YuDream]A01.5_hair,abdata,"
            "chara/YuDream/[YuDream]A01.5_hair.unity3d,"
            "00000000FEDEE1F0,00000000FEDEE1F0,0,chara/YuDream,"
        ).encode("ascii") + "[YuDream]A01.5_晴空黛紫\r\n".encode("gb18030")

        encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
        items = read_items_from_csv("abdata/list/characustom/yudream.csv", csv_bytes)

        self.assertEqual(encoding, "gb18030")
        self.assertIn("[YuDream]A01.5_晴空黛紫", text)
        self.assertEqual(items[0].thumb_tex, "[YuDream]A01.5_晴空黛紫")

    def test_prefers_gb18030_when_cp932_decodes_fullwidth_dash_as_halfwidth_gibberish(self):
        csv_bytes = (
            "241,,,,,,,,,,,,,,,,\r\n"
            "0,,,,,,,,,,,,,,,,\r\n"
            "list.bytes,,,,,,,,,,,,,,,,\r\n"
            "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,ThumbAB,ThumbTex\r\n"
            "23041081,0,1,JING－MEIGUIYITANBOT,0,abdata,"
            "chara/JING－MEIGUIYITAN.unity3d,BOT,"
            "chara/JING－MEIGUIYITAN.unity3d,JING－MEIGUIYITAN\r\n"
        ).encode("gb18030")

        encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
        items = read_items_from_csv("abdata/list/characustom/ds.csv", csv_bytes)

        self.assertEqual(encoding, "gb18030")
        self.assertIn("JING－MEIGUIYITAN", text)
        self.assertEqual(items[0].main_ab, "chara/JING－MEIGUIYITAN.unity3d")

    def test_reads_pattern_main_texture_fields_as_main_resource(self):
        csv_bytes = (
            "348\r\n"
            "0\r\n"
            "Assets/in-house/assetbundle/list/characustom/00/st_pattern_00.bytes\r\n"
            "ID,Kind,Possess,Name,EN_US,MainTexAB,MainTex,ThumbAB,ThumbTex\r\n"
            "171,0,1,patt-01,0,chara/00/st_pattern_Alex7997.unity3d,"
            "pattern_Alex7997_01,chara/thumb/00/st_pattern_Alex7997.unity3d,"
            "thumb_pattern_Alex7997_01\r\n"
        ).encode("utf-8")

        items = read_items_from_csv("abdata/list/characustom/st_pattern.csv", csv_bytes)

        self.assertEqual(items[0].main_ab, "chara/00/st_pattern_Alex7997.unity3d")
        self.assertEqual(items[0].main_data, "pattern_Alex7997_01")

    def test_reads_paint_addtex_as_main_resource_name(self):
        csv_bytes = (
            "313\r\n"
            "0\r\n"
            "abdata/list/characustom/00/st_paint_00_yoshi_list.csv\r\n"
            "ID,Kind,Possess,Name,EN_US,MainAB,AddTex,GlossTex,ThumbAB,ThumbTex\r\n"
            "0,0,1,RedRibbonLogo1,0,chara/00/st_paint_00_yoshi.unity3d,"
            "RR1_clamp,RR1_clamp,chara/thumb/00/st_paint_00_yoshi.unity3d,"
            "missing_thumb\r\n"
        ).encode("utf-8")

        items = read_items_from_csv("abdata/list/characustom/00/RR1.csv", csv_bytes)

        self.assertEqual(items[0].main_ab, "chara/00/st_paint_00_yoshi.unity3d")
        self.assertEqual(items[0].main_data, "RR1_clamp")


class AbdataPathTests(unittest.TestCase):
    def test_numeric_manifest_field_is_not_treated_as_path_root(self):
        self.assertEqual(
            normalize_abdata_path("1", "chara/SF/SF_wq_my.unity3d"),
            "abdata/chara/SF/SF_wq_my.unity3d",
        )

    def test_missing_manifest_field_defaults_to_abdata(self):
        self.assertEqual(
            normalize_abdata_path("", "chara/example/main.unity3d"),
            "abdata/chara/example/main.unity3d",
        )

    def test_manifest_field_value_is_ignored_for_main_ab_root(self):
        self.assertEqual(
            normalize_abdata_path("abtada", "chara/Asslie/a3.unity3d"),
            "abdata/chara/Asslie/a3.unity3d",
        )


class Unity3dDirectoryFallbackTests(unittest.TestCase):
    def test_matches_zip_member_names_decoded_with_wrong_legacy_encoding(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "sample.zipmod"
            mojibake_name = "abdata/chara/JING－MEIGUIYITAN.unity3d".encode("gb18030").decode("cp437")
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(mojibake_name, b"bundle")

            with zipfile.ZipFile(zipmod_path) as zf:
                self.assertEqual(
                    find_zip_member(zf, "abdata/chara/JING－MEIGUIYITAN.unity3d"),
                    mojibake_name,
                )

    def test_matches_zip_directory_names_decoded_with_wrong_legacy_encoding(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "sample.zipmod"
            mojibake_name = "abdata/chara/JING－MEIGUIYITAN/asset.png".encode("gb18030").decode("cp437")
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(mojibake_name, b"png")

            with zipfile.ZipFile(zipmod_path) as zf:
                self.assertEqual(
                    find_zip_directory(zf, "abdata/chara/JING－MEIGUIYITAN"),
                    "abdata/chara/JING－MEIGUIYITAN",
                )

    def test_accepts_directory_with_same_name_as_missing_unity3d_bundle(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/00/st_paint_00_yoshi/RR1_clamp.png", b"png")

            item = CsvItem(
                csv_path="abdata/list/characustom/00/RR1.csv",
                item_id="0",
                kind="313",
                name="RedRibbonLogo1",
                main_manifest="",
                main_ab="chara/00/st_paint_00_yoshi.unity3d",
                main_data="",
                thumb_ab="",
                thumb_tex="",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                self.assertEqual(
                    find_zip_unity3d_or_directory(
                        zf,
                        "abdata/chara/00/st_paint_00_yoshi.unity3d",
                    ),
                    "abdata/chara/00/st_paint_00_yoshi",
                )
                status = inspect_unity3d_status(Path(temp_dir), zf, item)

            self.assertEqual(status.status, "in_mod")
            self.assertEqual(status.error, "")

    def test_unity3d_with_no_parsed_objects_is_error(self):
        class EmptyEnv:
            container = {}
            objects = []

        class EmptyUnityPy:
            @staticmethod
            def load(_bundle_bytes):
                return EmptyEnv()

        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>sample.guid</guid><name>Sample</name><version>1</version><author>a</author></manifest>",
                )
                zf.writestr(
                    "abdata/list/characustom/sample.csv",
                    "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,"
                    "ThumbAB,ThumbTex\r\n"
                    "1,210,1,Sample,0,abdata,chara/sample/main.unity3d,main,"
                    "chara/sample/main.unity3d,prev\r\n",
                )
                zf.writestr("abdata/chara/sample/main.unity3d", b"bundle")

            item = CsvItem(
                csv_path="abdata/list/characustom/sample.csv",
                item_id="1",
                kind="210",
                name="Sample",
                main_manifest="abdata",
                main_ab="chara/sample/main.unity3d",
                main_data="main_asset",
                thumb_ab="chara/sample/main.unity3d",
                thumb_tex="prev",
                parse_status="ok",
                parse_error="",
            )

            original = mod_database_assets.UnityPy
            try:
                mod_database_assets.UnityPy = EmptyUnityPy
                with zipfile.ZipFile(zipmod_path) as zf:
                    status = inspect_unity3d_status(
                        Path(temp_dir),
                        zf,
                        item,
                        ZipMemberIndex(zf),
                    )
                prepared = prepare_mod_items(
                    Path(temp_dir),
                    ZipmodCandidate(
                        manifest=ManifestData("sample.guid", "Sample", "1", "a", "ok", ""),
                        path=zipmod_path,
                        relative_path="mods/sample.zipmod",
                        file_size=zipmod_path.stat().st_size,
                        modified_at="",
                    ),
                    Path(temp_dir) / "thumbs",
                )
            finally:
                mod_database_assets.UnityPy = original

        self.assertEqual(status.status, "in_mod")
        self.assertEqual(prepared.items[0].unity3d_status, "error")
        self.assertIn("UnityPy loaded no objects", prepared.items[0].unity3d_error)
        summary = summarize_prepared_unity3d(
            [
                PreparedModItem(
                    csv_path=item.csv_path,
                    item_id=item.item_id,
                    kind=item.kind,
                    name=item.name,
                    main_manifest=item.main_manifest,
                    main_ab=item.main_ab,
                    main_data=item.main_data,
                    thumb_ab=item.thumb_ab,
                    thumb_tex=item.thumb_tex,
                    thumbnail_cache_path="",
                    thumbnail_status=prepared.items[0].thumbnail_status,
                    thumbnail_error=prepared.items[0].thumbnail_error,
                    unity3d_status=prepared.items[0].unity3d_status,
                    unity3d_error=prepared.items[0].unity3d_error,
                    parse_status="ok",
                    parse_error="",
                )
            ]
        )
        self.assertEqual(summary[0], "error")


class ModItemPreparationTests(unittest.TestCase):
    def test_duplicate_item_signature_uses_guid_kind_and_item_id_only(self):
        first = PreparedModItem(
            csv_path="abdata/list/first.csv",
            item_id="217101",
            kind="301",
            name="B17 Long",
            main_manifest="abdata",
            main_ab="chara/Belgar17/first.unity3d",
            main_data="first_asset",
            thumb_ab="chara/Belgar17/first_thumb.unity3d",
            thumb_tex="thumb_a",
            thumbnail_cache_path="",
            thumbnail_status="ready",
            thumbnail_error="",
            unity3d_status="in_mod",
            unity3d_error="",
            parse_status="ok",
            parse_error="",
        )
        second = PreparedModItem(
            csv_path="abdata/list/renamed.csv",
            item_id="217101",
            kind="301",
            name="B17 Long Renamed",
            main_manifest="",
            main_ab="chara/Belgar17/second.unity3d",
            main_data="second_asset",
            thumb_ab="chara/Belgar17/second_thumb.unity3d",
            thumb_tex="thumb_b",
            thumbnail_cache_path="",
            thumbnail_status="missing",
            thumbnail_error="thumbnail asset not found",
            unity3d_status="missing",
            unity3d_error="missing unity3d",
            parse_status="ok",
            parse_error="",
        )

        self.assertEqual(
            _duplicate_item_signature(first, "AIMod_B17_HairF_01"),
            _duplicate_item_signature(second, "AIMod_B17_HairF_01"),
        )
        self.assertNotEqual(
            _duplicate_item_signature(first, "AIMod_B17_HairF_01"),
            _duplicate_item_signature(second, "OtherGuid"),
        )

    def test_preextract_zip_unity_thumbnails_writes_multiple_textures_from_one_bundle(self):
        class FakeBundle:
            def __init__(self):
                self.calls = []

            def write_thumbnail(self, thumb_tex, output_path):
                self.calls.append(thumb_tex)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(f"png:{thumb_tex}".encode("utf-8"))
                return ThumbnailResult(str(output_path), "ready", "")

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/sample/thumb.unity3d", b"bundle")

            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=zipmod_path.stat().st_size,
                modified_at="",
            )
            items = [
                CsvItem("", "1", "210", "", "", "", "", "chara/sample/thumb.unity3d", "tex_a", "ok", ""),
                CsvItem("", "2", "210", "", "", "", "", "chara/sample/thumb.unity3d", "tex_b", "ok", ""),
            ]
            bundle = FakeBundle()
            bundle_cache = UnityThumbnailBundleCache()
            bundle_cache.bundles[("zip", "abdata/chara/sample/thumb.unity3d")] = bundle
            source_cache = ThumbnailSourceCache()

            with zipfile.ZipFile(zipmod_path) as zf:
                preextract_zip_unity_thumbnails(
                    candidate,
                    items,
                    root / "thumbs",
                    zf,
                    ZipMemberIndex(zf),
                    bundle_cache,
                    source_cache,
                )

            self.assertEqual(bundle.calls, ["tex_a", "tex_b"])
            for item in items:
                output_path = Path(
                    source_cache.results[
                        (
                            "zip-unity",
                            str(zipmod_path.resolve()).lower(),
                            "abdata/chara/sample/thumb.unity3d",
                            item.thumb_tex,
                        )
                    ].cache_path
                )
                self.assertEqual(output_path.read_bytes(), f"png:{item.thumb_tex}".encode("utf-8"))

    def test_preextract_zip_unity_thumbnails_skips_bad_bundle_without_raising(self):
        class BrokenZip:
            def read(self, _member_name):
                raise zipfile.BadZipFile(
                    "Bad CRC-32 for file 'abdata/chara/sample/thumb.unity3d'"
                )

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            zipmod_path.write_bytes(b"not used")
            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=zipmod_path.stat().st_size,
                modified_at="",
            )
            item = CsvItem(
                "",
                "1",
                "210",
                "",
                "",
                "",
                "",
                "chara/sample/thumb.unity3d",
                "tex_a",
                "ok",
                "",
            )
            index = type(
                "Index",
                (),
                {"find_member": lambda self, _path: "abdata/chara/sample/thumb.unity3d"},
            )()

            preextract_zip_unity_thumbnails(
                candidate,
                [item],
                root / "thumbs",
                BrokenZip(),
                index,
                UnityThumbnailBundleCache(),
                ThumbnailSourceCache(),
            )

    def test_thumbnail_source_cache_reuses_ready_source_for_distinct_item_paths(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_path = root / "thumbs" / "first.png"
            second_path = root / "thumbs" / "second.png"
            first_path.parent.mkdir(parents=True, exist_ok=True)
            first_path.write_bytes(b"png")

            cache = ThumbnailSourceCache()
            cache.remember(
                ("zip-unity", "sample.zipmod", "thumb.unity3d", "preview"),
                ThumbnailResult(str(first_path), "ready", ""),
            )

            result = cache.get(("zip-unity", "sample.zipmod", "thumb.unity3d", "preview"), second_path)

            self.assertIsNotNone(result)
            self.assertEqual(result.status, "ready")
            self.assertEqual(Path(result.cache_path), second_path)
            self.assertEqual(second_path.read_bytes(), b"png")

    def test_same_item_id_with_different_kinds_is_not_deduplicated(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample</guid></manifest>")
                zf.writestr("abdata/chara/sample/head.unity3d", b"bundle")
                zf.writestr("abdata/chara/sample/skin.unity3d", b"bundle")
                zf.writestr(
                    "abdata/list/characustom/head.csv",
                    (
                        "210\r\n"
                        "0\r\n"
                        "head.bytes\r\n"
                        "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,ThumbAB,ThumbTex\r\n"
                        "424,0,1,Ada Head,0,abdata,chara/sample/head.unity3d,head,chara/sample/head.unity3d,thumb\r\n"
                    ),
                )
                zf.writestr(
                    "abdata/list/characustom/skin.csv",
                    (
                        "211\r\n"
                        "0\r\n"
                        "skin.bytes\r\n"
                        "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,ThumbAB,ThumbTex\r\n"
                        "424,0,1,Ada Skin,0,abdata,chara/sample/skin.unity3d,skin,chara/sample/head.unity3d,thumb\r\n"
                    ),
                )

            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=zipmod_path.stat().st_size,
                modified_at="",
            )

            prepared = prepare_mod_items(root, candidate, root / "thumbs")

            self.assertEqual(prepared.ok_count, 2)
            self.assertEqual(prepared.duplicate_items, 0)
            self.assertEqual(
                {(item.csv_path, item.item_id, item.kind) for item in prepared.items},
                {
                    ("abdata/list/characustom/head.csv", "424", "210"),
                    ("abdata/list/characustom/skin.csv", "424", "211"),
                },
            )

    def test_unity3d_missing_zipmods_are_retried_on_incremental_build(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        with conn:
            conn.execute(
                """
                INSERT INTO zipmods (
                    guid, name, file_path, scan_status, last_scanned_at, created_at, updated_at,
                    unity3d_status, unity3d_missing_count
                )
                VALUES ('sample.guid', 'sample', 'sample.zipmod', 'ok', '', '', '', 'missing', 1)
                """
            )

        self.assertEqual(unity3d_retry_guids(conn), {"sample.guid"})

    def test_repair_zipmod_unity3d_moves_source_from_game_abdata(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "mods" / "sample.zipmod"
            zipmod_path.parent.mkdir(parents=True)
            source = root / "abdata" / "chara" / "sample" / "main.unity3d"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"bundle")

            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample.guid</guid></manifest>")
                zf.writestr(
                    "abdata/list/characustom/sample.csv",
                    (
                        "0,,,,,,,,,,,,,,\r\n"
                        "0,,,,,,,,,,,,,,\r\n"
                        "sample,,,,,,,,,,,,,,\r\n"
                        "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,"
                        "TexManifest,TexAB,TexD,TexC,SetHair,ThumbAB,ThumbTex\r\n"
                        "1,210,1,Sample,0,abdata,chara/sample/main.unity3d,main,"
                        "abdata,,,,,chara/sample/main.unity3d,thumb\r\n"
                    ),
                )

            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            try:
                conn.row_factory = sqlite3.Row
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at, unity3d_status,
                            unity3d_in_game_count
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "sample.guid",
                            "sample",
                            str(zipmod_path),
                            "sample.zipmod",
                            "sample.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                            "in_game",
                            1,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, main_manifest,
                            main_ab, main_data, thumb_ab, thumb_tex, thumbnail_status,
                            unity3d_status, parse_status, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            zipmod_id,
                            "sample.guid",
                            "1",
                            "210",
                            "Sample",
                            "abdata",
                            "chara/sample/main.unity3d",
                            "main",
                            "chara/sample/main.unity3d",
                            "thumb",
                            "missing",
                            "in_game",
                            "ok",
                            now,
                            now,
                        ),
                    )
            finally:
                conn.close()

            result = repair_zipmod_unity3d_from_game(zipmod_id, db_path=db_path, thumbnail_dir=root / "thumbs")

            self.assertTrue(result["ok"])
            self.assertEqual(result["moved"], ["abdata/chara/sample/main.unity3d"])
            self.assertFalse(source.exists())
            with zipfile.ZipFile(zipmod_path) as zf:
                self.assertEqual(zf.read("abdata/chara/sample/main.unity3d"), b"bundle")

    def test_bulk_repair_copies_shared_unity3d_and_preserves_source(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "abdata" / "chara" / "shared" / "main.unity3d"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"shared-bundle")
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            now = "2026-01-01T00:00:00+00:00"

            def add_zipmod(name: str) -> int:
                zipmod_path = root / "mods" / f"{name}.zipmod"
                zipmod_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zipmod_path, "w") as zf:
                    zf.writestr("manifest.xml", f"<manifest><guid>{name}.guid</guid></manifest>")
                    zf.writestr(
                        "abdata/list/characustom/sample.csv",
                        (
                            "0,,,,,,,,,,,,,,\r\n"
                            "0,,,,,,,,,,,,,,\r\n"
                            "sample,,,,,,,,,,,,,,\r\n"
                            "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,"
                            "TexManifest,TexAB,TexD,TexC,SetHair,ThumbAB,ThumbTex\r\n"
                            f"1,210,1,{name},0,abdata,chara/shared/main.unity3d,main,"
                            "abdata,,,,,chara/shared/main.unity3d,thumb\r\n"
                        ),
                    )
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at, unity3d_status,
                            unity3d_in_game_count
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{name}.guid",
                            name,
                            str(zipmod_path),
                            f"{name}.zipmod",
                            f"{name}.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                            "in_game",
                            1,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, main_manifest,
                            main_ab, main_data, thumb_ab, thumb_tex, thumbnail_status,
                            unity3d_status, parse_status, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            zipmod_id,
                            f"{name}.guid",
                            "1",
                            "210",
                            name,
                            "abdata",
                            "chara/shared/main.unity3d",
                            "main",
                            "chara/shared/main.unity3d",
                            "thumb",
                            "missing",
                            "in_game",
                            "ok",
                            now,
                            now,
                        ),
                    )
                return int(zipmod_id)

            first_id = add_zipmod("first")
            second_id = add_zipmod("second")
            conn.close()

            from star_manager.services.mod_database_assets import bulk_repair_zipmods_unity3d_from_game

            result = bulk_repair_zipmods_unity3d_from_game([first_id, second_id], db_path=db_path, thumbnail_dir=root / "thumbs")

            self.assertTrue(result["ok"])
            self.assertEqual(result["shared_source_count"], 1)
            self.assertTrue(source.exists())
            self.assertEqual(sum(item["copied_count"] for item in result["repaired"]), 2)
            self.assertEqual(sum(item["moved_count"] for item in result["repaired"]), 0)
            for name in ("first", "second"):
                with zipfile.ZipFile(root / "mods" / f"{name}.zipmod") as zf:
                    self.assertEqual(zf.read("abdata/chara/shared/main.unity3d"), b"shared-bundle")

    def test_thumb_unity3d_found_in_game_is_thumbnail_issue_only(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "mods" / "sample.zipmod"
            zipmod_path.parent.mkdir(parents=True)
            thumb_source = root / "abdata" / "thumbnail" / "sample" / "thumbs.unity3d"
            thumb_source.parent.mkdir(parents=True)
            thumb_source.write_bytes(b"thumb-bundle")

            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample.guid</guid><name>Sample</name></manifest>")
                zf.writestr(
                    "abdata/list/characustom/sample.csv",
                    (
                        "0,,,,,,,,,\r\n"
                        "0,,,,,,,,,\r\n"
                        "sample,,,,,,,,,\r\n"
                        "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,ThumbAB,ThumbTex\r\n"
                        "1,240,1,Sample,0,abdata,chara/sample/main.unity3d,main,"
                        "thumbnail/sample/thumbs.unity3d,thumb\r\n"
                    ),
                )
                zf.writestr("abdata/chara/sample/main.unity3d", b"main-bundle")

            candidate = ZipmodCandidate(
                manifest=ManifestData("sample.guid", "Sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="mods/sample.zipmod",
                file_size=zipmod_path.stat().st_size,
                modified_at="",
            )
            prepared = prepare_mod_items(root, candidate, root / "thumbs")

            self.assertEqual(prepared.items[0].unity3d_status, "in_mod")
            self.assertEqual(prepared.items[0].unity3d_error, "")
            self.assertNotIn(prepared.items[0].thumbnail_status, {"ready", "ok"})

            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at, unity3d_status,
                            unity3d_in_game_count
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "sample.guid",
                            "Sample",
                            str(zipmod_path),
                            "mods/sample.zipmod",
                            "sample.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                            "in_mod",
                            1,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, main_manifest,
                            main_ab, main_data, thumb_ab, thumb_tex, thumbnail_status,
                            unity3d_status, parse_status, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            zipmod_id,
                            "sample.guid",
                            "1",
                            "240",
                            "Sample",
                            "abdata",
                            "chara/sample/main.unity3d",
                            "main",
                            "thumbnail/sample/thumbs.unity3d",
                            "thumb",
                            "missing",
                            "in_mod",
                            "ok",
                            now,
                            now,
                        ),
                    )
            finally:
                conn.close()

            diagnostics = mod_database_assets.zipmod_unity3d_diagnostics(zipmod_id, db_path=db_path)
            unity_issues = [issue for issue in diagnostics["issues"] if issue["type"] == "unity3d"]
            self.assertEqual(unity_issues, [])
            thumbnail_issue = next(issue for issue in diagnostics["issues"] if issue["type"] == "thumbnail")
            self.assertEqual(thumbnail_issue["affected_count"], 1)
            self.assertTrue(thumb_source.exists())

    def test_uses_resource_image_as_thumbnail_for_paint_items(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample</guid></manifest>")
                zf.writestr("abdata/chara/00/st_paint_00_yoshi/RR1_clamp.png", b"png")

            item = CsvItem(
                csv_path="abdata/list/characustom/00/RR1.csv",
                item_id="0",
                kind="313",
                name="RedRibbonLogo1",
                main_manifest="",
                main_ab="chara/00/st_paint_00_yoshi.unity3d",
                main_data="RR1_clamp",
                thumb_ab="chara/thumb/00/st_paint_00_yoshi.unity3d",
                thumb_tex="missing_thumb",
                parse_status="ok",
                parse_error="",
            )
            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=0,
                modified_at="",
            )

            result = extract_thumbnail_from_zipmod(root, candidate, item, root / "thumbs")

            self.assertIn(
                "abdata/chara/00/st_paint_00_yoshi/RR1_clamp.png",
                resource_image_candidates(item),
            )
            self.assertEqual(result.status, "ready")
            self.assertEqual(Path(result.cache_path).read_bytes(), b"png")

    def test_uses_matching_abdata_image_when_thumb_ab_directory_is_wrong(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample</guid></manifest>")
                zf.writestr("abdata/other/EIL.png", b"wrong")
                zf.writestr("abdata/tubge/EIL.png", b"png")

            item = CsvItem(
                csv_path="abdata/list/characustom/00/fo_top_00.csv",
                item_id="0",
                kind="240",
                name="[TuBge]Eli Top",
                main_manifest="abdata",
                main_ab="tubge/MYL.unity3d",
                main_data="tubge_gloves_pbdm",
                thumb_ab="chara",
                thumb_tex="EIL",
                parse_status="ok",
                parse_error="",
            )
            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=0,
                modified_at="",
            )

            result = extract_thumbnail_from_zipmod(root, candidate, item, root / "thumbs")

            self.assertEqual(result.status, "ready")
            self.assertEqual(Path(result.cache_path).read_bytes(), b"png")

    def test_missing_thumb_tex_is_reported_as_thumbnail_issue(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample</guid></manifest>")
                zf.writestr("abdata/thumbnail/star_manager/item.png", b"png")

            item = CsvItem(
                csv_path="abdata/list/characustom/sample.csv",
                item_id="1",
                kind="240",
                name="Sample",
                main_manifest="abdata",
                main_ab="chara/sample.unity3d",
                main_data="sample",
                thumb_ab="thumbnail/star_manager/item.png",
                thumb_tex="",
                parse_status="ok",
                parse_error="",
            )
            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=0,
                modified_at="",
            )

            result = extract_thumbnail_from_zipmod(root, candidate, item, root / "thumbs")

            self.assertEqual(result.status, "missing")
            self.assertEqual(result.error, "ThumbTex is empty")

    def test_uses_main_ab_directory_when_thumb_ab_unity3d_path_is_wrong(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample</guid></manifest>")
                zf.writestr("abdata/chara/wrong/EIL.png", b"wrong")
                zf.writestr("abdata/tubge/EIL.png", b"png")

            item = CsvItem(
                csv_path="abdata/list/characustom/00/fo_top_00.csv",
                item_id="0",
                kind="240",
                name="[TuBge]Eli Top",
                main_manifest="abdata",
                main_ab="tubge/MYL.unity3d",
                main_data="tubge_gloves_pbdm",
                thumb_ab="chara/wrong/MYL.unity3d",
                thumb_tex="EIL",
                parse_status="ok",
                parse_error="",
            )
            candidate = ZipmodCandidate(
                manifest=ManifestData("sample", "sample", "", "", "ok", ""),
                path=zipmod_path,
                relative_path="sample.zipmod",
                file_size=0,
                modified_at="",
            )

            result = extract_thumbnail_from_zipmod(root, candidate, item, root / "thumbs")

            self.assertEqual(result.status, "ready")
            self.assertEqual(Path(result.cache_path).read_bytes(), b"png")

    def test_paint_item_directory_resource_counts_as_in_mod(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/bodypaint_minitattos/Paint01_clamp.png", b"png")

            item = CsvItem(
                csv_path="abdata/list/characustom/00/bodypaint.csv",
                item_id="3000",
                kind="313",
                name="Tatto01",
                main_manifest="",
                main_ab="chara/bodypaint_minitattos",
                main_data="Paint01_clamp",
                thumb_ab="chara/thumb/minitattos.unity3d",
                thumb_tex="Paint01_thumb",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(root, zf, item)

            self.assertEqual(status.status, "in_mod")
            self.assertEqual(status.error, "")

    def test_missing_thumb_unity3d_does_not_mark_item_unity3d_missing(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/sample/main.unity3d", b"bundle")

            item = CsvItem(
                csv_path="abdata/list/characustom/sample.csv",
                item_id="1",
                kind="210",
                name="Sample",
                main_manifest="abdata",
                main_ab="chara/sample/main.unity3d",
                main_data="main",
                thumb_ab="chara/sample/missing_thumb.unity3d",
                thumb_tex="thumb",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(root, zf, item)

            self.assertEqual(status.status, "in_mod")
            self.assertEqual(status.error, "")

    def test_missing_main_unity3d_marks_item_unity3d_missing_even_if_thumb_exists(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/sample/thumb.unity3d", b"bundle")

            item = CsvItem(
                csv_path="abdata/list/characustom/sample.csv",
                item_id="1",
                kind="210",
                name="Sample",
                main_manifest="abdata",
                main_ab="chara/sample/missing_main.unity3d",
                main_data="main",
                thumb_ab="chara/sample/thumb.unity3d",
                thumb_tex="thumb",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(root, zf, item)

            self.assertEqual(status.status, "missing")
            self.assertIn("abdata/chara/sample/missing_main.unity3d", status.error)


class Unity3dSignatureTests(unittest.TestCase):
    def test_numeric_versions_ignore_trailing_zero_segments(self):
        self.assertEqual(_version_sort_key("1.0"), _version_sort_key("1.0.0"))
        self.assertGreater(_version_sort_key("1.0.1"), _version_sort_key("1.0"))
        self.assertGreater(_version_sort_key("1.1"), _version_sort_key("1.0.9"))

    def test_unity3d_average_modified_can_break_duplicate_ties(self):
        older_signatures = {
            "abdata/chara/sample/main.unity3d": {
                "crc": 1,
                "size": 10,
                "modified": "2026-01-01 00:00:00",
                "modified_key": (2026, 1, 1, 0, 0, 0),
            },
            "abdata/chara/sample/thumb.unity3d": {
                "crc": 2,
                "size": 10,
                "modified": "2026-01-03 00:00:00",
                "modified_key": (2026, 1, 3, 0, 0, 0),
            },
        }
        newer_signatures = {
            "abdata/chara/sample/main.unity3d": {
                "crc": 1,
                "size": 10,
                "modified": "2026-02-01 00:00:00",
                "modified_key": (2026, 2, 1, 0, 0, 0),
            },
            "abdata/chara/sample/thumb.unity3d": {
                "crc": 2,
                "size": 10,
                "modified": "2026-02-03 00:00:00",
                "modified_key": (2026, 2, 3, 0, 0, 0),
            },
        }
        older_score, older_label = _unity3d_average_modified(older_signatures)
        newer_score, newer_label = _unity3d_average_modified(newer_signatures)

        older_candidate = {
            "recommendation_reasons": ["most_complete", "latest_version"],
            "completeness_score": 100,
            "unity3d_average_modified_score": older_score,
            "ok_item_count": 1,
            "unity3d_in_mod_count": 1,
            "file_size": 200,
        }
        newer_candidate = {
            "recommendation_reasons": ["most_complete", "latest_version", "newer_unity3d_average"],
            "completeness_score": 100,
            "unity3d_average_modified_score": newer_score,
            "ok_item_count": 1,
            "unity3d_in_mod_count": 1,
            "file_size": 100,
        }

        self.assertEqual(older_label, "2026-01-02 00:00:00")
        self.assertEqual(newer_label, "2026-02-02 00:00:00")
        self.assertGreater(_duplicate_keep_sort_key(newer_candidate), _duplicate_keep_sort_key(older_candidate))

    def test_unity3d_member_signatures_include_only_referenced_members(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.zipmod"
            second = root / "second.zipmod"
            third = root / "third.zipmod"

            with zipfile.ZipFile(first, "w") as zf:
                zf.writestr("abdata/chara/sample/main.unity3d", b"bundle-a")
                zf.writestr("abdata/chara/sample/unused.unity3d", b"new-unused")
                zf.writestr("manifest.xml", b"<manifest />")
            with zipfile.ZipFile(second, "w") as zf:
                zf.writestr("abdata/chara/sample/main.unity3d", b"bundle-a")
                zf.writestr("abdata/chara/sample/unused.unity3d", b"old-unused")
            with zipfile.ZipFile(third, "w") as zf:
                zf.writestr("abdata/chara/sample/main.unity3d", b"bundle-b")

            referenced = ["abdata/chara/sample/main.unity3d"]
            first_signatures, first_error = unity3d_member_signatures(first, referenced)
            second_signatures, second_error = unity3d_member_signatures(second, referenced)
            third_signatures, third_error = unity3d_member_signatures(third, referenced)

            self.assertEqual(first_error, "")
            self.assertEqual(second_error, "")
            self.assertEqual(third_error, "")
            self.assertEqual(first_signatures, second_signatures)
            self.assertNotEqual(first_signatures, third_signatures)
            self.assertEqual(set(first_signatures), {"abdata/chara/sample/main.unity3d"})
            self.assertEqual(
                set(first_signatures["abdata/chara/sample/main.unity3d"]),
                {"crc", "size", "modified", "modified_key"},
            )


if __name__ == "__main__":
    unittest.main()
