from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

SENSITIVE_METADATA_KEYS = {
    "content",
    "message",
    "messages",
    "prompt",
    "api_key",
    "authorization",
    "password",
    "secret",
    "system_prompt",
    "token",
    "user_message",
    "user_prompt",
}


@dataclass(frozen=True)
class StageTrace:
    correlation_id: str
    game_id: str
    turn_id: int
    stage: str
    duration_ms: float
    status: str
    accepted: bool | None = None
    model: str | None = None
    prompt_version: str | None = None
    token_usage: dict[str, int] | None = None
    retry_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnTrace:
    correlation_id: str
    game_id: str
    turn_id: int | None
    duration_ms: float
    status: str


class TraceRecorder(Protocol):
    def record(self, trace: StageTrace) -> None: ...

    def record_turn(self, trace: TurnTrace) -> None: ...


class NoOpTraceRecorder:
    def record(self, trace: StageTrace) -> None:
        return None

    def record_turn(self, trace: TurnTrace) -> None:
        return None


class InMemoryTraceRecorder:
    def __init__(self) -> None:
        self.traces: list[StageTrace] = []
        self.turn_traces: list[TurnTrace] = []

    def record(self, trace: StageTrace) -> None:
        self.traces.append(trace)

    def record_turn(self, trace: TurnTrace) -> None:
        self.turn_traces.append(trace)


def safe_metadata(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if metadata is None:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_METADATA_KEYS:
            safe[key] = "[redacted]"
        else:
            safe[key] = value
    return safe
