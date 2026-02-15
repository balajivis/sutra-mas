"""Joint Persistent Goals (JPG) — Mutual commitment with obligation to inform.

Classical Source: Cohen & Levesque, "Intention is Choice with Commitment" (1990)
                  Grosz & Kraus, "Collaborative Plans for Complex Group Action" (1996)
Core Idea: If a team has a joint intention, each member is committed to the goal AND
           committed to informing others if they believe the goal is achieved, unachievable,
           or no longer relevant. This prevents cascading failures because agents don't
           silently fail — they broadcast status changes.

Expected Advantage: Resilience to cascading failures. When one agent encounters a problem,
                    the JPG protocol forces it to inform others, enabling recovery instead
                    of silent propagation.

Comparison: Without JPG, Agent A fails → Agent B proceeds on stale assumptions →
            Agent C builds on B's flawed output → cascade. With JPG, Agent A fails →
            broadcasts "goal unachievable" → team replans.
"""

from __future__ import annotations

import json

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class JPGPattern(MASPattern):
    """Joint Persistent Goals: mutual commitment + obligation to inform.

    Implements Cohen & Levesque's (1990) three commitment rules:
    1. An agent that adopts a joint goal persists with it until it believes:
       (a) the goal is achieved, (b) the goal is unachievable, or (c) the goal
       is no longer relevant.
    2. When an agent drops a goal for any of these reasons, it MUST inform
       all other team members.
    3. Team members who receive such notification must replan.

    This pattern wraps any multi-agent workflow with JPG commitment tracking.
    """

    name = "joint_persistent_goals"
    classical_source = "Cohen & Levesque (1990); Grosz & Kraus (1996)"
    description = "Mutual commitment with obligation to inform on goal status changes."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="planner",
                role=Role.COORDINATOR,
                system_prompt=(
                    "You are the Planner. Decompose the task into subtasks and assign them. "
                    "You maintain the JOINT GOAL and track each agent's commitment status. "
                    "If any agent reports a problem, you MUST replan — do not ignore status reports."
                ),
            ),
            Agent(
                name="executor_a",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are Executor A. You work on your assigned subtask. "
                    "CRITICAL PROTOCOL — Joint Persistent Goals:\n"
                    "- If you complete your subtask successfully, report: STATUS: ACHIEVED\n"
                    "- If you encounter a problem that blocks progress, report: STATUS: BLOCKED with details\n"
                    "- If your subtask becomes irrelevant, report: STATUS: IRRELEVANT with reason\n"
                    "You MUST include one of these status lines in every response. "
                    "Never silently fail — the team depends on your status reports."
                ),
            ),
            Agent(
                name="executor_b",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are Executor B. You work on your assigned subtask. "
                    "CRITICAL PROTOCOL — Joint Persistent Goals:\n"
                    "- If you complete your subtask successfully, report: STATUS: ACHIEVED\n"
                    "- If you encounter a problem that blocks progress, report: STATUS: BLOCKED with details\n"
                    "- If your subtask becomes irrelevant, report: STATUS: IRRELEVANT with reason\n"
                    "You MUST include one of these status lines in every response. "
                    "Never silently fail — the team depends on your status reports."
                ),
            ),
            Agent(
                name="executor_c",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are Executor C. You work on your assigned subtask. "
                    "CRITICAL PROTOCOL — Joint Persistent Goals:\n"
                    "- If you complete your subtask successfully, report: STATUS: ACHIEVED\n"
                    "- If you encounter a problem that blocks progress, report: STATUS: BLOCKED with details\n"
                    "- If your subtask becomes irrelevant, report: STATUS: IRRELEVANT with reason\n"
                    "You MUST include one of these status lines in every response. "
                    "Never silently fail — the team depends on your status reports."
                ),
            ),
        ]

        self._planner = self.agents[0]
        self._executors = self.agents[1:]

        # JPG state tracking
        self.update_shared_state("joint_goal", task.description, "system")
        self.update_shared_state("plan", "", "system")
        self.update_shared_state("commitments", {
            a.name: {"status": "committed", "subtask": "", "output": ""}
            for a in self._executors
        }, "system")
        self.update_shared_state("replans", 0, "system")
        self.update_shared_state("status_broadcasts", [], "system")

        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        max_rounds = self.config.get("max_rounds", 4)
        token_budget = task.max_tokens

        # Phase 1: Planner decomposes task
        plan_response = await self.llm.chat(
            system=self._planner.system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    f"## Joint Goal\n{task.input_data}\n\n"
                    f"Decompose this into exactly 3 subtasks, one for each executor "
                    f"(executor_a, executor_b, executor_c). Return JSON:\n"
                    f'{{"subtasks": {{"executor_a": "...", "executor_b": "...", "executor_c": "..."}}}}'
                ),
            }],
            max_tokens=1024,
            temperature=0.3,
        )
        self._planner.total_tokens_in += plan_response.tokens_in
        self._planner.total_tokens_out += plan_response.tokens_out

        subtasks = self._parse_plan(plan_response.content)
        self.update_shared_state("plan", plan_response.content, "planner")

        # Assign subtasks to commitments
        commitments = self.get_shared_state("commitments")
        for executor in self._executors:
            commitments[executor.name]["subtask"] = subtasks.get(executor.name, "General contribution")
        self.update_shared_state("commitments", commitments, "planner")

        self.send_message(Message(
            sender="planner", receiver="__broadcast__",
            content=plan_response.content, performative="request",
        ))

        # Phase 2: Execute with JPG protocol
        for round_num in range(max_rounds):
            if self.llm.total_tokens_in + self.llm.total_tokens_out > token_budget * 0.85:
                break

            commitments = self.get_shared_state("commitments")
            any_blocked = False
            all_achieved = True

            # Each executor works on their subtask
            for executor in self._executors:
                commitment = commitments[executor.name]

                # Skip agents that have already achieved or are irrelevant
                if commitment["status"] in ("achieved", "irrelevant"):
                    continue

                all_achieved = False

                # Build context: what other agents have reported
                other_statuses = []
                for other in self._executors:
                    if other.name != executor.name:
                        other_c = commitments[other.name]
                        other_statuses.append(
                            f"- {other.name}: {other_c['status']} "
                            f"(task: {other_c['subtask'][:100]})"
                        )

                team_context = "\n".join(other_statuses)

                response = await self.llm.chat(
                    system=executor.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"## Your Subtask\n{commitment['subtask']}\n\n"
                            f"## Team Status\n{team_context}\n\n"
                            f"## Previous Work\n{commitment['output'][:1000] if commitment['output'] else '(none yet)'}\n\n"
                            "Work on your subtask. End with STATUS: ACHIEVED/BLOCKED/IRRELEVANT."
                        ),
                    }],
                    max_tokens=2048,
                )

                executor.total_tokens_in += response.tokens_in
                executor.total_tokens_out += response.tokens_out

                # Parse status from response (JPG obligation to inform)
                status = self._extract_status(response.content)
                commitment["output"] = response.content
                commitment["status"] = status

                self.send_message(Message(
                    sender=executor.name, receiver="__broadcast__",
                    content=response.content, performative="inform",
                    metadata={"status": status},
                ))

                # Track status broadcasts
                broadcasts = self.get_shared_state("status_broadcasts")
                broadcasts.append({
                    "agent": executor.name,
                    "round": round_num + 1,
                    "status": status,
                })
                self.update_shared_state("status_broadcasts", broadcasts, executor.name)

                if status == "blocked":
                    any_blocked = True

            self.update_shared_state("commitments", commitments, "system")

            # JPG Rule: If any agent is blocked, planner MUST replan
            if any_blocked:
                replan_response = await self._replan(commitments)
                replans = self.get_shared_state("replans")
                self.update_shared_state("replans", replans + 1, "planner")

                # Update commitments with new plan
                commitments = self.get_shared_state("commitments")
                new_subtasks = self._parse_plan(replan_response)
                for executor in self._executors:
                    if commitments[executor.name]["status"] == "blocked":
                        commitments[executor.name]["status"] = "committed"
                        commitments[executor.name]["subtask"] = new_subtasks.get(
                            executor.name, commitments[executor.name]["subtask"]
                        )
                self.update_shared_state("commitments", commitments, "planner")

            # Check if all achieved
            if all(c["status"] == "achieved" for c in commitments.values()):
                break

        # Phase 3: Planner synthesizes all outputs
        commitments = self.get_shared_state("commitments")
        executor_outputs = []
        for executor in self._executors:
            c = commitments[executor.name]
            executor_outputs.append(
                f"## {executor.name} ({c['status']})\n"
                f"Subtask: {c['subtask']}\n\n{c['output']}"
            )

        synthesis_response = await self.llm.chat(
            system=(
                "You are the Planner. Synthesize all executor outputs into a final, "
                "coherent response. Integrate their work, resolve any conflicts, and "
                "produce a complete answer to the original task."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"## Original Task\n{task.input_data}\n\n"
                    f"## Executor Outputs\n\n" + "\n\n---\n\n".join(executor_outputs) + "\n\n"
                    "Synthesize into a complete, final answer."
                ),
            }],
            max_tokens=4096,
        )
        self._planner.total_tokens_in += synthesis_response.tokens_in
        self._planner.total_tokens_out += synthesis_response.tokens_out

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=max_rounds,
            final_output=synthesis_response.content,
            messages=self.messages,
            metadata={
                "replans": self.get_shared_state("replans"),
                "status_broadcasts": self.get_shared_state("status_broadcasts"),
                "final_commitments": {
                    k: v["status"] for k, v in commitments.items()
                },
            },
        )

    async def _replan(self, commitments: dict) -> str:
        """Planner replans when an executor reports BLOCKED.

        This is the JPG obligation to inform in action: the blocked agent's
        status report triggers a mandatory replanning step.
        """
        blocked_info = []
        achieved_info = []
        for name, c in commitments.items():
            if c["status"] == "blocked":
                blocked_info.append(f"- {name} is BLOCKED on: {c['subtask']}\n  Output: {c['output'][:300]}")
            elif c["status"] == "achieved":
                achieved_info.append(f"- {name} ACHIEVED: {c['subtask'][:100]}")

        response = await self.llm.chat(
            system=self._planner.system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    "## REPLANNING REQUIRED (JPG Protocol)\n\n"
                    "An executor reported BLOCKED. You must replan.\n\n"
                    f"## Blocked Agents\n" + "\n".join(blocked_info) + "\n\n"
                    f"## Achieved Agents\n" + ("\n".join(achieved_info) or "(none)") + "\n\n"
                    "Provide new subtask assignments for blocked agents. "
                    "You can reassign their work, break it differently, or merge with another agent.\n"
                    f'Return JSON: {{"subtasks": {{"executor_a": "...", "executor_b": "...", "executor_c": "..."}}}}'
                ),
            }],
            max_tokens=1024,
            temperature=0.3,
        )
        self._planner.total_tokens_in += response.tokens_in
        self._planner.total_tokens_out += response.tokens_out

        self.send_message(Message(
            sender="planner", receiver="__broadcast__",
            content=f"REPLAN: {response.content}", performative="request",
        ))

        return response.content

    def _parse_plan(self, text: str) -> dict[str, str]:
        """Extract subtask assignments from planner output."""
        import re
        # Try JSON extraction
        match = re.search(r'\{[^{}]*"subtasks"\s*:\s*\{([^}]+)\}', text, re.DOTALL)
        if match:
            try:
                json_str = '{"subtasks": {' + match.group(1) + '}}'
                data = json.loads(json_str)
                return data.get("subtasks", {})
            except json.JSONDecodeError:
                pass

        # Try broader JSON match
        match = re.search(r'\{[\s\S]*?"subtasks"[\s\S]*?\}[\s\S]*?\}', text)
        if match:
            try:
                data = json.loads(match.group(0))
                return data.get("subtasks", {})
            except json.JSONDecodeError:
                pass

        # Fallback: split text into 3 roughly equal parts
        lines = text.strip().split("\n")
        third = max(len(lines) // 3, 1)
        return {
            "executor_a": "\n".join(lines[:third]),
            "executor_b": "\n".join(lines[third:2*third]),
            "executor_c": "\n".join(lines[2*third:]),
        }

    def _extract_status(self, text: str) -> str:
        """Extract JPG status from agent response."""
        text_upper = text.upper()
        if "STATUS: BLOCKED" in text_upper or "STATUS:BLOCKED" in text_upper:
            return "blocked"
        if "STATUS: IRRELEVANT" in text_upper or "STATUS:IRRELEVANT" in text_upper:
            return "irrelevant"
        if "STATUS: ACHIEVED" in text_upper or "STATUS:ACHIEVED" in text_upper:
            return "achieved"
        # Default: still committed (working)
        return "committed"
