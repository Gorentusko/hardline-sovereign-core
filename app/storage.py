from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import ensure_data_dirs, settings


def write_object(content: bytes) -> tuple[str, Path]:
    ensure_data_dirs()
    digest = hashlib.sha256(content).hexdigest()
    obj_dir = settings.objects_path / digest[:2]
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj_path = obj_dir / digest
    if not obj_path.exists():
        obj_path.write_bytes(content)
    return digest, obj_path


def read_object(path: str) -> bytes:
    return Path(path).read_bytes()
