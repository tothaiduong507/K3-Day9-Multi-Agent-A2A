"""CLI chạy một case hoặc toàn bộ thư mục input."""

import argparse
import json
from pathlib import Path

from src.agents.delivery import DeliveryAgent
from src.agents.order_seller import OrderSellerAgent
from src.agents.payment import PaymentAgent
from src.agents.policy import PolicyAgent
from src.agents.verifier import VerifierAgent
from src.config import DEFAULT_SETTINGS
from src.coordinator import Coordinator
from src.data_loader import OlistDataLoader
from src.models import CaseInput
from src.trace_logger import TraceLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve Olist dispute cases")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_SETTINGS.input_dir)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SETTINGS.output_dir)
    parser.add_argument("--case", help="Example: EC_001; omit to run all cases")
    return parser


def build_coordinator() -> Coordinator:
    data = OlistDataLoader(DEFAULT_SETTINGS.data_dir)
    data.load()
    return Coordinator(
        data=data,
        order_agent=OrderSellerAgent(),
        payment_agent=PaymentAgent(),
        delivery_agent=DeliveryAgent(),
        policy_agent=PolicyAgent(),
        verifier_agent=VerifierAgent(),
        trace=TraceLogger(DEFAULT_SETTINGS.trace_path),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    coordinator = build_coordinator()
    coordinator.trace.reset()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    paths = [args.input_dir / f"{args.case}.json"] if args.case else sorted(
        args.input_dir.glob("EC_*.json")
    )
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        case = CaseInput.from_dict(payload)
        output = coordinator.run_case(case)
        target = args.output_dir / f"{case.case_id}.json"
        target.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0
