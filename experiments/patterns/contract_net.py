"""Contract Net Protocol — Task allocation via announce/bid/award.

Classical Source: Smith, "The Contract Net Protocol" (1980)
Core Idea: A manager announces tasks, agents bid based on capability/availability,
           manager awards to best bidder. Decentralized task allocation.
Expected Advantage: Better task-agent matching, load balancing, agents self-select
                    based on competence. DALA auction (2025) validated with LLMs
                    (84% MMLU, 6.25M tokens).
"""

from __future__ import annotations

import json

from harness.base import Agent, BenchmarkTask, ExperimentResult, MASPattern, Message, Role


class ContractNetPattern(MASPattern):
    """Contract Net Protocol: announce/bid/award task allocation.

    Implements Smith's (1980) three-phase protocol:
    1. Announcement: Manager decomposes task and announces sub-tasks
    2. Bidding: Agents evaluate sub-tasks and submit capability-based bids
    3. Awarding: Manager selects best bidder for each sub-task
    """

    name = "contract_net"
    classical_source = "Smith, 'The Contract Net Protocol' (1980)"
    description = "Manager decomposes task, agents bid on sub-tasks, best bidder executes."

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [
            Agent(
                name="manager",
                role=Role.COORDINATOR,
                system_prompt=(
                    "You are the Contract Manager. Your responsibilities:\n"
                    "1. DECOMPOSE: Break the task into 3-5 independent sub-tasks\n"
                    "2. ANNOUNCE: Describe each sub-task clearly with requirements\n"
                    "3. EVALUATE: Review bids from specialist agents\n"
                    "4. AWARD: Assign each sub-task to the best bidder\n"
                    "5. SYNTHESIZE: Combine completed sub-task results into final output\n\n"
                    "Output structured JSON for decomposition and awards."
                ),
            ),
            Agent(
                name="specialist_a",
                role=Role.BIDDER,
                system_prompt=(
                    "You are Specialist A. Your strengths: deep analysis, technical accuracy, "
                    "finding edge cases. When you see a Call for Proposals (CFP), evaluate "
                    "honestly whether you can do the sub-task well. Bid with a capability score "
                    "(1-10) and brief justification. If awarded, complete the sub-task thoroughly."
                ),
            ),
            Agent(
                name="specialist_b",
                role=Role.BIDDER,
                system_prompt=(
                    "You are Specialist B. Your strengths: broad knowledge, synthesis, "
                    "clear communication, structured output. When you see a CFP, evaluate "
                    "honestly whether you can do the sub-task well. Bid with a capability score "
                    "(1-10) and brief justification. If awarded, complete the sub-task thoroughly."
                ),
            ),
            Agent(
                name="specialist_c",
                role=Role.BIDDER,
                system_prompt=(
                    "You are Specialist C. Your strengths: creative problem-solving, "
                    "identifying implications, practical recommendations. When you see a CFP, "
                    "evaluate honestly. Bid with capability score (1-10) and justification. "
                    "If awarded, complete the sub-task thoroughly."
                ),
            ),
        ]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        manager = self.agents[0]
        bidders = self.agents[1:]

        # Phase 1: Task Decomposition
        decomp_response = await self.llm.chat(
            system=manager.system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    f"Decompose this task into 3-5 independent sub-tasks.\n\n"
                    f"Task: {task.input_data}\n\n"
                    "Return JSON array: [{\"id\": 1, \"title\": \"...\", \"description\": \"...\", "
                    "\"requirements\": \"...\"}]"
                ),
            }],
            max_tokens=2048,
        )
        manager.total_tokens_in += decomp_response.tokens_in
        manager.total_tokens_out += decomp_response.tokens_out

        # Parse sub-tasks
        try:
            text = decomp_response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            sub_tasks = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            # Fallback: treat entire task as single sub-task
            sub_tasks = [{"id": 1, "title": "Complete task", "description": task.input_data, "requirements": ""}]

        # Phase 2: Call for Proposals + Bidding
        awards: dict[int, Agent] = {}

        for st in sub_tasks:
            cfp = (
                f"CALL FOR PROPOSALS — Sub-task {st['id']}: {st['title']}\n"
                f"Description: {st['description']}\n"
                f"Requirements: {st.get('requirements', 'None specified')}\n\n"
                "Submit your bid as JSON: {\"capability_score\": <1-10>, \"justification\": \"...\"}"
            )

            # Announce CFP
            self.send_message(Message(
                sender="manager",
                receiver="__broadcast__",
                content=cfp,
                performative="cfp",
            ))

            # Collect bids
            bids = []
            for bidder in bidders:
                bid_response = await self.llm.chat(
                    system=bidder.system_prompt,
                    messages=[{"role": "user", "content": cfp}],
                    max_tokens=256,
                )
                bidder.total_tokens_in += bid_response.tokens_in
                bidder.total_tokens_out += bid_response.tokens_out

                self.send_message(Message(
                    sender=bidder.name,
                    receiver="manager",
                    content=bid_response.content,
                    performative="propose",
                    token_count=bid_response.tokens_in + bid_response.tokens_out,
                ))

                # Parse bid
                try:
                    bid_text = bid_response.content.strip()
                    if bid_text.startswith("```"):
                        bid_text = bid_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    bid_data = json.loads(bid_text)
                    bids.append((bidder, bid_data.get("capability_score", 5)))
                except (json.JSONDecodeError, KeyError):
                    bids.append((bidder, 5))  # Default score

            # Award to highest bidder
            best_bidder = max(bids, key=lambda x: x[1])[0]
            awards[st["id"]] = best_bidder

            self.send_message(Message(
                sender="manager",
                receiver=best_bidder.name,
                content=f"AWARDED: Sub-task {st['id']} — {st['title']}",
                performative="accept",
            ))

        # Phase 3: Execution
        completed = {}
        for st in sub_tasks:
            assigned = awards.get(st["id"], bidders[0])
            exec_response = await self.llm.chat(
                system=assigned.system_prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"You have been awarded Sub-task {st['id']}: {st['title']}\n\n"
                        f"Description: {st['description']}\n\n"
                        f"Original task context: {task.input_data}\n\n"
                        "Complete this sub-task thoroughly."
                    ),
                }],
                max_tokens=2048,
            )
            assigned.total_tokens_in += exec_response.tokens_in
            assigned.total_tokens_out += exec_response.tokens_out
            completed[st["id"]] = {"agent": assigned.name, "output": exec_response.content}

        # Phase 4: Synthesis by manager
        results_text = "\n\n".join(
            f"## Sub-task {sid}: {next(s['title'] for s in sub_tasks if s['id'] == sid)}\n"
            f"Completed by: {data['agent']}\n\n{data['output']}"
            for sid, data in completed.items()
        )

        synth_response = await self.llm.chat(
            system=manager.system_prompt,
            messages=[{
                "role": "user",
                "content": (
                    f"All sub-tasks are complete. Synthesize into a single coherent output.\n\n"
                    f"Original task: {task.input_data}\n\n"
                    f"Sub-task results:\n{results_text}"
                ),
            }],
            max_tokens=4096,
        )
        manager.total_tokens_in += synth_response.tokens_in
        manager.total_tokens_out += synth_response.tokens_out

        return ExperimentResult(
            num_agents=len(self.agents),
            num_rounds=3,  # decompose, bid+award, execute+synthesize
            final_output=synth_response.content,
            messages=self.messages,
            metadata={"sub_tasks": len(sub_tasks), "awards": {k: v.name for k, v in awards.items()}},
        )
