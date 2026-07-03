from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from star_manager.services.mod_database import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    build_database,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the local Star_Manager mod database.")
    parser.add_argument(
        "game_dir",
        nargs="?",
        type=Path,
        default=Path("test/hs2"),
        help="HS2 game directory. Defaults to test/hs2.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite output path. Defaults to {DEFAULT_DB_PATH}.",
    )
    parser.add_argument(
        "--thumbnail-dir",
        type=Path,
        default=DEFAULT_THUMBNAIL_DIR,
        help=f"Thumbnail cache directory. Defaults to {DEFAULT_THUMBNAIL_DIR}.",
    )
    args = parser.parse_args()

    stats = build_database(args.game_dir, args.db, args.thumbnail_dir)
    print(f"database: {args.db.resolve()}")
    print(f"thumbnail_dir: {args.thumbnail_dir.resolve()}")
    for key, value in stats.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
