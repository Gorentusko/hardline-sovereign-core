# Architecture

```text
+------------------------------------------------------+
| Hardline Sovereign Core                              |
|                                                      |
|  FastAPI API + Dashboard                             |
|  SQLite WAL Database                                 |
|  Local Object Store /data/objects                    |
|  JSONL Event Ledger /data/ledger/events.jsonl        |
|  Mock Agent Runner                                   |
|  Approval Queue                                      |
|                                                      |
+------------------------------------------------------+
```

## Design rule

The core must run without BookStack, Gitea, Nextcloud, OpenRouter, or Proxmox.

Those systems can become optional connectors later.
