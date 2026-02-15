# Classical Multi-Agent Systems Theory Meets Modern LLM Agents

*Research Survey compiled February 2026*

---

## Overview

The field is characterized by a **bifurcation**: classical MAS researchers extend toward LLMs (ChatBDI, NatBDI, SPADE), while LLM framework developers build from scratch ignoring 30 years of agent theory. A small but growing body of work bridges the gap.

---

## 1. BDI + LLM Integration Projects

### ChatBDI (AAMAS 2025) -- The Most Direct Bridge
- Extends BDI agents on Jason/JaCaMo with LLM-powered natural language communication using KQML as intermediary
- BDI provides "intentional brain" to LLMs; LLMs add "creative language actuator" to BDI agents
- Can retrofit communication onto existing legacy BDI agents without source modification
- Paper: [ChatBDI: Think BDI, Talk LLM](https://www.ifaamas.org/Proceedings/aamas2025/pdfs/p2541.pdf)
- Code: [github.com/VEsNA-ToolKit/chatbdi](https://github.com/VEsNA-ToolKit/chatbdi)

### NatBDI (AAMAS 2024)
- BDI agents where beliefs, desires, intentions expressed in natural language (not formal logic)
- Built on Jason/AgentSpeak, uses RL to bootstrap reasoning
- Paper: [BDI Agents in Natural Language Environments](https://www.ifaamas.org/Proceedings/aamas2024/pdfs/p880.pdf)

### Hybrid BDI-LLM for Safety-Critical Applications (2025)
- BDI provides formal verification + safety guarantees; LLM handles unstructured interface
- BDI constrains LLM output space to verifiable behaviors
- Paper: [Engineering Applications of AI, Vol. 141](https://www.sciencedirect.com/science/article/pii/S0952197624019304)

### BDI Structured Prompting (HAI 2023)
- Maps BDI knowledge representation directly into prompt design
- Uses BDI conceptual framework to structure LLM reasoning
- Paper: [ACM HAI 2023](https://dl.acm.org/doi/10.1145/3623809.3623930)

---

## 2. Classical MAS Frameworks: Status

### JADE (Java Agent Development Framework)
- Gold standard for FIPA-compliant MAS (late 1990s-2010s)
- Original team stopped maintenance 2021
- Community fork at [github.com/dpsframework/jade-platform](https://github.com/dpsframework/jade-platform) (v4.6.1, Java 17)
- Effectively legacy -- no LLM integration, no modern protocol support

### SPADE 4.0 (Python) -- Closest Modern Equivalent
- FIPA-compliant, Python-native, XMPP/Jabber transport, async (asyncio)
- Web interface for monitoring, supports FIPA interaction protocols
- **No native LLM integration** -- remains classical MAS framework
- [SPADE GitHub](https://github.com/javipalanca/spade)

### PADE (Python)
- Lighter FIPA-compliant Python framework
- [pade.readthedocs.io](https://pade.readthedocs.io/en/latest/)

### GAMA Platform
- Supports FIPA ACL (inform, request, cfp) and interaction protocols (CNP, Request) natively
- Targets simulation, not production deployment

---

## 3. Argumentation-Based Negotiation with LLMs

### The Sobering Result: "Can LLM Agents Really Debate?" (November 2025)
**Most important paper on this topic.**
- Majority pressure suppresses independent correction (rates as low as 3.6% for weaker models)
- Performance gains come from **voting, not argumentation**
- Eloquence beats correctness (agents respond to rhetorical quality, not logical validity)
- **Debate induces a martingale over belief trajectories** -- no expected improvement over simple voting
- Only when agents follow "rational, validity-aligned reasoning" do correction rates exceed 90%
- Paper: [arxiv.org/abs/2511.07784](https://arxiv.org/abs/2511.07784)

**Implication for Kapi**: Design argumentation protocols with structured critique (propose-counter with typed reasons), not open-ended debate. Use performatives to force structured evaluation.

### Other Negotiation Work
- **Game-theoretic LLM** (Nov 2024): Guides reasoning toward Nash Equilibria. Structured prompting, not genuine belief revision. [arxiv.org/abs/2411.05990](https://arxiv.org/abs/2411.05990)
- **Personality-Driven Argumentation** (EMNLP 2025): Integrates argumentation profiles and buying styles. [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.1390.pdf)
- **LLM-Deliberation** (NeurIPS 2024): Multi-agent negotiation under cooperative/competitive/adversarial conditions. [GitHub](https://github.com/S-Abdelnabi/LLM-Deliberation)

---

## 4. Contract Net Protocol with LLMs

### DALA (November 2025) -- Closest Modern CNP Analog
- VCG auction mechanism where agents bid for communication opportunity
- 84.32% on MMLU, 91.21% on HumanEval using only 6.25M tokens
- Agents learn "strategic silence" -- communicate only when high value density
- Paper: [arxiv.org/abs/2511.13193](https://arxiv.org/html/2511.13193v1)

### Mechanism Design for LLMs (Google Research 2025)
- Token auction mechanisms across competing models
- Payment functions incentivize truthful capability reporting
- [Google Research Blog](https://research.google/blog/mechanism-design-for-large-language-models/)

### Magentic Marketplace (Microsoft Research 2025)
- Open-source environment for agentic markets with bidding/allocation
- [Microsoft Research Paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/10/multi-agent-marketplace.pdf)

---

## 5. Holonic Agent Architectures with LLMs

**Current state: Hierarchical yes, holonic no.** No framework implements true recursive self-similarity.

### HALO (May 2025) -- Closest to Holonic
- Three-tier: planning agent -> role-design agents -> inference agents
- Dynamically creates specialized agents per subtask (14.4% improvement)
- Not truly holonic (agents at each level are structurally different)
- Paper: [arxiv.org/abs/2505.13516](https://arxiv.org/abs/2505.13516)

### LLM-Adaptive Drone Swarms (September 2025)
- LLMs dynamically select between centralized/hierarchical/holonic architectures
- LLM selects architecture rather than participating in it
- Paper: [arxiv.org/abs/2509.05355](https://arxiv.org/html/2509.05355v1)

---

## 6. The 10 Gaps

Capabilities from classical MAS absent from **every** current LLM framework:

1. **Formal Commitments** -- no commitment stores, no violation detection
2. **Performative Semantics** -- no typed message acts, everything unstructured
3. **Shared Ontologies** -- implicit via NL, no disambiguation
4. **Argumentation-Based Belief Revision** -- debate is social conformity, not logic
5. **Runtime Agent Discovery** -- static definitions at design time
6. **Holonic Self-Organization** -- fixed hierarchies, no dynamic group formation
7. **Interaction Protocol Verification** -- no termination/safety proofs
8. **Social Norms / Institutional Rules** -- system prompts with no enforcement
9. **Protocol Composability** -- flat patterns, no nesting
10. **Resource-Bounded Reasoning** -- agents don't self-manage cost

---

## 7. Key Survey Papers

- [Contemporary Agent Technology: LLM-Driven vs Classic MAS](https://arxiv.org/abs/2509.02515) (Sep 2025) -- 33-page comparison
- [Reliable Agent Engineering Should Integrate Machine-Compatible Organizational Principles](https://arxiv.org/abs/2512.07665) (Dec 2025) -- strongest case for classical org theory in LLM agents
- [Survey of Agent Interoperability Protocols](https://arxiv.org/html/2505.02279v1) (May 2025) -- MCP, A2A, ACP, ANP comparison
- [Agentic AI Frameworks: Architectures, Protocols, and Design Challenges](https://arxiv.org/html/2508.10146) (Aug 2025)

---

## Foundational Texts

1. Smith (1980) -- "The Contract Net Protocol"
2. Finin et al. (1994) -- KQML specification
3. FIPA standards -- ACL, interaction protocols (fipa.org)
4. Wooldridge (2009) -- *An Introduction to MultiAgent Systems*
5. Rao & Georgeff (1995) -- BDI agent architecture
6. Grosz & Kraus (1996) -- SharedPlans theory
7. Rosenschein & Zlotkin (1994) -- *Rules of Encounter*
8. Cohen & Levesque -- Joint Intention Theory
9. Dung (1995) -- Abstract argumentation frameworks
