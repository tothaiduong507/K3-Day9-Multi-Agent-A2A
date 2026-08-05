"""Contract dữ liệu chung giữa Coordinator và các agent."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import re
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
        try:
            request = payload["customer_request"]
            case = cls(
                case_id=payload["case_id"],
                opened_at=payload["opened_at"],
                language=request["language"],
                message=request["message"],
                claimed_order_id=request["claimed_order_id"],
                policy_version=payload["policy_version"],
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid case input structure: missing {exc}") from exc
        case.validate()
        return case

    def validate(self) -> None:
        if not re.fullmatch(r"EC_\d{3}", self.case_id):
            raise ValueError(f"Invalid case_id: {self.case_id!r}")
        for name in ("opened_at", "language", "message", "claimed_order_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if self.policy_version != "EC_POLICY_V1":
            raise ValueError(f"Unsupported policy_version: {self.policy_version!r}")
        try:
            datetime.fromisoformat(self.opened_at)
        except ValueError as exc:
            raise ValueError(f"Invalid opened_at: {self.opened_at!r}") from exc


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
    item_seqs: list[str] = field(default_factory=list)
    seller_ids: list[str] = field(default_factory=list)
    seller_handoff_violations: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.items and not self.item_seqs:
            self.item_seqs = [item.order_item_id for item in self.items]
        if self.items and not self.seller_ids:
            self.seller_ids = list(dict.fromkeys(item.seller_id for item in self.items))


@dataclass
class PaymentAnalysis:
    order_id: str
    item_total_brl: Decimal = Decimal("0")
    freight_total_brl: Decimal = Decimal("0")
    payment_total_brl: Decimal = Decimal("0")
    payment_row_count: int = 0
    num_payment_rows: int = 0
    payment_seqs: list[str] = field(default_factory=list)
    payment_ids: list[str] = field(default_factory=list)
    is_reconciled: bool = False
    evidence_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        count = self.payment_row_count or self.num_payment_rows
        self.payment_row_count = count
        self.num_payment_rows = count


@dataclass
class DeliveryAnalysis:
    order_id: str
    is_delivered_late: bool = False
    seller_handoff_late: bool = False
    is_carrier_late: bool = False
    is_seller_late: bool = False
    suggested_responsibility: PartyType | None = None
    late_seller_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        delivered_late = self.is_delivered_late or self.is_carrier_late
        seller_late = self.seller_handoff_late or self.is_seller_late
        self.is_delivered_late = delivered_late
        self.is_carrier_late = delivered_late
        self.seller_handoff_late = seller_late
        self.is_seller_late = seller_late


@dataclass
class PolicyDecision:
    primary_issue: str
    case_status: CaseStatus
    confidence: Decimal
    root_cause_code: str
    responsible_parties: list[dict[str, str]] = field(default_factory=list)
    responsible_party_type: PartyType | None = None
    responsible_party_id: str | None = None
    recommended_refund_brl: Decimal = Decimal("0")
    resolution_actions: list[str] = field(default_factory=list)
    action: str | None = None
    evidence_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.responsible_parties and not self.responsible_party_type:
            first = self.responsible_parties[0]
            self.responsible_party_type = first.get("party_type")  # type: ignore[assignment]
            self.responsible_party_id = first.get("party_id")
        elif self.responsible_party_type and not self.responsible_parties:
            self.responsible_parties = [
                {
                    "party_type": self.responsible_party_type,
                    "party_id": self.responsible_party_id or "",
                }
            ]
        if self.resolution_actions and not self.action:
            self.action = self.resolution_actions[0]
        elif self.action and not self.resolution_actions:
            self.resolution_actions = [self.action]


@dataclass
class AnalysisBundle:
    case: CaseInput
    order_analysis: OrderAnalysis
    payment_analysis: PaymentAnalysis
    delivery_analysis: DeliveryAnalysis
    policy_decision: PolicyDecision


FinalCaseOutput = dict[str, Any]

