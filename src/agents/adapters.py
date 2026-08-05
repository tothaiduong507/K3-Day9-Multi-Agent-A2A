"""Adapters from feature-branch agent APIs to the shared Coordinator contract."""

from decimal import Decimal

from src.agents.order_seller_agent import OrderSellerAgent as DomainOrderSellerAgent
from src.agents.payment import PaymentAgent as DomainPaymentAgent
from src.data_loader import OlistDataLoader
from src.models import CaseInput, ItemRecord, OrderAnalysis, PaymentAnalysis
from src.utils.decimal_utils import as_decimal


class IntegratedOrderSellerAgent:
    """Convert TV2's ``process(context)`` output into ``OrderAnalysis``."""

    def analyze(self, case: CaseInput, data: OlistDataLoader) -> OrderAnalysis:
        result = DomainOrderSellerAgent(data).process(
            {"claimed_order_id": case.claimed_order_id}
        )
        timestamps = result.get("timestamps", {})
        items = [
            ItemRecord(
                order_id=case.claimed_order_id,
                order_item_id=str(item.get("order_item_id", "")),
                product_id=str(item.get("product_id", "")),
                seller_id=str(item.get("seller_id", "")),
                shipping_limit_date=str(item.get("shipping_limit_date", "")),
                price_brl=as_decimal(item.get("price", 0)),
                freight_brl=as_decimal(item.get("freight_value", 0)),
            )
            for item in result.get("items", [])
        ]
        return OrderAnalysis(
            order_found=bool(result.get("exists")),
            order_id=str(result.get("order_id") or case.claimed_order_id),
            order_status=result.get("order_status"),
            delivered_carrier_at=timestamps.get("delivered_carrier"),
            delivered_customer_at=timestamps.get("delivered_customer"),
            estimated_delivery_at=timestamps.get("estimated_delivery"),
            items=items,
            item_seqs=[item.order_item_id for item in items],
            seller_ids=[str(value) for value in result.get("sellers", [])],
            seller_handoff_violations=[
                str(value) for value in result.get("violating_seller_ids", [])
            ],
            evidence_ids=[str(value) for value in result.get("evidence_ids", [])],
        )


class IntegratedPaymentAgent:
    """Supply loader data to TV3 and convert its result to shared analysis."""

    def analyze(self, case: CaseInput, data: OlistDataLoader) -> PaymentAnalysis:
        order_id = case.claimed_order_id
        raw_items = data.get_order_items(order_id)
        item_total = sum(
            (as_decimal(row.get("price", 0)) for row in raw_items),
            start=Decimal("0"),
        )
        freight_total = sum(
            (as_decimal(row.get("freight_value", 0)) for row in raw_items),
            start=Decimal("0"),
        )
        domain_agent = DomainPaymentAgent(
            {order_id: data.get_order_payments(order_id)}
        )
        result = domain_agent.analyze(
            order_id=order_id,
            item_total_brl=item_total,
            freight_total_brl=freight_total,
        )
        payment_seqs = [payment_id.rsplit(":", 1)[-1] for payment_id in result.payment_ids]
        return PaymentAnalysis(
            order_id=order_id,
            item_total_brl=item_total,
            freight_total_brl=freight_total,
            payment_total_brl=result.payment_total_brl,
            payment_row_count=result.payment_count,
            payment_seqs=payment_seqs,
            payment_ids=result.payment_ids,
            is_reconciled=result.is_reconciled,
            evidence_ids=result.evidence_ids,
        )

