"""Core abstractions for the MAS pattern test harness."""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    """Agent roles in a multi-agent system."""
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    CRITIC = "critic"
    GENERATOR = "generator"
    BIDDER = "bidder"
    OBSERVER = "observer"


@dataclass
class Message:
    """A message between agents or to/from the shared state."""
    sender: str
    receiver: str  # agent name or "__blackboard__" or "__broadcast__"
    content: str
    performative: str = "inform"  # inform, request, propose, accept, reject, cfp
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0

    def __repr__(self) -> str:
        return f"Message({self.sender}->{self.receiver}: {self.performative}, {len(self.content)} chars)"


@dataclass
class Agent:
    """An agent in the multi-agent system."""
    name: str
    role: Role
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    message_history: list[Message] = field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0

    @property
    def total_tokens(self) -> int:
        return self.total_tokens_in + self.total_tokens_out


@dataclass
class BenchmarkTask:
    """A benchmark task for evaluating MAS patterns."""
    id: str
    name: str
    description: str
    input_data: str
    expected_aspects: list[str]  # aspects a good solution should cover
    evaluation_rubric: dict[str, str]  # criterion -> description
    max_rounds: int = 10
    max_tokens: int = 50000


@dataclass
class ExperimentResult:
    """Result of running a pattern on a benchmark task."""
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pattern_name: str = ""
    benchmark_name: str = ""
    model: str = ""
    num_agents: int = 0
    num_rounds: int = 0
    total_tokens: int = 0
    wall_time_seconds: float = 0.0
    quality_score: float = 0.0  # 0-100
    final_output: str = ""
    messages: list[Message] = field(default_factory=list)
    agent_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def token_efficiency(self) -> float:
        """Quality points per 1000 tokens."""
        if self.total_tokens == 0:
            return 0.0
        return (self.quality_score / self.total_tokens) * 1000


class MASPattern(ABC):
    """Abstract base class for multi-agent coordination patterns.

    Each pattern implements a specific coordination mechanism from classical
    MAS literature and adapts it for LLM agents.
    """

    name: str = "unnamed"
    classical_source: str = "unknown"
    description: str = ""

    def __init__(self, llm_client: Any, config: dict[str, Any] | None = None):
        self.llm = llm_client
        self.config = config or {}
        self.agents: list[Agent] = []
        self.messages: list[Message] = []
        self.shared_state: dict[str, Any] = {}

    @abstractmethod
    def setup(self, task: BenchmarkTask) -> list[Agent]:
        """Configure agents for this task. Returns the list of agents."""
        ...

    @abstractmethod
    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        """Execute the pattern on a task. Returns structured result."""
        ...

    def send_message(self, msg: Message) -> None:
        """Record a message and deliver to recipient."""
        self.messages.append(msg)
        for agent in self.agents:
            if agent.name == msg.receiver or msg.receiver == "__broadcast__":
                agent.message_history.append(msg)

    def get_shared_state(self, key: str | None = None) -> Any:
        """Read from shared state (blackboard)."""
        if key is None:
            return self.shared_state
        return self.shared_state.get(key)

    def update_shared_state(self, key: str, value: Any, agent_name: str = "") -> None:
        """Write to shared state (blackboard)."""
        self.shared_state[key] = value
        # Record as message for tracing
        self.messages.append(Message(
            sender=agent_name or "system",
            receiver="__blackboard__",
            content=f"Updated {key}",
            performative="inform",
            metadata={"key": key},
        ))
