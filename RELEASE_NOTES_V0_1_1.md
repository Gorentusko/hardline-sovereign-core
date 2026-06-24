# Release Notes — v0.1.1 (Dashboard + Demo Polish)

## Summary

v0.1.1 polishes the v0.1 MVP into a clean, public-safe, Docker-deployable
release candidate. No new product features, providers, or external write
paths were added. This release focuses on stats/observability, a usable
dashboard, demo ergonomics, and a stability fix.

## Added

- `GET /api/stats` — single endpoint with counts for tasks, runs,
  artifacts, memory, approvals (total/pending), packages, and ledger
  validity.
- `POST /api/demo/seed` — creates one safe, deterministic, offline demo
  task for quick walkthroughs.
- `GET /api/packages` — lists exported packages from `/data/exports`.
- `GET /api/packages/{name}` — downloads a single export. Filenames are
  validated (must be a bare name, must end in `.tar.gz`, must resolve
  inside `/data/exports`) to reject path traversal.

## Changed

- Dashboard rebuilt with: live status cards (Tasks, Runs, Artifacts,
  Memory, Pending approvals, Ledger validity), one-click Create demo
  task / Run newest task / Verify ledger / Export package buttons, a
  readable ledger viewer, a memory viewer, an inline artifact preview,
  and a downloadable packages list.
- Test suite expanded to cover the new endpoints, package download
  safety, and the full task -> run -> artifact -> memory -> approval ->
  ledger flow end to end.
- README and reviewer docs rewritten to reflect the above and to state
  clearly what this project is and is not.

## Fixed

- **SQLite connection leak.** `app/db.py:get_conn()` is now a proper
  context manager: it commits on success, rolls back and re-raises on
  exception, and always closes the underlying connection in a `finally`
  block. Previously, relying on `sqlite3.Connection`'s built-in
  `__exit__` left every request's connection open. API behavior is
  unchanged; all existing call sites (`with get_conn() as conn:`)
  required no modification. Two regression tests were added to lock in
  this behavior for both the success and exception paths, plus an
  end-to-end test exercising the real 404 path through the API.

## Verified before this release

- `pytest`: 12/12 tests passing (per independent review).
- `py_compile` clean across all modules.
- Package export / list / download, including path-traversal rejection,
  covered by tests.
- `docker compose up --build` starts the app and serves the dashboard at
  `http://localhost:8099`.

## Explicitly not in this release

- No paid AI calls.
- No OpenRouter integration.
- No live writes to GitHub, Gitea, BookStack, or Nextcloud. Connector
  endpoints remain mock-status / dry-run only.
- No new authentication, RBAC, or multi-tenant model.

## Known issues carried forward

- Each API request still opens and closes its own SQLite connection
  (no pooling). This is acceptable at MVP/demo scale but should be
  revisited if concurrent load increases.
- No structured logging or metrics beyond `/api/stats` and the ledger.
- No automated CI workflow is bundled yet (tests are run manually via
  `pytest`).
