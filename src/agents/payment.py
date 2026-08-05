from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence


MONEY_ZERO = Decimal("0.00")
PAYMENT_TOLERANCE = Decimal("0.10")
MAX_PAYMENT_IDS = 5
MAX_EVIDENCE_IDS = 10


def to_decimal(value: Any, *, default: Decimal = MONEY_ZERO) -> Decimal:
    """
    Chuyển dữ liệu CSV hoặc Python sang Decimal an toàn.

    Không dùng Decimal(float) trực tiếp vì float có thể đã mang sai số nhị phân.
    Luôn chuyển qua str trước:
        Decimal(str(value))

    Các giá trị None, chuỗi rỗng hoặc NaN được trả về default.
    """
    if value is None:
        return default

    text = str(value).strip()

    if text == "" or text.lower() in {"nan", "none", "null", "<na>"}:
        return default

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def money_to_output(value: Decimal) -> float:
    """
    Chỉ làm tròn ở ranh giới output.

    ROUND_HALF_UP có thể được thêm nếu contract nhóm yêu cầu rõ.
    Với dữ liệu Olist đã có hai chữ số thập phân, quantize 0.01 là đủ.
    """
    return float(value.quantize(Decimal("0.01")))


def safe_int(value: Any) -> int:
    """Chuyển payment_sequential hoặc installments sang int an toàn."""
    if value is None:
        raise ValueError("Expected integer but received None")

    text = str(value).strip()

    if text == "" or text.lower() in {"nan", "none", "null", "<na>"}:
        raise ValueError(f"Invalid integer value: {value!r}")

    try:
        # Hỗ trợ trường hợp pandas đọc thành 1.0
        numeric = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid integer value: {value!r}") from exc

    if numeric != numeric.to_integral_value():
        raise ValueError(f"Expected integer but received {value!r}")

    return int(numeric)


@dataclass(frozen=True)
class PaymentRow:
    order_id: str
    payment_sequential: int
    payment_type: str
    payment_installments: int
    payment_value: Decimal

    @property
    def entity_id(self) -> str:
        return f"{self.order_id}:{self.payment_sequential}"

    @property
    def evidence_id(self) -> str:
        return f"payment:{self.order_id}:{self.payment_sequential}"


@dataclass
class PaymentAnalysis:
    order_id: str
    payment_count: int
    payment_total_brl: Decimal
    expected_total_brl: Decimal
    reconciliation_difference_brl: Decimal
    is_split_payment: bool
    is_reconciled: bool
    has_positive_payment: bool
    payment_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    payment_methods: list[str] = field(default_factory=list)
    root_cause_signal: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Chuyển kết quả nội bộ thành dictionary có thể ghi JSON.

        Chỉ tại đây mới làm tròn tiền thành hai chữ số.
        """
        return {
            "order_id": self.order_id,
            "payment_count": self.payment_count,
            "payment_total_brl": money_to_output(self.payment_total_brl),
            "expected_total_brl": money_to_output(self.expected_total_brl),
            "reconciliation_difference_brl": money_to_output(
                self.reconciliation_difference_brl
            ),
            "is_split_payment": self.is_split_payment,
            "is_reconciled": self.is_reconciled,
            "has_positive_payment": self.has_positive_payment,
            "payment_ids": self.payment_ids[:MAX_PAYMENT_IDS],
            "evidence_ids": self.evidence_ids[:MAX_EVIDENCE_IDS],
            "payment_methods": self.payment_methods,
            "root_cause_signal": self.root_cause_signal,
            "errors": self.errors,
        }


class PaymentAgent:
    """
    Agent phân tích domain payment.

    Trách nhiệm:
    - Lấy toàn bộ payment row của order.
    - Tính tổng payment.
    - Phát hiện split payment.
    - Đối soát payment với item_total + freight_total.
    - Sinh payment entity IDs và evidence IDs hợp lệ.
    - Gửi tín hiệu cho Policy Agent.

    Không chịu trách nhiệm:
    - Chọn primary_issue cuối cùng.
    - Xác định seller/logistics chịu trách nhiệm.
    - Quyết định refund cuối cùng.
    """

    def __init__(
        self,
        payment_rows_by_order: Mapping[str, Sequence[Mapping[str, Any]]],
        *,
        reconciliation_tolerance: Decimal = PAYMENT_TOLERANCE,
    ) -> None:
        self._payment_rows_by_order = payment_rows_by_order
        self._tolerance = reconciliation_tolerance

    def analyze(
        self,
        *,
        order_id: str,
        item_total_brl: Decimal | str | float | int,
        freight_total_brl: Decimal | str | float | int,
    ) -> PaymentAnalysis:
        normalized_order_id = str(order_id).strip()

        if not normalized_order_id:
            raise ValueError("order_id must not be empty")

        item_total = to_decimal(item_total_brl)
        freight_total = to_decimal(freight_total_brl)
        expected_total = item_total + freight_total

        raw_rows = self._payment_rows_by_order.get(normalized_order_id, [])

        payment_rows: list[PaymentRow] = []
        errors: list[str] = []

        for row_index, raw_row in enumerate(raw_rows):
            try:
                payment_row = self._parse_payment_row(
                    raw_row=raw_row,
                    expected_order_id=normalized_order_id,
                )
                payment_rows.append(payment_row)
            except (ValueError, KeyError) as exc:
                errors.append(
                    f"Invalid payment row at index {row_index}: {exc}"
                )

        # Sắp xếp để output ổn định, không phụ thuộc thứ tự DataFrame.
        payment_rows.sort(key=lambda row: row.payment_sequential)

        # Kiểm tra payment_sequential trùng nhau.
        sequential_values = [
            row.payment_sequential for row in payment_rows
        ]

        if len(sequential_values) != len(set(sequential_values)):
            errors.append("Duplicate payment_sequential detected")

        payment_total = sum(
            (row.payment_value for row in payment_rows),
            start=MONEY_ZERO,
        )

        difference = abs(payment_total - expected_total)
        is_reconciled = difference <= self._tolerance
        is_split_payment = len(payment_rows) >= 2
        has_positive_payment = payment_total > MONEY_ZERO

        payment_ids = [row.entity_id for row in payment_rows]
        evidence_ids = [row.evidence_id for row in payment_rows]

        # Duy trì thứ tự xuất hiện nhưng loại trùng.
        payment_methods = list(
            dict.fromkeys(row.payment_type for row in payment_rows)
        )

        root_cause_signal: str | None = None

        if is_split_payment and is_reconciled:
            root_cause_signal = "MULTIPLE_PAYMENTS_RECONCILED"

        return PaymentAnalysis(
            order_id=normalized_order_id,
            payment_count=len(payment_rows),
            payment_total_brl=payment_total,
            expected_total_brl=expected_total,
            reconciliation_difference_brl=difference,
            is_split_payment=is_split_payment,
            is_reconciled=is_reconciled,
            has_positive_payment=has_positive_payment,
            payment_ids=payment_ids[:MAX_PAYMENT_IDS],
            evidence_ids=evidence_ids[:MAX_EVIDENCE_IDS],
            payment_methods=payment_methods,
            root_cause_signal=root_cause_signal,
            errors=errors,
        )

    @staticmethod
    def _parse_payment_row(
        *,
        raw_row: Mapping[str, Any],
        expected_order_id: str,
    ) -> PaymentRow:
        row_order_id = str(raw_row["order_id"]).strip()

        if row_order_id != expected_order_id:
            raise ValueError(
                "Payment row order_id does not match requested order_id: "
                f"{row_order_id!r} != {expected_order_id!r}"
            )

        payment_sequential = safe_int(raw_row["payment_sequential"])
        payment_installments = safe_int(raw_row["payment_installments"])
        payment_value = to_decimal(raw_row["payment_value"])

        payment_type = str(raw_row["payment_type"]).strip()

        if not payment_type:
            raise ValueError("payment_type must not be empty")

        if payment_sequential <= 0:
            raise ValueError("payment_sequential must be greater than zero")

        if payment_installments < 0:
            raise ValueError("payment_installments must not be negative")

        if payment_value < MONEY_ZERO:
            raise ValueError("payment_value must not be negative")

        return PaymentRow(
            order_id=row_order_id,
            payment_sequential=payment_sequential,
            payment_type=payment_type,
            payment_installments=payment_installments,
            payment_value=payment_value,
        )