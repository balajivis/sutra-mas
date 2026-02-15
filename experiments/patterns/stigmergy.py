"""Stigmergy Pattern — Environment-mediated indirect communication.

Classical Source: Heylighen, "Stigmergy as a Universal Coordination Mechanism"
Core Idea: Agents communicate indirectly by modifying a shared environment.
           No direct messaging — agents leave "traces" that influence others.
           Scales O(n) vs O(n^2) for direct messaging.
Expected Advantage: Better scaling with agent count, emergent organization,
                    reduced communication overhead.
"""

from __future__ import annotations

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class StigmergyPattern(MASPattern):
    """Stigmergic coordination: agents modify shared environment, others react to changes.

    Inspired by ant colony optimization and wiki-style collaborative editing.
    Agents never address each other directly — they read the environment,
    contribute, and the environment state guides subsequent behavior.
    """

    name = "stigmergy"
    classical_source = "Heylighen, 'Stigmergy as a Universal Coordination Mechanism'"
    description = "Agents modify shared environment. No direct messaging. Emergent coordination."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        num_agents = self.config.get("num_agents", 4)
        self.agents = [
            Agent(
                name=f"worker_{i}",
                role=Role.SPECIALIST,
                system_prompt=(
                    f"You are Worker {i+1}. You are working on a shared document. "
                    "You CANNOT communicate with other workers directly. "
                    "You can only READ the current document state and MODIFY it.\n\n"
                    "Rules:\n"
                    "1. Read the current document carefully\n"
                    "2. Identify what's missing, incorrect, or could be improved\n"
                    "3. Make your contribution — add content, fix errors, improve structure\n"
                    "4. Leave markers (like TODO or NOTE) to signal areas needing attention\n"
                    "5. Don't delete others' work — build on it or refine it\n\n"
                    "Your output should be the UPDATED version of the document."
                ),
            )
            for i in range(num_agents)
        ]

        # Initialize environment (the shared document)
        self.update_shared_state("document", "", "system")
        self.update_shared_state("revision", 0, "system")

        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        max_rounds = self.config.get("max_rounds", 3)

        # Seed the environment with the task
        self.update_shared_state("document", f"# Task\n\n{task.input_data}\n\n# Working Document\n\n", "system")

        for round_num in range(max_rounds):
            for agent in self.agents:
                current_doc = self.get_shared_state("document")
                revision = self.get_shared_state("revision")

                response = await self.llm.chat(
                    system=agent.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"## Current Document (Revision {revision})\n\n"
                            f"{current_doc}\n\n"
                            "---\n"
                            "Read the document above. Make your contribution. "
                            "Output the COMPLETE updated document with your changes."
                        ),
                    }],
                    max_tokens=4096,
                )

                agent.total_tokens_in += response.tokens_in
                agent.total_tokens_out += response.tokens_out

                # Update environment
                self.update_shared_state("document", response.content, agent.name)
                self.update_shared_state("revision", revision + 1, agent.name)

                # Record trace
                self.send_message(Message(
                    sender=agent.name,
                    receiver="__blackboard__",  # environment
                    content=f"Revision {revision + 1}",
                    performative="inform",
                    token_count=response.tokens_in + response.tokens_out,
                ))

        final_doc = self.get_shared_state("document")

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=max_rounds,
            final_output=final_doc,
            messages=self.messages,
            metadata={"total_revisions": self.get_shared_state("revision")},
        )
