## The Popular Narrative (Summary)

The mainstream story goes:

1. MAS peaked in early 2000s (FIPA, JADE, agent-based e-commerce)
2. Deep Learning eclipsed MAS in the 2010s (easier to scale one big model than coordinate many small agents)
3. LLMs revived MAS in 2024-2026 by "solving communication" (agents can now talk in natural language)
4. Modern MAS uses "context partitioning" (each agent gets a clean, focused context window)
5. Agent debate creates "dialectical reasoning" that escapes the "average" of a single model
6. The hard problem is now the Manager/Orchestrator, not the communication protocol

This narrative is ~60% correct, ~20% misleading, and ~20% dangerously incomplete.

## What's Correct

### The Historical Arc
MAS did peak around 2000-2005 (FIPA standards ratified 1997-2003, JADE released 1999, agent-based e-commerce research booming). The deep learning revolution (AlexNet 2012, transformers 2017, GPT-3 2020) did redirect AI research funding and attention away from symbolic/logic-based MAS. The LLM agent renaissance is real (AutoGen 2023, CrewAI 2024, LangGraph 2024, Google ADK 2025).

**Validated by**: Our `multiagent-coordination.md` traces the same arc. The JADE status section in `classical-mas-llm-bridge.md` confirms JADE is effectively legacy (community fork at v4.6.1, no active development).

### The Coordination Tax
The claim that communication overhead grows exponentially with agent count, making single large models often more efficient, is well-supported.

**Validated by**: Kim et al. (Google DeepMind, 2025) quantifies 17.2x error amplification with independent agents. Cemri et al. (ICLR 2025) shows 36.9% of MAS failures come from inter-agent misalignment. The 5-agent ceiling is documented in multiple sources.

### Context Partitioning
Giving each agent a focused context window instead of one massive monolithic prompt does improve quality. This is a genuine advantage of MAS.

**Validated by**: Anthropic's production multi-agent research system confirms this pattern. LbMAS (2025) shows 13-57% improvement and 3x token efficiency with structured coordination (Blackboard) vs. monolithic approaches.

### Sequential Penalty
The 35-70% degradation on sequential tasks is accurate.

**Validated by**: Kim et al. (Google DeepMind, 2025) reports 39-70% degradation on sequential tasks. This is one of the most robust findings in recent MAS research.

### Small Teams Consensus
The "3-5 specialized agents" recommendation is the emerging consensus.

**Validated by**: The 5-agent ceiling in LangGraph limitations research. Anthropic's engineering blog recommends "orchestrator + 2-4 specialists." Our `why-mas-works.md` documents this.
### "Communication Solved by LLMs" (The Most Dangerous Claim)

**The claim**: "The rise of LLM-based agents solved the biggest bottleneck of the old days: Communication. We no longer have to define every possible state for an agent."

**The reality**: LLMs made it *easier to write* inter-agent messages in natural language. They made the **communication structure problem dramatically worse**:

| Dimension | Classical MAS (FIPA era) | Modern LLM Frameworks |
|-----------|------------------------|----------------------|
| Message types | 22 typed performatives (inform, request, propose, accept, refuse...) with formal semantics | Unstructured strings |
| Protocol structure | Interaction protocols with defined state machines (CNP, propose-counter, auction) | "Just call the next agent" |
| Content vs. protocol separation | KQML explicitly separated what is communicated from how | Everything mixed together |
| Commitment tracking | Commitment stores with lifecycle (conditional → active → fulfilled/violated) | Nothing |
| Shared ontology | Explicit domain ontologies declared per conversation | Implicit, ambiguous |
| Message validation | Formal preconditions and postconditions per performative | Hope the LLM interprets correctly |

LLMs didn't solve communication. They **papered over it with fluent natural language**, hiding the structural problems that classical MAS spent 20 years identifying and solving. When modern MAS fails (the 40-80% failure rate in Cemri et al.), a significant portion of failures trace to exactly the communication structure problems that FIPA had solutions for.

**This is the central gap that KAR addresses.**

---

## What's Dangerously Missing

The popular narrative omits the most important concepts from classical MAS research — concepts that directly explain why modern LLM agent systems fail at the rates they do.

### 1. Result Sharing (Durfee, 1999)

The narrative focuses entirely on **task sharing** (dividing work) and ignores **result sharing** (agents improving each other's solutions). Durfee identified 4 ways result sharing improves distributed problem solving:

- **Confidence**: Cross-checking independently derived solutions
- **Completeness**: Combining partial views into a full picture
- **Precision**: Refining local results using peers' constraints
- **Timeliness**: Starting dependent work before predecessors finish

The Blackboard pattern is the primary mechanism for result sharing. It's the most important coordination pattern for LLM agents (13-57% improvement, 3x token efficiency) and the narrative doesn't mention it at all.

See: `durfee-result-sharing.md`

### 2. Humans as Team Members (Not Supervisors)

The narrative treats HITL as "human-in-the-loop **or** manager agent" — a supervisory role bolted onto the system. Our thesis: humans are **peer agents** who participate in the same protocols as LLM agents:

- Humans bid alongside LLM agents in Contract Net auctions
- Humans participate in argumentation protocols with typed reasons for rejection
- Humans contribute to the Blackboard with domain knowledge that no RAG index can provide
- Human commitments are tracked with the same lifecycle as agent commitments

The narrative's "Manager" framing recreates the supervisor bottleneck that classical MAS already identified as an anti-pattern.

See: `kapi-agent-runtime.md`, "The Human-Agent Team Thesis"

### 3. Commitment Tracking and Accountability

Classical MAS had commitment stores — formal records of inter-agent promises with lifecycle states and violation detection. The popular narrative mentions none of this. Without commitments:

- An agent that "agrees" to perform a task can hallucinate a different action with no detection
- Approved HITL responses can be silently modified downstream with no audit trail
- Enterprise compliance requirements (EU AI Act, SOC 2) cannot be met

See: `kapi-agent-runtime.md`, Layer 4 (Commitment Store)

### 4. The FA/C Insight (Lesser & Corkill, 1983)

The Functionally Accurate, Cooperative approach — that agents should share partial, tentative results early rather than waiting for perfection — is the opposite of the rigid graph workflow the narrative advocates. LLMs are naturally FA/C-compatible (they're probabilistic, producing tentative results by nature), but every modern framework forces them into sequential, all-or-nothing execution.

See: `durfee-result-sharing.md`, "Connection to FA/C"

### 5. The Contract Net Protocol (Smith, 1980)

The narrative's "Manager picks the right agent" is a centralized bottleneck. CNP solves this through decentralized capability-based bidding — each agent evaluates its own fitness and bids, the manager just evaluates bids. Adding a new agent type requires zero changes to the orchestrator. The narrative doesn't mention this foundational protocol.

See: `kapi-agent-runtime.md`, Contract Net section

---

## Revised Narrative (What We'd Say Instead)

```
MAS didn't "fail" in the 2010s — it was waiting for models capable of
flexible communication. LLMs provided that, but the community threw out
30 years of coordination theory in the process.

The result: 40-80% failure rates in modern LLM agent systems.
Not because the models are bad, but because the coordination is naive.

The fix isn't better models or better prompting.
The fix is better structure:
  - Typed communication (not free-form chat)
  - Result sharing through Blackboard patterns (not just task division)
  - Commitment tracking (not hope-based coordination)
  - Humans as peer agents in formal protocols (not supervisors)
  - Contract Net for task allocation (not hardcoded routing)
  - FA/C philosophy: share tentative results early, refine through iteration

This is what classical MAS knew. This is what KAR builds.
```