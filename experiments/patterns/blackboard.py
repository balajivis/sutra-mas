"""Blackboard Pattern — Shared state space with independent agent contributions.

Classical Source: Nii, "Blackboard Systems" (1986)
Core Idea: Agents read from and write to a shared workspace. A control shell
           determines which agent acts next based on the current state.
Expected Advantage: Better convergence, fewer tokens (agents build on each other's
                    work instead of duplicating). LbMAS (2025) showed 13-57% improvement
                    with 3x fewer tokens.
"""

from __future__ import annotations

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class BlackboardPattern(MASPattern):
    """Blackboard coordination: shared state + knowledge sources + control shell.

    Implements Nii's (1986) three-component architecture:
    1. Blackboard (shared state space)
    2. Knowledge Sources (specialized agents)
    3. Control Shell (determines agent activation order)
    """

    name = "blackboard"
    classical_source = "Nii, 'Blackboard Systems' (1986); LbMAS (2025)"
    description = "Agents read/write to shared workspace. Control shell picks next agent."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="analyst",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Analyst knowledge source. Your job is to read the current "
                    "blackboard state and add ANALYSIS — identify key issues, patterns, and "
                    "structure. Write your findings to the blackboard. Build on what others "
                    "have written, don't repeat."
                ),
            ),
            Agent(
                name="researcher",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Researcher knowledge source. Your job is to read the current "
                    "blackboard state and add EVIDENCE — facts, references, data that support "
                    "or challenge the analysis. Write your findings to the blackboard. Build on "
                    "what others have written, don't repeat."
                ),
            ),
            Agent(
                name="synthesizer",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Synthesizer knowledge source. Your job is to read the current "
                    "blackboard state and produce SYNTHESIS — integrate the analysis and evidence "
                    "into a coherent, well-structured output. Resolve contradictions. Fill gaps. "
                    "Write your synthesis to the blackboard."
                ),
            ),
        ]

        # Initialize blackboard
        self.update_shared_state("task", task.input_data, "system")
        self.update_shared_state("contributions", [], "system")
        self.update_shared_state("iteration", 0, "system")

        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        max_rounds = self.config.get("max_rounds", 3)
        token_budget = task.max_tokens

        for round_num in range(max_rounds):
            self.update_shared_state("iteration", round_num + 1, "system")

            # Control shell: determine agent activation order based on state
            activation_order = self._control_shell(round_num)

            for agent in activation_order:
                if self.llm.total_tokens_in + self.llm.total_tokens_out > token_budget:
                    break

                # Agent reads blackboard
                blackboard_view = self._format_blackboard()

                # Agent contributes
                response = await self.llm.chat(
                    system=agent.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"## Current Blackboard State (Round {round_num + 1})\n\n"
                            f"{blackboard_view}\n\n"
                            "Read the blackboard and add your contribution. "
                            "Build on what's already there. Don't repeat existing content."
                        ),
                    }],
                    max_tokens=2048,
                )

                agent.total_tokens_in += response.tokens_in
                agent.total_tokens_out += response.tokens_out

                # Write to blackboard
                contribution = {
                    "agent": agent.name,
                    "round": round_num + 1,
                    "content": response.content,
                }
                contributions = self.get_shared_state("contributions")
                contributions.append(contribution)
                self.update_shared_state("contributions", contributions, agent.name)

                # Record message
                self.send_message(Message(
                    sender=agent.name,
                    receiver="__blackboard__",
                    content=response.content,
                    performative="inform",
                    token_count=response.tokens_in + response.tokens_out,
                ))

        # Final synthesis
        final_output = self._get_final_synthesis()

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=max_rounds,
            final_output=final_output,
            messages=self.messages,
        )

    def _control_shell(self, round_num: int) -> list[Agent]:
        """Determine agent activation order based on blackboard state.

        Round 0: Analyst first (break down the problem)
        Round 1: Researcher first (add evidence)
        Round 2+: Synthesizer first (integrate)
        """
        if round_num == 0:
            return [self.agents[0], self.agents[1]]  # analyst, researcher
        elif round_num == 1:
            return [self.agents[1], self.agents[2]]  # researcher, synthesizer
        else:
            return [self.agents[2]]  # synthesizer only

    def _format_blackboard(self) -> str:
        """Format current blackboard state for agent consumption."""
        lines = [f"**Task**: {self.get_shared_state('task')}\n"]
        contributions = self.get_shared_state("contributions") or []
        for c in contributions:
            lines.append(f"### {c['agent']} (Round {c['round']})")
            lines.append(c["content"])
            lines.append("")
        return "\n".join(lines)

    def _get_final_synthesis(self) -> str:
        """Extract the final output from the blackboard."""
        contributions = self.get_shared_state("contributions") or []
        # Return the last synthesizer contribution, or all contributions if no synthesizer
        for c in reversed(contributions):
            if c["agent"] == "synthesizer":
                return c["content"]
        # Fallback: concatenate all
        return "\n\n".join(c["content"] for c in contributions)
