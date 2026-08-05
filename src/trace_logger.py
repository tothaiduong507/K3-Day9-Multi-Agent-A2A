"""JSONL trace cho handoff giữa các agent."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def reset(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def emit(
        self,
        *,
        case_id: str,
        agent: str,
        event: str,
        status: str = "success",
        details: dict[str, Any] | None = None,
        handoff_to: str | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "agent": agent,
            "event": event,
            "status": status,
            "details": details or {},
            "handoff_to": handoff_to,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

