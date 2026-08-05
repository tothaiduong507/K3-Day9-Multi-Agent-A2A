"""Discovery and validation of EC input files."""

import json
from pathlib import Path

from src.models import CaseInput


EXPECTED_CASE_IDS = tuple(f"EC_{index:03d}" for index in range(1, 51))


class CaseInputError(ValueError):
    """Raised when the case input set violates its contract."""


def discover_case_paths(input_dir: Path, case_id: str | None = None) -> list[Path]:
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise CaseInputError(f"Input directory does not exist: {input_dir}")

    if case_id:
        if case_id not in EXPECTED_CASE_IDS:
            raise CaseInputError(f"Invalid case selection: {case_id}")
        path = input_dir / f"{case_id}.json"
        if not path.is_file():
            raise CaseInputError(f"Case file does not exist: {path}")
        return [path]

    paths = sorted(input_dir.glob("EC_*.json"))
    actual = tuple(path.stem for path in paths)
    if actual != EXPECTED_CASE_IDS:
        missing = sorted(set(EXPECTED_CASE_IDS) - set(actual))
        extra = sorted(set(actual) - set(EXPECTED_CASE_IDS))
        raise CaseInputError(
            f"Expected exactly EC_001..EC_050; missing={missing}, extra={extra}"
        )
    return paths


def load_cases(paths: list[Path]) -> list[CaseInput]:
    cases: list[CaseInput] = []
    seen: set[str] = set()
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            case = CaseInput.from_dict(payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise CaseInputError(f"Invalid case file {path}: {exc}") from exc
        if case.case_id != path.stem:
            raise CaseInputError(
                f"case_id {case.case_id!r} does not match filename {path.name!r}"
            )
        if case.case_id in seen:
            raise CaseInputError(f"Duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        cases.append(case)
    return cases

