from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import ensure_data_dirs, settings
from app.db import get_conn, rows_to_dicts


ZERO_HASH = "0" * 64


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _sha(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _last_hash() -> str:
    if not settings.ledger_path.exists():
        return ZERO_HASH
    last = ZERO_HASH
    for line in settings.ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            last = json.loads(line)["event_hash"]
        except Exception:
            continue
    return last


def append_event(
    event_type: str,
    actor: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_data_dirs()
    payload = payload or {}
    previous = _last_hash()
    event = {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": event_type,
        "actor": actor,
        "target_type": target_type,
        "target_id": target_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload_hash": _sha(_canonical(payload)),
        "previous_event_hash": previous,
    }
    event["event_hash"] = _sha(_canonical(event))
    with settings.ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(_canonical(event) + "\n")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO ledger_events
            (event_id, event_type, actor, target_type, target_id, timestamp, payload_hash, previous_event_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["event_type"],
                event["actor"],
                event["target_type"],
                event["target_id"],
                event["timestamp"],
                event["payload_hash"],
                event["previous_event_hash"],
                event["event_hash"],
            ),
        )
    return event


def list_events(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ledger_events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


def verify_ledger() -> dict[str, Any]:
    ensure_data_dirs()
    if not settings.ledger_path.exists():
        return {"valid": True, "events": 0, "reason": "ledger is empty"}

    previous = ZERO_HASH
    count = 0
    for line in settings.ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        expected_previous = event.get("previous_event_hash")
        if expected_previous != previous:
            return {
                "valid": False,
                "events_checked": count,
                "reason": "previous hash mismatch",
                "event_id": event.get("event_id"),
            }
        event_hash = event.pop("event_hash")
        recomputed = _sha(_canonical(event))
        if event_hash != recomputed:
            return {
                "valid": False,
                "events_checked": count,
                "reason": "event hash mismatch",
                "event_id": event.get("event_id"),
            }
        previous = event_hash
        count += 1

    return {"valid": True, "events": count, "tip_hash": previous}
