"""TV2: Order & Seller Agent."""

from src.data_loader import OlistDataLoader
from src.models import CaseInput, OrderAnalysis


class OrderSellerAgent:
    def analyze(self, case: CaseInput, data: OlistDataLoader) -> OrderAnalysis:
        raise NotImplementedError("TV2: implement OrderSellerAgent.analyze")

