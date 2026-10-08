"""Display-only startup state for future launcher event integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StartupStage:
    current: int
    total: int
    title: str
    status: StageStatus = StageStatus.PENDING
    summary: str = ""


@dataclass
class StartupDisplayState:
    """Small state container; it performs no launcher or system operations."""

    stages: dict[int, StartupStage] = field(default_factory=dict)
    current_stage: int | None = None
    total_stages: int = 4
    progress: int = 0
    detail_lines: list[str] = field(default_factory=list)
    ready: bool = False
    error_message: str = ""

    def set_stage(self, current: int, total: int, title: str) -> StartupStage:
        if total < 1 or current < 1 or current > total:
            raise ValueError("stage values must satisfy 1 <= current <= total")
        self.ready = False
        self.error_message = ""
        self.current_stage = current
        self.total_stages = total
        stage = self.stages.get(current) or StartupStage(current, total, str(title))
        stage.total = total
        stage.title = str(title)
        stage.status = StageStatus.RUNNING
        self.stages[current] = stage
        return stage

    def complete_current(self, summary: str | None = None) -> StartupStage | None:
        if self.current_stage is None:
            return None
        stage = self.stages[self.current_stage]
        stage.status = StageStatus.COMPLETE
        stage.summary = str(summary or self.latest_detail or stage.title).rstrip(".")
        self.progress = round(stage.current / stage.total * 100)
        return stage

    def set_detail(self, text: str) -> None:
        self.detail_lines = [str(text)] if text else []

    def append_detail(self, text: str) -> None:
        if text:
            self.detail_lines.append(str(text))
            self.detail_lines = self.detail_lines[-2:]

    def set_progress(self, value: float) -> None:
        self.progress = max(0, min(100, round(float(value))))

    def set_error(self, message: str) -> None:
        self.ready = False
        self.error_message = str(message)
        if self.current_stage is not None:
            self.stages[self.current_stage].status = StageStatus.ERROR

    def set_ready(self) -> None:
        self.error_message = ""
        self.ready = True
        self.progress = 100

    @property
    def current(self) -> StartupStage | None:
        if self.current_stage is None:
            return None
        return self.stages.get(self.current_stage)

    @property
    def latest_detail(self) -> str:
        return self.detail_lines[-1] if self.detail_lines else ""

    @property
    def completed_summaries(self) -> list[str]:
        return [
            stage.summary or stage.title.rstrip(".")
            for _, stage in sorted(self.stages.items())
            if stage.status == StageStatus.COMPLETE
        ][-2:]
