"""TV1 integration tests with fake domain agents."""

import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.batch_runner import BatchRunner
from src.agents.payment import PaymentAgent as DomainPaymentAgent
from src.agents.policy import PolicyAgent
from src.agents.verifier import VerifierAgent
from src.models import DeliveryAnalysis, OrderAnalysis, PaymentAnalysis
from src.output_writer import OutputWriter
import tests.test_coordinator as coordinator_fixtures


class IntegrationTests(unittest.TestCase):
    def test_payment_agent_preserves_source_row_order(self) -> None:
        rows = {
            "order-1": [
                {
                    "order_id": "order-1",
                    "payment_sequential": "2",
                    "payment_type": "voucher",
                    "payment_installments": "1",
                    "payment_value": "2.00",
                },
                {
                    "order_id": "order-1",
                    "payment_sequential": "1",
                    "payment_type": "credit_card",
                    "payment_installments": "1",
                    "payment_value": "10.00",
                },
            ]
        }
        result = DomainPaymentAgent(rows).analyze(
            order_id="order-1",
            item_total_brl=Decimal("10"),
            freight_total_brl=Decimal("2"),
        )
        self.assertEqual(["order-1:2", "order-1:1"], result.payment_ids)

    def test_tv5_policy_and_verifier_match_shared_contract(self) -> None:
        order = OrderAnalysis(
            order_found=True,
            order_id="order-1",
            order_status="canceled",
            item_seqs=["1"],
            seller_ids=["seller-1"],
        )
        payment = PaymentAnalysis(
            order_id="order-1",
            item_total_brl=Decimal("10"),
            freight_total_brl=Decimal("2"),
            payment_total_brl=Decimal("12"),
            payment_row_count=1,
            payment_seqs=["1"],
        )
        delivery = DeliveryAnalysis(order_id="order-1")
        decision = PolicyAgent().decide(
            coordinator_fixtures.CASE, order, payment, delivery
        )
        output = VerifierAgent().verify_and_build(
            coordinator_fixtures.CASE, order, payment, delivery, decision
        )
        self.assertEqual("canceled_order_paid", output["assessment"]["primary_issue"])
        self.assertEqual(Decimal("0.95"), output["assessment"]["confidence"])
        self.assertEqual(12.0, output["financial_resolution"]["recommended_refund_brl"])
        self.assertNotIn("seller:seller-1", output["evidence_ids"])

    def test_batch_writes_verified_output_and_summary(self) -> None:
        with TemporaryDirectory() as temp:
            helper = coordinator_fixtures.CoordinatorContractTests()
            helper.temp_dir = TemporaryDirectory()
            helper.trace_path = Path(helper.temp_dir.name) / "trace.jsonl"
            coordinator = helper.make_coordinator([])
            result = BatchRunner(coordinator, OutputWriter(Path(temp))).run(
                [coordinator_fixtures.CASE]
            )
            self.assertTrue(result.ok)
            self.assertEqual(1, result.succeeded)
            output = json.loads((Path(temp) / "EC_001.json").read_text("utf-8"))
            self.assertEqual(1.0, output["assessment"]["confidence"])
            helper.temp_dir.cleanup()

    def test_output_writer_rounds_decimal_at_boundary(self) -> None:
        with TemporaryDirectory() as temp:
            path = OutputWriter(Path(temp)).write(
                "EC_001",
                {
                    "recommended_refund_brl": Decimal("10.125"),
                    "confidence": Decimal("0.925"),
                },
            )
            output = json.loads(path.read_text("utf-8"))
            self.assertEqual(10.13, output["recommended_refund_brl"])
            self.assertEqual(0.925, output["confidence"])
