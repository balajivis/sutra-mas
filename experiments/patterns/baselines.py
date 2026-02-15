"""Baseline patterns for comparison — single agent and naive multi-agent."""

from __future__ import annotations

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class SingleAgentBaseline(MASPattern):
    """Single agent baseline. One agent, one shot, no coordination."""

    name = "baseline_single"
    classical_source = "Control condition"
    description = "Single agent given the full task. No coordination overhead."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="solo",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are an expert assistant. Complete the following task thoroughly. "
                    "Be comprehensive, accurate, and well-structured in your response."
                ),
            )
        ]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        agent = self.agents[0]

        response = await self.llm.chat(
            system=agent.system_prompt,
            messages=[{"role": "user", "content": task.input_data}],
            max_tokens=min(task.max_tokens, 8192),
        )

        agent.total_tokens_in = response.tokens_in
        agent.total_tokens_out = response.tokens_out

        return ExperimentResult(
            num_agents=1,
            num_rounds=1,
            final_output=response.content,
            messages=[],
        )


class NaiveMultiAgentBaseline(MASPattern):
    """Naive multi-agent baseline. Multiple agents work independently, outputs concatenated.

    This represents the "bag of agents" anti-pattern — no coordination,
    no shared state, no structured communication. Kim et al. (2025) showed
    this leads to 17.2x error amplification.
    """

    name = "baseline_naive"
    classical_source = "Anti-pattern (bag of agents)"
    description = "Multiple agents work independently. No coordination. Outputs concatenated."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        num_agents = self.config.get("num_agents", 3)
        self.agents = [
            Agent(
                name=f"agent_{i}",
                role=Role.SPECIALIST,
                system_prompt=(
                    f"You are Agent {i+1} of {num_agents}. Complete the following task. "
                    "You are working independently — you cannot see other agents' work."
                ),
            )
            for i in range(num_agents)
        ]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        outputs = []

        for agent in self.agents:
            response = await self.llm.chat(
                system=agent.system_prompt,
                messages=[{"role": "user", "content": task.input_data}],
                max_tokens=min(task.max_tokens // len(self.agents), 4096),
            )

            agent.total_tokens_in = response.tokens_in
            agent.total_tokens_out = response.tokens_out
            outputs.append(f"## {agent.name}\n\n{response.content}")

        # Simple concatenation — no synthesis, no coordination
        final_output = "\n\n---\n\n".join(outputs)

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=1,
            final_output=final_output,
            messages=[],
        )
