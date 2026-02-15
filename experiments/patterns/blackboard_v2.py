"""Blackboard V2 — LLM-Powered Control Shell + Incremental Summarization.

Classical Source: Nii, "Blackboard Systems" (1986)
Improvement Over V1:
  1. LLM-powered control shell (dynamic agent selection based on blackboard content)
  2. Incremental summarization (compress old contributions to prevent context bloat)
  3. Early stopping (control shell can declare the board "complete")
  4. Higher max_tokens for synthesizer (no truncation)

Motivated by: V1 experiment showing single agent (90) >> naive blackboard (62) due to
static round-robin control shell and quadratic context growth.
"""

from __future__ import annotations

import json

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class BlackboardV2Pattern(MASPattern):
    """Blackboard V2: faithful implementation of Nii's three-component architecture.

    Key difference from V1: the control shell is an LLM that inspects the blackboard
    and decides which agent to activate (or whether to stop), rather than following
    a fixed round-robin schedule.
    """

    name = "blackboard_v2"
    classical_source = "Nii, 'Blackboard Systems' (1986); LbMAS (Han & Zhang, 2025)"
    description = "LLM-powered control shell + incremental summarization + early stopping."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="analyst",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Analyst. Read the blackboard and identify key issues, "
                    "patterns, structure, and gaps. Be specific and actionable. "
                    "Only add NEW analysis — never repeat what's already on the board."
                ),
            ),
            Agent(
                name="researcher",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Researcher. Read the blackboard and add EVIDENCE — "
                    "facts, references, data, specific examples that support or challenge "
                    "the analysis. Only add NEW evidence — never repeat what's on the board."
                ),
            ),
            Agent(
                name="synthesizer",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Synthesizer. Read the blackboard and produce a COMPLETE, "
                    "FINAL synthesis. Integrate all analysis and evidence into a coherent, "
                    "well-structured output. Resolve contradictions. Fill gaps. "
                    "Your output should stand alone as the definitive answer."
                ),
            ),
        ]

        self._agent_map = {a.name: a for a in self.agents}

        # Initialize blackboard
        self.update_shared_state("task", task.input_data, "system")
        self.update_shared_state("contributions", [], "system")
        self.update_shared_state("summary", "", "system")
        self.update_shared_state("iteration", 0, "system")

        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        max_rounds = self.config.get("max_rounds", 5)
        token_budget = task.max_tokens
        actual_rounds = 0

        for round_num in range(max_rounds):
            self.update_shared_state("iteration", round_num + 1, "system")
            actual_rounds = round_num + 1

            if self.llm.total_tokens_in + self.llm.total_tokens_out > token_budget * 0.9:
                break

            # LLM-powered control shell decides next action
            decision = await self._control_shell(round_num)

            if decision["action"] == "stop":
                # Early stopping — board is complete
                self.send_message(Message(
                    sender="control_shell",
                    receiver="__blackboard__",
                    content=f"STOP: {decision.get('reason', 'Board complete')}",
                    performative="inform",
                ))
                break

            agent_name = decision["agent"]
            agent = self._agent_map.get(agent_name)
            if not agent:
                # Fallback: use synthesizer
                agent = self.agents[2]

            # Prepare blackboard view with summarization
            blackboard_view = self._format_blackboard_summarized()

            # Agent contributes (higher max_tokens for synthesizer)
            agent_max_tokens = 4096 if agent.name == "synthesizer" else 2048

            response = await self.llm.chat(
                system=agent.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"## Blackboard (Round {round_num + 1})\n\n"
                        f"{blackboard_view}\n\n"
                        f"## Your Task\n"
                        f"The control shell selected you because: {decision.get('reason', 'your expertise is needed')}\n\n"
                        "Add your contribution. Be concise and non-redundant."
                    ),
                }],
                max_tokens=agent_max_tokens,
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

            self.send_message(Message(
                sender=agent.name,
                receiver="__blackboard__",
                content=response.content,
                performative="inform",
                token_count=response.tokens_in + response.tokens_out,
            ))

            # Incremental summarization: compress older contributions
            if len(contributions) >= 3:
                await self._summarize_old_contributions()

        # Final synthesis pass if last contribution wasn't from synthesizer
        contributions = self.get_shared_state("contributions") or []
        last_agent = contributions[-1]["agent"] if contributions else ""

        if last_agent != "synthesizer" and (
            self.llm.total_tokens_in + self.llm.total_tokens_out < token_budget * 0.95
        ):
            blackboard_view = self._format_blackboard_summarized()
            response = await self.llm.chat(
                system=self.agents[2].system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"## Final Blackboard State\n\n{blackboard_view}\n\n"
                        "Produce the COMPLETE final synthesis. This is the definitive output."
                    ),
                }],
                max_tokens=4096,
            )
            self.agents[2].total_tokens_in += response.tokens_in
            self.agents[2].total_tokens_out += response.tokens_out

            contributions.append({
                "agent": "synthesizer",
                "round": actual_rounds + 1,
                "content": response.content,
            })
            self.update_shared_state("contributions", contributions, "synthesizer")

        final_output = self._get_final_synthesis()

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=actual_rounds,
            final_output=final_output,
            messages=self.messages,
            metadata={"control_shell": "llm_powered", "summarization": True},
        )

    async def _control_shell(self, round_num: int) -> dict:
        """LLM-powered control shell — inspects blackboard, decides next agent or stop.

        This is the key innovation from Nii (1986) that V1 was missing.
        The control shell reads the current board state and makes a content-aware
        decision about which knowledge source to activate next.
        """
        contributions = self.get_shared_state("contributions") or []

        # First round: always start with analyst (no need for LLM decision)
        if round_num == 0:
            return {"action": "activate", "agent": "analyst", "reason": "Initial analysis needed"}

        # Build a compact view of what's on the board
        board_summary = []
        for c in contributions:
            board_summary.append(f"- {c['agent']} (round {c['round']}): contributed {len(c['content'])} chars")

        summary_text = self.get_shared_state("summary") or "(no summary yet)"

        response = await self.llm.chat(
            system=(
                "You are the Control Shell of a blackboard system. Your job is to inspect "
                "the current state of the blackboard and decide what happens next. "
                "Available agents: analyst (identifies issues), researcher (adds evidence), "
                "synthesizer (integrates everything into final output). "
                "You MUST return valid JSON."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"## Task\n{self.get_shared_state('task')[:500]}\n\n"
                    f"## Board State (Round {round_num + 1})\n"
                    f"Contributions so far:\n" + "\n".join(board_summary) + "\n\n"
                    f"Current summary:\n{summary_text[:500]}\n\n"
                    "## Decision Required\n"
                    "Choose ONE:\n"
                    '1. Activate an agent: {"action": "activate", "agent": "analyst|researcher|synthesizer", "reason": "..."}\n'
                    '2. Stop (board is complete): {"action": "stop", "reason": "..."}\n\n'
                    "Guidelines:\n"
                    "- If analysis is thin, activate analyst\n"
                    "- If claims lack evidence, activate researcher\n"
                    "- If board has enough material for a complete answer, activate synthesizer\n"
                    "- If synthesizer has already produced a good output, STOP\n"
                    "- Prefer stopping over redundant rounds\n\n"
                    "Return JSON only:"
                ),
            }],
            max_tokens=200,
            temperature=0.0,
        )

        try:
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, KeyError):
            # Fallback: round-based heuristic
            agents = ["researcher", "synthesizer", "synthesizer"]
            idx = min(round_num, len(agents) - 1)
            return {"action": "activate", "agent": agents[idx], "reason": "fallback heuristic"}

    async def _summarize_old_contributions(self) -> None:
        """Compress older contributions into a summary to prevent context bloat.

        Keeps the most recent 2 contributions in full, summarizes the rest.
        This is the key to preventing the quadratic token growth seen in V1.
        """
        contributions = self.get_shared_state("contributions") or []
        if len(contributions) <= 2:
            return

        # Contributions to summarize (all but the last 2)
        old = contributions[:-2]
        old_text = "\n\n".join(
            f"**{c['agent']}** (round {c['round']}): {c['content'][:500]}"
            for c in old
        )

        response = await self.llm.chat(
            system="Summarize the following contributions into a concise paragraph. Preserve all key findings, evidence, and conclusions. Remove redundancy.",
            messages=[{
                "role": "user",
                "content": f"Summarize these blackboard contributions:\n\n{old_text}",
            }],
            max_tokens=500,
            temperature=0.0,
        )

        self.update_shared_state("summary", response.content, "control_shell")

    def _format_blackboard_summarized(self) -> str:
        """Format blackboard with summarization — old contributions compressed."""
        lines = [f"**Task**: {self.get_shared_state('task')}\n"]

        summary = self.get_shared_state("summary")
        contributions = self.get_shared_state("contributions") or []

        if summary:
            lines.append("### Summary of Earlier Contributions")
            lines.append(summary)
            lines.append("")
            # Only show the last 2 contributions in full
            recent = contributions[-2:] if len(contributions) > 2 else contributions
        else:
            recent = contributions

        for c in recent:
            lines.append(f"### {c['agent']} (Round {c['round']})")
            lines.append(c["content"])
            lines.append("")

        return "\n".join(lines)

    def _get_final_synthesis(self) -> str:
        """Extract the final output from the blackboard."""
        contributions = self.get_shared_state("contributions") or []
        for c in reversed(contributions):
            if c["agent"] == "synthesizer":
                return c["content"]
        return "\n\n".join(c["content"] for c in contributions)
