"""Benchmark the real original-resource index without touching the app database.

Example: python scripts/benchmark_builtin_index.py "E:\\game\\HoneySelect 2 DX - TSYMQ"
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import threading
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from star_manager.services import builtin_database as builtin  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path)
    parser.add_argument("--mode", choices=("incremental", "full"), default="full")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8])
    args = parser.parse_args()
    game_dir = args.game_dir.resolve()
    if not (game_dir / builtin.BUILTIN_LIST_ROOT).is_dir():
        parser.error("game_dir has no abdata/list/characustom directory")

    totals: dict[str, dict[str, float | int]] = defaultdict(lambda: {"calls": 0, "seconds": 0.0})
    totals_lock = threading.Lock()
    names = (
        "_read_bundle_items_cached",
        "_read_mapinfo_items",
        "_scene_hpoint_info",
        "_builtin_source_signature",
        "_extract_builtin_thumbnail",
        "_resource_status",
    )
    originals = {name: getattr(builtin, name) for name in names}

    def measured(name: str):
        def wrapper(*args, **kwargs):
            start = perf_counter()
            try:
                return originals[name](*args, **kwargs)
            finally:
                with totals_lock:
                    totals[name]["calls"] += 1
                    totals[name]["seconds"] += perf_counter() - start
        return wrapper

    results = []
    with tempfile.TemporaryDirectory(prefix="builtin-index-benchmark-") as temp:
        work = Path(temp)
        last_run_dir: Path | None = None
        with patch.multiple(builtin, **{name: measured(name) for name in names}):
            for workers in args.workers:
                run_dir = work / f"workers-{workers}"
                run_dir.mkdir()
                last_run_dir = run_dir
                conn = sqlite3.connect(run_dir / "index.sqlite")
                conn.row_factory = sqlite3.Row
                try:
                    builtin._BUILTIN_BUNDLE_ITEMS_CACHE.clear()
                    builtin._BUILTIN_SCENE_HPOINT_CACHE.clear()
                    totals.clear()
                    start = perf_counter()
                    stats = builtin.build_builtin_items_index(
                        conn, game_dir, run_dir / "thumbnails", mode=args.mode, worker_count=workers
                    )
                    elapsed = perf_counter() - start
                    results.append({
                        "run": f"first_build_workers_{workers}",
                        "seconds": round(elapsed, 3),
                        "stats": stats,
                        "timings": {
                            name: {"calls": int(value["calls"]), "seconds": round(float(value["seconds"]), 3)}
                            for name, value in totals.items()
                        },
                    })
                finally:
                    conn.close()
            if last_run_dir is not None:
                conn = sqlite3.connect(last_run_dir / "index.sqlite")
                conn.row_factory = sqlite3.Row
                try:
                    totals.clear()
                    start = perf_counter()
                    stats = builtin.build_builtin_items_index(
                        conn,
                        game_dir,
                        last_run_dir / "thumbnails",
                        mode="incremental",
                        worker_count=args.workers[-1],
                    )
                    results.append({
                        "run": "cached_build",
                        "seconds": round(perf_counter() - start, 3),
                        "stats": stats,
                        "timings": {},
                    })
                finally:
                    conn.close()
    print(json.dumps({"game_dir": str(game_dir), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
