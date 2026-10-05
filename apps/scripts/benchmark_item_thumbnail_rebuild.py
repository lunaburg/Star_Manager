"""Time the real single-item thumbnail export/import path on isolated zipmod copies."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
import zipfile
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from star_manager.services import mod_database_assets as assets  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402


def add_row(conn: sqlite3.Connection, table: str, row: sqlite3.Row, changes: dict | None = None) -> None:
    values = dict(row)
    values.update(changes or {})
    columns = list(values)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        tuple(values.values()),
    )


def percentiles(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean": statistics.mean(ordered),
        "median": statistics.median(ordered),
        "p90": ordered[max(0, int(0.9 * len(ordered) + 0.999999) - 1)],
        "min": ordered[0],
        "max": ordered[-1],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(__file__).resolve().parents[1] / "backend/runtime/star_manager.sqlite")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "tmp/benchmark_item_thumbnail_rebuild_20261002.json")
    parser.add_argument("--per-decile", type=int, default=3)
    parser.add_argument("--max-zip-mb", type=int, default=350)
    parser.add_argument("--only-index", type=int)
    args = parser.parse_args()
    source_conn = sqlite3.connect(f"file:{args.db.resolve().as_posix()}?mode=ro", uri=True)
    source_conn.row_factory = sqlite3.Row
    rows = source_conn.execute(
        """SELECT i.*, z.file_size AS sample_zip_size, z.file_path AS sample_zip_path,
                  z.id AS sample_zip_id
           FROM mod_items i JOIN zipmods z ON z.id = i.zipmod_id
           WHERE i.item_domain != 'studio' AND i.thumbnail_status = 'ready'
             AND i.parse_status = 'ok' AND z.scan_status = 'ok'
           ORDER BY z.file_size, i.id"""
    ).fetchall()
    eligible = [
        row for row in rows
        if Path(row["sample_zip_path"]).is_file()
        and Path(row["thumbnail_cache_path"]).is_file()
    ]
    capped = [row for row in eligible if row["sample_zip_size"] <= args.max_zip_mb * 1024 * 1024]
    rng = random.Random(20261002)
    selected = []
    used_zip_ids = set()
    for decile in range(10):
        lower = len(capped) * decile // 10
        upper = len(capped) * (decile + 1) // 10
        candidates = list(capped[lower:upper])
        rng.shuffle(candidates)
        for row in candidates:
            if row["sample_zip_id"] in used_zip_ids:
                continue
            selected.append((decile + 1, row))
            used_zip_ids.add(row["sample_zip_id"])
            if sum(bucket == decile + 1 for bucket, _ in selected) >= args.per_decile:
                break
    results = []
    root = args.output.parent / "benchmark_item_thumbnail_rebuild_work"
    root.mkdir(parents=True, exist_ok=True)
    for index, (decile, row) in enumerate(selected, start=1):
        if args.only_index is not None and index != args.only_index:
            continue
        stage = {"zip_rewrite_s": 0.0, "rescan_s": 0.0}
        with tempfile.TemporaryDirectory(prefix="sample_", dir=root) as temp_name:
            work = Path(temp_name)
            zip_path = work / "mods" / "sample.zipmod"
            zip_path.parent.mkdir()
            original_zip = Path(row["sample_zip_path"])
            shutil.copy2(original_zip, zip_path)
            db_path = work / "sample.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            zip_row = source_conn.execute("SELECT * FROM zipmods WHERE id = ?", (row["sample_zip_id"],)).fetchone()
            add_row(conn, "zipmods", zip_row, {"file_path": str(zip_path), "relative_path": "sample.zipmod"})
            item_row = source_conn.execute("SELECT * FROM mod_items WHERE id = ?", (row["id"],)).fetchone()
            add_row(conn, "mod_items", item_row)
            conn.commit()
            conn.close()
            thumbnail_dir = work / "thumbnails"
            export_start = time.perf_counter()
            exported = assets.export_zipmod_item_thumbnail(int(row["id"]), str(work / "export"), db_path=db_path)
            export_s = time.perf_counter() - export_start
            if not exported.get("ok"):
                results.append({"index": index, "decile": decile, "error": exported.get("error"), "phase": "export"})
                continue
            image = Path(exported["target_path"])
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            original_rewrite = assets.rewrite_zip_members
            original_rescan = assets._replace_mod_items

            def timed_rewrite(*a, **kw):
                started = time.perf_counter()
                try:
                    return original_rewrite(*a, **kw)
                finally:
                    stage["zip_rewrite_s"] += time.perf_counter() - started

            def timed_rescan(*a, **kw):
                started = time.perf_counter()
                try:
                    return original_rescan(*a, **kw)
                finally:
                    stage["rescan_s"] += time.perf_counter() - started

            assets.rewrite_zip_members = timed_rewrite
            assets._replace_mod_items = timed_rescan
            try:
                started = time.perf_counter()
                imported = assets.import_zipmod_item_thumbnail(
                    int(row["id"]), str(image), db_path=db_path, thumbnail_dir=thumbnail_dir
                )
                import_s = time.perf_counter() - started
            finally:
                assets.rewrite_zip_members = original_rewrite
                assets._replace_mod_items = original_rescan
            verified = False
            if imported.get("ok"):
                with zipfile.ZipFile(zip_path) as archive:
                    member = archive.read(imported["image_path"])
                    csv_member = archive.read(imported["csv_path"])
                with closing(sqlite3.connect(db_path)) as check:
                    new_item = check.execute(
                        "SELECT thumbnail_status, thumbnail_cache_path, thumb_ab, thumb_tex "
                        "FROM mod_items WHERE zipmod_id = ? AND item_id = ? AND csv_path = ?",
                        (row["sample_zip_id"], row["item_id"], row["csv_path"]),
                    ).fetchone()
                verified = bool(
                    hashlib.sha256(member).hexdigest() == digest
                    and new_item and new_item[0] == "ready"
                    and Path(new_item[1]).is_file()
                    and hashlib.sha256(Path(new_item[1]).read_bytes()).hexdigest() == digest
                    and new_item[2].encode() in csv_member
                    and new_item[3].encode() in csv_member
                )
            result = {
                "index": index, "decile": decile, "item_db_id": row["id"],
                "zip_size_mb": round(row["sample_zip_size"] / 1048576, 3),
                "image_kb": round(image.stat().st_size / 1024, 3),
                "export_s": export_s, "import_s": import_s, **stage,
                "other_s": import_s - stage["zip_rewrite_s"] - stage["rescan_s"],
                "ok": bool(imported.get("ok")), "verified": verified,
                "error": imported.get("error", ""),
            }
            results.append(result)
            print(f"{index}/{len(selected)} decile={decile} zip={result['zip_size_mb']:.1f}MB import={import_s:.3f}s verified={verified}", flush=True)
    success = [item for item in results if item.get("verified")]
    summary = {
        "eligible_items": len(eligible), "capped_items": len(capped),
        "cap_mb": args.max_zip_mb, "sample_count": len(results), "success_count": len(success),
        "export_s": percentiles([r["export_s"] for r in success]) if success else None,
        "import_s": percentiles([r["import_s"] for r in success]) if success else None,
        "zip_rewrite_s": percentiles([r["zip_rewrite_s"] for r in success]) if success else None,
        "rescan_s": percentiles([r["rescan_s"] for r in success]) if success else None,
        "other_s": percentiles([r["other_s"] for r in success]) if success else None,
        "by_decile": [
            {"decile": decile, **percentiles([r["import_s"] for r in success if r["decile"] == decile])}
            for decile in range(1, 11) if any(r["decile"] == decile for r in success)
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": summary, "samples": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    source_conn.close()
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
