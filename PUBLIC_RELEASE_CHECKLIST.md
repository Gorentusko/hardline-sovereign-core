# Public Release Checklist — v0.1.2

This checklist documents the safety/cleanliness review performed before
publishing this repository publicly (e.g., to GitHub). Each item is
labeled with how it was actually verified, so this document doesn't
overclaim what was or wasn't run.

Legend:

- **[TEST]** — covered by an automated `pytest` test in this repo.
- **[STATIC]** — verified by reading the code/config/files directly
  (grep, manual inspection, `py_compile`), not by executing the app.
- **[PENDING]** — not yet verified in this environment; must be checked
  once before publishing.

## Identity

- [STATIC] Repo folder is named `hardline-sovereign-core`.
- [STATIC] Version is `0.1.2` (`manifest.json`, `README.md`,
  `pyproject.toml`).
- [STATIC] Project is described accurately as a local-first MVP — not
  AGI, not autonomous remediation, not production-hardened software
  (`README.md`, `SECURITY.md`, `PRODUCT_SPEC.md`).

## No secrets or environment leakage

- [STATIC] No `.env` file is included in the package (only
  `.env.example`, which contains no token/secret values).
- [STATIC] `.gitignore` excludes `.env`, `*.db`, `*.sqlite`, `data/`,
  `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`.
- [STATIC] No API keys, tokens, passwords, or credentials appear
  anywhere in source, docs, or config files.
- [STATIC] The previously-present `SOVEREIGN_AUTH_TOKEN` setting has
  been removed entirely (it was unused dead config, not real
  protection). The app has no auth layer; this is documented in
  `SECURITY.md` and `.env.example`, not hidden.

## No runtime data leakage

- [STATIC] No `data/` directory is included (no SQLite DB, no object
  store contents, no ledger events from any prior run).
- [STATIC] No `*.db`, `*.sqlite`, `*.tar.gz`, or `events.jsonl` files are
  present in the package.
- [STATIC] No `__pycache__/` or `*.pyc` files are present in the
  package.
- [TEST] Package export no longer leaves stray intermediate JSON files
  under `/data/temp` — it uses `tempfile.TemporaryDirectory`, which is
  removed automatically when the export finishes.

## No private infrastructure or customer data

- [STATIC] No private/internal domain names.
- [STATIC] No LAN or private IP addresses (checked for
  `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x` patterns).
- [STATIC] No Proxmox container/VM IDs or host-specific infrastructure
  details. Proxmox is only referenced generically as something the core
  intentionally does **not** depend on.
- [STATIC] No customer names, customer data, or third-party confidential
  information anywhere in code, tests, or docs.

## Safety defaults (verified in code, not just docs)

- [STATIC] No paid AI calls — the only agent implementation is the
  deterministic, offline `app/agent.py:run_mock_agent`.
- [STATIC] No OpenRouter integration present.
- [STATIC] No live write paths to GitHub, Gitea, BookStack, or
  Nextcloud. `/api/connectors/*` endpoints are status/dry-run only and
  never perform an external network call.
- [STATIC] `SOVEREIGN_ALLOW_EXTERNAL_CONNECTORS` defaults to `false`.
- [STATIC] No authentication layer exists; this is documented
  truthfully rather than implied via dead config (`SECURITY.md`).

## Functional verification

- [TEST] `pytest` test suite covers: health/ready, `/api/stats`,
  `/api/demo/seed`, full task -> run -> artifact -> memory -> approval ->
  ledger flow, approval reject path, package export/list/download,
  path-traversal rejection, export temp-file cleanup and collision-safe
  naming, and the SQLite connection-leak fix (success and exception
  paths). **Confirmed by external review: 15/15 tests passed**, against
  the `hardline-sovereign-core-v0.1.2-public-preflight.zip` build of
  this codebase. This `fix1` package changes two documentation files
  only (see `RELEASE_NOTES_V0_1_2.md`) — the application code, and
  therefore this test result, is unchanged.
- [STATIC] `python -m py_compile` passes across all modules.
  **Confirmed by external review**, same package/lineage as above.
- [TEST] `scripts/smoke_test.sh` run against a locally-started Uvicorn
  instance (not a Docker container). **Confirmed by external review:
  6/6 checks passed, 0 failures**, same package/lineage as above.
- [STATIC] `@app.on_event("startup")` has been replaced with a FastAPI
  `lifespan` handler; reviewed by reading the code, not by capturing
  live deprecation-warning output.
- [PENDING] **`docker compose up --build` has not been executed against
  this codebase, in any environment, by anyone, yet.** Every environment
  that has touched this project so far (the one that produced it and
  the one that ran the pytest/py_compile/Uvicorn-smoke checks above)
  lacked Docker. The `Dockerfile` and `docker-compose.yml` were reviewed
  by hand for correctness (base image, `COPY`/`CMD`, port `8099`,
  `/data` volume), but that is static review, not a build-and-run test.
- [PENDING] `scripts/smoke_test.sh` run **against a Docker container**
  specifically has not been executed. The Uvicorn-based run above is a
  good signal but is not equivalent to testing the actual Docker image.

## Documentation

- [STATIC] `README.md` states what the project is and is not,
  quickstart, demo flow, API surface, safety defaults, and roadmap.
- [STATIC] `docs/REVIEWER_DEMO.md` gives a step-by-step reviewer
  walkthrough.
- [STATIC] `docs/API_EXAMPLES.md` gives curl examples for the full API.
- [STATIC] `RELEASE_NOTES_V0_1_1.md` and `RELEASE_NOTES_V0_1_2.md`
  document what changed in each release.
- [STATIC] `SECURITY.md` and `ARCHITECTURE.md` are present and accurate,
  including the no-auth/local-only statement.

## What "release-ready" means right now

Python-level testing is in good shape: `py_compile`, `pytest` (15/15),
and a Uvicorn-based smoke test (6/6) have all passed on this exact
package. The one thing nobody has actually done yet, in any
environment, for this specific package is a live
`docker compose up --build` followed by `scripts/smoke_test.sh` against
the resulting container. Do that once, locally, before pushing to
GitHub. If it passes, this package is ready to publish.

## Sign-off

This checklist was completed as part of preparing
`hardline-sovereign-core-v0.1.2-public-preflight.zip`. No new product
features were added during this pass — it is a hardening, honesty, and
packaging pass on top of the `v0.1.1` release.
