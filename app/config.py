from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = "Hardline Sovereign Core"
    host: str = os.getenv("SOVEREIGN_HOST", "0.0.0.0")
    port: int = int(os.getenv("SOVEREIGN_PORT", "8099"))
    data_dir: str = os.getenv("SOVEREIGN_DATA_DIR", "/data")
    agent_provider: str = os.getenv("SOVEREIGN_AGENT_PROVIDER", "mock")
    allow_external_connectors: bool = env_bool("SOVEREIGN_ALLOW_EXTERNAL_CONNECTORS", False)

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def db_path(self) -> Path:
        return self.data_path / "sovereign.db"

    @property
    def objects_path(self) -> Path:
        return self.data_path / "objects"

    @property
    def ledger_path(self) -> Path:
        return self.data_path / "ledger" / "events.jsonl"

    @property
    def exports_path(self) -> Path:
        return self.data_path / "exports"


settings = Settings()


def ensure_data_dirs() -> None:
    for path in [
        settings.data_path,
        settings.objects_path,
        settings.ledger_path.parent,
        settings.exports_path,
        settings.data_path / "imports",
    ]:
        path.mkdir(parents=True, exist_ok=True)
