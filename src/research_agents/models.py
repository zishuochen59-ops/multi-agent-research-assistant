from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    url: str
    text: str


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    url: str
    excerpt: str
    score: float


@dataclass
class AgentEvent:
    agent: str
    action: str
    elapsed_ms: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Workspace:
    topic: str
    questions: list[str] = field(default_factory=list)
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    synthesis: str = ""
    draft: str = ""
    critique: list[str] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
