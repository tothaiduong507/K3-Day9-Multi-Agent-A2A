"""Coordinator tests use fake agents, independent of TV2-TV5 logic."""

import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.coordinator import Coordinator
from src.models import (
    CaseInput,
    DeliveryAnalysis,
    OrderAnalysis,
    PaymentAnalysis,
    PolicyDecision,
)
from src.trace_logger import TraceLogger


CASE = CaseInput(
    case_id="EC_001",
    opened_at="2018-10-18T00:00:00-03:00",
    language="vi",
    message="test",
    claimed_order_id="order-1",
    policy_version="EC_POLICY_V1",
)


class FakeOrderAgent:
    def __init__(self, calls: list[str], fail: bool = False) -> None:
        self.calls = calls
        self.fail = fail

    def analyze(self, case, data):
        self.calls.append("order")
        if self.fail:
            raise RuntimeError("order failed")
        return OrderAnalysis(order_found=True, order_id=case.claimed_order_id)


class FakePaymentAgent:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, case, data):
        self.calls.append("payment")
        return PaymentAnalysis(order_id=case.claimed_order_id)


class FakeDeliveryAgent:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def analyze(self, case, order):
        self.calls.append("delivery")
        return DeliveryAnalysis(order_id=case.claimed_order_id)


class FakePolicyAgent:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def decide(self, case, order, payment, delivery):
        self.calls.append("policy")
        return PolicyDecision(
            primary_issue="unsupported_late_claim",
            case_status="no_action",
            confidence=Decimal("1"),
            root_cause_code="DELIVERY_WITHIN_ESTIMATE",
        )


class FakeVerifierAgent:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def verify_and_build(self, case, order, payment, delivery, decision):
        self.calls.append("verifier")
        return {"case_id": case.case_id, "assessment": {"confidence": Decimal("1")}}


class CoordinatorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.trace_path = Path(self.temp_dir.name) / "trace.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_coordinator(self, calls: list[str], fail_order: bool = False) -> Coordinator:
        return Coordinator(
            data=object(),
            order_agent=FakeOrderAgent(calls, fail_order),
            payment_agent=FakePaymentAgent(calls),
            delivery_agent=FakeDeliveryAgent(calls),
            policy_agent=FakePolicyAgent(calls),
            verifier_agent=FakeVerifierAgent(calls),
            trace=TraceLogger(self.trace_path),
        )

    def test_handoff_order_and_output(self) -> None:
        calls: list[str] = []
        coordinator = self.make_coordinator(calls)
        output = coordinator.run_case(CASE)
        self.assertEqual(
            ["order", "payment", "delivery", "policy", "verifier"], calls
        )
        self.assertEqual("EC_001", output["case_id"])
        records = [
            json.loads(line)
            for line in self.trace_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual("case_started", records[0]["event"])
        self.assertEqual("verification_passed", records[-1]["event"])

    def test_failure_is_traced_and_propagated(self) -> None:
        coordinator = self.make_coordinator([], fail_order=True)
        with self.assertRaisesRegex(RuntimeError, "order failed"):
            coordinator.run_case(CASE)
        records = [
            json.loads(line)
            for line in self.trace_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual("case_failed", records[-1]["event"])
        self.assertEqual("error", records[-1]["status"])
