from __future__ import annotations

from datetime import datetime, timezone


def run_mock_agent(task: dict) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return f"""# Mock Agent Output

Generated UTC: `{now}`

## Task

**{task["title"]}**

{task.get("description", "")}

## Analysis

This is a deterministic mock agent run. No paid AI call was made.

## Suggested next steps

1. Review the task description.
2. Confirm whether the generated artifact is useful.
3. Approve or reject the approval item.
4. Export the package if this state should be shared.

## Safety

No external write was performed.
"""
