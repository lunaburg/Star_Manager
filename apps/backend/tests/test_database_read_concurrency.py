import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_library import resolve_card_dependencies  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402
from star_manager.services.mod_database_queries import database_status  # noqa: E402


def test_read_endpoints_do_not_request_schema_lock_during_write_transaction():
    with TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "star_manager.sqlite"
        writer = sqlite3.connect(db_path)
        writer.row_factory = sqlite3.Row
        try:
            init_db(writer)
            writer.commit()
            writer.execute("BEGIN IMMEDIATE")
            writer.execute(
                "INSERT INTO database_metadata (key, value) VALUES (?, ?)",
                ("write_in_progress", "1"),
            )

            status = database_status(db_path=db_path)
            assert status["exists"] is True

            with patch(
                "star_manager.services.card_library.extract_auto_resolver_records_from_card",
                return_value=[{"ModID": "missing.mod", "CategoryNo": 1, "Slot": 2}],
            ):
                dependencies = resolve_card_dependencies("test.png", db_path=db_path)

            assert len(dependencies) == 1
            assert dependencies[0]["mod_id"] == "missing.mod"
        finally:
            writer.rollback()
            writer.close()
