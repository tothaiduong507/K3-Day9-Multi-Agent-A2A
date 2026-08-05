"""Run validated cases while isolating per-case failures."""

from dataclasses import dataclass, field

from src.coordinator import Coordinator
from src.models import CaseInput
from src.output_writer import OutputWriter


@dataclass
class BatchResult:
    total: int
    succeeded: int = 0
    failed: int = 0
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.succeeded == self.total


class BatchRunner:
    def __init__(self, coordinator: Coordinator, writer: OutputWriter) -> None:
        self.coordinator = coordinator
        self.writer = writer

    def run(self, cases: list[CaseInput], *, fail_fast: bool = False) -> BatchResult:
        result = BatchResult(total=len(cases))
        self.coordinator.trace.reset()
        for case in cases:
            try:
                output = self.coordinator.run_case(case)
                target = self.writer.write(case.case_id, output)
                self.coordinator.trace.emit(
                    case_id=case.case_id,
                    agent="coordinator",
                    event="output_written",
                    details={"path": str(target)},
                )
                self.coordinator.trace.emit(
                    case_id=case.case_id,
                    agent="coordinator",
                    event="case_completed",
                )
                result.succeeded += 1
            except Exception as exc:
                result.failed += 1
                result.errors[case.case_id] = f"{type(exc).__name__}: {exc}"
                if fail_fast:
                    break
        return result
