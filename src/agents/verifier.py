"""TV5: Verifier Agent và output builder."""

from src.models import (
    CaseInput,
    DeliveryAnalysis,
    FinalCaseOutput,
    OrderAnalysis,
    PaymentAnalysis,
    PolicyDecision,
)


class VerifierAgent:
    def verify_and_build(
        self,
        case: CaseInput,
        order: OrderAnalysis,
        payment: PaymentAnalysis,
        delivery: DeliveryAnalysis,
        decision: PolicyDecision,
    ) -> FinalCaseOutput:
        raise NotImplementedError("TV5: implement VerifierAgent.verify_and_build")

