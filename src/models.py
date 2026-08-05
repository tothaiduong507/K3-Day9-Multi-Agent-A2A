"""Contract dữ liệu chung giữa Coordinator và các agent."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal


CaseStatus = Literal["action_required", "no_action"]
PartyType = Literal["seller", "logistics_provider", "platform"]


@dataclass(frozen=True)
class CaseInput:
    case_id: str
    opened_at: str
    language: str
    message: str
    claimed_order_id: str
    policy_version: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CaseInput":
        request = payload["customer_request"]
        return cls(
            case_id=payload["case_id"],
            opened_at=payload["opened_at"],
            language=request["language"],
            message=request["message"],
            claimed_order_id=request["claimed_order_id"],
            policy_version=payload["policy_version"],
        )


@dataclass(frozen=True)
class ItemRecord:
    order_id: str
    order_item_id: str
    product_id: str
    seller_id: str
    shipping_limit_date: str
    price_brl: Decimal
    freight_brl: Decimal


@dataclass
class OrderAnalysis:
    order_found: bool
    order_id: str
    order_status: str | None = None
    delivered_carrier_at: str | None = None
    delivered_customer_at: str | None = None
    estimated_delivery_at: str | None = None
    items: list[ItemRecord] = field(default_factory=list)
    seller_handoff_violations: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class PaymentAnalysis:
    order_id: str
    item_total_brl: Decimal = Decimal("0")
    freight_total_brl: Decimal = Decimal("0")
    payment_total_brl: Decimal = Decimal("0")
    payment_row_count: int = 0
    payment_ids: list[str] = field(default_factory=list)
    is_reconciled: bool = False
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class DeliveryAnalysis:
    order_id: str
    is_delivered_late: bool = False
    seller_handoff_late: bool = False
    suggested_responsibility: PartyType | None = None
    late_seller_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class PolicyDecision:
    primary_issue: str
    case_status: CaseStatus
    confidence: Decimal
    root_cause_code: str
    responsible_parties: list[dict[str, str]] = field(default_factory=list)
    recommended_refund_brl: Decimal = Decimal("0")
    resolution_actions: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class AnalysisBundle:
    case: CaseInput
    order_analysis: OrderAnalysis
    payment_analysis: PaymentAnalysis
    delivery_analysis: DeliveryAnalysis
    policy_decision: PolicyDecision


FinalCaseOutput = dict[str, Any]

