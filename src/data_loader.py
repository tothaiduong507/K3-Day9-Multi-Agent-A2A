"""Centralized, read-once access to the Olist CSV files."""

import csv
from pathlib import Path
from typing import Any


class DataLoaderError(RuntimeError):
    """Raised when the Olist dataset cannot be loaded safely."""


class OlistDataLoader:
    REQUIRED_FILES = {
        "orders": "olist_orders_dataset.csv",
        "items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
    }

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self._loaded = False
        self._orders: dict[str, dict[str, str]] = {}
        self._items_by_order: dict[str, list[dict[str, str]]] = {}
        self._payments_by_order: dict[str, list[dict[str, str]]] = {}
        self._sellers: dict[str, dict[str, str]] = {}

    def load(self) -> None:
        """Load required files once and atomically publish the indexes."""
        if self._loaded:
            return

        paths = {
            name: self.data_dir / filename
            for name, filename in self.REQUIRED_FILES.items()
        }
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            raise DataLoaderError(f"Missing required dataset files: {', '.join(missing)}")

        orders: dict[str, dict[str, str]] = {}
        for row in self._read_rows(paths["orders"]):
            self._insert_unique(orders, row, "order_id", paths["orders"])

        items_by_order: dict[str, list[dict[str, str]]] = {}
        for row in self._read_rows(paths["items"]):
            self._append_grouped(items_by_order, row, "order_id", paths["items"])

        payments_by_order: dict[str, list[dict[str, str]]] = {}
        for row in self._read_rows(paths["payments"]):
            self._append_grouped(
                payments_by_order, row, "order_id", paths["payments"]
            )

        sellers: dict[str, dict[str, str]] = {}
        for row in self._read_rows(paths["sellers"]):
            self._insert_unique(sellers, row, "seller_id", paths["sellers"])

        self._orders = orders
        self._items_by_order = items_by_order
        self._payments_by_order = payments_by_order
        self._sellers = sellers
        self._loaded = True

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        row = self._orders.get(order_id)
        return dict(row) if row is not None else None

    def get_order_items(self, order_id: str) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return [dict(row) for row in self._items_by_order.get(order_id, ())]

    def get_order_payments(self, order_id: str) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return [dict(row) for row in self._payments_by_order.get(order_id, ())]

    def get_seller(self, seller_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        row = self._sellers.get(seller_id)
        return dict(row) if row is not None else None

    @property
    def stats(self) -> dict[str, int]:
        self._ensure_loaded()
        return {
            "orders": len(self._orders),
            "items": sum(map(len, self._items_by_order.values())),
            "payments": sum(map(len, self._payments_by_order.values())),
            "sellers": len(self._sellers),
        }

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames:
                    raise DataLoaderError(f"CSV has no header: {path}")
                return [dict(row) for row in reader]
        except (OSError, csv.Error) as exc:
            raise DataLoaderError(f"Cannot read CSV {path}: {exc}") from exc

    @staticmethod
    def _insert_unique(
        target: dict[str, dict[str, str]],
        row: dict[str, str],
        key_field: str,
        source: Path,
    ) -> None:
        key = row.get(key_field, "")
        if not key:
            raise DataLoaderError(f"Missing {key_field} in {source}")
        if key in target:
            raise DataLoaderError(f"Duplicate {key_field}={key} in {source}")
        target[key] = row

    @staticmethod
    def _append_grouped(
        target: dict[str, list[dict[str, str]]],
        row: dict[str, str],
        key_field: str,
        source: Path,
    ) -> None:
        key = row.get(key_field, "")
        if not key:
            raise DataLoaderError(f"Missing {key_field} in {source}")
        target.setdefault(key, []).append(row)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            raise DataLoaderError("OlistDataLoader.load() must be called first")

