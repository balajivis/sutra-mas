# Durfee's 4 Ways Result Sharing Improves Distributed Problem Solvers

*From: Edmund H. Durfee, "Distributed Problem Solving and Planning" (1999)*
*In: Weiss (ed.), Multiagent Systems: A Modern Approach to Distributed AI, MIT Press*

---

## Context: Task Sharing vs Result Sharing

Durfee identifies two fundamental coordination strategies for distributed problem solving:

- **Task sharing**: agents divide the computational workload. A manager decomposes the problem into subtasks and distributes them across agents. This is what most LLM frameworks do (LangGraph supervisor, CrewAI crews, OpenAI handoffs).

- **Result sharing**: agents exchange their partial/intermediate results to improve each other's solutions. Agents work on overlapping or related problems and progressively refine the collective answer. This is what Blackboard systems do — and what no current LLM framework does well.

Task sharing asks: "Who should do what?"
Result sharing asks: "How can what you've found help me do better?"

---

## The 4 Ways

Result sharing improves the group's problem-solving along 4 dimensions:

### 1. Confidence

Heterogeneous independent agents working on the same or overlapping problems may arrive at different results. By sharing results, agents can **cross-check independently derived solutions** to detect errors and deviations. When multiple agents converge on the same answer through different methods, confidence increases. When they diverge, it's a signal that something needs human attention.

**Kapi mapping**: RAG Agent and Research Agent both answer a strategic question. If they converge → high confidence, auto-release. If they diverge → the delta is surfaced on the Blackboard, triggering HITL review. The Propose-Counter protocol structures how the divergence gets resolved.

**Why humans matter**: A human domain expert can break ties that LLM agents cannot. When two agents disagree, the human doesn't just pick one — they bring contextual knowledge ("the APAC data changed last quarter") that neither agent has. Confidence through cross-checking is most powerful when the cross-checkers include humans.

### 2. Completeness

Individual agents working on subtasks have only partial views of the overall problem. When agents share their intermediate results, an **increasingly more complete picture** of the overall solution becomes possible. No single agent has the full answer, but the combination of shared results covers the solution space.

**Kapi mapping**: Strategic planning blueprint — market agent contributes market data, finance agent contributes cost model, risk agent contributes threats, compliance agent flags regulatory constraints. Each writes to the Blackboard. The union is the complete strategic picture. No single agent could produce it.

**Why humans matter**: Humans contribute completeness dimensions that agents literally cannot access — organizational politics, unwritten institutional knowledge, relationship context, ethical judgment. A strategic plan without "the CEO hates this approach" is incomplete in ways no RAG index can fix.

### 3. Precision

To adapt their own local solution to be consistent with the overall solution, agents need to know about others' solutions. Result sharing lets agents **refine and sharpen** their local results by incorporating constraints and information from peers.

**Kapi mapping**: RAG Agent retrieves documents and generates an answer → Eval Agent reads the answer on the Blackboard and posts a critique ("missing citation for the 30-day clause") → RAG Agent reads the critique and refines with the specific citation → each iteration is more precise. This is the Propose-Counter protocol operating over the Blackboard.

**Why humans matter**: Human precision is qualitatively different from LLM precision. A legal counsel doesn't just add a citation — they reframe the entire answer to account for an exception clause. The argumentation protocol lets humans inject precision that restructures, not just refines.

### 4. Timeliness

Agents that receive early partial results from peers can **begin working sooner** on dependent subtasks rather than waiting for complete solutions. Sharing intermediate results allows the group to make progress in parallel, reducing the overall time to solution.

**Kapi mapping**: While RAG Agent is still retrieving documents, Memory Agent has already posted relevant past conversations to the Blackboard. The answer-generation agent can start incorporating memory context before retrieval completes. The Subscribe-Notify protocol enables this: agents subscribe to Blackboard regions and wake up as soon as relevant content appears.

**Why humans matter**: Humans are the slowest agents in any team (minutes/hours vs. seconds). Timeliness through early sharing means the system can pre-compute before the human is even ready to review. When the compliance officer opens the review queue, the Blackboard already has the agent's proposal, the eval critique, the supporting evidence, and the risk assessment — all computed while the human was in another meeting.

---

## The Critical Caveat: Selective Sharing

Durfee emphasizes that **result sharing is not free**:

> Agents have to know what to do with received results from other agents, and communication causes costs, so agents should be selective with the information they exchange with others.

This maps directly to KAR design decisions:

| Problem | KAR Solution |
|---------|-------------|
| Agents flooded with irrelevant results | **Subscribe-Notify protocol**: agents only receive results they've subscribed to |
| Communication costs (tokens, latency) | **Scoped Blackboard**: private / protocol / tenant layers control visibility |
| Agents don't know what to do with results | **Typed performatives**: each message has a performative (inform, propose, cfp) that tells the receiver what's expected |
| Sharing everything is wasteful | **DALA insight**: agents learn "strategic silence" — share only when value density is high |

---

## Connection to FA/C (Functionally Accurate, Cooperative)

Durfee's framework builds on Lesser and Corkill's FA/C approach — the foundational idea that distributed systems should exchange **partial, tentative results** and progressively refine them, rather than waiting for each agent to produce a complete, correct answer before sharing.

The FA/C philosophy:
1. Agents produce partial, potentially incorrect results early
2. They share these tentative results with peers
3. Peers use them to refine their own results
4. The system converges through cooperative iteration
5. Errors are detected and corrected through cross-checking (confidence dimension)

**Why this is perfectly suited to LLM agents**: LLMs *already* produce partial, tentative results — they're probabilistic by nature. The FA/C approach says: **embrace that.** Let agents share their best guesses early. Let other agents refine them. Let the system converge through iteration rather than demanding perfection from any single agent.

**Why this is the opposite of LangGraph**: LangGraph requires each node to produce a complete state update before the next node runs. Nodes execute sequentially along graph edges. There is no mechanism for an agent to share a tentative result that other agents can begin working with before it's finalized. The graph enforces artificial serialization.

The Blackboard pattern + FA/C philosophy = agents writing partial results to a shared workspace, other agents picking them up as soon as they're useful, progressive refinement through multiple rounds, and convergence through the 4 dimensions (confidence, completeness, precision, timeliness).

---

## Connection to Contract Net Protocol

Task sharing and result sharing are complementary, not competing strategies. In KAR:

- **Contract Net** handles task sharing: "Who should do what?" The orchestrator broadcasts a CFP, agents bid, the best agent is awarded the contract.
- **Blackboard** handles result sharing: "How can what you've found help me do better?" Agents write partial results, peers read and refine.

A complete coordination flow uses both:

```
1. Contract-Net: Orchestrator broadcasts CFP for "strategic analysis of market entry"
   → Market Agent, Finance Agent, Risk Agent bid
   → All 3 awarded (parallel execution)

2. Blackboard (result sharing):
   → Market Agent writes preliminary market sizing (partial, tentative)
   → Finance Agent reads market sizing, begins cost modeling using those numbers
   → Risk Agent reads both, begins identifying risks for that market + cost structure
   → Market Agent reads risk assessment, refines market sizing to account for risks
   → Each round: more complete, more precise, higher confidence

3. Propose-Counter: Eval Agent reads the converged Blackboard state
   → Proposes: "Ready for human review"
   → Or rejects: "Finance model assumes 2025 exchange rates, needs update"
   → Agents refine further

4. HITL-Review: Human PM reviews the Blackboard
   → Sees the full picture (completeness)
   → Sees convergence/divergence (confidence)
   → Adds organizational context no agent has
   → Approves or sends back with typed reasons
```

---

## The 4 Dimensions as Eval Criteria

Durfee's 4 dimensions also serve as **evaluation criteria for multi-agent output quality**:

| Dimension | Eval Question | Metric |
|-----------|--------------|--------|
| **Confidence** | Did multiple agents converge on this answer? | Agreement score across agents |
| **Completeness** | Are all relevant aspects covered? | Checklist coverage (which Blackboard regions have content) |
| **Precision** | Was the answer refined through peer critique? | Number of refinement rounds, citation density |
| **Timeliness** | Was the answer produced within acceptable time? | Wall-clock time, with early partial results credited |

These map directly to Kapi's eval layer (Layer 7) — the 18 eval criteria could be extended or grouped along these 4 dimensions.

---

## References

- Durfee, E.H. (1999). "Distributed Problem Solving and Planning." In Weiss (ed.), *Multiagent Systems: A Modern Approach to Distributed Artificial Intelligence*, MIT Press. [PDF](https://jmvidal.cse.sc.edu/library/durfee99a.pdf) | [Springer](https://link.springer.com/chapter/10.1007/3-540-47745-4_6)
- Lesser, V.R. and Corkill, D.D. (1983). "Functionally Accurate, Cooperative Distributed Systems." [Semantic Scholar](https://www.semanticscholar.org/paper/Functionally-Accurate,-Cooperative-Distributed-Lesser-Corkill/ab2ed8b3a8cf14103930480ae01caf9372ee120c)
- Durfee, E.H. and Lesser, V.R. (1991). "Partial Global Planning: A Coordination Framework for Distributed Hypothesis Formation." [Semantic Scholar](https://www.semanticscholar.org/paper/Partial-global-planning:-a-coordination-framework-Durfee-Lesser/9d36f224aa606c292841e70f2c6d62d3d630f700)
- Lesser, V.R. and Corkill, D.D. (1983). "The Distributed Vehicle Monitoring Testbed." [ResearchGate](https://www.researchgate.net/publication/220605616_The_Distributed_Vehicle_Monitoring_Testbed_A_Tool_for_Investigating_Distributed_Problem_Solving_Networks)
- Durfee, E.H. (1988). *Coordination of Distributed Problem Solvers.* Springer. [Amazon](https://www.amazon.com/Coordination-Distributed-Springer-International-Engineering/dp/089838284X)
- [Bamberg University seminar slides on Durfee's framework](https://cogsys.uni-bamberg.de/teaching/ws0506/s_planning/slides/trabert_tabatabai.pdf)
