"""BDI Pattern — Belief-Desire-Intention reasoning loop.

Classical Source: Rao & Georgeff, "BDI Agents" (1995)
Core Idea: Agents maintain explicit beliefs (world model), desires (goals),
           and intentions (committed plans). Deliberation cycle: perceive →
           update beliefs → generate options → filter intentions → execute.
Expected Advantage: Better goal-directed behavior, plan revision when beliefs
                    change, explicit reasoning about what to do vs what can be done.
"""

from __future__ import annotations

import json

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class BDIPattern(MASPattern):
    """BDI (Belief-Desire-Intention) multi-agent coordination.

    Each agent maintains explicit B/D/I states and communicates beliefs
    and intentions to coordinate. Implements a simplified BDI deliberation
    cycle adapted for LLM agents.
    """

    name = "bdi"
    classical_source = "Rao & Georgeff, 'BDI Agents' (1995)"
    description = "Agents maintain beliefs/desires/intentions. Deliberation cycle for goal-directed behavior."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="planner",
                role=Role.COORDINATOR,
                system_prompt=(
                    "You are the Planner agent operating under BDI architecture.\n\n"
                    "You maintain:\n"
                    "- **Beliefs**: What you know/believe about the current state\n"
                    "- **Desires**: What goals you want to achieve\n"
                    "- **Intentions**: What plans you've committed to\n\n"
                    "BDI Deliberation Cycle:\n"
                    "1. PERCEIVE: Read the current state and other agents' beliefs\n"
                    "2. UPDATE BELIEFS: Revise what you believe based on new information\n"
                    "3. DELIBERATE: Generate possible plans to achieve desires\n"
                    "4. FILTER: Select which plan to commit to (intention)\n"
                    "5. EXECUTE: Take action on your intention\n\n"
                    "Output your state as JSON after each cycle:\n"
                    "{\"beliefs\": [...], \"desires\": [...], \"intentions\": [...], "
                    "\"action\": \"...\", \"output\": \"...\"}"
                ),
            ),
            Agent(
                name="executor_a",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are Executor A. You receive intentions from the Planner and execute them.\n"
                    "After execution, report back:\n"
                    "1. What you did\n"
                    "2. What you observed (new beliefs to share)\n"
                    "3. Whether the intention was fully satisfied\n\n"
                    "Output JSON: {\"executed\": \"...\", \"observations\": [...], "
                    "\"satisfied\": true/false, \"output\": \"...\"}"
                ),
            ),
            Agent(
                name="executor_b",
                role=Role.SPECIALIST,
                system_prompt=(
                    "You are Executor B. You receive intentions from the Planner and execute them.\n"
                    "After execution, report back:\n"
                    "1. What you did\n"
                    "2. What you observed (new beliefs to share)\n"
                    "3. Whether the intention was fully satisfied\n\n"
                    "Output JSON: {\"executed\": \"...\", \"observations\": [...], "
                    "\"satisfied\": true/false, \"output\": \"...\"}"
                ),
            ),
        ]

        # Initialize BDI state
        self.update_shared_state("beliefs", [f"Task received: {task.description}"], "system")
        self.update_shared_state("desires", [f"Complete: {task.description}"], "system")
        self.update_shared_state("intentions", [], "system")
        self.update_shared_state("outputs", [], "system")

        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        planner = self.agents[0]
        executors = self.agents[1:]
        max_cycles = self.config.get("max_cycles", 3)

        for cycle in range(max_cycles):
            # Planner deliberation cycle
            beliefs = self.get_shared_state("beliefs")
            desires = self.get_shared_state("desires")
            intentions = self.get_shared_state("intentions")
            outputs = self.get_shared_state("outputs")

            plan_response = await self.llm.chat(
                system=planner.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"## BDI Deliberation Cycle {cycle + 1}\n\n"
                        f"**Task**: {task.input_data}\n\n"
                        f"**Current Beliefs**: {json.dumps(beliefs)}\n"
                        f"**Current Desires**: {json.dumps(desires)}\n"
                        f"**Current Intentions**: {json.dumps(intentions)}\n"
                        f"**Completed Outputs**: {json.dumps(outputs[:3])}\n\n"  # Limit context
                        "Run your deliberation cycle. What do you believe, desire, intend? "
                        "What action should be taken?"
                    ),
                }],
                max_tokens=2048,
            )
            planner.total_tokens_in += plan_response.tokens_in
            planner.total_tokens_out += plan_response.tokens_out

            # Parse planner state
            planner_state = self._parse_json(plan_response.content)
            new_beliefs = planner_state.get("beliefs", beliefs)
            new_intentions = planner_state.get("intentions", [])
            action = planner_state.get("action", "")

            self.update_shared_state("beliefs", new_beliefs, "planner")
            self.update_shared_state("intentions", new_intentions, "planner")

            self.send_message(Message(
                sender="planner",
                receiver="__broadcast__",
                content=plan_response.content,
                performative="inform",
                metadata={"cycle": cycle + 1},
            ))

            # If planner produced a final output, check if we're done
            if planner_state.get("output") and not new_intentions:
                outputs.append(planner_state["output"])
                self.update_shared_state("outputs", outputs, "planner")
                break

            # Executors handle intentions
            for i, intention in enumerate(new_intentions[:len(executors)]):
                executor = executors[i % len(executors)]

                exec_response = await self.llm.chat(
                    system=executor.system_prompt,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"## Intention to Execute\n{intention}\n\n"
                            f"## Task Context\n{task.input_data}\n\n"
                            f"## Current Beliefs\n{json.dumps(new_beliefs)}\n\n"
                            "Execute this intention and report back."
                        ),
                    }],
                    max_tokens=3072,
                )
                executor.total_tokens_in += exec_response.tokens_in
                executor.total_tokens_out += exec_response.tokens_out

                exec_state = self._parse_json(exec_response.content)

                # Update beliefs with executor's observations
                observations = exec_state.get("observations", [])
                current_beliefs = self.get_shared_state("beliefs")
                current_beliefs.extend(observations)
                self.update_shared_state("beliefs", current_beliefs, executor.name)

                # Collect output
                if exec_state.get("output"):
                    outputs.append(exec_state["output"])
                    self.update_shared_state("outputs", outputs, executor.name)

                self.send_message(Message(
                    sender=executor.name,
                    receiver="planner",
                    content=exec_response.content,
                    performative="inform",
                    metadata={"cycle": cycle + 1, "intention": intention[:100]},
                ))

        # Final synthesis
        all_outputs = self.get_shared_state("outputs") or []
        if all_outputs:
            # Ask planner to synthesize
            synth_response = await self.llm.chat(
                system=planner.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"All cycles complete. Synthesize the collected outputs into a "
                        f"final comprehensive response.\n\n"
                        f"Task: {task.input_data}\n\n"
                        f"Outputs:\n" + "\n---\n".join(str(o) for o in all_outputs)
                    ),
                }],
                max_tokens=4096,
            )
            planner.total_tokens_in += synth_response.tokens_in
            planner.total_tokens_out += synth_response.tokens_out
            final = synth_response.content
        else:
            final = plan_response.content

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=max_cycles,
            final_output=final,
            messages=self.messages,
            metadata={"bdi_cycles": max_cycles, "total_intentions": len(self.get_shared_state("intentions") or [])},
        )

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response."""
        try:
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            if "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return {"output": content}
