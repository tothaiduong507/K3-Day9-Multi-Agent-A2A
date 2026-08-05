"""Điều phối pipeline; không chứa logic quyết định policy."""

from src.agents.delivery import DeliveryAgent
from src.agents.order_seller import OrderSellerAgent
from src.agents.payment import PaymentAgent
from src.agents.policy import PolicyAgent
from src.agents.verifier import VerifierAgent
from src.data_loader import OlistDataLoader
from src.models import CaseInput, FinalCaseOutput
from src.trace_logger import TraceLogger


class Coordinator:
    def __init__(
        self,
        *,
        data: OlistDataLoader,
        order_agent: OrderSellerAgent,
        payment_agent: PaymentAgent,
        delivery_agent: DeliveryAgent,
        policy_agent: PolicyAgent,
        verifier_agent: VerifierAgent,
        trace: TraceLogger,
    ) -> None:
        self.data = data
        self.order_agent = order_agent
        self.payment_agent = payment_agent
        self.delivery_agent = delivery_agent
        self.policy_agent = policy_agent
        self.verifier_agent = verifier_agent
        self.trace = trace

    def run_case(self, case: CaseInput) -> FinalCaseOutput:
        self.trace.emit(case_id=case.case_id, agent="coordinator", event="case_started")

        order = self.order_agent.analyze(case, self.data)
        payment = self.payment_agent.analyze(case, self.data)
        delivery = self.delivery_agent.analyze(case, order)
        decision = self.policy_agent.decide(case, order, payment, delivery)
        output = self.verifier_agent.verify_and_build(
            case, order, payment, delivery, decision
        )

        self.trace.emit(case_id=case.case_id, agent="coordinator", event="case_completed")
        return output

