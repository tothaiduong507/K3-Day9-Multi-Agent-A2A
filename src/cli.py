"""CLI chạy một case hoặc toàn bộ thư mục input."""

import argparse
from pathlib import Path

from src.agents.delivery import DeliveryAgent
from src.agents.order_seller import OrderSellerAgent
from src.agents.payment import PaymentAgent
from src.agents.policy import PolicyAgent
from src.agents.verifier import VerifierAgent
from src.batch_runner import BatchRunner
from src.case_loader import CaseInputError, discover_case_paths, load_cases
from src.config import DEFAULT_SETTINGS
from src.coordinator import Coordinator
from src.data_loader import OlistDataLoader
from src.output_writer import OutputWriter
from src.trace_logger import TraceLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve Olist dispute cases")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_SETTINGS.input_dir)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SETTINGS.output_dir)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_SETTINGS.data_dir)
    parser.add_argument("--trace-path", type=Path, default=DEFAULT_SETTINGS.trace_path)
    parser.add_argument("--case", help="Example: EC_001; omit to run all cases")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def build_coordinator(data_dir: Path, trace_path: Path) -> Coordinator:
    data = OlistDataLoader(data_dir)
    data.load()
    return Coordinator(
        data=data,
        order_agent=OrderSellerAgent(),
        payment_agent=PaymentAgent(),
        delivery_agent=DeliveryAgent(),
        policy_agent=PolicyAgent(),
        verifier_agent=VerifierAgent(),
        trace=TraceLogger(trace_path),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = discover_case_paths(args.input_dir, args.case)
        cases = load_cases(paths)
        coordinator = build_coordinator(args.data_dir, args.trace_path)
    except (CaseInputError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.validate_only:
        print(
            f"Validation passed: {len(cases)} case(s); "
            f"dataset={coordinator.data.stats}"
        )
        return 0

    runner = BatchRunner(coordinator, OutputWriter(args.output_dir))
    result = runner.run(cases, fail_fast=args.fail_fast)
    print(
        f"Run completed: total={result.total}, "
        f"succeeded={result.succeeded}, failed={result.failed}"
    )
    for case_id, error in result.errors.items():
        print(f"  {case_id}: {error}")
    return 0 if result.ok else 1
