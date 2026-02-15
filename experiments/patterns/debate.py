"""Debate Pattern — Agents argue opposing positions.

Classical Source: Dialectical reasoning; Du et al., "Improving Factual Accuracy" (2023)
Core Idea: Multiple agents take opposing positions and argue. A judge evaluates.
           Useful for fact-checking and reducing hallucination.
Expected Advantage: Improved factual accuracy. Research shows debate converges toward
                    majority opinion. Generator/Critic variant more effective for quality.
Caution: Temperature doesn't actually create cognitive diversity (Martingale result).
"""

from __future__ import annotations

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class DebatePattern(MASPattern):
    """Structured debate: agents argue, judge evaluates.

    Implements a simplified dialectical process with explicit position-taking
    and a neutral judge who synthesizes.
    """

    name = "debate"
    classical_source = "Dialectical reasoning; Du et al. (2023)"
    description = "Agents take opposing positions, argue with evidence, judge synthesizes."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="proponent",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Proponent. Your job is to argue FOR the strongest "
                    "interpretation of the topic. Be thorough, cite evidence, and make "
                    "the best possible case. When you see the Opponent's arguments, "
                    "address them directly — concede valid points, rebut weak ones."
                ),
            ),
            Agent(
                name="opponent",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Opponent. Your job is to argue AGAINST or present "
                    "alternative perspectives. Find weaknesses, edge cases, counter-examples. "
                    "Be intellectually honest — don't argue against things that are clearly true. "
                    "When you see the Proponent's arguments, address them directly."
                ),
            ),
            Agent(
                name="judge",
                role=Role.COORDINATOR,
                system_prompt=(
                    "You are the Judge. After hearing both sides, produce the definitive "
                    "synthesis. Your job is NOT to split the difference — it's to determine "
                    "what's actually correct based on the strength of arguments and evidence.\n\n"
                    "For each point of contention:\n"
                    "1. State what each side argued\n"
                    "2. Assess the evidence\n"
                    "3. Render your judgment\n\n"
                    "Produce a comprehensive, balanced, well-structured final output."
                ),
            ),
        ]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        proponent, opponent, judge = self.agents
        max_rounds = self.config.get("debate_rounds", 2)

        proponent_args = []
        opponent_args = []

        for round_num in range(max_rounds):
            # Proponent argues
            pro_context = self._build_debate_context("proponent", proponent_args, opponent_args)
            pro_response = await self.llm.chat(
                system=proponent.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Round {round_num + 1} of {max_rounds}.\n\n"
                        f"Task: {task.input_data}\n\n"
                        f"{pro_context}\n\n"
                        "Present your arguments."
                    ),
                }],
                max_tokens=2048,
            )
            proponent.total_tokens_in += pro_response.tokens_in
            proponent.total_tokens_out += pro_response.tokens_out
            proponent_args.append(pro_response.content)

            self.send_message(Message(
                sender="proponent",
                receiver="__broadcast__",
                content=pro_response.content,
                performative="inform",
                token_count=pro_response.tokens_in + pro_response.tokens_out,
            ))

            # Opponent responds
            opp_context = self._build_debate_context("opponent", proponent_args, opponent_args)
            opp_response = await self.llm.chat(
                system=opponent.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Round {round_num + 1} of {max_rounds}.\n\n"
                        f"Task: {task.input_data}\n\n"
                        f"{opp_context}\n\n"
                        "Present your counter-arguments."
                    ),
                }],
                max_tokens=2048,
            )
            opponent.total_tokens_in += opp_response.tokens_in
            opponent.total_tokens_out += opp_response.tokens_out
            opponent_args.append(opp_response.content)

            self.send_message(Message(
                sender="opponent",
                receiver="__broadcast__",
                content=opp_response.content,
                performative="inform",
                token_count=opp_response.tokens_in + opp_response.tokens_out,
            ))

        # Judge synthesizes
        full_debate = self._format_full_debate(proponent_args, opponent_args)
        judge_response = await self.llm.chat(
            system=judge.system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    f"Task: {task.input_data}\n\n"
                    f"## Full Debate Transcript\n\n{full_debate}\n\n"
                    "Render your judgment. Produce the definitive answer."
                ),
            }],
            max_tokens=4096,
        )
        judge.total_tokens_in += judge_response.tokens_in
        judge.total_tokens_out += judge_response.tokens_out

        return ExperimentResult(
            num_agents=3,
            num_rounds=max_rounds,
            final_output=judge_response.content,
            messages=self.messages,
            metadata={"debate_rounds": max_rounds},
        )

    def _build_debate_context(
        self, perspective: str, pro_args: list[str], opp_args: list[str]
    ) -> str:
        if not pro_args and not opp_args:
            return "This is the opening round. No prior arguments."

        lines = ["## Prior Arguments\n"]
        for i, (p, o) in enumerate(zip(pro_args, opp_args)):
            lines.append(f"### Round {i+1}")
            lines.append(f"**Proponent**: {p}")
            lines.append(f"**Opponent**: {o}")
            lines.append("")

        # Handle unequal lengths
        if len(pro_args) > len(opp_args):
            lines.append(f"### Latest from Proponent")
            lines.append(pro_args[-1])

        return "\n".join(lines)

    def _format_full_debate(self, pro_args: list[str], opp_args: list[str]) -> str:
        lines = []
        for i in range(max(len(pro_args), len(opp_args))):
            lines.append(f"### Round {i+1}")
            if i < len(pro_args):
                lines.append(f"**Proponent**:\n{pro_args[i]}")
            if i < len(opp_args):
                lines.append(f"**Opponent**:\n{opp_args[i]}")
            lines.append("")
        return "\n".join(lines)
