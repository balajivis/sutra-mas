# Appendix: Seed Papers

> Referenced from [Contribution 1, Step 1](contributions.md) — the curated entry points for the Sutra Corpus pipeline.

---

## Classical Seeds (22 papers across 6 MAS branches)

### Communication & Language

| Paper | Year | DOI/ID | Key Concept |
|-------|------|--------|-------------|
| Finin et al., KQML | 1994 | | Agent communication language, performatives |
| FIPA ACL Specification | 2002 | | Formal semantics for agent communication |

### Organization & Structure

| Paper | Year | DOI/ID | Key Concept |
|-------|------|--------|-------------|
| Horling & Lesser, "Multi-Agent Organizational Paradigms" | 2004 | | Hierarchies, holarchies, coalitions, teams |
| Ferber & Gutknecht, "Aalaadin: Agent Organization Model" | 1998 | | Role-based organization |

### Coordination & Planning

| Paper | Year | DOI/ID | Key Concept |
|-------|------|--------|-------------|
| Smith, "The Contract Net Protocol" | 1980 | | Task allocation via announce/bid/award |
| Malone & Crowston, "Interdisciplinary Study of Coordination" | 1994 | 10.1145/174666.174668 | Dependencies determine coordination mechanisms |
| Durfee, "Distributed Problem Solving and Planning" | 1999 | | Result sharing, partial global planning |
| Lesser & Corkill, "Functionally Accurate, Cooperative Distributed Systems" | 1983 | | FA/C philosophy, approximate solutions |
| Grosz & Kraus, "SharedPlans" | 1996 | | Collaborative plans, mutual belief |
| Cohen & Levesque, "Joint Intentions" | 1990 | | Commitment, obligation to inform |
| Decker, "TAEMS: A Framework for Environment Centered Analysis & Design of Coordination Mechanisms" | 1996 | S2:02ba020ab9b8e7c0dfb5d295656f508ba42ac922 | Task environment modeling, coordination mechanism design |
| Tambe, "Towards Flexible Teamwork" (STEAM) | 1997 | S2:16993ee7c3b785986bac54c7d4977d0f0dd8c9ae | Joint intentions in practice, teamwork model |

### Architecture & Reasoning

| Paper | Year | DOI/ID | Key Concept |
|-------|------|--------|-------------|
| Wooldridge & Jennings, "Intelligent Agents: Theory and Practice" | 1995 | | Weak vs Strong agency |
| Rao & Georgeff, BDI Architecture | 1995 | | Belief-Desire-Intention |
| Nii, "Blackboard Systems" | 1986 | | Shared state, control shell |
| Brooks, "A Robust Layered Control System for a Mobile Robot" | 1986 | | Subsumption, reactive architecture |
| Shoham & Leyton-Brown, "Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations" | 2008 | | Canonical MAS textbook, formal foundations |

### Negotiation & Game Theory

| Paper | Year | DOI/ID | Key Concept |
|-------|------|--------|-------------|
| Rosenschein & Zlotkin, "Rules of Encounter" | 1994 | | Game-theoretic agent interaction |
| Jennings et al., "Automated Negotiation" | 2001 | | Negotiation protocols survey |
| Sandholm, "An Implementation of the Contract Net Protocol Based on Marginal Cost Calculations" | 1993 | S2:9eb3c83a1ab88b96dd17cfab0f4c845dff2c6604 | Formal bidding/awarding via marginal cost (TRACONET) |

### Engineering & Verification

| Paper | Year | DOI/ID | Key Concept |
|-------|------|--------|-------------|
| Jennings, "On Agent-Based Software Engineering" | 2000 | | Agent as abstraction above Object |
| Fisher, "Formal Verification of Multi-Agent Systems" | 2005 | | Model checking for MAS |

---

## Modern Bridge Papers (11 papers, 2024-2026)

These are NOT classical seeds — they are the modern papers we position against. They serve as:
- Forward citation targets (who cites our classical seeds?)
- Gap evidence (what do they miss?)
- Competitive landscape (what has already been said?)

| Paper | Year | ArXiv/ID | Role in Our Paper |
|-------|------|----------|-------------------|
| Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" | 2025 | ICLR 2025 | **The Problem Statement.** 14 failure modes we map to classical solutions |
| Kim et al., "Towards a Science of Scaling Agent Systems" (Google DeepMind) | 2025 | | **The Empirical Proof.** Centralized > decentralized, 17.2x error amplification |
| Tran et al., "Multi-Agent Collaboration Mechanisms: A Survey of LLMs" | 2025 | 2501.06322 | **The Comprehensive Survey.** 293 citations, broad but not deep on classical roots |
| "Contemporary Agent Technology: LLM-Driven vs Classic MAS" | 2025 | | **The Competitor/Companion.** Diagnoses BDI/FIPA vs ReAct/CoT disconnect but doesn't prescribe the fix |
| "Reliable Agent Engineering... Organizational Principles" | 2025 | | **The Solution Statement.** Argues organization > model size. A manifesto without a manual |
| "Can LLM Agents Really Debate?" | 2025 | | **The Warning.** Proves unstructured debate fails; validates formal argumentation (Dung-style) |
| "A Survey of Agent Interoperability Protocols: MCP, A2A, ANP" | 2025 | | **The Protocol Breakdown.** We connect specs to classical interaction patterns |
| "Game-Theoretic Lens on LLM-based MAS" | 2026 | | **The Economic Model.** Agents as rational actors; we adapt for cooperative enterprise allocation |
| Xi et al., "The Rise and Potential of Large Language Model Based Multi-Agent Collaboration" | 2025 | | **The Big List.** Comprehensive but too broad; we filter to high-reliability patterns |
| Wang et al., "Survey on Large Language Model based Autonomous Agents" | 2024 | | **The Seminal Overview.** Treats multi-agent as one subsection; we elevate it to the main event |
| "Agentic AI Frameworks: Architectures, Protocols, and Design Challenges" | 2025 | | **The Architecture Review.** Ignores HITL as agent peer; we claim that space |

# Seed Repos
## Tier 1: Primary Corpus Sources (1,000+ stars)

### Paper Lists (mine for corpus)

| Repo | Stars | Papers | Coverage | Use For |
|------|-------|--------|----------|---------|
| [AGI-Edgerunners/LLM-Agents-Papers](https://github.com/AGI-Edgerunners/LLM-Agents-Papers) | 2,222 | ~1,917 | Modern LLM agents | Largest raw paper count — bulk modern corpus |
| [WooooDyy/LLM-Agent-Paper-List](https://github.com/WooooDyy/LLM-Agent-Paper-List) | 8,058 | ~346 | Modern LLM agents | Most authoritative — companion to the big survey (Xi et al.) |
| [kyegomez/awesome-multi-agent-papers](https://github.com/kyegomez/awesome-multi-agent-papers) | 1,218 | ~244 | Modern multi-agent | Focused on multi-agent coordination specifically |
| [luo-junyu/Awesome-Agent-Papers](https://github.com/luo-junyu/Awesome-Agent-Papers) | 2,431 | ~365 | Modern LLM agents | Continuously updated with 2025-2026 papers |
| [tmgthb/Autonomous-Agents](https://github.com/tmgthb/Autonomous-Agents) | 1,147 | ~448 | Modern LLM agents | Updated daily — best for staying current |
| [zjunlp/LLMAgentPapers](https://github.com/zjunlp/LLMAgentPapers) | 2,887 | ~254 | Modern LLM agents | Highly curated "must-read" list (Zhejiang University NLP) |
| [LantaoYu/MARL-Papers](https://github.com/LantaoYu/MARL-Papers) | 4,711 | ~167 | Classical + modern MARL | Best for game-theoretic foundations, cooperative MARL |
| [Shichun-Liu/Agent-Memory-Paper-List](https://github.com/Shichun-Liu/Agent-Memory-Paper-List) | 1,206 | ~207 | Agent memory | Critical for multi-agent shared memory / blackboard patterns |

**Combined unique papers (estimated)**: ~3,300+ raw → ~1,300 after dedup + filtering

### Pattern & Architecture Repos (mine for implementations)

| Repo | Stars | Entries | Coverage | Use For |
|------|-------|---------|----------|---------|
| [FareedKhan-dev/all-agentic-architectures](https://github.com/FareedKhan-dev/all-agentic-architectures) | 2,461 | 17+ impls | Both (includes blackboard, voting) | Working pattern implementations to compare against |
| [nibzard/awesome-agentic-patterns](https://github.com/nibzard/awesome-agentic-patterns) | 3,257 | Patterns | Modern agent patterns | Closest to Sutra's Rosetta Stone — the overlap to differentiate from |
| [e2b-dev/awesome-ai-agents](https://github.com/e2b-dev/awesome-ai-agents) | 25,768 | ~1,149 | Modern (tools/products) | Agent ecosystem directory — cite, don't replicate |

### Protocol & Standards Repos

| Repo | Stars | Coverage | Use For |
|------|-------|----------|---------|
| [a2aproject/A2A](https://github.com/a2aproject/A2A) | 21,895 | Agent-to-agent protocol | The modern FIPA equivalent — the Idea 5 (Protocol Rosetta Stone) target |
| [ai-boost/awesome-a2a](https://github.com/ai-boost/awesome-a2a) | 514 | A2A ecosystem | A2A adoption landscape |

---

## Tier 2: Specialized Sources (100-999 stars)

| Repo | Stars | Papers | Focus | Use For |
|------|-------|--------|-------|---------|
| [weitianxin/Awesome-Agentic-Reasoning](https://github.com/weitianxin/Awesome-Agentic-Reasoning) | 933 | ~843 | Reasoning + planning | Agent reasoning papers (BDI-adjacent) |
| [xhyumiracle/Awesome-AgenticLLM-RL-Papers](https://github.com/xhyumiracle/Awesome-AgenticLLM-RL-Papers) | 1,556 | ~210 | LLM + RL intersection | RL-based agent training, connects to classical MARL |
| [DavidZWZ/Awesome-Deep-Research](https://github.com/DavidZWZ/Awesome-Deep-Research) | 635 | — | Deep research agents | Multi-step investigation agents (Sutra's own methodology) |
| [HKUSTDial/awesome-data-agents](https://github.com/HKUSTDial/awesome-data-agents) | 394 | ~148 | Data agents | Domain-specific multi-agent patterns |
| [TimeBreaker/MARL-papers](https://github.com/TimeBreaker/Multi-Agent-Reinforcement-Learning-papers) | 288 | ~228 | Classical + modern MARL | Well-categorized by methodology |
| [kaushikb11/awesome-llm-agents](https://github.com/kaushikb11/awesome-llm-agents) | 1,312 | ~45 | Frameworks only | Framework landscape comparison |
| [yxf203/Awesome-Efficient-Agents](https://github.com/yxf203/Awesome-Efficient-Agents) | 165 | — | Efficiency | Token efficiency papers (connects to Durfee's result sharing) |

---

## Tier 3: Niche / Domain-Specific

| Repo | Stars | Focus |
|------|-------|-------|
| [AgenticHealthAI/Awesome-AI-Agents-for-Healthcare](https://github.com/AgenticHealthAI/Awesome-AI-Agents-for-Healthcare) | 623 | Healthcare domain |
| [Wei-ZENG1020/Value-Alignment-Agentic-AI-Papers-Survey-Taxonomy](https://github.com/Wei-ZENG1020/Value-Alignment-Agentic-AI-Papers-Survey-Taxonomy) | 105 | Safety / alignment |
| [Coral-Protocol/awesome-agents-for-multi-agent-systems](https://github.com/Coral-Protocol/awesome-agents-for-multi-agent-systems) | 47 | Agent protocols |
| [richardblythman/awesome-multi-agent-systems](https://github.com/richardblythman/awesome-multi-agent-systems) | 22 | Both classical + modern (closest to Sutra, but tiny) |
