"""Tiện ích timestamp; so sánh theo giá trị trong CSV như đề bài yêu cầu."""

from datetime import datetime


OLIST_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_olist_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, OLIST_TIMESTAMP_FORMAT)

