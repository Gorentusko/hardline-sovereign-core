# API Examples

All examples assume the app is running locally on port 8099
(`docker compose up --build`, then `http://localhost:8099`).

## Stats

```bash
curl http://localhost:8099/api/stats
```

Returns counts for tasks, runs, artifacts, memory, approvals (total and
pending), exported packages, and ledger verification status.

## Demo seed

```bash
curl -X POST http://localhost:8099/api/demo/seed
```

Creates one safe, offline demo task. No external calls are made.

## Create task

```bash
curl -X POST http://localhost:8099/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Review demo state","description":"Create artifact","priority":"normal"}'
```

## List tasks

```bash
curl http://localhost:8099/api/tasks
```

## Run newest task (mock agent)

```bash
TASK_ID=$(curl -s http://localhost:8099/api/tasks | python3 -c "import sys,json; print(json.load(sys.stdin)['tasks'][0]['id'])")
curl -X POST http://localhost:8099/api/tasks/$TASK_ID/run
```

## Approve / reject

```bash
curl -X POST http://localhost:8099/api/approvals/<approval_id>/approve
curl -X POST http://localhost:8099/api/approvals/<approval_id>/reject
```

## Verify ledger

```bash
curl http://localhost:8099/api/ledger/verify
```

## Export, list, and download packages

```bash
curl -X POST http://localhost:8099/api/packages/export
curl http://localhost:8099/api/packages
curl -OJ http://localhost:8099/api/packages/<package_name>.tar.gz
```

The download endpoint only accepts plain filenames ending in `.tar.gz` that
exist inside `/data/exports`; path traversal attempts are rejected with a
400 response.
