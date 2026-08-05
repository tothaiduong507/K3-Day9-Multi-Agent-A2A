"""TV5: Policy Agent."""

from src.models import (
    CaseInput,
    DeliveryAnalysis,
    OrderAnalysis,
    PaymentAnalysis,
    PolicyDecision,
)


class PolicyAgent:
    def decide(
        self,
        case: CaseInput,
        order: OrderAnalysis,
        payment: PaymentAnalysis,
        delivery: DeliveryAnalysis,
    ) -> PolicyDecision:
        raise NotImplementedError("TV5: implement PolicyAgent.decide")

