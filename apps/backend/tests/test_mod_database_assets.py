import sys
import sqlite3
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.mod_database_core import CsvItem, PreparedModItem, STUDIO_ITEM_KIND, ThumbnailResult  # noqa: E402
from star_manager.services.mod_database_core import ManifestData, ZipmodCandidate, init_db  # noqa: E402
from star_manager.services.mod_database_assets import (  # noqa: E402
    _duplicate_keep_sort_key,
    _duplicate_item_signature,
    _unity3d_average_modified,
    _version_sort_key,
    DUAL_MAP_SCENE_KIND,
    GAME_MAP_SCENE_KIND,
    decode_csv_bytes_with_encoding,
    ensure_mod_item_thumbnail,
    extract_thumbnail_from_zipmod,
    find_zip_directory,
    find_zip_member,
    find_zip_unity3d_or_directory,
    inspect_unity3d_status,
    iter_open_zip_csv_items,
    normalize_abdata_path,
    preextract_zip_unity_thumbnails,
    read_kplug_map_items,
    read_manifest,
    read_items_from_csv,
    repair_zipmod_unity3d_from_game,
    resource_image_candidates,
    ThumbnailSourceCache,
    UnityThumbnailBundleCache,
    thumbnail_csv_reference_for_arcname,
    thumbnail_error_detail,
    unity3d_member_signatures,
    zipmod_unity3d_diagnostics,
    ZipMemberIndex,
)
from star_manager.services import mod_database_assets  # noqa: E402
from star_manager.services.mod_database import build_database, prepare_mod_items, summarize_prepared_unity3d  # noqa: E402
from star_manager.services.mod_database_queries import list_zipmods  # noqa: E402


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
    def test_ensure_mod_item_thumbnail_rebuilds_missing_cache_from_zipmod(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "mods" / "sample.zipmod"
            zipmod_path.parent.mkdir(parents=True)
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>sample.guid</guid><name>Sample</name>"
                    "<version>1</version><author>Author</author></manifest>",
                )
                zf.writestr("abdata/thumbnail/sample.png", b"png-from-zipmod")

            db_path = root / "runtime" / "star_manager.sqlite"
            db_path.parent.mkdir(parents=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                zipmod_id = conn.execute(
                    """
                    INSERT INTO zipmods (
                        guid, name, version, author, file_path, relative_path,
                        file_name, file_size, scan_status, last_scanned_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                    """,
                    (
                        "sample.guid",
                        "Sample",
                        "1",
                        "Author",
                        str(zipmod_path),
                        "mods/sample.zipmod",
                        zipmod_path.name,
                        zipmod_path.stat().st_size,
                        now,
                        now,
                        now,
                    ),
                ).lastrowid
                item_id = conn.execute(
                    """
                    INSERT INTO mod_items (
                        zipmod_id, zipmod_guid, item_id, kind, name,
                        thumb_ab, thumb_tex, thumbnail_status, parse_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', 'ok', ?, ?)
                    """,
                    (
                        zipmod_id,
                        "sample.guid",
                        "1",
                        "240",
                        "Sample Item",
                        "thumbnail/sample.png",
                        "sample",
                        now,
                        now,
                    ),
                ).lastrowid
                conn.commit()
            finally:
                conn.close()

            result = ensure_mod_item_thumbnail(
                item_id,
                db_path=db_path,
                thumbnail_dir=root / "runtime" / "thumbnails",
            )

            self.assertTrue(result["ok"])
            cache_path = Path(result["thumbnail_cache_path"])
            self.assertEqual(cache_path.read_bytes(), b"png-from-zipmod")
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute(
                    "SELECT thumbnail_status, thumbnail_cache_path FROM mod_items WHERE id = ?",
                    (item_id,),
                ).fetchone()
            finally:
                conn.close()
            self.assertEqual(row[0], "ready")
            self.assertEqual(Path(row[1]).resolve(), cache_path.resolve())

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

    def test_thumbnail_bundle_decodes_only_the_selected_asset(self):
        class ImageData:
            def __init__(self, name):
                self.image = object()
                self.name = name

        class LazyObject:
            type = type("ObjType", (), {"name": "Texture2D"})()

            def __init__(self, name):
                self.name = name
                self.peek_calls = 0
                self.read_calls = 0

            def peek_name(self):
                self.peek_calls += 1
                return self.name

            def read(self):
                self.read_calls += 1
                return ImageData(self.name)

        target = LazyObject("target")
        unrelated = LazyObject("unrelated")

        class LazyEnv:
            container = {
                "assets/target.png": target,
                "assets/unrelated.png": unrelated,
            }
            objects = [target, unrelated]

        class LazyUnityPy:
            @staticmethod
            def load(_bundle_bytes):
                return LazyEnv()

        original = mod_database_assets.UnityPy
        try:
            mod_database_assets.UnityPy = LazyUnityPy
            result = mod_database_assets.UnityThumbnailBundle.from_bytes(b"bundle")
            self.assertIsInstance(result, mod_database_assets.UnityThumbnailBundle)
            self.assertEqual(target.read_calls, 0)
            self.assertEqual(unrelated.read_calls, 0)
            self.assertIsNotNone(result.find_image("target"))
        finally:
            mod_database_assets.UnityPy = original

        self.assertEqual(target.read_calls, 1)
        self.assertEqual(unrelated.read_calls, 0)


class CsvEncodingTests(unittest.TestCase):
    def test_reads_studio_item_with_group_and_category_metadata(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "studio-item.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/studio/info/author/ItemGroup_author.csv", "ID,Name\n8460,Author Group\n")
                zf.writestr("abdata/studio/info/author/ItemCategory_06_8460.csv", "ID,Name\n6,Animals\n")
                zf.writestr(
                    "abdata/studio/info/author/ItemList_01_8460_06.csv",
                    "ID,BigCategory,MidCategory,Name,Manifest,Bundle,Object\n"
                    "2,8460,6,Bull,abdata,author/data_prefab_000.unity3d,Bull\n",
                )
            with zipfile.ZipFile(zipmod_path) as source:
                items = list(iter_open_zip_csv_items(source))

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.kind, STUDIO_ITEM_KIND)
        self.assertEqual(item.item_domain, "studio")
        self.assertEqual(item.item_id, "2")
        self.assertEqual(item.main_ab, "author/data_prefab_000.unity3d")
        self.assertEqual(item.main_data, "Bull")
        self.assertEqual((item.studio_group_id, item.studio_group_name), ("8460", "Author Group"))
        self.assertEqual((item.studio_category_id, item.studio_category_name), ("6", "Animals"))
        self.assertEqual((item.thumb_ab, item.thumb_tex), ("", ""))

    def test_studio_item_skips_thumbnail_extraction(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "studio-item.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>studio.item.guid</guid><name>Studio Item</name>"
                    "<version>1</version><author>Author</author></manifest>",
                )
                zf.writestr("abdata/studio/info/author/ItemGroup_author.csv", "ID,Name\n8460,Author Group\n")
                zf.writestr("abdata/studio/info/author/ItemCategory_06_8460.csv", "ID,Name\n6,Animals\n")
                zf.writestr(
                    "abdata/studio/info/author/ItemList_01_8460_06.csv",
                    "ID,BigCategory,MidCategory,Name,Manifest,Bundle,Object\n"
                    "2,8460,6,Bull,abdata,author/data_prefab_000.unity3d,Bull\n",
                )
                zf.writestr("abdata/author/data_prefab_000.unity3d", b"UnityFS")
                zf.writestr("abdata/studio_thumbnails/00008460-00000006-Bull.png", b"unused")

            candidate = ZipmodCandidate(
                manifest=ManifestData("studio.item.guid", "Studio Item", "1", "Author", "ok", ""),
                path=zipmod_path,
                relative_path="studio-item.zipmod",
                file_size=zipmod_path.stat().st_size,
                modified_at="2026-09-17T00:00:00+00:00",
            )
            prepared = prepare_mod_items(root, candidate, root / "thumbnails")

        self.assertEqual(len(prepared.items), 1)
        item = prepared.items[0]
        self.assertEqual(item.item_domain, "studio")
        self.assertEqual(item.thumbnail_status, "not_applicable")
        self.assertEqual(item.thumbnail_cache_path, "")
        self.assertEqual(item.unity3d_status, "in_mod")
    def test_reads_utf16_le_bom_csv_with_metadata_rows(self):
        csv_bytes = (
            "247\r\n"
            "assetboye\r\n"
            "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,StateType,"
            "MainTex,ColorMaskTex,MainTex02,ColorMask02Tex,ThumbAB,ThumbTex\r\n"
            "298,0,1,[rz]Boots2,0,abdata,chara/HS_Boots2.unity3d,HS_Boots2,1,"
            "boots2_c,mc,0,0,chara/thumb,Boots2\r\n"
        ).encode("utf-16")

        encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
        items = read_items_from_csv(
            "abdata/list/characustom/HS_Boots.csv",
            csv_bytes,
        )

        self.assertEqual(encoding, "utf-16")
        self.assertIn("ID,Kind,Possess,Name", text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].item_id, "298")
        self.assertEqual(items[0].kind, "247")
        self.assertEqual(items[0].name, "[rz]Boots2")
        self.assertEqual(items[0].main_ab, "chara/HS_Boots2.unity3d")
        self.assertEqual(items[0].thumb_ab, "chara/thumb")
        self.assertEqual(items[0].thumb_tex, "Boots2")
        self.assertEqual(items[0].parse_status, "ok")

    def test_reads_legacy_bare_carriage_return_csv(self):
        csv_bytes = (
            "\ufeff334\r"
            "0\r"
            "Assets/in-house/assetbundle/list/characustom/00/st_nip_00.bytes\r"
            "ID,Kind,Possess,Name,EN_US,MainAB,AddTex,ThumbAB,ThumbTex\r"
            "240,0,1,[Praline]Illu_mix01,0,chara/Praline/nip_illu_mix.unity3d,"
            "c_t_nip_illu_mix01,chara/Praline/nip_illu_mix.unity3d,thumb_c_t_nip_illu_mix\r"
            "241,0,1,[Praline]Illu_mix02,0,chara/Praline/nip_illu_mix.unity3d,"
            "c_t_nip_illu_mix02,chara/Praline/nip_illu_mix.unity3d,thumb_c_t_nip_illu_mix\r"
        ).encode("utf-8")

        items = read_items_from_csv(
            "abdata/list/characustom/nip_illu_mix.csv",
            csv_bytes,
        )

        self.assertEqual(
            [(item.item_id, item.kind) for item in items],
            [("240", "334"), ("241", "334")],
        )
        self.assertTrue(all(item.parse_status == "ok" for item in items))

    def test_reads_kplug_map_registration_as_map_scene_item(self):
        csv_bytes = (
            "MAPMOD,,,\r\n"
            "MAPMOD,,,\r\n"
            "0,(Mas75) Crystal Cave Lair,"
            "_mas75__crystal_cave_lair_bundles/_mas75__crystal_cave_lair/data_scene_000.unity3d,"
            "(Mas75) Crystal Cave Lair,abdata\r\n"
        ).encode("utf-8")

        items = read_kplug_map_items(
            "abdata/studio/info/kPlug/Map_kPlug.csv",
            csv_bytes,
            thumbnail_references=[("maps/crystal/data_thumbnail_000.unity3d", "map_thumb_s.psd")],
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, "__map_scene__")
        self.assertEqual(items[0].name, "(Mas75) Crystal Cave Lair")
        self.assertEqual(
            items[0].main_ab,
            "_mas75__crystal_cave_lair_bundles/_mas75__crystal_cave_lair/data_scene_000.unity3d",
        )
        self.assertEqual(items[0].main_manifest, "abdata")
        self.assertEqual(items[0].thumb_ab, "maps/crystal/data_thumbnail_000.unity3d")
        self.assertEqual(items[0].thumb_tex, "map_thumb_s.psd")

    def test_classifies_kplug_map_with_mapinfo_as_game_and_studio_map(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "dual-map.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "abdata/studio/info/kPlug/Map_kPlug.csv",
                    "MAPMOD,,,\n0,Dual Map,maps/dual/data_scene_000.unity3d,scene2,abdata\n",
                )
                zf.writestr("abdata/map/list/mapinfo/dual_mapdata_000.unity3d", b"mapinfo")
            with zipfile.ZipFile(zipmod_path) as source:
                items = list(iter_open_zip_csv_items(source, "Dual Map"))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, DUAL_MAP_SCENE_KIND)
        self.assertEqual(items[0].name, "Dual Map")
        self.assertEqual(items[0].main_ab, "maps/dual/data_scene_000.unity3d")

    def test_classifies_mapinfo_without_kplug_as_game_only_map(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "game-map.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/map/list/mapinfo/game_mapdata_000.unity3d", b"mapinfo")
            with zipfile.ZipFile(zipmod_path) as source:
                items = list(iter_open_zip_csv_items(source, "Game Map"))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, GAME_MAP_SCENE_KIND)
        self.assertEqual(items[0].name, "Game Map")
        self.assertEqual(items[0].main_ab, "map/list/mapinfo/game_mapdata_000.unity3d")

    def test_prepares_kplug_map_as_ready_scene_item_without_thumbnail(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "map.zipmod"
            bundle_path = "abdata/maps/crystal/data_scene_000.unity3d"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>map.guid</guid><name>Crystal Cave</name><version>1</version><author>Mas75</author></manifest>",
                )
                zf.writestr(
                    "abdata/studio/info/kPlug/Map_kPlug.csv",
                    "MAPMOD,,,\n0,Crystal Cave,maps/crystal/data_scene_000.unity3d,Crystal Cave,abdata\n",
                )
                zf.writestr(bundle_path, b"bundle")

            prepared = prepare_mod_items(
                root,
                ZipmodCandidate(
                    manifest=ManifestData("map.guid", "Crystal Cave", "1", "Mas75", "ok", ""),
                    path=zipmod_path,
                    relative_path="mods/map.zipmod",
                    file_size=zipmod_path.stat().st_size,
                    modified_at="",
                ),
                root / "thumbs",
            )

        self.assertEqual(prepared.ok_count, 1)
        self.assertEqual(prepared.items[0].kind, "__map_scene__")
        self.assertEqual(prepared.items[0].thumbnail_status, "ready")
        self.assertEqual(prepared.items[0].unity3d_status, "in_mod")

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

    def test_reads_texab_as_an_additional_unity3d_dependency(self):
        csv_bytes = (
            "348\r\n"
            "ID,Kind,Possess,Name,MainManifest,MainAB,MainData,TexManifest,TexAB,TexD,ThumbAB,ThumbTex\r\n"
            "171,0,1,hair-01,abdata,chara/hair/main.unity3d,hair,abdata,chara/hair/hair_tex.unity3d,placeholder,,\r\n"
        ).encode("utf-8")

        items = read_items_from_csv("abdata/list/characustom/hair.csv", csv_bytes)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].main_ab, "chara/hair/main.unity3d")
        self.assertEqual(items[0].tex_ab, "chara/hair/hair_tex.unity3d")

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
    def test_missing_texab_unity3d_does_not_mark_item_as_missing(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "sample.zipmod"
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/hair/main.unity3d", b"main-bundle")

            item = CsvItem(
                csv_path="abdata/list/characustom/hair.csv",
                item_id="171",
                kind="348",
                name="hair-01",
                main_manifest="abdata",
                main_ab="chara/hair/main.unity3d",
                main_data="hair",
                tex_ab="chara/hair/hair_tex.unity3d",
                thumb_ab="",
                thumb_tex="",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(Path(temp_dir), zf, item)

        self.assertEqual(status.status, "in_mod")
        self.assertEqual(status.error, "")

    def test_texab_in_common_game_chara_slot_is_ignored(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            common_tex = root / "abdata" / "chara" / "60" / "hair_tex.unity3d"
            common_tex.parent.mkdir(parents=True)
            common_tex.write_bytes(b"common-tex-bundle")
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/hair/main.unity3d", b"main-bundle")

            item = CsvItem(
                csv_path="abdata/list/characustom/hair.csv",
                item_id="171",
                kind="348",
                name="hair-01",
                main_manifest="abdata",
                main_ab="chara/hair/main.unity3d",
                main_data="hair",
                tex_ab="chara/60/hair_tex.unity3d",
                thumb_ab="",
                thumb_tex="",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(root, zf, item)

        self.assertEqual(status.status, "in_mod")
        self.assertEqual(status.error, "")

    def test_texab_outside_common_game_chara_slots_is_external_warning(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            external_tex = root / "abdata" / "chara" / "shared" / "hair_tex.unity3d"
            external_tex.parent.mkdir(parents=True)
            external_tex.write_bytes(b"external-tex-bundle")
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/chara/hair/main.unity3d", b"main-bundle")

            item = CsvItem(
                csv_path="abdata/list/characustom/hair.csv",
                item_id="171",
                kind="348",
                name="hair-01",
                main_manifest="abdata",
                main_ab="chara/hair/main.unity3d",
                main_data="hair",
                tex_ab="chara/shared/hair_tex.unity3d",
                thumb_ab="",
                thumb_tex="",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(root, zf, item)

        self.assertEqual(status.status, "not_in_mod")
        self.assertEqual(status.source, "game_abdata")
        self.assertIn("chara/shared/hair_tex.unity3d", status.error)

    def test_mainab_in_common_game_chara_slot_is_ignored(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "sample.zipmod"
            common_main = root / "abdata" / "chara" / "00" / "f0_top_00.unity3d"
            common_main.parent.mkdir(parents=True)
            common_main.write_bytes(b"common-main-bundle")
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("abdata/list/characustom/top.csv", b"csv")

            item = CsvItem(
                csv_path="abdata/list/characustom/top.csv",
                item_id="171",
                kind="351",
                name="top-01",
                main_manifest="abdata",
                main_ab="chara/00/f0_top_00.unity3d",
                main_data="f0_top_00",
                tex_ab="",
                thumb_ab="",
                thumb_tex="",
                parse_status="ok",
                parse_error="",
            )

            with zipfile.ZipFile(zipmod_path) as zf:
                status = inspect_unity3d_status(root, zf, item)

        self.assertEqual(status.status, "in_mod")
        self.assertEqual(status.error, "")

    def test_unity3d_in_other_zipmod_is_not_in_current_mod_and_is_warning(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "game"
            mods_dir = game_dir / "mods"
            mods_dir.mkdir(parents=True)
            shared_reference = "chara/shared/hair_tex.unity3d"
            provider_path = mods_dir / "provider.zipmod"
            with zipfile.ZipFile(provider_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>provider.guid</guid><name>Provider</name><version>1</version><author>A</author></manifest>",
                )
                zf.writestr(f"abdata/{shared_reference}", b"shared-tex")

            current_path = mods_dir / "current.zipmod"
            with zipfile.ZipFile(current_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>current.guid</guid><name>Current</name><version>1</version><author>A</author></manifest>",
                )
                zf.writestr(
                    "abdata/list/characustom/hair.csv",
                    "348\r\nID,Kind,Possess,Name,MainManifest,MainAB,MainData,TexManifest,TexAB,TexD,ThumbAB,ThumbTex\r\n"
                    f"171,0,1,hair-01,abdata,chara/current/main.unity3d,hair,abdata,{shared_reference},placeholder,,\r\n"
                    f"172,0,1,hair-02,abdata,chara/current/main.unity3d,hair,abdata,{shared_reference},placeholder,,\r\n",
                )
                zf.writestr("abdata/chara/current/main.unity3d", b"main")

            db_path = root / "star_manager.sqlite"
            build_database(game_dir, db_path, root / "thumbs")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                current_id = conn.execute(
                    "SELECT id FROM zipmods WHERE guid = 'current.guid'"
                ).fetchone()[0]
                item = conn.execute(
                    "SELECT unity3d_status, unity3d_source FROM mod_items WHERE zipmod_guid = 'current.guid'"
                ).fetchone()
            finally:
                conn.close()

            self.assertEqual((item["unity3d_status"], item["unity3d_source"]), ("not_in_mod", "other_zipmod"))
            diagnostics = zipmod_unity3d_diagnostics(current_id, db_path)
            warning_rows = list_zipmods(db_path, status="warning")

        self.assertTrue(diagnostics["ok"])
        issues = [issue for issue in diagnostics["issues"] if issue["type"] == "unity3d"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["status"], "not_in_mod")
        self.assertEqual(issues[0]["source"], "other_zipmod")
        self.assertEqual(issues[0]["repair_action"], "")
        self.assertEqual(issues[0]["other_zipmods"][0]["guid"], "provider.guid")
        self.assertEqual(issues[0]["affected_count"], 2)
        self.assertEqual(warning_rows["total"], 1)
        self.assertEqual(warning_rows["rows"][0]["guid"], "current.guid")

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
    def test_build_database_ignores_missing_texab_dependency(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "game"
            zipmod_path = game_dir / "mods" / "hair.zipmod"
            zipmod_path.parent.mkdir(parents=True)
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr(
                    "manifest.xml",
                    "<manifest><guid>hair.guid</guid><name>Hair</name>"
                    "<version>1</version><author>Author</author></manifest>",
                )
                zf.writestr(
                    "abdata/list/characustom/hair.csv",
                    "348\r\n"
                    "ID,Kind,Possess,Name,MainManifest,MainAB,MainData,TexManifest,TexAB,TexD,ThumbAB,ThumbTex\r\n"
                    "171,0,1,hair-01,abdata,chara/hair/main.unity3d,hair,abdata,"
                    "chara/hair/hair_tex.unity3d,placeholder,,\r\n",
                )
                zf.writestr("abdata/chara/hair/main.unity3d", b"main-bundle")

            db_path = root / "star_manager.sqlite"
            build_database(game_dir, db_path, root / "thumbs")

            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute(
                    "SELECT tex_ab, unity3d_status, unity3d_error FROM mod_items"
                ).fetchone()
            finally:
                conn.close()

        self.assertEqual(row[0], "chara/hair/hair_tex.unity3d")
        self.assertEqual(row[1], "in_mod")
        self.assertEqual(row[2], "")

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

    def test_bulk_repair_copies_shared_texab_unity3d_and_preserves_source(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "game"
            source = game_dir / "abdata" / "chara" / "shared" / "hair_tex.unity3d"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"shared-tex-bundle")

            for name in ("first", "second"):
                zipmod_path = game_dir / "mods" / f"{name}.zipmod"
                zipmod_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zipmod_path, "w") as zf:
                    zf.writestr(
                        "manifest.xml",
                        f"<manifest><guid>{name}.guid</guid><name>{name}</name>"
                        "<version>1</version><author>Author</author></manifest>",
                    )
                    zf.writestr(
                        "abdata/list/characustom/hair.csv",
                        (
                            "348\r\n"
                            "ID,Kind,Possess,Name,MainManifest,MainAB,MainData,"
                            "TexManifest,TexAB,TexD,ThumbAB,ThumbTex\r\n"
                            f"171,0,1,{name},abdata,chara/{name}/main.unity3d,{name},"
                            "abdata,chara/shared/hair_tex.unity3d,placeholder,,\r\n"
                        ),
                    )
                    zf.writestr(
                        f"abdata/chara/{name}/main.unity3d",
                        f"main-{name}".encode("utf-8"),
                    )

            db_path = root / "star_manager.sqlite"
            thumbnail_dir = root / "thumbs"
            build_database(game_dir, db_path, thumbnail_dir)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows_before = conn.execute(
                    "SELECT zipmod_guid, tex_ab, unity3d_status FROM mod_items ORDER BY zipmod_guid"
                ).fetchall()
                zipmod_ids = [
                    int(row[0])
                    for row in conn.execute("SELECT id FROM zipmods ORDER BY guid")
                ]
            finally:
                conn.close()

            self.assertEqual(
                [(row["zipmod_guid"], row["tex_ab"], row["unity3d_status"]) for row in rows_before],
                [
                    ("first.guid", "chara/shared/hair_tex.unity3d", "not_in_mod"),
                    ("second.guid", "chara/shared/hair_tex.unity3d", "not_in_mod"),
                ],
            )

            from star_manager.services.mod_database_assets import bulk_repair_zipmods_unity3d_from_game

            result = bulk_repair_zipmods_unity3d_from_game(
                zipmod_ids,
                db_path=db_path,
                thumbnail_dir=thumbnail_dir,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["shared_source_count"], 1)
            self.assertEqual(sum(item["copied_count"] for item in result["repaired"]), 2)
            self.assertEqual(sum(item["moved_count"] for item in result["repaired"]), 0)
            self.assertTrue(source.exists())
            for name in ("first", "second"):
                with zipfile.ZipFile(game_dir / "mods" / f"{name}.zipmod") as zf:
                    self.assertEqual(
                        zf.read("abdata/chara/shared/hair_tex.unity3d"),
                        b"shared-tex-bundle",
                    )

            conn = sqlite3.connect(db_path)
            try:
                statuses_after = conn.execute(
                    "SELECT zipmod_guid, tex_ab, unity3d_status FROM mod_items ORDER BY zipmod_guid"
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(
                [(row[0], row[1], row[2]) for row in statuses_after],
                [
                    ("first.guid", "chara/shared/hair_tex.unity3d", "in_mod"),
                    ("second.guid", "chara/shared/hair_tex.unity3d", "in_mod"),
                ],
            )

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
