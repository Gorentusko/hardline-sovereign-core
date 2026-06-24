# Release Notes — v0.1.2 (Public Preflight / Hardening Pass)

## Summary

v0.1.2 is a hardening and honesty pass on top of v0.1.1. No new product
features were added. The goal is a clean, testable, GitHub-ready
repository that doesn't overclaim what has actually been verified.

## Fixed

- **Truthful release checklist.** `PUBLIC_RELEASE_CHECKLIST.md` no
  longer claims Docker was verified in an environment where it wasn't
  actually run. Every item is now labeled `[TEST]`, `[STATIC]`, or
  `[PENDING]` so it's clear what was checked by an automated test, what
  was checked by reading the code, and what still needs a live local
  smoke test before publishing.
- **FastAPI startup deprecation.** `@app.on_event("startup")` was
  replaced with a `lifespan` async context manager in `app/main.py`.
  Behavior is identical (ensure data dirs exist, open/close one
  connection to apply the schema) — only the registration mechanism
  changed.
- **Dead auth config removed.** `SOVEREIGN_AUTH_TOKEN` existed in
  `app/config.py` and `.env.example` but was never read or enforced
  anywhere — it looked like security but did nothing. It has been
  removed entirely. `SECURITY.md` and `.env.example` now state plainly
  that v0.1.2 has no authentication layer and is intended for
  `localhost` / a trusted private network only, not the public
  internet. Real auth is left for a future version rather than faked
  now.
- **Package export correctness.**
  - Intermediate JSON files (manifest + per-table dumps) are now
    written to a `tempfile.TemporaryDirectory`, which is removed
    automatically when the export finishes, instead of accumulating
    forever under `/data/temp`.
  - Export filenames now include a short random suffix in addition to
    the second-resolution timestamp
    (`sovereign_export_<timestamp>_<8 hex chars>.tar.gz`), so two
    exports started in the same second can no longer collide.
  - The `package.exported` ledger event is appended *after* the archive
    is written (it has to be — the event references the finished
    archive's filename). This means that specific event is not present
    inside the `ledger/events.jsonl` or `db/ledger_events.json` copied
    into that same archive. This was already true in v0.1.1 but was
    undocumented; v0.1.2 states it explicitly in the export's own
    `manifest.json` and here, rather than leaving it as a silent gap.

## Added

- `.github/workflows/ci.yml` — installs `requirements.txt` and
  `requirements-dev.txt`, then runs `python -m py_compile` and
  `pytest -v` on every push and pull request to `main`.
- `scripts/smoke_test.sh` — black-box smoke test against a running
  instance: `/health`, `/ready`, `/api/stats`, `/api/demo/seed`, run the
  newest task, `/api/ledger/verify`. Exits non-zero on any failure.
- `scripts/smoke_test.ps1` — PowerShell equivalent for Windows.
- `pyproject.toml` — minimal project metadata, `[tool.pytest.ini_options]`
  pointing at `tests/`, and an optional `[tool.ruff]` config (line
  length 110, `E`/`F`/`I` rule sets). Ruff itself is not run in CI in
  this release — the config is provided for local use but hasn't been
  exercised against the full codebase in this environment, so it isn't
  presented as a verified "lint-clean" guarantee.
- Three new regression tests covering: package export temp-file
  cleanup, collision-resistant export filenames, and that the removed
  auth-token setting is fully gone (no `SOVEREIGN_AUTH_TOKEN` attribute
  on `Settings`, no reference in `.env.example`).

## Explicitly not in this release

- No paid AI calls.
- No OpenRouter integration.
- No live writes to GitHub, Gitea, BookStack, or Nextcloud.
- No real authentication (see "Fixed" above — this is intentional and
  documented, not an oversight).
- No autonomous remediation, no multi-agent swarm behavior.
- No big new product features — this release is a hardening pass only.

## Known issues / pending verification

- **Docker has not yet been run against this codebase, by anyone, in
  any environment.** `python -m py_compile` passed, the `pytest` suite
  passed (15 tests), and a live local Uvicorn smoke test using
  `scripts/smoke_test.sh` passed (6 checks, 0 failures) during external
  review of the `v0.1.2-public-preflight` build of this codebase. This
  `fix1` package only changes documentation (this file and
  `PUBLIC_RELEASE_CHECKLIST.md`) — the application code is identical, so
  those results still apply, but none of them exercise the `Dockerfile`
  or `docker-compose.yml` build path. `docker compose up --build`
  followed by `scripts/smoke_test.sh` against the running container is
  still the final pending gate before this is published — see
  `PUBLIC_RELEASE_CHECKLIST.md`.
- Each API request still opens and closes its own SQLite connection (no
  pooling). Acceptable at MVP/demo scale.
- No structured logging or metrics beyond `/api/stats` and the ledger.
- `ruff` config exists but has not been run against the codebase in
  this environment — treat it as a starting point, not a clean-lint
  guarantee.
- Still local-first, single-tenant, no RBAC, no authentication — by
  design for this version, see `SECURITY.md`.

See also: `RELEASE_NOTES_V0_1_1.md` for the prior release's changes.
