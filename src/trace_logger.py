"""JSONL trace cho handoff giữa các agent."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any


class TraceLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
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
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(record, ensure_ascii=False, default=self._json_default)
                    + "\n"
                )

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, Decimal):
            return str(value)
        raise TypeError(f"Cannot serialize {type(value).__name__} in trace")

