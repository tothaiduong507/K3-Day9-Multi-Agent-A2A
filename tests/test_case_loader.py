"""Validation tests for case file discovery and parsing."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.case_loader import CaseInputError, discover_case_paths, load_cases


def case_payload(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "opened_at": "2018-10-18T00:00:00-03:00",
        "customer_request": {
            "language": "vi",
            "message": "test",
            "claimed_order_id": "order-1",
        },
        "policy_version": "EC_POLICY_V1",
    }


class CaseLoaderTests(unittest.TestCase):
    def test_single_case_must_match_filename(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "EC_001.json"
            path.write_text(json.dumps(case_payload("EC_002")), encoding="utf-8")
            with self.assertRaisesRegex(CaseInputError, "does not match filename"):
                load_cases([path])

    def test_full_run_requires_exactly_fifty_cases(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "EC_001.json").write_text(
                json.dumps(case_payload("EC_001")), encoding="utf-8"
            )
            with self.assertRaisesRegex(CaseInputError, "Expected exactly"):
                discover_case_paths(root)

    def test_rejects_unsupported_policy(self) -> None:
        with TemporaryDirectory() as temp:
            path = Path(temp) / "EC_001.json"
            payload = case_payload("EC_001")
            payload["policy_version"] = "OTHER"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CaseInputError, "Unsupported policy"):
                load_cases([path])
