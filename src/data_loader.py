"""Truy cập tập trung vào dữ liệu Olist.

TV1 hoàn thiện việc load CSV một lần, lập index và trả bản sao/read-only data
cho các agent. Không để từng agent tự quét lại CSV.
"""

from pathlib import Path
from typing import Any


class OlistDataLoader:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def load(self) -> None:
        """Đọc các CSV cần thiết và xây index theo order_id/seller_id."""
        raise NotImplementedError("TV1: implement OlistDataLoader.load")

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("TV1: implement get_order")

    def get_order_items(self, order_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("TV1: implement get_order_items")

    def get_order_payments(self, order_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("TV1: implement get_order_payments")

    def get_seller(self, seller_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("TV1: implement get_seller")

