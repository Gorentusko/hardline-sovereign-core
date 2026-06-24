import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def set_data_dir(tmp_path: Path):
    settings.data_dir = str(tmp_path)


def test_health(tmp_path):
    set_data_dir(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready(tmp_path):
    set_data_dir(tmp_path)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_stats_empty(tmp_path):
    set_data_dir(tmp_path)
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["tasks"] == 0
    assert data["runs"] == 0
    assert data["artifacts"] == 0
    assert data["memory"] == 0
    assert data["approvals"] == {"total": 0, "pending": 0}
    assert data["ledger"]["valid"] is True


def test_demo_seed(tmp_path):
    set_data_dir(tmp_path)
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "seeded"
    assert body["task_id"].startswith("task_")

    tasks = client.get("/api/tasks").json()["tasks"]
    assert any(t["id"] == body["task_id"] for t in tasks)

    stats = client.get("/api/stats").json()
    assert stats["tasks"] == 1


def test_task_run_artifact_approval_ledger(tmp_path):
    set_data_dir(tmp_path)

    created = client.post(
        "/api/tasks",
        json={"title": "Test task", "description": "demo", "priority": "normal"},
    ).json()
    task_id = created["task_id"]

    run = client.post(f"/api/tasks/{task_id}/run").json()
    assert run["status"] == "success"

    artifact_id = run["artifact_id"]
    content = client.get(f"/api/artifacts/{artifact_id}/content")
    assert content.status_code == 200
    assert "Mock Agent Output" in content.text

    memory = client.get("/api/memory").json()["memory"]
    assert any(m["id"] == run["memory_id"] for m in memory)

    approvals = client.get("/api/approvals").json()["approvals"]
    assert approvals
    approval_id = approvals[0]["id"]
    decided = client.post(f"/api/approvals/{approval_id}/approve").json()
    assert decided["status"] == "approved"

    verify = client.get("/api/ledger/verify").json()
    assert verify["valid"] is True

    stats = client.get("/api/stats").json()
    assert stats["tasks"] == 1
    assert stats["runs"] == 1
    assert stats["artifacts"] == 1
    assert stats["memory"] == 1
    assert stats["approvals"]["total"] == 1
    assert stats["approvals"]["pending"] == 0
    assert stats["ledger"]["valid"] is True


def test_approval_reject_flow(tmp_path):
    set_data_dir(tmp_path)
    created = client.post(
        "/api/tasks",
        json={"title": "Reject me", "description": "", "priority": "low"},
    ).json()
    run = client.post(f"/api/tasks/{created['task_id']}/run").json()
    approvals = client.get("/api/approvals").json()["approvals"]
    pending = [a for a in approvals if a["status"] == "pending"]
    assert pending
    decided = client.post(f"/api/approvals/{pending[0]['id']}/reject").json()
    assert decided["status"] == "rejected"


def test_package_export_listing_and_download(tmp_path):
    set_data_dir(tmp_path)
    client.post("/api/tasks", json={"title": "Export task", "description": "", "priority": "normal"})

    exported = client.post("/api/packages/export").json()
    assert exported["status"] == "exported"
    assert Path(exported["path"]).exists()

    listing = client.get("/api/packages").json()
    assert listing["packages"]
    names = [p["name"] for p in listing["packages"]]
    assert exported["name"] in names

    download = client.get(f"/api/packages/{exported['name']}")
    assert download.status_code == 200
    assert download.headers["content-type"] in ("application/gzip", "application/x-gzip")


def test_package_download_rejects_path_traversal(tmp_path):
    set_data_dir(tmp_path)
    client.post("/api/packages/export")

    traversal = client.get("/api/packages/..%2F..%2Fapp%2Fmain.py")
    assert traversal.status_code in (400, 404)

    missing = client.get("/api/packages/does-not-exist.tar.gz")
    assert missing.status_code == 404

    bad_extension = client.get("/api/packages/notes.txt")
    assert bad_extension.status_code == 400


def test_full_demo_flow_end_to_end(tmp_path):
    set_data_dir(tmp_path)

    seeded = client.post("/api/demo/seed").json()
    task_id = seeded["task_id"]

    run = client.post(f"/api/tasks/{task_id}/run").json()
    assert run["status"] == "success"

    artifact = client.get(f"/api/artifacts/{run['artifact_id']}").json()["artifact"]
    assert artifact["sha256"]

    memory = client.get("/api/memory").json()["memory"]
    assert memory

    approvals = client.get("/api/approvals").json()["approvals"]
    pending = [a for a in approvals if a["status"] == "pending"]
    assert pending
    client.post(f"/api/approvals/{pending[0]['id']}/approve")

    verify = client.get("/api/ledger/verify").json()
    assert verify["valid"] is True

    exported = client.post("/api/packages/export").json()
    assert exported["status"] == "exported"

    stats = client.get("/api/stats").json()
    assert stats["tasks"] == 1
    assert stats["packages"] == 1


def test_get_conn_closes_connection_on_success(tmp_path):
    """Regression test for the v0.1 connection leak.

    app.db.get_conn() must close the underlying sqlite3 connection after a
    successful `with` block, not just commit. We open it manually here
    (bypassing the API) and assert the connection is unusable afterward.
    """
    set_data_dir(tmp_path)
    from app.db import get_conn

    with get_conn() as conn:
        conn.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_get_conn_closes_connection_on_exception(tmp_path):
    """The connection must also be closed (after rollback) when the with
    block raises, e.g. a 404 raised mid-transaction in an API handler."""
    set_data_dir(tmp_path)
    from app.db import get_conn

    captured = {}
    with pytest.raises(ValueError):
        with get_conn() as conn:
            captured["conn"] = conn
            raise ValueError("boom")

    with pytest.raises(sqlite3.ProgrammingError):
        captured["conn"].execute("SELECT 1")


def test_decide_approval_404_still_rolls_back_and_closes(tmp_path):
    """End-to-end check that a 404 raised inside a get_conn() block (as in
    decide_approval) still returns a clean 404 and does not leave a stuck
    transaction or unclosed connection behind."""
    set_data_dir(tmp_path)
    response = client.post("/api/approvals/does-not-exist/approve")
    assert response.status_code == 404

    # The DB must still be fully usable afterward (no leaked/broken connection).
    stats = client.get("/api/stats").json()
    assert stats["tasks"] == 0


def test_package_export_does_not_leave_temp_files_behind(tmp_path):
    """Regression test: export_package must not leave intermediate JSON
    files (manifest_*.json, <table>_*.json) sitting under /data/temp
    forever. It should use a TemporaryDirectory that is cleaned up."""
    set_data_dir(tmp_path)
    client.post("/api/tasks", json={"title": "Temp cleanup check", "description": "", "priority": "normal"})

    exported = client.post("/api/packages/export").json()
    assert exported["status"] == "exported"

    temp_dir = tmp_path / "temp"
    if temp_dir.exists():
        leftover = list(temp_dir.glob("*.json"))
        assert leftover == [], f"export left temp files behind: {leftover}"

    # The archive itself should still contain the expected contents.
    import tarfile

    with tarfile.open(exported["path"]) as tar:
        names = tar.getnames()
    assert "manifest.json" in names
    assert "db/tasks.json" in names
    assert "ledger/events.jsonl" in names


def test_package_export_filenames_are_collision_resistant(tmp_path):
    """Two exports triggered back-to-back (potentially within the same
    second) must not produce colliding filenames."""
    set_data_dir(tmp_path)
    client.post("/api/tasks", json={"title": "Collision check", "description": "", "priority": "normal"})

    first = client.post("/api/packages/export").json()
    second = client.post("/api/packages/export").json()

    assert first["name"] != second["name"]
    assert Path(first["path"]).exists()
    assert Path(second["path"]).exists()

    listing = client.get("/api/packages").json()["packages"]
    names = {p["name"] for p in listing}
    assert first["name"] in names
    assert second["name"] in names


def test_no_dead_auth_token_config(tmp_path):
    """Regression test for the removed SOVEREIGN_AUTH_TOKEN dead config.

    There should be no auth_token attribute on Settings, and no
    SOVEREIGN_AUTH_TOKEN reference in .env.example, so a reader can't be
    misled into thinking there is real auth protection."""
    set_data_dir(tmp_path)
    assert not hasattr(settings, "auth_token")

    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    contents = env_example.read_text(encoding="utf-8")
    assert "SOVEREIGN_AUTH_TOKEN" not in contents
