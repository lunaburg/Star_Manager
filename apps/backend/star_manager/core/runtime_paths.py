from __future__ import annotations

import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def runtime_root() -> Path:
    configured = os.environ.get("STAR_MANAGER_RUNTIME_DIR", "").strip()
    if configured:
        return Path(configured)
    return BACKEND_ROOT / "runtime"
