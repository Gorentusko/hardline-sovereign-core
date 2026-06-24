# Reviewer Demo

This walkthrough exercises the full local loop: task -> run -> artifact ->
memory -> approval -> ledger proof -> package export. Everything runs
offline against the bundled mock agent. No external network calls, no paid
AI calls, and no writes to GitHub/Gitea/BookStack/Nextcloud occur anywhere
in this flow.

## 1. Run it

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8099
```

## 2. Walk the demo flow

1. Click **Create demo task** (or fill in the form and click **Create task**).
2. Click **Run newest task** — this runs the mock/offline agent, which
   creates a run, an artifact, a memory entry, and a pending approval.
3. Check the **Status overview** cards at the top: Tasks, Runs, Artifacts,
   Memory, Pending approvals, and Ledger valid should all update.
4. Open the new artifact from the **Artifacts** card (inline preview or the
   "open" link) and confirm it contains the mock agent output.
5. Approve or reject the item in the **Approvals** card.
6. Click **Verify ledger** and confirm `valid: true`.
7. Scroll the **Ledger** card to see the append-only event history
   (`task.created`, `run.completed`, `artifact.created`, `memory.created`,
   `approval.created`, `approval.approved`/`approval.rejected`).
8. Click **Export package** and confirm it appears in the **Exported
   packages** card with a working download link.

## 3. Verify from the API directly (optional)

```bash
curl http://localhost:8099/api/stats
curl -X POST http://localhost:8099/api/demo/seed
curl http://localhost:8099/api/ledger/verify
curl http://localhost:8099/api/packages
```

## What this proves

- Docker deployment via `docker compose up --build`
- FastAPI JSON API surface
- SQLite metadata model
- local content-addressed object storage under `/data/objects`
- append-only, hash-chained ledger under `/data/ledger/events.jsonl`
- approval gate before any artifact would be considered "published"
- deterministic mock agent workflow with no paid AI calls
- safe, validated package export/listing/download under `/data/exports`

## What this does NOT prove

- It does not call any paid AI provider or OpenRouter.
- It does not write to any external system (GitHub, Gitea, BookStack,
  Nextcloud). Connector endpoints are mock/dry-run only.
- It is not a production-hardened, multi-tenant, or autonomous system.
