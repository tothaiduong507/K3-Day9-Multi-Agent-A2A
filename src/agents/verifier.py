"""TV5: Verifier Agent và output builder."""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from src.models import (
    CaseInput,
    DeliveryAnalysis,
    FinalCaseOutput,
    OrderAnalysis,
    PaymentAnalysis,
    PolicyDecision,
)


class VerifierAgent:
    def __init__(self):
        # Biểu thức chính quy kiểm tra 5 dạng Evidence ID
        self.evidence_patterns = [
            re.compile(r"^order:[a-zA-Z0-9_]+$"),
            re.compile(r"^item:[a-zA-Z0-9_]+:\d+$"),
            re.compile(r"^payment:[a-zA-Z0-9_]+:\d+$"),
            re.compile(r"^seller:[a-zA-Z0-9_]+$"),
            re.compile(r"^policy:[A-Z_]+$"),
        ]

    def _round_currency(self, val: Decimal | float | str) -> float:
        """Làm tròn an toàn 2 chữ số thập phân bằng ROUND_HALF_UP."""
        dec = Decimal(str(val))
        return float(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def verify_and_build(
        self,
        case: CaseInput,
        order: OrderAnalysis,
        payment: PaymentAnalysis,
        delivery: DeliveryAnalysis,
        decision: PolicyDecision,
    ) -> FinalCaseOutput:
        case_id = case.case_id
        order_id = getattr(order, "order_id", None)
        item_seqs = getattr(order, "item_seqs", []) or []
        seller_ids = getattr(order, "seller_ids", []) or []
        payment_seqs = getattr(payment, "payment_seqs", []) or []

        # 1. Thu thập Affected Entities & giới hạn tối đa 5 IDs mỗi mảng
        affected_order_ids = ([order_id] if order_id else [])[:5]
        affected_item_ids = [f"{order_id}:{seq}" for seq in item_seqs][:5]
        affected_seller_ids = seller_ids[:5]
        affected_payment_ids = [f"{order_id}:{seq}" for seq in payment_seqs][:5]

        # 2. Xây dựng & Kiểm tra định dạng Evidence IDs
        raw_evidences: List[str] = []
        if order_id:
            raw_evidences.append(f"order:{order_id}")
        for seq in item_seqs:
            raw_evidences.append(f"item:{order_id}:{seq}")
        for seq in payment_seqs:
            raw_evidences.append(f"payment:{order_id}:{seq}")
        for s_id in seller_ids:
            raw_evidences.append(f"seller:{s_id}")
        raw_evidences.append(f"policy:{decision.root_cause_code}")

        # Lọc qua Regex và cắt tối đa 10 Evidence IDs
        valid_evidences = [
            ev for ev in raw_evidences 
            if any(p.match(ev) for p in self.evidence_patterns)
        ][:10]

        # 3. Tính toán & Làm tròn các giá trị tài chính (ở ranh giới Output)
        item_total = self._round_currency(getattr(payment, "item_total_brl", 0.0))
        freight_total = self._round_currency(getattr(payment, "freight_total_brl", 0.0))
        payment_total = self._round_currency(getattr(payment, "payment_total_brl", 0.0))
        recommended_refund = self._round_currency(decision.recommended_refund_brl)

        # Quy tắc khi đơn không chứa item row
        if not affected_item_ids:
            affected_seller_ids = []
            item_total = 0.0
            freight_total = 0.0

        # 4. Xây dựng Root Cause Analysis & Actions
        ranked_causes = [{"cause_code": decision.root_cause_code, "rank": 1}][:3]
        
        responsible_parties = []
        if decision.responsible_party_type:
            responsible_parties.append({
                "party_type": decision.responsible_party_type,
                "party_id": decision.responsible_party_id
            })
        responsible_parties = responsible_parties[:3]

        resolution_actions = ([decision.action] if decision.action else [])[:5]

        # 5. Dựng FinalCaseOutput khớp hoàn toàn Pydantic Model
        return FinalCaseOutput(
            case_id=case_id,
            assessment={
                "primary_issue": decision.primary_issue,
                "case_status": decision.case_status,
                "confidence": decision.confidence,
            },
            affected_entities={
                "order_ids": affected_order_ids,
                "item_ids": affected_item_ids,
                "seller_ids": affected_seller_ids,
                "payment_ids": affected_payment_ids,
            },
            root_cause_analysis={
                "ranked_causes": ranked_causes,
                "responsible_parties": responsible_parties,
            },
            evidence_ids=valid_evidences,
            financial_resolution={
                "currency": "BRL",
                "item_total_brl": item_total,
                "freight_total_brl": freight_total,
                "payment_total_brl": payment_total,
                "recommended_refund_brl": recommended_refund,
            },
            resolution_actions=resolution_actions,
        )