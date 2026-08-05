"""TV5: Policy Agent."""

from decimal import Decimal
from typing import Dict

from src.models import (
    CaseInput,
    DeliveryAnalysis,
    OrderAnalysis,
    PaymentAnalysis,
    PolicyDecision,
)

ROOT_CAUSE_MAP: Dict[str, str] = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}


class PolicyAgent:
    def _to_decimal(self, val: float | str | Decimal | None) -> Decimal:
        """Chuyển đổi an toàn sang Decimal để tránh trôi số chấm động."""
        if val is None:
            return Decimal("0.00")
        return Decimal(str(val))

    def decide(
        self,
        case: CaseInput,
        order: OrderAnalysis,
        payment: PaymentAnalysis,
        delivery: DeliveryAnalysis,
    ) -> PolicyDecision:
        # Lấy giá trị trạng thái & tiền tệ
        order_status = getattr(order, "order_status", None)
        
        item_total = self._to_decimal(getattr(payment, "item_total_brl", 0.0))
        freight_total = self._to_decimal(getattr(payment, "freight_total_brl", 0.0))
        payment_total = self._to_decimal(getattr(payment, "payment_total_brl", 0.0))
        
        num_payments = getattr(payment, "num_payment_rows", 0)
        
        is_carrier_late = getattr(delivery, "is_carrier_late", False)
        is_seller_late = getattr(delivery, "is_seller_late", False)
        seller_ids = getattr(order, "seller_ids", []) or []

        # --- CÂY QUY TẮC EC_POLICY_V1 THEO THỨ TỰ ƯU TIÊN ---
        primary_issue = None
        responsible_party_type = None
        responsible_party_id = None
        refund_amount = Decimal("0.00")
        action = None

        # Rule 1: canceled_order_paid
        if order_status == "canceled" and payment_total > Decimal("0.00"):
            primary_issue = "canceled_order_paid"
            responsible_party_type = "platform"
            responsible_party_id = "OLIST_PLATFORM"
            refund_amount = payment_total
            action = "issue_full_refund"

        # Rule 2: unavailable_order_paid
        elif order_status == "unavailable" and payment_total > Decimal("0.00"):
            primary_issue = "unavailable_order_paid"
            responsible_party_type = "platform"
            responsible_party_id = "OLIST_PLATFORM"
            refund_amount = payment_total
            action = "issue_full_refund"

        # Rule 3: late_delivery_seller
        elif is_carrier_late and is_seller_late:
            primary_issue = "late_delivery_seller"
            responsible_party_type = "seller"
            responsible_party_id = seller_ids[0] if seller_ids else "UNKNOWN_SELLER"
            refund_amount = freight_total
            action = "refund_freight"

        # Rule 4: late_delivery_logistics
        elif is_carrier_late and not is_seller_late:
            primary_issue = "late_delivery_logistics"
            responsible_party_type = "logistics_provider"
            responsible_party_id = "LOGISTICS_PROVIDER"
            refund_amount = freight_total
            action = "refund_freight"

        # Rule 5: valid_split_payment
        elif num_payments >= 2 and abs(payment_total - (item_total + freight_total)) <= Decimal("0.10"):
            primary_issue = "valid_split_payment"
            responsible_party_type = None
            responsible_party_id = None
            refund_amount = Decimal("0.00")
            action = "explain_valid_split_payment"

        # Rule 6: unsupported_late_claim (Mặc định)
        else:
            primary_issue = "unsupported_late_claim"
            responsible_party_type = None
            responsible_party_id = None
            refund_amount = Decimal("0.00")
            action = "reject_late_refund"

        root_cause_code = ROOT_CAUSE_MAP[primary_issue]
        case_status = "action_required" if refund_amount > Decimal("0.00") else "no_action"

        # Trả về Pydantic Object / Dataclass PolicyDecision
        return PolicyDecision(
            primary_issue=primary_issue,
            case_status=case_status,
            confidence=0.95,
            root_cause_code=root_cause_code,
            responsible_party_type=responsible_party_type,
            responsible_party_id=responsible_party_id,
            recommended_refund_brl=refund_amount,
            action=action,
        )