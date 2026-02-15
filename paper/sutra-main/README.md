# Sutra: Threading Classical Coordination Through the Age of LLM Agents

> *Sutra* (Sanskrit: "thread that connects") -- the Vedic texts that compress vast knowledge into essential threads.

Modern LLM agent systems fail 40-80% of the time. Not because the models are weak -- because the coordination is naive. Thirty years of multi-agent systems research solved some of these problems. This project threads that wisdom through.

## The Core Argument

```
The 17.2x error amplification in "bag of agents" systems
is not a law of nature. It is a design failure.

Centralized coordination reduces it to 4.4x.
Anthropic's production system achieves 90.2% improvement over single-agent.
Blackboard architectures achieve 13-57% improvement with 3x fewer tokens.

The difference is not the agents. It is the infrastructure:
  - Shared artifacts, not chat           (MetaGPT, blackboard systems)
  - Typed communication, not free text   (CRM readback, FIPA performatives)
  - Quality gates at every handoff       (surgical checklists, CI/CD)
  - Supervision trees, not flat chaos    (Erlang/OTP, HRO deference to expertise)
  - Bounded autonomy with clear roles    (Auftragstaktik, Linux maintainers)
  - Error recovery, not fail-and-forget  (circuit breakers, rollback)
  - Constructive intellectual friction   (red teams, peer review, debate)
  - Conditions over individual capability (Hackman, Google Aristotle)
```

## The Gap

The industry has two buckets and nothing in between:

| Bucket | Examples | What's Missing |
|--------|----------|---------------|
| **Tool Lists** ("pip install crewai") | awesome-ai-agents, framework docs | No theory, no "why" |
| **Academic Benchmarks** ("85% on HumanEval") | LLM-Agent-Paper-List, GAIA | No architecture, no "how" |

**The missing link**: Why agents fail, what 1995 already solved, and how to build systems that actually work. This project is that bridge -- it maps classical MAS primitives to modern LLM implementations.

| Existing Work | What It Covers | Gap We Fill |
|---------------|---------------|-------------|
| Cemri et al. (ICLR 2025) | 14 failure modes taxonomized | Map every failure mode to a classical MAS solution |
| Kim et al. (Google DeepMind 2025) | Proves centralized > decentralized | Explain *why* using coordination theory; prescribe the Control Shell |
| "Contemporary Agent Technology" (Sept 2025) | Diagnoses the BDI/FIPA vs ReAct/CoT disconnect | Focus on organizational design and coordination failure, not just comparison |
| "Reliable Agent Engineering" (Dec 2025) | Argues for organization over model size | Provide the manual -- YAML schemas, not just the manifesto |
| "Agent Interoperability Protocols" (May 2025) | Technical protocol breakdown | Connect specs to interaction patterns (e.g., "Contract Net over A2A") |

## What This Project Produces

1. **Two ArXiv Papers** -- Paper 1: "Sutra" (Lost Canary methodology + Rosetta Stone); Paper 2: "Agent 0" (human-as-team-member in AI research pipelines)
2. **Research Dashboard** -- sutra.balajivis.com -- interactive exploration of 22K-paper corpus, cluster maps, citation lineage, reinvention radar
3. **Test Harness** -- 9 classical coordination patterns + 2 baselines evaluated across 5 benchmarks (58 experiment results)
4. **GitHub Repo** -- `agent-coordination-patterns` -- the Rosetta Stone, experiment code, pipeline, and pattern library

## Key Quantitative Findings

| Finding | Source |
|---------|--------|
| 40-80% failure rate in naive MAS | Cemri et al., ICLR 2025 |
| 14 unique failure modes across 3 categories | Cemri et al., ICLR 2025 |
| 36.9% of failures from inter-agent misalignment | Cemri et al., ICLR 2025 |
| 17.2x error amplification (independent agents) | Kim et al., Google DeepMind 2025 |
| 4.4x error amplification (centralized) | Kim et al., Google DeepMind 2025 |
| 80.9% improvement on parallelizable tasks | Kim et al., Google DeepMind 2025 |
| 39-70% degradation on sequential tasks | Kim et al., Google DeepMind 2025 |
| 45% capability ceiling (beyond which MAS hurts) | Kim et al., Google DeepMind 2025 |
| 87% accuracy predicting optimal architecture from task features | Kim et al., Google DeepMind 2025 |
| 90.2% improvement (Anthropic orchestrator-worker) | Anthropic Engineering Blog 2025 |
| 80% of performance variance explained by token budget | Anthropic Engineering Blog 2025 |
| 13-57% improvement, 3x fewer tokens (blackboard) | LbMAS 2025 |
| 35.3% max success on complex enterprise tasks | AgentArch (ServiceNow) 2025 |
| CRM reduced aviation accidents by 50%+ | FAA/SKYbrary |
| Surgical checklist cut fatality rates by 33%+ | WHO/Gawande |
| Enabling conditions explain >50% of team effectiveness | Hackman |

## The Eight Design Principles

Synthesized from organizational science + MAS research + production systems:

| # | Principle | Human Origin | Agent Implementation |
|---|-----------|-------------|---------------------|
| 1 | Start with dependencies, not agents | Malone & Crowston coordination theory | Map task dependency structure before choosing topology |
| 2 | Architecture selection is measurable | Google DeepMind scaling study | Use task decomposability to predict optimal topology (87% accuracy) |
| 3 | Communicate through artifacts, not chat | MetaGPT, stigmergy, blackboard systems | Shared versioned workspace; agents read/write deliverables directly |
| 4 | Enforce conceptual integrity | Brooks' surgical team model | One agent/human as architectural guardian; ADRs as machine-readable constraints |
| 5 | Quality gates at every handoff | CRM readback, surgical checklists, CI/CD | Generator/Critic pattern; typed verification at each step |
| 6 | Scale token investment, not agent count | Anthropic production system | Multi-agent as a token allocation mechanism; upgrade model before adding agents |
| 7 | Bound autonomy explicitly | Auftragstaktik, HROs, Linux maintainers | Clear scope limits, escalation paths, ability to say "I don't know" |
| 8 | Design for failure recovery | Erlang/OTP supervision, HRO resilience | Checkpointing, restart strategies, circuit breakers, rollback |

## The Rosetta Stone

| Classical Concept                   | Year | Modern Reinvention                       | What It Actually Means                                                           |
| ----------------------------------- | ---- | ---------------------------------------- | -------------------------------------------------------------------------------- |
| Blackboard (Nii)                    | 1986 | Shared state / context management        | Agents read/write shared artifacts instead of messaging (LangGraph state, Redis) |
| Contract Net (Smith)                | 1980 | Task routing / agent dispatch            | Announce/bid/award -- agents self-select based on capability (A2A task lifecycle) |
| BDI (Rao & Georgeff)                | 1995 | System prompt + RAG + CoT                | Explicit beliefs (RAG), desires (system prompt), intentions (CoT reasoning)      |
| FIPA ACL Performatives              | 2000 | JSON message schemas, A2A Parts          | Typed inter-agent messages with semantic intent                                  |
| Holonic Organization (Horling)      | 2004 | Hierarchical agent teams                 | Recursive hierarchies -- the only way to scale past flat topologies               |
| Stigmergy (Grasse)                  | 1959 | Document-driven coordination             | Indirect communication through shared environment (MetaGPT SOPs)                 |
| Argumentation (Dung)                | 1995 | Generator/Critic, structured debate      | Formal attack/support relations, not free-form "chat"                            |
| Organizational Paradigms (Horling)  | 2004 | Role-based crews                         | Clear roles + norms > raw agent capability (CrewAI, AutoGen)                     |
| Supervision Trees (Erlang)          | 1986 | *(Gap -- nobody does this yet)*           | Error recovery via restart strategies, not fail-and-forget                       |
| Joint Intentions (Cohen & Levesque) | 1990 | *(Gap -- agents don't track commitments)* | Shared goals require mutual belief -- knowing the plan AND knowing others know it |

## The Test Harness

```bash
cd experiments
pip3 install -r requirements.txt
python3 -m harness.runner --pattern blackboard --benchmark code_review --model claude-opus-4-6 --compare
```

**9 patterns + 2 baselines** (blackboard V1/V2, contract net, stigmergy, BDI, supervisor, debate, generator/critic, joint persistent goals) tested against **5 benchmarks** (code review, research synthesis, planning, cascading failure V1/V2) with baseline comparison. Star result: Blackboard V2 scores 95/100; novel finding: Joint Persistent Goals scores 52/100 (LLMs can't detect their own epistemic failures).

## Research Knowledge Base

| # | Document | What You'll Learn |
|---|----------|-------------------|
| 1 | **[Why MAS Works](why-mas-works.md)** | Core thesis. Why MAS fails today (quantified), the 8 design principles, conditions under which MAS excels. **Start here.** |
| 2 | **[Organizational Principles](organizational-principles.md)** | What high-performing human teams (HROs, surgical teams, military C2, aviation CRM, open source) teach us about agent team design. 10 transferable principles. |
| 3 | **[Theoretical Foundations](theoretical-foundations.md)** | Formal theory: coordination theory (Malone & Crowston), stigmergy, process algebras, actor model, game theory, distributed systems (CAP/PACELC), runtime verification. |
| 4 | **[Protocol Stack 2026](evolution-from-classics-to-mcp.md)** | The emerging standard: MCP (agent-to-tool), A2A (agent-to-agent), ANP (decentralized). Classical roots: KQML, FIPA ACL, Contract Net. |
| 5 | **[Durfee's Result Sharing](durfee-result-sharing.md)** | The 4 ways result sharing improves problem solvers: confidence, completeness, precision, timeliness. FA/C philosophy. |
| 6 | **[Classical-Modern Bridge](classical-mas-llm-bridge.md)** | Direct mapping between classical MAS concepts and modern LLM agent implementations. |

## Key Reading

### Classical "Canaries" (1980-2005)

Papers that predicted exactly why modern "bag of agents" systems are failing:

| Paper                                                        | Year | Key Insight                                                                                                                       |
| ------------------------------------------------------------ | ---- | --------------------------------------------------------------------------------------------------------------------------------- |
| Smith, "The Contract Net Protocol"                           | 1980 | Task allocation via announce/bid/award. Still the best pattern for dynamic routing.                                               |
| Nii, "Blackboard Systems"                                    | 1986 | The "Control Shell" problem -- how to decide who speaks next. Modern frameworks struggle with this exact scheduling problem. |
| Malone & Crowston, "Interdisciplinary Study of Coordination" | 1994 | Dependencies determine coordination mechanisms. The foundational theorem.                                                         |
| Wooldridge & Jennings, "Intelligent Agents"                  | 1995 | Weak Agency vs Strong Agency. Modern LLMs have "Strong" capabilities deployed with "Weak" architectures.                          |
| Rao & Georgeff, BDI Architecture                             | 1995 | Separating beliefs/desires/intentions. Modern equivalent: RAG (belief) + system prompt (desire) + CoT (intention).                |
| Grosz & Kraus, "SharedPlans"                                 | 1996 | Coordination requires mutual belief -- knowing the plan AND knowing others know it.                                                |
| Jennings, "On Agent-Based Software Engineering"              | 2000 | "Agent" is above "Object." We're treating agents as functions, not intent-driven entities. The Social Level is missing.           |
| Jennings et al., "Automated Negotiation"                     | 2001 | Why "chatting" is unstable. Need game-theoretic constraints to guarantee convergence.                                             |
| Horling & Lesser, "Multi-Agent Organizational Paradigms"     | 2004 | Flat organizations fail at scale. Holarchies are the only way to scale.                                                           |

### Modern Bridge Papers (2024-2026)

| Paper | Role |
|-------|------|
| "Why Do Multi-Agent LLM Systems Fail?" (Cemri, ICLR 2025) | The Problem Statement. 14 failure modes mapped to classical solutions. |
| "Towards a Science of Scaling Agent Systems" (Google DeepMind, 2025) | The Empirical Proof. Data showing centralized > decentralized. |
| "Can LLM Agents Really Debate?" (Nov 2025) | The Warning. Proves unstructured debate fails; validates formal argumentation. |
| "Reliable Agent Engineering... Organizational Principles" (Dec 2025) | The Solution Statement. Organization over model size. |
| "Agent Interoperability Protocols: MCP, A2A, ANP" (May 2025) | Technical protocol breakdown. Connect to classical interaction patterns. |
| "Game-Theoretic Lens on LLM-based MAS" (Jan 2026) | Modeling agents as rational actors. |

### Key References

**Landmark Papers**
- Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" ICLR 2025 ([arXiv](https://arxiv.org/abs/2503.13657))
- Kim et al., "Towards a Science of Scaling Agent Systems" Google DeepMind 2025 ([arXiv](https://arxiv.org/abs/2512.08296))
- Tran et al., "Multi-Agent Collaboration Mechanisms: A Survey of LLMs" 2025 ([arXiv](https://arxiv.org/abs/2501.06322))

**Production Systems**
- [Anthropic: How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Google ADK: Developer's Guide to Multi-Agent Patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [Google Research: Towards a Science of Scaling Agent Systems](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)

**Foundational Theory**
- Malone & Crowston, "The Interdisciplinary Study of Coordination" ACM Computing Surveys 1994
- Hoare, "Communicating Sequential Processes" 1978
- Hewitt et al., "A Universal Modular ACTOR Formalism for AI" IJCAI 1973
- Smith, "The Contract Net Protocol" 1980
- Durfee, "Distributed Problem Solving and Planning" in Weiss (ed.) *Multiagent Systems* 1999
- Lesser & Corkill, "Functionally Accurate, Cooperative Distributed Systems" 1983

**Human Team Science**
- Edmondson, "Psychological Safety and Learning Behavior in Work Teams" 1999
- Weick & Sutcliffe, "Managing the Unexpected" (HRO principles)
- McChrystal, "Team of Teams" (shared consciousness + empowered execution)
- Gawande, "The Checklist Manifesto"

### The Ecosystem

| Repo                        | What It Is | Our Angle                                           |
| --------------------------- | ---------- | --------------------------------------------------- |
| `e2b-dev/awesome-ai-agents` | The Bazaar | They curate tools; we own patterns.                 |
| `microsoft/autogen`         | The Swarm  | Closest to Actor Model. Lacks a Control Shell.      |
| `langchain-ai/langgraph`    | The Graph  | Static coordination. Contrast with dynamic/holonic. |
| `geekan/MetaGPT`            | The SOP    | Implemented stigmergy without naming it.            |
| `VEsNA-ToolKit/chatbdi`     | The Proof  | Literal BDI in LLMs. Our closest ally.              |
| `modelcontextprotocol`      | The Pipe   | The USB-C layer. Build on top of, not against.      |

## Paper-Specific Status

| Paper | Target | Status | Details |
|-------|--------|--------|---------|
| **Paper 1**: Sutra (this paper) | ArXiv, AAMAS 2027 | Source material ~85% ready, 0% written | [LaTeX](latex/main.tex) |
| **Paper 2**: Agent 0 | Nature MI / NeurIPS 2027 | LaTeX draft complete, needs figures + ablation | [cointelligence/README.md](../cointelligence/README.md) |

## Key Documents

| Document | Purpose |
|----------|---------|
| [contributions.md](contributions.md) | 8 contributions + methodology preamble + Paper 2 bridge (central document) |
| [appendix-seed-papers-and-repos.md](appendix-seed-papers-and-repos.md) | 22 classical + 11 modern bridge seed paper tables |
| [appendix-research-commands.md](appendix-research-commands.md) | 6 Claude Code research commands (Level 1 methodology instruments) |

---

*Part of the [Kapi AI](https://getkapi.com) research portfolio. This research informs Kapi's multi-agent coordination architecture.*
