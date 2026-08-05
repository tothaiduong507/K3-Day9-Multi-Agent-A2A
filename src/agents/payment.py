"""TV3: Payment Agent."""

from src.data_loader import OlistDataLoader
from src.models import CaseInput, PaymentAnalysis


class PaymentAgent:
    def analyze(self, case: CaseInput, data: OlistDataLoader) -> PaymentAnalysis:
        raise NotImplementedError("TV3: implement PaymentAgent.analyze")

