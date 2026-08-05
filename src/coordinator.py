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
        self.trace.emit(
            case_id=case.case_id,
            agent="coordinator",
            event="case_started",
            details={"order_id": case.claimed_order_id},
        )
        try:
            self._started(case, "order_seller_agent")
            order = self.order_agent.analyze(case, self.data)
            self._completed(case, "order_seller_agent", "delivery_agent")

            self._started(case, "payment_agent")
            payment = self.payment_agent.analyze(case, self.data)
            self._completed(case, "payment_agent", "policy_agent")

            self._started(case, "delivery_agent")
            delivery = self.delivery_agent.analyze(case, order)
            self._completed(case, "delivery_agent", "policy_agent")

            self._started(case, "policy_agent")
            decision = self.policy_agent.decide(case, order, payment, delivery)
            self._completed(case, "policy_agent", "verifier_agent")

            self._started(case, "verifier_agent")
            output = self.verifier_agent.verify_and_build(
                case, order, payment, delivery, decision
            )
            self.trace.emit(
                case_id=case.case_id,
                agent="verifier_agent",
                event="verification_passed",
                handoff_to="coordinator",
            )
            return output
        except Exception as exc:
            self.trace.emit(
                case_id=case.case_id,
                agent="coordinator",
                event="case_failed",
                status="error",
                details={"error_type": type(exc).__name__, "message": str(exc)},
            )
            raise

    def _started(self, case: CaseInput, agent: str) -> None:
        self.trace.emit(case_id=case.case_id, agent=agent, event="agent_started")

    def _completed(self, case: CaseInput, agent: str, handoff_to: str) -> None:
        self.trace.emit(
            case_id=case.case_id,
            agent=agent,
            event="analysis_completed",
            handoff_to=handoff_to,
        )

