"""Supervisor Pattern — Central coordinator routes to specialists.

Classical Source: Organizational hierarchy (management science);
                 LangGraph supervisor pattern; Anthropic orchestrator-worker (2025)
Core Idea: One coordinator agent receives the task, decomposes it, routes
           sub-tasks to specialists, and synthesizes results.
Expected Advantage: Clear control flow, quality oversight. Anthropic showed
                    90.2% improvement over single-agent with this pattern.
                    Risk: supervisor bottleneck (Kim et al., 2025).
"""

from __future__ import annotations

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class SupervisorPattern(MASPattern):
    """Supervisor/orchestrator-worker pattern.

    One agent coordinates, others execute. All communication goes through
    the supervisor — no direct specialist-to-specialist communication.
    """

    name = "supervisor"
    classical_source = "Hierarchical organization; Anthropic orchestrator-worker (2025)"
    description = "Central coordinator routes tasks to specialists and synthesizes results."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="supervisor",
                role=Role.COORDINATOR,
                system_prompt=(
                    "You are the Supervisor. You coordinate a team of specialists.\n\n"
                    "Your workflow:\n"
                    "1. Analyze the task and decide which specialist(s) should handle it\n"
                    "2. Give clear, specific instructions to each specialist\n"
                    "3. Review their outputs for quality and completeness\n"
                    "4. Request revisions if needed\n"
                    "5. Synthesize all specialist outputs into a final response\n\n"
                    "Available specialists:\n"
                    "- 'analyst': Deep analysis, finding patterns, critical thinking\n"
                    "- 'writer': Clear communication, structured output, synthesis\n"
                    "- 'reviewer': Quality review, finding gaps, fact-checking\n\n"
                    "For each step, output JSON: {\"action\": \"delegate\"|\"synthesize\", "
                    "\"specialist\": \"name\", \"instruction\": \"...\"} or "
                    "{\"action\": \"synthesize\", \"final_output\": \"...\"}"
                ),
            ),
            Agent(
                name="analyst",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Analyst specialist. When the Supervisor gives you a task, "
                    "perform deep analysis. Be thorough, identify patterns, flag issues, "
                    "and provide structured findings. Focus on accuracy over speed."
                ),
            ),
            Agent(
                name="writer",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Writer specialist. When the Supervisor gives you content to "
                    "write up, produce clear, well-structured, comprehensive output. Focus on "
                    "communication quality — the reader should understand everything without "
                    "additional context."
                ),
            ),
            Agent(
                name="reviewer",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are the Reviewer specialist. When the Supervisor asks you to review, "
                    "critically evaluate the work. Check for: completeness, accuracy, gaps, "
                    "inconsistencies, and quality. Be constructive but honest."
                ),
            ),
        ]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        supervisor = self.agents[0]
        specialists = {a.name: a for a in self.agents[1:]}
        max_rounds = self.config.get("max_rounds", 5)

        conversation = [{"role": "user", "content": f"Task: {task.input_data}"}]
        accumulated_work: dict[str, str] = {}

        for round_num in range(max_rounds):
            # Supervisor decides next action
            context = self._build_supervisor_context(accumulated_work)
            if context:
                conversation.append({"role": "user", "content": f"Completed work so far:\n{context}\n\nWhat's next?"})

            sup_response = await self.llm.chat(
                system=supervisor.system_prompt,
                messages=conversation,
                max_tokens=2048,
            )
            supervisor.total_tokens_in += sup_response.tokens_in
            supervisor.total_tokens_out += sup_response.tokens_out

            conversation.append({"role": "assistant", "content": sup_response.content})

            # Parse supervisor's decision
            action = self._parse_supervisor_action(sup_response.content)

            if action.get("action") == "synthesize" and "final_output" in action:
                # Supervisor is done
                return ExperimentResult(
                    num_agents=len(self.agents),
                    num_rounds=round_num + 1,
                    final_output=action["final_output"],
                    messages=self.messages,
                )

            if action.get("action") == "delegate":
                specialist_name = action.get("specialist", "analyst")
                instruction = action.get("instruction", task.input_data)
                specialist = specialists.get(specialist_name, self.agents[1])

                # Record delegation
                self.send_message(Message(
                    sender="supervisor",
                    receiver=specialist.name,
                    content=instruction,
                    performative="request",
                ))

                # Specialist executes
                spec_response = await self.llm.chat(
                    system=specialist.system_prompt,
                    messages=[{"role": "user", "content": instruction}],
                    max_tokens=3072,
                )
                specialist.total_tokens_in += spec_response.tokens_in
                specialist.total_tokens_out += spec_response.tokens_out

                accumulated_work[f"{specialist.name}_r{round_num}"] = spec_response.content

                self.send_message(Message(
                    sender=specialist.name,
                    receiver="supervisor",
                    content=spec_response.content,
                    performative="inform",
                    token_count=spec_response.tokens_in + spec_response.tokens_out,
                ))

        # If we exhausted rounds, do a final synthesis
        context = self._build_supervisor_context(accumulated_work)
        synth_response = await self.llm.chat(
            system=supervisor.system_prompt,
            messages=[{
                "role": "user",
                "content": f"All rounds complete. Synthesize into final output.\n\n{context}",
            }],
            max_tokens=4096,
        )
        supervisor.total_tokens_in += synth_response.tokens_in
        supervisor.total_tokens_out += synth_response.tokens_out

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=max_rounds,
            final_output=synth_response.content,
            messages=self.messages,
        )

    def _build_supervisor_context(self, work: dict[str, str]) -> str:
        if not work:
            return ""
        return "\n\n".join(f"### {key}\n{val}" for key, val in work.items())

    def _parse_supervisor_action(self, content: str) -> dict:
        """Parse supervisor's JSON action, with fallback.

        Handles cases where the supervisor outputs multiple JSON objects
        (e.g., a plan with several delegation steps). Extracts the FIRST
        valid JSON object with an 'action' key.
        """
        import json
        import re

        text = content.strip()

        # Find all JSON-like objects in the text
        for match in re.finditer(r'\{[^{}]*\}', text):
            try:
                obj = json.loads(match.group(0))
                if "action" in obj:
                    return obj
            except json.JSONDecodeError:
                continue

        # Try nested JSON (for {"action": "synthesize", "final_output": "..."} with long content)
        try:
            if "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: delegate to analyst with the raw content as instruction
        return {"action": "delegate", "specialist": "analyst", "instruction": content}
