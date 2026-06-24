# Security

Hardline Sovereign Core v0.1 is local-first and safe by default.

## Defaults

- Mock agent only.
- No paid AI calls.
- No bundled secrets.
- No external writes.
- No destructive actions.
- Approval gates before publish-style workflows.

## Authentication

Hardline Sovereign Core v0.1.2 has **no authentication layer**. There is
no token, password, or session model protecting any endpoint. It is
designed to run on `localhost` or inside a trusted private network only.

**Do not expose this service directly to the public internet.** If you
need remote access, put it behind a VPN, SSH tunnel, or a reverse proxy
that you control and that handles authentication itself. Optional
bearer-token or other auth may be added in a future version — it is not
in v0.1.2.

## Secrets

Do not commit `.env`, tokens, customer data, private domains, or private infrastructure paths.

## Production status

v0.1 is a portfolio/developer MVP. It is not production hardened.
