from __future__ import annotations

import json
import tarfile
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.agent import run_mock_agent
from app.config import ensure_data_dirs, settings
from app.db import get_conn, rows_to_dicts
from app.ledger import append_event, list_events, verify_ledger
from app.storage import read_object, write_object
from app.ui import dashboard_html


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: make sure the data directories and schema exist before the
    # app starts accepting requests.
    ensure_data_dirs()
    with get_conn():
        pass
    yield
    # No shutdown work needed: get_conn() already closes every connection
    # it opens, and the ledger/object store are plain files on disk.


app = FastAPI(title=settings.app_name, lifespan=lifespan)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    priority: str = "normal"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


class MemoryCreate(BaseModel):
    scope: str = "global"
    title: str
    body: str
    tags: list[str] = []


@app.get("/", response_class=HTMLResponse)
def root():
    return dashboard_html()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "agent_provider": settings.agent_provider,
        "external_connectors_allowed": settings.allow_external_connectors,
    }


@app.get("/ready")
def ready():
    ensure_data_dirs()
    return {
        "ready": True,
        "db": str(settings.db_path),
        "objects": str(settings.objects_path),
        "ledger": str(settings.ledger_path),
    }


@app.get("/api/tasks")
def list_tasks():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    return {"tasks": rows_to_dicts(rows)}


@app.post("/api/tasks")
def create_task(payload: TaskCreate):
    task_id = new_id("task")
    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, 'open', ?, ?, ?)
            """,
            (task_id, payload.title, payload.description, payload.priority, now, now),
        )
    append_event("task.created", "user", "task", task_id, payload.model_dump())
    return {"status": "created", "task_id": task_id}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task": dict(row)}


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no_change", "task_id": task_id}
    updates["updated_at"] = utc_now()
    columns = ", ".join([f"{k}=?" for k in updates])
    values = list(updates.values()) + [task_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {columns} WHERE id = ?", values)
    append_event("task.updated", "user", "task", task_id, updates)
    return {"status": "updated", "task_id": task_id}


@app.post("/api/tasks/{task_id}/run")
def run_task(task_id: str):
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    task_dict = dict(task)
    run_id = new_id("run")
    artifact_id = new_id("artifact")
    memory_id = new_id("mem")
    approval_id = new_id("approval")
    started = utc_now()

    output = run_mock_agent(task_dict)
    content = output.encode("utf-8")
    digest, object_path = write_object(content)
    finished = utc_now()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (id, task_id, runner, status, started_at, finished_at, summary) VALUES (?, ?, ?, 'success', ?, ?, ?)",
            (run_id, task_id, settings.agent_provider, started, finished, "Mock agent generated artifact and approval item."),
        )
        conn.execute(
            """
            INSERT INTO artifacts (id, run_id, kind, name, sha256, size_bytes, content_type, object_path, source, created_at)
            VALUES (?, ?, 'markdown', ?, ?, ?, 'text/markdown', ?, 'run', ?)
            """,
            (artifact_id, run_id, f"{task_id}_mock_agent_output.md", digest, len(content), str(object_path), finished),
        )
        conn.execute(
            """
            INSERT INTO memory_entries (id, scope, title, body, tags, source_artifact_id, created_at)
            VALUES (?, 'task', ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                f"Memory from {task_dict['title']}",
                f"Mock agent completed task {task_id} and created artifact {artifact_id}.",
                json.dumps(["mock-agent", "task-output"]),
                artifact_id,
                finished,
            ),
        )
        conn.execute(
            """
            INSERT INTO approvals (id, target_type, target_id, status, reason, created_at)
            VALUES (?, 'artifact', ?, 'pending', 'Review generated artifact before publishing or exporting.', ?)
            """,
            (approval_id, artifact_id, finished),
        )
        conn.execute("UPDATE tasks SET status='done', updated_at=? WHERE id=?", (finished, task_id))

    append_event("run.completed", "agent:mock", "run", run_id, {"task_id": task_id, "artifact_id": artifact_id})
    append_event("artifact.created", "agent:mock", "artifact", artifact_id, {"sha256": digest, "size_bytes": len(content)})
    append_event("memory.created", "system", "memory", memory_id, {"source_artifact_id": artifact_id})
    append_event("approval.created", "system", "approval", approval_id, {"target_type": "artifact", "target_id": artifact_id})

    return {
        "status": "success",
        "task_id": task_id,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "memory_id": memory_id,
        "approval_id": approval_id,
    }


@app.get("/api/runs")
def list_runs():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY started_at DESC").fetchall()
    return {"runs": rows_to_dicts(rows)}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run": dict(row)}


@app.get("/api/artifacts")
def list_artifacts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM artifacts ORDER BY created_at DESC").fetchall()
    return {"artifacts": rows_to_dicts(rows)}


@app.get("/api/artifacts/{artifact_id}")
def get_artifact(artifact_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="artifact not found")
    return {"artifact": dict(row)}


@app.get("/api/artifacts/{artifact_id}/content", response_class=PlainTextResponse)
def get_artifact_content(artifact_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="artifact not found")
    return read_object(dict(row)["object_path"]).decode("utf-8", errors="replace")


@app.get("/api/memory")
def list_memory():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM memory_entries ORDER BY created_at DESC").fetchall()
    return {"memory": rows_to_dicts(rows)}


@app.post("/api/memory")
def create_memory(payload: MemoryCreate):
    memory_id = new_id("mem")
    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO memory_entries (id, scope, title, body, tags, source_artifact_id, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """,
            (memory_id, payload.scope, payload.title, payload.body, json.dumps(payload.tags), now),
        )
    append_event("memory.created", "user", "memory", memory_id, payload.model_dump())
    return {"status": "created", "memory_id": memory_id}


@app.get("/api/approvals")
def list_approvals():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC").fetchall()
    return {"approvals": rows_to_dicts(rows)}


def decide_approval(approval_id: str, status: str):
    now = utc_now()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="approval not found")
        conn.execute(
            "UPDATE approvals SET status=?, decided_at=? WHERE id=?",
            (status, now, approval_id),
        )
    append_event(f"approval.{status}", "user", "approval", approval_id, {})
    return {"status": status, "approval_id": approval_id}


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: str):
    return decide_approval(approval_id, "approved")


@app.post("/api/approvals/{approval_id}/reject")
def reject(approval_id: str):
    return decide_approval(approval_id, "rejected")


@app.get("/api/ledger")
def ledger():
    return {"events": list_events()}


@app.get("/api/ledger/verify")
def ledger_verify():
    return verify_ledger()


@app.get("/api/connectors")
def connectors():
    return {
        "connectors": [
            {
                "id": "mock",
                "status": "available",
                "external_write": False,
            }
        ],
        "external_connectors_allowed": settings.allow_external_connectors,
    }


@app.get("/api/connectors/mock/status")
def mock_connector_status():
    return {"id": "mock", "ready": True, "writes_enabled": False}


@app.post("/api/connectors/mock/dry-run")
def mock_connector_dry_run():
    return {
        "status": "dry_run",
        "would_write": False,
        "message": "Mock connector dry-run complete. No external write was performed.",
    }


@app.post("/api/packages/export")
def export_package():
    ensure_data_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique = uuid.uuid4().hex[:8]
    export_path = settings.exports_path / f"sovereign_export_{stamp}_{unique}.tar.gz"

    manifest = {
        "app": settings.app_name,
        "created_at": utc_now(),
        "ledger": verify_ledger(),
        "note": (
            "This manifest's ledger verification snapshot was taken before the "
            "package.exported ledger event was appended, so that event is not "
            "itself included in db/ledger_events.json or ledger/events.jsonl "
            "inside this archive. See RELEASE_NOTES for details."
        ),
    }

    # All intermediate JSON files are written to a temporary directory and
    # discarded as soon as the tarball is built, instead of being left
    # behind under /data/temp forever.
    with tempfile.TemporaryDirectory(prefix="sovereign_export_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        with tarfile.open(export_path, "w:gz") as tar:
            tar.add(manifest_file, arcname="manifest.json")
            if settings.ledger_path.exists():
                tar.add(settings.ledger_path, arcname="ledger/events.jsonl")
            with get_conn() as conn:
                for table in ["tasks", "runs", "artifacts", "memory_entries", "approvals", "ledger_events"]:
                    rows = rows_to_dicts(conn.execute(f"SELECT * FROM {table}").fetchall())
                    table_file = tmp_path / f"{table}.json"
                    table_file.write_text(json.dumps(rows, indent=2), encoding="utf-8")
                    tar.add(table_file, arcname=f"db/{table}.json")
        # tmp_dir and everything inside it is removed automatically here.

    append_event("package.exported", "user", "package", export_path.name, {"path": str(export_path)})
    return {"status": "exported", "path": str(export_path), "name": export_path.name}


@app.get("/api/packages")
def list_packages():
    ensure_data_dirs()
    packages = []
    for entry in sorted(settings.exports_path.glob("*.tar.gz"), reverse=True):
        stat = entry.stat()
        packages.append(
            {
                "name": entry.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "download_url": f"/api/packages/{entry.name}",
            }
        )
    return {"packages": packages}


@app.get("/api/packages/{name}")
def download_package(name: str):
    # Safety: only allow plain filenames inside the exports directory.
    # Reject path separators / traversal so this can never read outside /data/exports.
    if name != Path(name).name or not name.endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="invalid package name")

    ensure_data_dirs()
    candidate = (settings.exports_path / name).resolve()
    exports_root = settings.exports_path.resolve()
    if exports_root not in candidate.parents and candidate != exports_root:
        raise HTTPException(status_code=400, detail="invalid package path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="package not found")

    return FileResponse(
        path=candidate,
        media_type="application/gzip",
        filename=candidate.name,
    )


@app.get("/api/stats")
def stats():
    with get_conn() as conn:
        task_count = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        run_count = conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]
        artifact_count = conn.execute("SELECT COUNT(*) AS c FROM artifacts").fetchone()["c"]
        memory_count = conn.execute("SELECT COUNT(*) AS c FROM memory_entries").fetchone()["c"]
        approval_total = conn.execute("SELECT COUNT(*) AS c FROM approvals").fetchone()["c"]
        approval_pending = conn.execute(
            "SELECT COUNT(*) AS c FROM approvals WHERE status = 'pending'"
        ).fetchone()["c"]

    ledger_status = verify_ledger()
    package_count = len(list(settings.exports_path.glob("*.tar.gz"))) if settings.exports_path.exists() else 0

    return {
        "tasks": task_count,
        "runs": run_count,
        "artifacts": artifact_count,
        "memory": memory_count,
        "approvals": {"total": approval_total, "pending": approval_pending},
        "packages": package_count,
        "ledger": ledger_status,
    }


@app.post("/api/demo/seed")
def seed_demo_task():
    """Create one demo task using safe, deterministic, offline content.

    This never calls an external service and never triggers a paid AI call.
    """
    task_id = new_id("task")
    now = utc_now()
    title = "Demo: Sovereign Core walkthrough"
    description = (
        "Sample task created by the demo seeder. Run it with the mock agent to "
        "generate an artifact, a memory entry, and a pending approval."
    )
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, 'open', 'normal', ?, ?)
            """,
            (task_id, title, description, now, now),
        )
    append_event("task.created", "demo-seed", "task", task_id, {"title": title, "demo": True})
    return {"status": "seeded", "task_id": task_id, "title": title}
