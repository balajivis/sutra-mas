# Sutra — 16-Pillar Cluster Guide

The corpus of 17,969 papers is partitioned into 16 guided clusters, each representing a distinct **coordination mechanism or concern** in multi-agent systems research. The anchors are aligned with AAMAS conference tracks and the classical MAS taxonomy.

| #   | Cluster                                                                                                                                 | Papers |
| --- | --------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 0   | [Shared Medium Coordination](#0-shared-medium-coordination)                                                                             | 1,096  |
| 1   | [Contract Net and Task Allocation](#1-contract-net-and-task-allocation)                                                                 | 945    |
| 2   | [Organizational Design and Team Structures](#2-organizational-design-and-team-structures)                                               | 2,167  |
| 3   | [Distributed Planning, Problem Solving, and Teamwork](#3-distributed-planning-problem-solving-and-teamwork)                             | 1,798  |
| 4   | [Agent Communication Languages and Protocols](#4-agent-communication-languages-and-protocols)                                           | 281    |
| 5   | [Governance, Norms, and AI Safety](#5-governance-norms-and-ai-safety)                                                                   | 370    |
| 6   | [Negotiation, Argumentation, and Economic Paradigms](#6-negotiation-argumentation-and-economic-paradigms)                               | 1,555  |
| 7   | [BDI and Cognitive Agent Architectures](#7-bdi-and-cognitive-agent-architectures)                                                       | 1,970  |
| 8   | [Human-Agent Interaction and HITL](#8-human-agent-interaction-and-hitl)                                                                 | 337    |
| 9   | [Trust, Reputation, and Social Mechanisms](#9-trust-reputation-and-social-mechanisms)                                                    | 288    |
| 10  | [Multi-Agent Engineering: Methodologies, Frameworks, and Platforms](#10-multi-agent-engineering-methodologies-frameworks-and-platforms) | 2,411  |
| 11  | [Multi-Agent Robotics and Embodied Teams](#11-multi-agent-robotics-and-embodied-teams)                                                  | 929    |
| 12  | [Evaluation Benchmarks and Failure Analysis](#12-evaluation-benchmarks-and-failure-analysis)                                            | 955    |
| 13  | [Memory and Context Management](#13-memory-and-context-management)                                                                      | 107    |
| 14  | [Learning and Adaptation](#14-learning-and-adaptation)                                                                                  | 2,386  |
| 15  | [Modeling and Simulating Artificial Societies](#15-modeling-and-simulating-artificial-societies)                                        | 374    |

**Total: 17,969 papers**

---

## 0. Shared Medium Coordination
**1,096 papers**

Agents coordinate by reading and writing a shared medium — whether a structured blackboard with a control shell (Hearsay-II, Nii 1986) or an unstructured environment where traces emerge (stigmergy, Grasse 1959, pheromone trails). Unlike *Contract Net* where agents exchange explicit messages, or *Agent Communication* which defines message semantics, shared medium coordination uses the workspace itself as the communication channel. The modern lineage spans LangGraph's shared state, Redis-backed scratchpads, MetaGPT's standard operating procedures, tuple spaces, and artifact-driven workflows where agents coordinate through shared documents.

## 1. Contract Net and Task Allocation
**945 papers**

Agents coordinate through a market-like announce-bid-award protocol: a manager broadcasts a task, agents bid based on capability, and the best bidder wins the contract. This is distinct from *Organizational Design* (which assigns roles statically) and *Negotiation/Game Theory* (which optimizes utility across strategic agents) — Contract Net is specifically about dynamic, capability-based task routing. The pattern appears today as LLM agent dispatch, where a router selects which specialist agent handles a user query.

## 2. Organizational Design and Team Structures
**2,167 papers**

Addresses the static and semi-static structure of agent societies: hierarchies, holarchies, coalitions, roles, and institutional norms that define who can do what. Unlike *Contract Net* (dynamic per-task allocation) or *Distributed Planning/Teamwork* (shared goals and commitments), this cluster is about the organizational blueprint itself — the topology before any task arrives. Modern equivalents include CrewAI's role definitions, supervisor-worker topologies, and the question of how many agents to deploy and how to structure authority.

## 3. Distributed Planning, Problem Solving, and Teamwork
**1,798 papers**

Agents decompose complex problems into sub-problems, solve them in parallel, merge partial solutions, and maintain team commitments. Unifies the planning and dependency management layer (PGP, GPGP, distributed constraint satisfaction) with the philosophical foundation of joint intentions (Cohen & Levesque 1990, Grosz & Kraus SharedPlans 1996, Tambe's STEAM). Unlike *Organizational Design* (which defines structure) or *Contract Net* (which routes individual tasks), this cluster addresses how agents collaboratively plan, commit to shared goals, and honor obligations to inform teammates when conditions change.

## 4. Agent Communication Languages and Protocols
**281 papers**

Defines the syntax, semantics, and pragmatics of how agents talk to each other: KQML, FIPA ACL, speech acts, performatives, interaction protocols. Unlike *Negotiation and Argumentation* (which structures strategic exchange and debate) this cluster is about the messaging layer itself — the envelope, not the content. The modern descendants are MCP (Model Context Protocol), A2A (agent-to-agent protocol), and the question of how to standardize inter-agent messaging.

## 5. Governance, Norms, and AI Safety
**370 papers**

How societies of agents establish, enforce, and evolve behavioral constraints: social laws, normative frameworks, sanctions, institutional design, constitutional AI, and the mechanisms that keep open multi-agent systems aligned with intended behavior. Unlike *Trust and Reputation* (which models agent-level credibility signals) or *Organizational Design* (which defines static team topology), governance addresses the regulatory layer — what agents *must not* do, what happens when they violate constraints, and how norms adapt as the system evolves. Classical lineage: Shoham & Tennenholtz's social laws (1995), Dignum's normative MAS, Castelfranchi's social commitment theory. Modern relevance: guardrails, content filtering, EU AI Act compliance, constitutional AI (Bai et al. 2022), RLHF alignment constraints, and the emerging question of how to govern autonomous LLM agents that operate in open environments. Promoted from the governance half of the former Trust/Reputation/Norms cluster — the 7.3:1 terminological burial ratio (4,834 governance-adjacent papers scattered across other clusters vs. 658 in the home cluster) demonstrated that governance deserved first-class pillar status.

## 6. Negotiation, Argumentation, and Economic Paradigms
**1,555 papers**

Agents with competing or partially aligned interests reach agreements through strategic interaction — whether by trading utility (Nash equilibria, mechanism design, VCG auctions, bargaining protocols), by structured argumentation (Dung's abstract frameworks, persuasion dialogues, argumentation-based negotiation), or by coalition formation (Shapley values, core stability). Unlike *Contract Net* (a specific allocation protocol) or *Agent Communication* (message-layer semantics), this cluster covers the full landscape of how self-interested agents resolve conflicts and allocate resources. Absorbs the former Argumentation and Structured Debate cluster: 56% of argumentation papers already use negotiation terminology, and argumentation-based negotiation (Rahwan, Amgoud, Jennings) is one of classical MAS's most cited subfields — the epistemic structure of disagreement and the economic structure of exchange are two faces of the same coordination problem. Modern relevance includes LLM debate patterns, generator-critic loops, resource allocation among competing agents, incentive design for multi-agent cooperation, and multi-agent verification through structured disagreement.

## 7. BDI and Cognitive Agent Architectures
**1,970 papers**

The internal architecture of a single agent: beliefs, desires, intentions, plan libraries, means-end reasoning, and the deliberation cycle. Where other clusters address inter-agent coordination, BDI asks how one agent decides what to do — practical reasoning, intention reconsideration, reactive vs. deliberative control. Unlike *Memory* (which focuses on retention and retrieval) or *Learning* (which focuses on adaptation over time), BDI is about the reasoning loop itself. Spans from Rao & Georgeff (1995) and AgentSpeak/Jason through hybrid architectures to today's questions about giving LLM agents structured internal reasoning.

## 8. Human-Agent Interaction and HITL
**337 papers**

Addresses the boundary between human and artificial agents: adjustable autonomy, mixed-initiative interaction, trust calibration, when to escalate, and how to keep humans meaningfully in the loop. Unlike *Trust and Reputation* (which models computational trust between agents), this cluster is specifically about human-machine teaming — the human as a first-class agent in the system. Maps directly to modern HITL patterns: approval queues, escalation triggers, and the graduated autonomy question in production AI deployments.

## 9. Trust, Reputation, and Social Mechanisms
**288 papers**

Models how agents assess each other's reliability through direct experience, witness reports, and institutional certification — and how these assessments drive delegation, coalition selection, and interaction partner choice. Unlike *Governance* (which enforces behavioral constraints top-down) or *Human-Agent Interaction* (focused on human-machine trust calibration), this cluster addresses the bottom-up credibility layer: how agents build, propagate, and reason about trustworthiness in open systems where agents may deceive, free-ride, or defect. Classical lineage: Marsh's formalization of trust (1994), Sabater & Sierra's ReGreT, witness-based reputation (Yu & Singh), certified trust (Ramchurn et al.). Modern relevance includes LLM agent reliability scoring, model selection based on past performance, delegation confidence thresholds, and the open question of how to establish trust between agents with no shared history. Narrowed from the former Trust/Reputation/Norms cluster after governance, norms, and safety concerns were promoted to their own pillar (C5).

## 10. Multi-Agent Engineering: Methodologies, Frameworks, and Platforms
**2,411 papers**

The software engineering discipline of building agent systems, spanning both classical methodologies (Prometheus, GAIA, Tropos, MaSE) and modern frameworks (LangGraph, CrewAI, AutoGen, MetaGPT, ChatDev). Where *BDI* defines the conceptual architecture and *Learning* addresses how agents improve, this cluster is about the concrete tooling — how you design, implement, test, and deploy multi-agent systems. Unifies AOSE with the post-2023 wave of LLM agent frameworks, making the gap between classical engineering rigor and modern rapid prototyping most visible.

## 11. Multi-Agent Robotics and Embodied Teams
**929 papers**

Coordination in physical space: multi-robot formation control, MRTA (multi-robot task allocation), distributed sensing, and consensus in networked agents. Unlike the software-focused clusters, embodied teams face physics constraints — communication range, sensor noise, actuator delay, spatial reasoning. Spans from RoboCup and multi-UAV coordination to consensus algorithms (Olfati-Saber, Ren & Beard) and modern multi-robot systems. Note: swarm intelligence algorithms (ACO, PSO) now sit primarily in *Learning and Adaptation*.

## 12. Evaluation Benchmarks and Failure Analysis
**955 papers**

How we measure whether multi-agent systems actually work: benchmarks (GAIA, SWE-bench), failure taxonomies (Cemri et al.'s 14 failure modes), error amplification studies (Kim et al.'s 17.2x finding), coordination overhead analysis, and token efficiency metrics. Unlike *Multi-Agent Engineering* (which addresses how to build agents), this cluster asks how to tell if they're working — and why they fail. Critical for the Sutra thesis that 40-80% failure rates stem from naive construction, not fundamental limits.

## 13. Memory and Context Management
**107 papers**

How agents retain, retrieve, and share information across interactions and sessions. Unlike *BDI* (which models the reasoning cycle) or *Shared Medium Coordination* (where the shared workspace is the coordination mechanism), this cluster focuses on memory as a first-class concern: episodic memory, working memory, long-term retention, context window management, and memory-augmented agents. The modern lineage includes MemGPT, RAG pipelines, entity memory, conversation memory, and the challenge of maintaining coherent context across multi-turn multi-agent interactions. Smallest cluster — reflects that memory is often treated as a sub-concern of other areas rather than studied independently.

## 14. Learning and Adaptation
**2,386 papers**

How agents improve their behavior over time through experience, interaction, and feedback. Covers multi-agent reinforcement learning (MARL), Markov games, Dec-POMDPs, emergent communication, self-play, opponent modeling, and co-evolution. Unlike *BDI* (which models deliberation at a point in time) or *Evaluation* (which measures performance), this cluster addresses the adaptation loop — how agents learn coordination strategies, develop communication protocols, and improve through interaction. Includes swarm intelligence algorithms (ACO, PSO) as bio-inspired learning. The largest cluster, reflecting MARL's dominance in recent MAS research.

## 15. Modeling and Simulating Artificial Societies
**374 papers**

Uses agent-based models to study emergent social phenomena: opinion dynamics, cooperation evolution, segregation, contagion, and economic markets. Unlike *Organizational Design* (which prescribes structure) or *Governance* (which enforces behavioral constraints), MABS treats agent societies as objects of scientific study — observing what emerges from simple interaction rules. The lineage runs from Epstein & Axtell's Sugarscape and Schelling's segregation model through ODD protocols to modern generative agents simulating human social behavior.

Notes:
2,616 papers address memory-adjacent concerns, yet only 107 treat memory as a first-class architectural concern —
   the rest subsume it under beliefs (BDI), knowledge sources (blackboard), or experience (learning). This
  terminological absorption explains why LLM agent builders, searching for 'memory architecture,' find almost
  nothing — and end up reinventing context management from scratch.
  - "Belief revision/update" → 471 papers went to BDI (classical term for agent memory)                             
  - "Shared memory" → 412 papers went to Shared Medium Coordination                                                 
  - "Experience replay", "world model" → 354 papers went to Learning 