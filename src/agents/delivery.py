"""TV4: Delivery Agent.

Phân tích giao hàng theo EC_POLICY_V1:
- Giao trễ nếu order_delivered_customer_date > order_estimated_delivery_date.
- Seller bàn giao trễ nếu order_delivered_carrier_date > shipping_limit_date của item.
- Không parse timezone; dùng timestamp string từ CSV theo đề bài.
"""

from src.models import CaseInput, DeliveryAnalysis, OrderAnalysis


class DeliveryAgent:
    def analyze(self, case: CaseInput, order: OrderAnalysis) -> DeliveryAnalysis:
        """Tạo DeliveryAnalysis từ kết quả Order & Seller Agent.

        Delivery Agent không đọc CSV trực tiếp. Coordinator truyền OrderAnalysis đã chứa
        mốc giao hàng và danh sách item. Output dùng cho Policy Agent phân biệt:
        - late_delivery_seller
        - late_delivery_logistics
        - unsupported_late_claim
        """
        order_id = order.order_id if order and order.order_id else case.claimed_order_id

        if not order or not order.order_found:
            return self._with_policy_aliases(
                DeliveryAnalysis(order_id=order_id)
            )

        is_delivered_late = self._is_after(
            order.delivered_customer_at,
            order.estimated_delivery_at,
        )

        late_seller_ids: list[str] = []
        seen_sellers: set[str] = set()

        for item in order.items:
            if self._is_after(order.delivered_carrier_at, item.shipping_limit_date):
                seller_id = item.seller_id
                if seller_id and seller_id not in seen_sellers:
                    seen_sellers.add(seller_id)
                    late_seller_ids.append(seller_id)

        seller_handoff_late = bool(late_seller_ids)
        suggested_responsibility = None
        if is_delivered_late:
            suggested_responsibility = (
                "seller" if seller_handoff_late else "logistics_provider"
            )

        evidence_ids = [f"order:{order_id}"]
        evidence_ids.extend(f"seller:{seller_id}" for seller_id in late_seller_ids[:4])

        return self._with_policy_aliases(
            DeliveryAnalysis(
                order_id=order_id,
                is_delivered_late=is_delivered_late,
                seller_handoff_late=seller_handoff_late,
                suggested_responsibility=suggested_responsibility,
                late_seller_ids=late_seller_ids,
                evidence_ids=evidence_ids[:10],
            )
        )

    @staticmethod
    def _is_after(left: str | None, right: str | None) -> bool:
        """True nếu left > right; thiếu timestamp thì False."""
        if not left or not right:
            return False
        return left > right

    @staticmethod
    def _with_policy_aliases(analysis: DeliveryAnalysis) -> DeliveryAnalysis:
        """Gắn alias để tương thích PolicyAgent hiện tại.

        models.py dùng is_delivered_late/seller_handoff_late, nhưng policy.py hiện
        đang đọc is_carrier_late/is_seller_late bằng getattr. Dataclass không frozen,
        nên gắn alias tại đây để không sửa phần TV5.
        """
        analysis.is_carrier_late = analysis.is_delivered_late
        analysis.is_seller_late = analysis.seller_handoff_late
        return analysis
