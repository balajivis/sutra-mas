"""Generator/Critic Pattern — One generates, one critiques iteratively.

Classical Source: Generate-and-test (Newell & Simon); Quality gates (Deming);
                 Google ADK Pattern #5; CRM readback protocol (aviation)
Core Idea: Generator produces output, Critic evaluates and provides actionable
           feedback, Generator revises. Iterates until quality threshold met.
Expected Advantage: Higher output quality through iterative refinement.
                    Maps directly to Kapi's Eval layer (Layer 7).
"""

from __future__ import annotations

import json

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class GeneratorCriticPattern(MASPattern):
    """Generator/Critic iterative refinement.

    Implements the generate-evaluate-revise loop with typed critique
    (not just "make it better" — structured feedback on specific dimensions).
    """

    name = "generator_critic"
    classical_source = "Generate-and-test; CRM readback; Google ADK Pattern #5"
    description = "Generator produces, Critic evaluates with typed feedback, iterative refinement."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="generator",
                role=Role.GENERATOR,
                system_prompt=(
                    "You are the Generator. Produce high-quality output for the given task. "
                    "When you receive critique, revise your output addressing EVERY point "
                    "the Critic raised. Show what you changed and why."
                ),
            ),
            Agent(
                name="critic",
                role=Role.CRITIC,
                system_prompt=(
                    "You are the Critic. Evaluate the Generator's output on these dimensions:\n"
                    "1. **Completeness** (0-10): Does it address all aspects of the task?\n"
                    "2. **Accuracy** (0-10): Are claims factually correct?\n"
                    "3. **Structure** (0-10): Is it well-organized and clear?\n"
                    "4. **Depth** (0-10): Does it go beyond surface-level?\n"
                    "5. **Actionability** (0-10): Can the reader act on this?\n\n"
                    "For each dimension, provide a score and SPECIFIC, ACTIONABLE feedback. "
                    "Not 'needs improvement' but 'add a comparison table for X vs Y'.\n\n"
                    "Output JSON: {\"scores\": {\"completeness\": N, ...}, "
                    "\"feedback\": [{\"dimension\": \"...\", \"issue\": \"...\", \"fix\": \"...\"}], "
                    "\"overall\": N, \"pass\": true/false}"
                ),
            ),
        ]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        generator, critic = self.agents
        max_iterations = self.config.get("max_iterations", 3)
        quality_threshold = self.config.get("quality_threshold", 8.0)

        current_output = ""
        critique_history = []

        for iteration in range(max_iterations):
            # Generate (or revise)
            if iteration == 0:
                gen_prompt = f"Task: {task.input_data}\n\nProduce your best output."
            else:
                gen_prompt = (
                    f"Task: {task.input_data}\n\n"
                    f"## Your Previous Output\n{current_output}\n\n"
                    f"## Critic's Feedback\n{critique_history[-1]}\n\n"
                    "Revise your output addressing EVERY point of feedback."
                )

            gen_response = await self.llm.chat(
                system=generator.system_prompt,
                messages=[{"role": "user", "content": gen_prompt}],
                max_tokens=4096,
            )
            generator.total_tokens_in += gen_response.tokens_in
            generator.total_tokens_out += gen_response.tokens_out
            current_output = gen_response.content

            self.send_message(Message(
                sender="generator",
                receiver="critic",
                content=current_output,
                performative="inform",
                metadata={"iteration": iteration + 1},
                token_count=gen_response.tokens_in + gen_response.tokens_out,
            ))

            # Critique
            crit_response = await self.llm.chat(
                system=critic.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Task: {task.input_data}\n\n"
                        f"## Generator's Output (Iteration {iteration + 1})\n{current_output}\n\n"
                        "Evaluate this output on all 5 dimensions."
                    ),
                }],
                max_tokens=2048,
            )
            critic.total_tokens_in += crit_response.tokens_in
            critic.total_tokens_out += crit_response.tokens_out
            critique_history.append(crit_response.content)

            self.send_message(Message(
                sender="critic",
                receiver="generator",
                content=crit_response.content,
                performative="inform",
                metadata={"iteration": iteration + 1},
                token_count=crit_response.tokens_in + crit_response.tokens_out,
            ))

            # Check if quality threshold met
            overall = self._parse_overall_score(crit_response.content)
            if overall >= quality_threshold:
                break

        return ExperimentResult(
            num_agents=2,
            num_rounds=len(critique_history),
            final_output=current_output,
            messages=self.messages,
            metadata={
                "iterations": len(critique_history),
                "final_score": self._parse_overall_score(critique_history[-1]) if critique_history else 0,
                "quality_threshold": quality_threshold,
            },
        )

    def _parse_overall_score(self, critique: str) -> float:
        """Extract overall score from critic's response."""
        try:
            text = critique.strip()
            if "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                data = json.loads(text[start:end])
                return float(data.get("overall", 5))
        except (json.JSONDecodeError, ValueError):
            pass
        return 5.0  # Default middle score
