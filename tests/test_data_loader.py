"""Tests for the centralized Olist data loader."""

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.data_loader import DataLoaderError, OlistDataLoader


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class DataLoaderContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        write_csv(
            root / "olist_orders_dataset.csv",
            ["order_id", "order_status"],
            [{"order_id": "order-1", "order_status": "delivered"}],
        )
        write_csv(
            root / "olist_order_items_dataset.csv",
            ["order_id", "order_item_id", "seller_id"],
            [
                {"order_id": "order-1", "order_item_id": "1", "seller_id": "s1"},
                {"order_id": "order-1", "order_item_id": "2", "seller_id": "s1"},
            ],
        )
        write_csv(
            root / "olist_order_payments_dataset.csv",
            ["order_id", "payment_sequential", "payment_value"],
            [
                {
                    "order_id": "order-1",
                    "payment_sequential": "1",
                    "payment_value": "10.00",
                },
                {
                    "order_id": "order-1",
                    "payment_sequential": "2",
                    "payment_value": "5.00",
                },
            ],
        )
        write_csv(
            root / "olist_sellers_dataset.csv",
            ["seller_id", "seller_state"],
            [{"seller_id": "s1", "seller_state": "SP"}],
        )
        self.loader = OlistDataLoader(root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_loads_and_indexes_required_entities(self) -> None:
        self.loader.load()
        self.assertEqual("delivered", self.loader.get_order("order-1")["order_status"])
        self.assertEqual(2, len(self.loader.get_order_items("order-1")))
        self.assertEqual(2, len(self.loader.get_order_payments("order-1")))
        self.assertEqual("SP", self.loader.get_seller("s1")["seller_state"])
        self.assertEqual(
            {"orders": 1, "items": 2, "payments": 2, "sellers": 1},
            self.loader.stats,
        )

    def test_returns_defensive_copies_and_empty_defaults(self) -> None:
        self.loader.load()
        order = self.loader.get_order("order-1")
        order["order_status"] = "changed"
        self.assertEqual("delivered", self.loader.get_order("order-1")["order_status"])
        self.assertEqual([], self.loader.get_order_items("missing"))
        self.assertIsNone(self.loader.get_seller("missing"))

    def test_requires_load_before_query(self) -> None:
        with self.assertRaises(DataLoaderError):
            self.loader.get_order("order-1")

    def test_load_is_idempotent(self) -> None:
        self.loader.load()
        self.loader.load()
        self.assertEqual(1, self.loader.stats["orders"])
