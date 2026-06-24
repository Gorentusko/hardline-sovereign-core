# Product Spec: Hardline Sovereign Core v0.1

## One-line description

Hardline Sovereign Core is a Docker-deployable AI-native workspace for tasks, artifacts, memory, approvals, and append-only execution history.

## Scope

v0.1 proves the core loop:

```text
create task -> run mock agent -> create artifact -> create memory -> queue approval -> write ledger event
```

## In scope

- Docker Compose app
- FastAPI backend
- built-in dashboard
- SQLite
- local object store
- JSONL ledger
- mock agent runner
- tasks
- runs
- artifacts
- memory
- approvals
- package export
- tests

## Out of scope

- real AI providers
- paid API calls
- real external writes
- full Git hosting
- full file sync
- multi-user enterprise auth
- Proxmox-specific behavior
- AGI/autonomous claims
