"""Quy ước Decimal chung cho dữ liệu BRL."""

from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def as_decimal(value: str | int | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_brl(value: Decimal) -> Decimal:
    """Chỉ gọi tại ranh giới output."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)

