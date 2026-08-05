"""Cấu hình dùng chung; không đặt secret hoặc API key tại đây."""

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = PROJECT_ROOT / "data"
    input_dir: Path = PROJECT_ROOT / "input"
    output_dir: Path = PROJECT_ROOT / "output"
    trace_path: Path = PROJECT_ROOT / "logging" / "trace.jsonl"
    metadata_path: Path = PROJECT_ROOT / "logging" / "metadata.json"
    policy_version: str = "EC_POLICY_V1"
    payment_tolerance_brl: str = "0.10"


DEFAULT_SETTINGS = Settings()

