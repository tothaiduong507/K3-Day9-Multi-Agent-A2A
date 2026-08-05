"""TV4: Delivery Agent."""

from src.models import CaseInput, DeliveryAnalysis, OrderAnalysis


class DeliveryAgent:
    def analyze(self, case: CaseInput, order: OrderAnalysis) -> DeliveryAnalysis:
        raise NotImplementedError("TV4: implement DeliveryAgent.analyze")

