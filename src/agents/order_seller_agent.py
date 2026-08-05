from typing import Dict, Any, List
from src.agents.base_agent import BaseAgent
from src.data_loader import DataLoader

class OrderSellerAgent(BaseAgent):
    """TV2 Order & Seller Agent.
    Responsible for analyzing order status, items, seller details,
    and comparing carrier handoff timestamp against shipping limit dates.
    """

    def __init__(self, data_loader: DataLoader):
        super().__init__(name="OrderSellerAgent", role="TV2 Order & Seller Agent")
        self.data_loader = data_loader

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        claimed_order_id = context.get("claimed_order_id")
        order_record = self.data_loader.get_order(claimed_order_id)
        
        if not order_record:
            return {
                "order_id": claimed_order_id,
                "order_status": "unknown",
                "exists": False,
                "timestamps": {},
                "items": [],
                "sellers": [],
                "has_items": False,
                "seller_handoff_late": False,
                "violating_seller_ids": [],
                "affected_order_ids": [claimed_order_id],
                "affected_item_ids": [],
                "affected_seller_ids": [],
                "evidence_ids": [f"order:{claimed_order_id}"]
            }

        order_status = order_record.get("order_status", "unknown")
        carrier_date = order_record.get("order_delivered_carrier_date")
        customer_date = order_record.get("order_delivered_customer_date")
        estimated_date = order_record.get("order_estimated_delivery_date")

        raw_items = self.data_loader.get_order_items(claimed_order_id)
        has_items = len(raw_items) > 0

        analyzed_items = []
        violating_seller_ids = set()
        all_seller_ids = set()

        for item in raw_items:
            item_id = item.get("order_item_id")
            seller_id = item.get("seller_id")
            shipping_limit = item.get("shipping_limit_date")
            price = float(item.get("price", 0.0))
            freight = float(item.get("freight_value", 0.0))

            if seller_id:
                all_seller_ids.add(seller_id)

            is_late_handoff = False
            if carrier_date and shipping_limit and str(carrier_date) > str(shipping_limit):
                is_late_handoff = True
                if seller_id:
                    violating_seller_ids.add(seller_id)

            analyzed_items.append({
                "order_item_id": item_id,
                "product_id": item.get("product_id"),
                "seller_id": seller_id,
                "shipping_limit_date": shipping_limit,
                "price": price,
                "freight_value": freight,
                "is_handoff_late": is_late_handoff
            })

        seller_handoff_late = len(violating_seller_ids) > 0

        # Build affected entity ID sets (capped at 5)
        affected_order_ids = [claimed_order_id][:5]
        affected_item_ids = [f"{claimed_order_id}:{item['order_item_id']}" for item in analyzed_items][:5]
        affected_seller_ids = list(all_seller_ids)[:5]

        # Build evidence IDs
        evidence_ids = [f"order:{claimed_order_id}"]
        for item_str in affected_item_ids:
            evidence_ids.append(f"item:{item_str}")
        for s_id in affected_seller_ids:
            evidence_ids.append(f"seller:{s_id}")

        return {
            "order_id": claimed_order_id,
            "order_status": order_status,
            "exists": True,
            "timestamps": {
                "purchase": order_record.get("order_purchase_timestamp"),
                "approved": order_record.get("order_approved_at"),
                "delivered_carrier": carrier_date,
                "delivered_customer": customer_date,
                "estimated_delivery": estimated_date
            },
            "items": analyzed_items,
            "sellers": list(all_seller_ids),
            "has_items": has_items,
            "seller_handoff_late": seller_handoff_late,
            "violating_seller_ids": list(violating_seller_ids),
            "affected_order_ids": affected_order_ids,
            "affected_item_ids": affected_item_ids,
            "affected_seller_ids": affected_seller_ids,
            "evidence_ids": evidence_ids
        }
