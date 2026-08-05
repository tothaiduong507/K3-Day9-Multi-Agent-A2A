"""Atomic serialization of verifier-approved case outputs."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.models import FinalCaseOutput
from src.utils.decimal_utils import round_brl


class OutputWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)

    def write(self, case_id: str, output: FinalCaseOutput) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / f"{case_id}.json"
        temporary = self.output_dir / f".{case_id}.json.tmp"
        content = json.dumps(
            self._normalize(output),
            ensure_ascii=False,
            indent=2,
        )
        temporary.write_text(content + "\n", encoding="utf-8")
        temporary.replace(target)
        return target

    @classmethod
    def _normalize(cls, value: Any, field_name: str | None = None) -> Any:
        if isinstance(value, dict):
            return {key: cls._normalize(item, key) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._normalize(item, field_name) for item in value]
        if isinstance(value, Decimal):
            normalized = (
                round_brl(value)
                if field_name and field_name.endswith("_brl")
                else value
            )
            return float(normalized)
        return value
