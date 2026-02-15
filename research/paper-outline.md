# Paper Outline: Sutra — Threading Classical Coordination Through the Age of LLM Agents

> Target: ArXiv (cs.MA + cs.AI), ~45-60 pages
> Extraction: 9-page AAMAS 2027 submission from Sections 1-2, 5-6, 8, 10
> Author: Balaji Viswanathan

---

## Section 1: Introduction (~3 pages)

**Opening hook**: The hockey stick. Figure 1 = Google Trends chart showing "agentic AI" search interest exploding 2024-2026. The renaissance is real. Everyone is building multi-agent systems.

**The uncomfortable truth** (paragraph 2): But they're failing. 40-80% failure rates (Cemri et al., ICLR 2025). 17.2x error amplification when agents operate independently (Kim et al., Google DeepMind 2025). 36.9% of failures from inter-agent misalignment.

**The thesis** (paragraph 3):
> These failures are not evidence that multi-agent coordination doesn't work. They are evidence that 30 years of coordination theory is being ignored. The fix is not better models or better prompting. The fix is better structure.

**The popular narrative, fact-checked** (3-4 paragraphs): The mainstream story is ~60% correct, ~20% misleading, ~20% dangerously incomplete.
- Source: `MAS rebirth.md`
- What's correct: historical arc (FIPA peak → DL eclipse → LLM revival), coordination tax, context partitioning, sequential penalty, small teams consensus
- What's misleading: "LLMs solved communication" — the 6-row comparison table (FIPA era vs. modern frameworks) showing typed performatives vs. unstructured strings, protocol structure vs. "just call the next agent," commitment tracking vs. nothing
- What's dangerously missing: result sharing (Durfee), commitment tracking, FA/C philosophy, Contract Net, humans as peers not supervisors

**The gap statement**: Two buckets exist (tool lists vs. academic benchmarks) and nothing in between. No work maps classical MAS primitives to modern LLM implementations with empirical evidence. Table: 5 closest existing works and the gap we fill (from README.md).

**Contributions** (numbered list, 1-2 sentences each):
1. **The Sutra Corpus** — 12,527 papers processed by a 7-agent blackboard pipeline with structured coordination-pattern annotations
2. **Semi-supervised 16-segment MAS taxonomy** — bridging 50 years of research into a navigable map with reading triples per segment
3. **The Lost Canary Algorithm** — a citation-graph methodology for detecting forgotten concepts (4 genuinely lost, 8 renamed without citation)
4. **The Rosetta Stone** — a classical-to-modern mapping with fidelity ratings, gap analysis, and protocol-level translation
5. **Eight Design Principles** — synthesized from organizational science, classical MAS theory, and production system evidence, each with falsifiable predictions
6. **Empirical validation** — 9 classical patterns + 2 baselines tested across 5 benchmarks (58 experiments); star result: Blackboard V2 = 95/100
7. **Open research infrastructure** — the Sutra Portal (interactive dashboard), GitHub repository (structured corpus + experiment harness), and pipeline code
8. **Replication infrastructure** — Agent 5/6 scouting + reproduction targets for 6 key papers (bridges to follow-up paper)

**Paper organization** (final paragraph): roadmap of remaining sections.

---

## Section 2: Background — The Arc of Multi-Agent Systems (~4 pages)

**Purpose**: Establish the historical context. Not a full survey (that's Section 4) but enough for a reader new to classical MAS to follow the argument.

### 2.1 The Classical Era (1980-2005)
- The founding problem: distributed problem solving (Durfee, Lesser, Corkill)
- Three intellectual traditions: Joint Intentions school, DAI/Cooperation Frameworks, Social/Organizational school
- Key protocols: Contract Net (Smith 1980), KQML (1993), FIPA ACL (1997-2003)
- Key architectures: Blackboard (Nii 1986), BDI (Rao & Georgeff 1995)
- Key theory: Coordination Theory (Malone & Crowston 1994), SharedPlans (Grosz & Kraus 1996), Argumentation (Dung 1995)
- The peak: AAMAS founded 2002, FIPA standards ratified, JADE mature
- Source: `theoretical-foundations.md`, `classical-mas-llm-bridge.md`

### 2.2 The Lost Decade (2006-2022)
- AlexNet (2012) → Transformers (2017) → GPT-3 (2020): attention and funding shift to scaling single models
- MAS research continues (AAMAS, JAAMAS) but loses mainstream visibility
- The citation cliff begins: root primitives accumulate total citations but modernity scores drop below 0.05
- JADE stops maintenance (2021). FIPA effectively dormant.
- Source: `modernity_scores.json`, era distribution from corpus (2010s = 12.2%, the trough)

### 2.3 The LLM Agent Renaissance (2023-2026)
- AutoGen (2023), CrewAI (2024), LangGraph (2024), Google ADK (2025)
- The protocol stack emerges: MCP (agent-to-tool), A2A (agent-to-agent), ANP (discovery)
- The 2025+ surge: 26.3% of our corpus is from 2025+
- Production deployments: Anthropic, Cognition Devin, ChatDev, MetaGPT
- But: building from scratch, ignoring 30 years of theory
- The bifurcation: classical researchers extend toward LLMs (ChatBDI, NatBDI, SPADE) while framework developers build from scratch
- Source: `evolution-from-classics-to-mcp.md`, `classical-mas-llm-bridge.md`

### 2.4 The Failure Landscape (Quantified)
- Cemri et al.'s 14 failure modes across 3 categories (FC1: Spec/Design, FC2: Inter-Agent, FC3: Verification)
- Kim et al.'s 180 configurations: 17.2x vs. 4.4x vs. hybrid
- The 45% capability ceiling, the sequential penalty (39-70%)
- The 87% architecture prediction accuracy from task features alone
- Key insight: "failures require more complex solutions" — not prompt fixes but organizational design
- Source: `why-mas-works.md` (The Numbers section)

---

## Section 3: Methodology (~5 pages)

### 3.1 The Two-Level Human-AI Research Architecture
- Level 1: Interactive (6 custom Claude Code commands, sprints r1-r2)
- Level 2: Autonomous (8-agent blackboard pipeline, sprint r3+)
- The transition: Level 1 findings informed Level 2 design
- Self-referential note: the pipeline IS a blackboard architecture studying blackboard architectures
- Source: `contributions.md` methodology preamble

### 3.2 The Lost Canary Algorithm
- Phase 1: Seed selection (22 classical + 11 modern bridge, 6 MAS branches)
- Phase 2: Backward pass (root primitive scoring: `cite_count x branch_diversity`, threshold >= 6)
- Phase 3: Forward pass (modernity score, Lost Canary threshold: total > 500, modernity < 0.05)
- Phase 4: Concept tracing (anti-false-positive checks: field growth normalization, survey citation check, indirect citation check)
- Phase 5: Multi-perspective assessment (Archivist / Modernist / Bridge Builder + Critic)
- Phase 6: Human synthesis (5 irreplaceable author roles)
- Self-critique protocol: 4 mandatory questions per mapping, verdicts (STRONG/WEAK/FALSE ALARM/GENUINELY NEW)
- Source: `contributions.md` C1 and C3

### 3.3 The 7-Agent Blackboard Pipeline
- Agent table (7 agents: Collector, Relevance Filter, Deep Analyst, Async Analyst, Citation Enricher, Scout, Reproducer)
- Status flow diagram
- Concurrency model (FOR UPDATE SKIP LOCKED)
- Feedback expansion (controlled snowball with 3 safety bounds)
- FP/FN validation (author-supervised sampling, convergence to 0%/0%)
- Source: `contributions.md` C1

### 3.4 The Semi-Supervised Taxonomy Method
- Structured embedding construction (MAS-aware, not raw abstracts)
- 16 expert-curated anchor clusters with rich descriptions
- Cosine-similarity assignment (not iterative clustering)
- Iterative refinement: HDBSCAN (63 micro-clusters) → k-means k=10 → k=16 → guided anchors
- UMAP + custom physics for visualization
- Reading triple identification (landmark, central, survey per cluster)
- Source: `contributions.md` C2

### 3.5 The Experiment Harness Design
- 9 patterns + 2 baselines (table with classical source per pattern)
- 5 benchmarks (code review, research synthesis, planning, cascading failure v1/v2)
- Quality scoring: LLM-as-judge against task-specific rubrics
- Metrics: quality score, total tokens, token efficiency, rounds, wall time, per-agent breakdown
- Source: `contributions.md` C6

---

## Section 4: The 16 Pillars of Multi-Agent Systems — A Structured Survey (~20 pages)

**Purpose**: This is the survey-within-the-survey. For each of the 16 MAS segments, we provide: (a) the classical foundation, (b) the modern state of the art, (c) the gap/bridge between them, (d) key trends, (e) the reading triple. This is the section that makes the paper a tour-de-force reference.

**Figure**: The UMAP cluster visualization (the "signature figure") showing 6,500+ papers colored by cluster, with era shading. Classical papers and modern papers landing in the same cluster = visual proof of reinvention.

### 4.1 Blackboard & Shared State Coordination
- **Classical**: Nii 1986 (Blackboard Systems), Hearsay-II (Erman et al. 1980), BB1 control shell
- **The 3 components**: shared state, knowledge sources, control shell
- **Modern**: LangGraph StateGraph, Redis shared context, LbMAS (2025: 13-57% improvement, 3x fewer tokens)
- **The gap**: Shared state survives. Control shell is lost. Our experiment: V1 (no control shell) = 62, V2 (LLM control shell) = 95 — the +53% is the control shell
- **Key trend**: Convergence toward shared-state patterns across all major frameworks
- **Reading triple**: Landmark: Nii 1986 | Central: LbMAS 2025 | Survey: [best cluster survey]
- Source: `theoretical-foundations.md` (stigmergy section), experiment results, `contributions.md` C6

### 4.2 Contract Net & Task Allocation
- **Classical**: Smith 1980 (The Contract Net Protocol), TRACONET, announce/bid/award cycle
- **Modern**: DALA (VCG auctions, 84.32% MMLU, strategic silence), Magentic Marketplace (Microsoft), A2A task lifecycle
- **The gap**: Bid/award pattern survives informally but without formal cost models, marginal cost bidding, or the ability for agents to self-select. Modern "routing" is centralized dispatch, not decentralized bidding.
- **Key trend**: Mechanism design for LLMs (Google Research 2025), token auction mechanisms
- **Reading triple**: Landmark: Smith 1980 | Central: DALA 2025 | Survey: [best cluster survey]
- Source: `classical-mas-llm-bridge.md` Section 4

### 4.3 Organizational Design & Team Structure
- **Classical**: AGR (Agent-Group-Role), MOISE, Horling & Lesser 2004 (8 organizational paradigms: hierarchy, holarchy, coalition, team, congregation, society, federation, market)
- **Modern**: CrewAI roles, AutoGen group chat, Google ADK sequential/parallel/loop agents
- **The gap**: Role labels survive but formal org theory (authority gradients, holarchies, normative rules) absent. No framework implements true recursive holonic self-organization.
- **Key trend**: HALO (3-tier dynamic agent creation, 14.4% improvement), role-based crews
- **Human parallel**: Hackman's enabling conditions, Google Aristotle, Team of Teams shared consciousness
- **Reading triple**: Landmark: Horling & Lesser 2004 | Central: [best] | Survey: [best]
- Source: `organizational-principles.md`, `classical-mas-llm-bridge.md` Section 5

### 4.4 Distributed Problem Solving & Cooperation
- **Classical**: GPGP (Generalized Partial Global Planning), FA/C (Lesser & Corkill 1983), result sharing (Durfee 1999)
- **The 4 ways result sharing improves**: confidence, completeness, precision, timeliness
- **Modern**: No framework explicitly implements result sharing. All do task sharing (divide work). None do result sharing (improve each other's work).
- **The gap**: The FA/C philosophy — sharing partial, tentative results early — is the opposite of rigid sequential graph workflows. LLMs are naturally FA/C-compatible (probabilistic, tentative) but forced into all-or-nothing execution.
- **Key trend**: Early signs of FA/C thinking in streaming architectures and progressive elaboration patterns
- **Reading triple**: Landmark: Lesser & Corkill 1983 | Central: Durfee 1999 | Survey: [best]
- Source: `durfee-result-sharing.md`

### 4.5 Joint Intentions & Shared Plans
- **Classical**: Cohen & Levesque 1990 (Joint Intentions), Grosz & Kraus 1996 (SharedPlans), STEAM (Tambe 1997)
- **The obligation-to-inform**: When an agent's goal becomes unachievable, it must inform all team members. Joint commitment is not individual commitment — it requires mutual belief.
- **Modern**: No equivalent. No framework tracks shared goals, mutual belief, or obligation-to-inform.
- **The gap**: Our experiment — JPG scores 52/100 (lowest), because LLMs can't detect epistemic failures. The obligation-to-inform never triggers because the LLM always produces confident-looking output.
- **Novel finding**: Shared-constraint patterns (blackboard) outperform shared-goal patterns (JPG) for knowledge tasks because they propagate epistemic limits externally.
- **Reading triple**: Landmark: Cohen & Levesque 1990 | Central: Grosz & Kraus 1996 | Survey: [best]
- Source: `contributions.md` C6 (JPG star result)

### 4.6 Agent Communication Languages & Protocols
- **Classical**: KQML (Finin et al. 1994), FIPA ACL (2000), 22 typed performatives, interaction protocol state machines
- **The separation principle**: KQML separated *what* is communicated (content) from *how* (protocol). FIPA added formal semantics — each performative has preconditions and postconditions.
- **Modern**: MCP (agent-to-tool, Anthropic), A2A (agent-to-agent, Google), ANP (discovery, W3C DID)
- **The gap**: MCP and A2A handle transport and task lifecycle but NOT the semantics of conversation. The FIPA performative gap table: 9 performatives mapped, gaps concentrate on negotiation (cfp, propose, accept-proposal, reject-proposal).
- **Key trend**: Protocol standardization accelerating (Linux Foundation, AAIF), but semantic layer still missing
- **Reading triple**: Landmark: FIPA ACL 2000 | Central: A2A spec 2025 | Survey: Agent Interop Protocols (May 2025)
- Source: `evolution-from-classics-to-mcp.md`, `contributions.md` C4 (FIPA gap table)

### 4.7 Argumentation & Structured Debate
- **Classical**: Dung 1995 (Abstract Argumentation Frameworks), attack/support relations, argumentation-based negotiation (Rahwan et al.)
- **Modern**: Generator/Critic pattern (Google ADK), multi-agent debate (Du et al. 2023)
- **The sobering result**: "Can LLM Agents Really Debate?" (Nov 2025) — majority pressure suppresses correction (3.6% for weak models), eloquence beats correctness, debate induces a martingale. Performance gains come from voting, not argumentation.
- **The gap**: Unstructured debate fails. Formal argumentation (typed attack/support with validity evaluation) works — but no framework implements it.
- **Key trend**: Moving from free-form debate to structured critique (propose-counter with typed reasons)
- **Reading triple**: Landmark: Dung 1995 | Central: "Can LLM Agents Really Debate?" 2025 | Survey: [best]
- Source: `classical-mas-llm-bridge.md` Section 3

### 4.8 Negotiation & Game Theory
- **Classical**: Nash bargaining, VCG mechanism, Rosenschein & Zlotkin 1994 (Rules of Encounter), automated negotiation (Jennings et al. 2001)
- **Why "chatting" is unstable**: Without game-theoretic constraints, negotiation doesn't guarantee convergence. Jennings 2001 proved this.
- **Modern**: Game-theoretic LLM (Nov 2024, Nash Equilibria guidance), personality-driven argumentation (EMNLP 2025), LLM-Deliberation (NeurIPS 2024)
- **The gap**: No framework implements formal negotiation protocols with convergence guarantees. "Negotiation" in LLM systems means free-text turn-taking.
- **Key trend**: "Game-Theoretic Lens on LLM-based MAS" (Jan 2026) — modeling agents as rational actors
- **Reading triple**: Landmark: Rosenschein & Zlotkin 1994 | Central: [best] | Survey: Game-Theoretic Lens 2026
- Source: `classical-mas-llm-bridge.md` Section 3

### 4.9 BDI & Cognitive Agent Architectures
- **Classical**: Rao & Georgeff 1995 (BDI), AgentSpeak, Jason/JaCaMo
- **The mapping**: Beliefs = RAG, Desires = system prompt, Intentions = CoT reasoning
- **Modern**: ChatBDI (AAMAS 2025, most direct bridge), NatBDI (AAMAS 2024), BDI structured prompting (HAI 2023), hybrid BDI-LLM for safety-critical (2025)
- **The gap**: Modern LLMs have BDI capabilities but no explicit BDI architecture. No commitment to intentions (intention reconsideration), no plan library, no belief revision.
- **Key insight**: "Strong Agency capabilities deployed with Weak Agency architectures" (Wooldridge & Jennings 1995)
- **Reading triple**: Landmark: Rao & Georgeff 1995 | Central: ChatBDI 2025 | Survey: [best]
- Source: `classical-mas-llm-bridge.md` Section 1

### 4.10 Stigmergy & Indirect Coordination
- **Classical**: Grasse 1959 (termite mound building), sematectonic vs. marker-based, cognitive stigmergy (Omicini), Artifacts
- **Modern**: MetaGPT SOPs (agents communicate through documents, not dialogue), ChatDev (code as coordination artifact), Wikipedia editing model
- **Token scaling insight**: Stigmergic coordination scales O(n). Direct messaging scales O(n^2). This explains the 3x token efficiency of blackboard/stigmergy approaches.
- **The gap**: MetaGPT implements stigmergy without naming it. No framework provides first-class artifact support with perception, sharing, and rational use.
- **Formal guarantees**: CodeCRDT (Oct 2025) — CRDT-based stigmergy with proven safety invariants and strong eventual consistency (<200ms convergence)
- **Reading triple**: Landmark: Grasse 1959 | Central: MetaGPT 2024 | Survey: [best]
- Source: `theoretical-foundations.md` (stigmergy section)

### 4.11 Human-Agent Interaction & HITL
- **Classical**: Mixed-initiative interaction, adjustable autonomy (Scerri et al.), COLLAGEN (Grosz & Sidner)
- **Modern**: Approval queues, escalation, review-before-send (Kapi Layer 6), cursor-style pair programming
- **The missing frame**: Humans as peer agents (not supervisors) who participate in the same protocols — bid in Contract Net auctions, contribute to blackboards, tracked with same commitment lifecycle
- **Key data**: 68% of production agents perform at most 10 steps before human handover
- **Key trend**: Moving from "human approves AI output" to "human and AI are co-scientists" (Paper 2 preview)
- **Human parallel**: Aviation CRM, surgical checklist, submarine reader-worker pattern
- **Reading triple**: Landmark: Scerri et al. (adjustable autonomy) | Central: [best] | Survey: [best]
- Source: `organizational-principles.md` Principle 2, `MAS rebirth.md` (HITL section)

### 4.12 Trust, Reputation & Social Norms
- **Classical**: Trust models (Sabater & Sierra), reputation systems, social norms (Shoham & Tennenholtz), institutional rules (Esteva et al.)
- **Modern**: System prompt guardrails, RLHF alignment, constitutional AI, safety filters
- **The gap**: System prompts state norms but don't enforce them. No norm violation detection, no reputation tracking, no formal social contracts between agents.
- **Key trend**: EU AI Act compliance requirements driving formal accountability; guardrails as a necessity, not a feature
- **Reading triple**: Landmark: Shoham & Tennenholtz (social norms) | Central: [best] | Survey: [best]
- Source: `classical-mas-llm-bridge.md` Section 6 (The 10 Gaps, #8)

### 4.13 Agent-Oriented Software Engineering
- **Classical**: AOSE methodologies (Prometheus, GAIA, Tropos), JADE platform, formal verification (model checking agent protocols)
- **Modern**: LangGraph graph definition, CrewAI YAML configuration, AutoGen code generation
- **The gap**: No methodology for designing agent systems (just "prompt and hope"). No formal verification of agent interaction protocols. No termination or safety proofs.
- **The 10 gaps** (from classical-mas-llm-bridge.md): formal commitments, performative semantics, shared ontologies, protocol verification, composability, resource-bounded reasoning — all absent from every current framework
- **Reading triple**: Landmark: JADE / FIPA | Central: [best] | Survey: "Contemporary Agent Technology" (Sep 2025)
- Source: `classical-mas-llm-bridge.md` Section 6

### 4.14 Multi-Agent Robotics & Swarm Intelligence
- **Classical**: Multi-robot coordination, swarm intelligence (Reynolds boids, ant colony optimization), formation control
- **Modern**: LLM-adaptive drone swarms (Sep 2025: LLMs select between centralized/hierarchical/holonic architectures), embodied multi-agent reinforcement learning
- **Scope note**: Robotics MAS is a distinct sub-community with different constraints (physical, real-time, safety-critical). We survey for completeness but the paper's primary focus is software/knowledge agent coordination.
- **Reading triple**: Landmark: Reynolds 1987 / Ant Colony Optimization | Central: [best] | Survey: [best]

### 4.15 LLM Multi-Agent Frameworks
- **Classical precedent**: None (this is genuinely new)
- **The current landscape**: LangGraph (graph-based), CrewAI (role-based), AutoGen (conversation-based), MetaGPT (SOP-based), ChatDev (code-centric), Google ADK (sequential/parallel/loop)
- **Framework comparison** (7 frameworks on 10 dimensions): coordination pattern, state management, HITL support, error recovery, protocol typing, scalability, etc.
- **Key finding**: All reinvent classical patterns without citing them. MetaGPT = stigmergy. AutoGen = actor model. LangGraph = blackboard (minus control shell). CrewAI = organizational paradigms.
- **Reading triple**: Landmark: AutoGen 2023 | Central: LangGraph 2024 | Survey: "Reliable Agent Engineering" (Dec 2025)
- Source: `classical-mas-llm-bridge.md` (framework status), README ecosystem table

### 4.16 Evaluation, Benchmarking & Failure Analysis
- **Classical**: Agent competition platforms, RoboCup, Trading Agent Competition
- **Modern**: GAIA, SWE-bench, HumanEval, MMLU; Cemri et al.'s 14 failure modes; Kim et al.'s scaling study
- **Our contribution**: The experiment harness (9 patterns x 5 benchmarks) and the failure-mode-to-classical-solution mapping
- **The gap**: No benchmark evaluates coordination quality. All evaluate task output. Our benchmarks specifically test coordination patterns (e.g., cascading failure V2 tests epistemic honesty, not task completion).
- **Key trend**: Moving from "did the agent solve the problem?" to "how well did the agents coordinate?"
- **Reading triple**: Landmark: Cemri et al. ICLR 2025 | Central: Kim et al. 2025 | Survey: [best]
- Source: `contributions.md` C6

---

## Section 5: Results (~7 pages)

### 5.1 The Sutra Corpus: Scale and Structure
- Final corpus statistics (12,527 papers, era distribution, pattern distribution)
- The 2010s trough as visible evidence of the citation disconnect
- Figure: Era distribution histogram (pre-1990 through 2025+)

### 5.2 Lost Canaries Found
- 18 root primitives → 6 candidates → 3-way classification
  - 4 genuinely lost (Joint Persistent Goals, Discourse Coherence, Formal Responsibility, Social Knowledge Semantics)
  - 1 known-but-ignored
  - 8 renamed without citation
- The aggregate signal: top 10 "missing classical concepts" from 12,527 papers (Org Models: 5,556; BDI: 4,166; FIPA: 3,882; ...)
- Triangulation: bottom-up (LLM-flagged) correlates with top-down (citation-based)
- Figure: **The Citation Cliff** — the signature figure. X=time, Y=citations/year per concept, color=lost/renamed/active

### 5.3 The Rosetta Stone
- The consolidated mapping table (14+ entries with fidelity ratings: Full/Medium/Low/None)
- Per-entry: classical concept, year, modern equivalent, fidelity, what's lost in translation
- The protocol-level mapping (FIPA performatives → A2A/MCP equivalents, gap analysis)
- The reinvention edge graph: concept overlap without citation
- Figure: Reinvention detection bipartite graph (modern papers left, classical papers right, edges colored by citation presence)

### 5.4 The 16-Segment Taxonomy
- The UMAP cluster visualization with reading triples
- Per-cluster statistics: paper count, era split, landmark/central/survey papers
- Cross-cluster citation patterns: which clusters cite each other? Where are the bridges? Where are the walls?
- Figure: The UMAP cluster map (the "poster figure")

### 5.5 Open Research Artifacts: The Sutra Portal and Repository
- **The GitHub repository** — not a reading list but a research instrument:
  - The Sutra Corpus as structured JSON (12,527 papers with coordination pattern annotations, classical concept gaps, Rosetta entries)
  - 16-cluster taxonomy with reading triples per cluster
  - Citation edges + reinvention edges (concept overlap without citation)
  - Lost Canary data (modernity scores, concept traces, 3-way classifications)
  - The experiment harness (runnable: 9 patterns + 2 baselines + 5 benchmarks)
  - The Rosetta Stone as machine-readable JSON (queryable in both directions)
  - ~12,000 lines of pipeline code (7-agent blackboard system)
- **Comparison with existing repos**: Table comparing against 7 top paper-list repos (25K+ stars combined). No existing repo provides structured metadata, cross-era connections, citation relationships, or queryable data. All are curated bibliographies.
- **The Sutra Portal** (sutra.balajivis.com) — interactive research dashboard:
  - Coordinated visualizations across the corpus (cluster map, citation graph, era distribution, pattern distribution)
  - 12 routes, 26 components, 25 API endpoints — built with zero external chart libraries
  - Figure: Screenshot of the cluster map visualization with era shading
- Source: `contributions.md` C7, `portal-analysis.md`

### 5.6 What's Genuinely New
- 4 capabilities LLMs bring that classical MAS couldn't do:
  1. Natural language understanding for flexible communication
  2. Few-shot generalization across domains
  3. Implicit world models for common-sense reasoning
  4. Integration scale via MCP (10,000+ tool servers)
- Honest scholarship: not everything is reinvention. Some things are genuinely new.

---

## Section 6: The Eight Design Principles (~4 pages)

**Purpose**: The prescriptive contribution. Synthesized from organizational science, classical MAS theory, and production systems evidence.

| # | Principle | Human Origin | Agent Implementation | Evidence |
|---|-----------|-------------|---------------------|----------|
| 1 | Start with dependencies, not agents | Malone & Crowston 1994 | Map task dependency structure before choosing topology | Kim et al.: 87% prediction accuracy from task features |
| 2 | Architecture selection is measurable | DeepMind scaling study | Use decomposability to predict topology | 180 configurations tested |
| 3 | Communicate through artifacts, not chat | MetaGPT, stigmergy, blackboard | Shared versioned workspace; O(n) not O(n^2) | 3x token efficiency (LbMAS) |
| 4 | Enforce conceptual integrity | Brooks' surgical team | One agent/human as architectural guardian; ADRs | Hackman: conditions > capability |
| 5 | Quality gates at every handoff | CRM readback, surgical checklists | Generator/Critic, typed verification | CRM: 50%+ accident reduction |
| 6 | Scale token investment, not agent count | Anthropic production system | Upgrade model before adding agents | 80% variance from token budget |
| 7 | Bound autonomy explicitly | Auftragstaktik, HROs, Linux maintainers | Clear scope, escalation, "I don't know" | 68% of agents: <=10 steps before human |
| 8 | Design for failure recovery | Erlang/OTP, HRO resilience | Checkpointing, restart strategies, circuit breakers | *(Gap: nobody does this yet)* |

For each principle: 1 paragraph human evidence, 1 paragraph agent implementation, 1 paragraph empirical support.

- Source: `why-mas-works.md` (8 principles), `organizational-principles.md` (10 human team principles)

---

## Section 7: Empirical Validation (~5 pages)

### 7.1 The Experiment Matrix
- 11 patterns x 5 benchmarks = 55 cells (58 total results including reruns)
- Table: Full result matrix (quality scores, token counts)
- Figure: Pattern comparison bar chart (quality vs. tokens per pattern)

### 7.2 Star Result 1: The Control Shell Breakthrough
- Blackboard V1 (62) vs V2 (95): +53.2% quality, -50.3% tokens
- V2 control shell decisions: adaptive agent selection, early stopping
- Confirms Nii 1986: the control shell is the most valuable component
- Source: `contributions.md` C6

### 7.3 Star Result 2: The Epistemic Failure Gap (Novel Finding)
- JPG scores 52/100 (lowest) despite using most tokens (37,567)
- Why: LLMs can't detect epistemic failures. The obligation-to-inform never triggers.
- Blackboard V2 (82) propagates epistemic limits through shared state. JPG (52) doesn't.
- The novel claim: shared-constraint > shared-goal for knowledge tasks with LLMs
- Source: `contributions.md` C6

### 7.4 Cross-Pattern Analysis
- Which patterns consistently outperform baselines? Under what conditions?
- Token efficiency analysis: coordination overhead vs. productive work
- Pattern selection guidance: "For task type X, use pattern Y"
- Connect each finding to a Rosetta Stone entry and a Design Principle

### 7.5 The Self-Referential Validation
- The pipeline = a blackboard architecture. Blackboard V2 = highest score.
- Not a proof, but a self-consistency check: the methodology validates the thesis.

---

## Section 8: Related Work (~3 pages)

### 8.1 Existing Surveys of LLM Agent Systems
- Tran et al. 2025 ("Multi-Agent Collaboration Mechanisms: A Survey of LLMs")
- "Contemporary Agent Technology: LLM-Driven vs Classic MAS" (Sep 2025) — diagnoses the disconnect but doesn't prescribe solutions
- "Reliable Agent Engineering Should Integrate Machine-Compatible Organizational Principles" (Dec 2025) — argues for org theory but provides the manifesto, not the manual
- "Agent Interoperability Protocols: MCP, A2A, ANP" (May 2025) — protocol breakdown but no connection to classical interaction patterns
- Position against each: what they cover, what gap we fill

### 8.2 Classical MAS Surveys
- Wooldridge & Jennings 1995 (Weak vs Strong Agency)
- Horling & Lesser 2004 (Organizational Paradigms)
- Durfee 1999 (Distributed Problem Solving)
- Weiss (ed.) 1999 (Multiagent Systems: A Modern Approach)
- Position: these are the foundations we thread forward

### 8.3 Failure Analysis and Scaling Studies
- Cemri et al., ICLR 2025 (the problem statement)
- Kim et al., Google DeepMind 2025 (the empirical proof)
- AgentArch/ServiceNow 2025 (35.3% max on enterprise tasks)
- Position: we map every failure mode to a classical solution

### 8.4 Production Multi-Agent Systems
- Anthropic multi-agent research system
- Google ADK patterns
- MetaGPT, ChatDev, Cognition Devin
- Position: we explain *why* these systems work using coordination theory

### 8.5 Human Team Science Applied to AI
- Hackman (enabling conditions), Edmondson (psychological safety)
- Weick & Sutcliffe (HROs), McChrystal (Team of Teams)
- Gawande (surgical checklists), aviation CRM
- Position: we synthesize these into 8 actionable design principles

### 8.6 Bridge Papers (Closest to Our Work)
- ChatBDI (AAMAS 2025) — most direct classical-modern bridge for BDI
- "Game-Theoretic Lens on LLM-based MAS" (Jan 2026) — closest to formal MAS + LLMs
- DALA (Nov 2025) — closest to Contract Net + LLMs
- Position: these are allies. We provide the umbrella framework they fit into.

---

## Section 9: Discussion (~3 pages)

### 9.1 The Counter-Narrative: Distillation
- AgentArk (Feb 2026): distill multi-agent debate dynamics into single model weights
- Implication: MAS may be most valuable as a training-time technique for well-understood tasks
- Reframe: for novel, decomposable, context-heavy tasks, coordinate at runtime. For learned tasks, distill.

### 9.2 When NOT to Use MAS
- Sequential tasks (39-70% degradation)
- Single-agent accuracy >45% on non-decomposable tasks (adding agents hurts)
- Well-understood tasks where distillation is cheaper
- Honesty about limits strengthens the thesis

### 9.3 Limitations
- Corpus bias: pipeline seeded from ArXiv + specific GitHub lists; may underrepresent non-English MAS research
- Lost Canary methodology: citation-based detection may miss concepts that were transmitted through textbooks rather than papers
- Experiment harness: N=1 runs (need statistical reruns), LLM-as-judge evaluation (need human baselines)
- Self-referential risk: the pipeline validates blackboard, but we built the pipeline as a blackboard — potential confirmation bias
- Model dependency: all experiments on Claude Opus 4.6; results may not generalize to weaker models

### 9.4 Open Problems
- The commitment tracking gap (7 gaps without modern equivalent)
- Formal verification of LLM agent protocols
- Holonic self-organization with LLMs
- Resource-bounded reasoning (agents managing their own token budgets)
- The human-agent protocol formalization (preview of Paper 2)

---

## Section 10: Conclusion (~1 page)

Restate the thesis with evidence:
- 12,527 papers analyzed → 4 genuinely lost concepts + 8 renamed without citation
- 16-segment taxonomy bridging 50 years of MAS research
- 8 design principles from organizational science → agent implementation
- Blackboard V2 with control shell: 95/100 (+53% over static, -50% tokens)
- JPG epistemic failure: the novel finding that changes how we think about shared goals in LLM systems

The punchline:
> The 40-80% failure rate in modern multi-agent systems is not a law of nature. It is a design failure. The solutions existed before the problems were created. This paper threads those solutions through.

---

## Appendices

### Appendix A: Seed Papers
- 22 classical + 11 modern bridge papers with DOIs and selection rationale
- Source: `appendix-seed-papers-and-repos.md`

### Appendix B: Research Commands
- 6 Claude Code commands with prompt summaries
- Source: `appendix-research-commands.md`

### Appendix C: Full Experiment Results
- Complete 11 x 5 result matrix with all metrics
- Per-agent token breakdowns for star results

### Appendix D: Corpus Statistics
- Full era distribution, pattern distribution, MAS branch distribution
- Cluster populations and reading triples for all 16 segments

---

## Figures (Planned)

| # | Figure | Section | Source | Status |
|---|--------|---------|--------|--------|
| 1 | Google Trends "agentic AI" hockey stick | 1 | Screenshot | HAVE IT |
| 2 | Era distribution histogram | 5.1 | Corpus stats | TO GENERATE |
| 3 | **The Citation Cliff** (signature figure) | 5.2 | `modernity_scores.json` | TO GENERATE |
| 4 | The UMAP cluster map | 5.4 | Dashboard / Postgres | TO GENERATE |
| 5 | Reinvention bipartite graph | 5.3 | `reinvention_edges` | TO GENERATE |
| 6 | Pipeline architecture diagram | 3.3 | Manual | TO DRAW |
| 7 | Pattern comparison bar chart | 7.1 | Experiment results | TO GENERATE |
| 8 | Blackboard V1 vs V2 detail | 7.2 | Experiment results | TO GENERATE |
| 9 | JPG vs Blackboard V2 on cascading failure | 7.3 | Experiment results | TO GENERATE |
| 10 | The Rosetta Stone table (full-page) | 5.3 | Consolidated sources | TO FORMAT |
| 11 | Sutra Portal screenshot (cluster map) | 5.5 | sutra.balajivis.com | SCREENSHOT |
| 12 | GitHub repo comparison table | 5.5 | `contributions.md` C7 | TO FORMAT |

---

## Page Budget Estimate

| Section | Pages | Notes |
|---------|-------|-------|
| 1. Introduction | 3 | Hook + thesis + gap + contributions |
| 2. Background | 4 | Historical arc + failure landscape |
| 3. Methodology | 5 | Two-level architecture + pipeline + harness |
| 4. The 16 Pillars (survey) | 20 | ~1.25 pages per pillar |
| 5. Results | 7 | Corpus + Lost Canaries + Rosetta + taxonomy + open artifacts + what's new |
| 6. Design Principles | 4 | 8 principles with evidence |
| 7. Empirical Validation | 5 | Star results + cross-pattern + self-referential |
| 8. Related Work | 3 | Position against 6 categories |
| 9. Discussion | 3 | Counter-narrative + limitations + open problems |
| 10. Conclusion | 1 | |
| References | ~4 | ~150-200 references |
| Appendices | ~5 | Seed papers, commands, full results, corpus stats |
| **Total** | **~64** | **Within the 40-60 page ArXiv target (with appendices)** |

---

## Source Material Mapping

| Section | Primary Source Documents |
|---------|------------------------|
| 1 (Intro) | `MAS rebirth.md`, `why-mas-works.md` (failure stats), `README.md` (gap table) |
| 2 (Background) | `theoretical-foundations.md`, `classical-mas-llm-bridge.md`, `evolution-from-classics-to-mcp.md` |
| 3 (Methodology) | `contributions.md` (preamble, C1, C2, C3, C6) |
| 4 (16 Pillars) | All research docs + `contributions.md` C2 (16 anchors) + per-cluster data |
| 5.1-5.4 (Results) | `contributions.md` C1-C4, pipeline data JSONs |
| 5.5 (Open Artifacts) | `contributions.md` C7, `portal-analysis.md` |
| 5.6 (What's New) | Agent 3b analysis across 12,527 papers |
| 6 (Principles) | `contributions.md` C5, `why-mas-works.md`, `organizational-principles.md` |
| 7 (Experiments) | `contributions.md` C6, experiment results/ |
| 8 (Related Work) | `classical-mas-llm-bridge.md`, `README.md` (ecosystem table) |
| 9 (Discussion) | `MAS rebirth.md` (revised narrative), `why-mas-works.md` (counter-narrative) |
| 10 (Conclusion) | Synthesis |

---

## AAMAS 2027 Extraction Plan (9 pages)

For the conference submission, extract:
- Section 1 (Introduction): compressed to 1 page
- Section 2.4 (Failure Landscape): 0.5 pages
- Section 3.2 (Lost Canary Algorithm): 1 page
- Section 5.1-5.4 (Results): compressed to 2 pages (Lost Canaries + Rosetta Stone + 1 figure)
- Section 5.5-5.6 (Artifacts + What's New): 0.5 pages (mention repo URL + key capabilities)
- Section 6 (Design Principles): 1 page (table only)
- Section 7.2-7.3 (Star Results): 1.5 pages
- Section 8 (Related Work): 1 page
- Section 10 (Conclusion): 0.5 pages
- References: 0.5 pages

Drop: Section 4 (16 Pillars — too long for conference), Appendices. Reference the ArXiv version for the full survey.
