# Pillar 2: Organizational Design & Team Structures

> *Back to [main README](../README.md)*

## Overview

With a shared medium in place and a mechanism for allocating tasks, the third foundational decision is *how to structure the agents themselves*. This is not a matter of labeling -- calling one agent a "researcher" and another a "coder" -- but of defining the authority relationships, communication topologies, and scaling patterns that determine whether a system of ten agents can grow to a hundred. The evidence that structure dominates capability is overwhelming: Google's Project Aristotle found that *who* is on a team matters less than *how* the team is structured.

## Classical Foundations

Horling and Lesser's seminal survey provided the definitive taxonomy: **eight organizational paradigms** for multi-agent systems -- hierarchy, holarchy, coalition, team, congregation, society, federation, and market -- each implying different authority structures, communication patterns, and scaling properties. Three structural constraints shape the design space: authority and accountability (who can direct whom?), scalability (flat topologies scale as O(n²) in communication cost), and adaptability (static structures cannot respond to changing task requirements).

## Modern State

Modern LLM frameworks implement at most **3 of 8** paradigms, and none preserves the formal properties:

| Paradigm | Authority | Modern Equivalent | Gap |
|----------|-----------|-------------------|-----|
| Hierarchy | Top-down | ADK (2-level) | No depth >2 |
| Holarchy | Recursive | None | No self-similar recursion |
| Coalition | Dynamic | None | No runtime formation |
| Team | Joint goals | CrewAI roles | No shared mental model |
| Congregation | Self-organized | None | No capability ads |
| Society | Open, norms | AutoGen chat | No norm enforcement |
| Federation | Brokered | None | No broker agents |
| Market | Competitive | DALA (partial) | No formal auctions |

## The Gap

The gap is not missing labels but missing *formal authority gradients*. Without explicit authority structures, conflicts between agents are resolved by whoever speaks last -- not by organizational design but by scheduling accident. No framework supports dynamic coalition formation, holonic recursion, or organizational adaptation. Agents are assigned to teams at configuration time and remain fixed throughout execution.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1995 | Gasser — *Understanding Cooperation: An Agent's Perspective* | Classical | |
| 1998 | Fox et al. — *An Organizational Ontology for Enterprise Modeling* | Classical | |
| 1998 | PROSA — *Reference Architecture for Holonic Manufacturing Systems* | Classical | |
| 2002 | Hackman — *Leading Teams: Setting the Stage for Great Performances* | Classical | |
| 2004 | Horling & Lesser — *A Survey of Multi-Agent Organizational Paradigms* | Classical | [DOI](https://doi.org/10.1017/s0269888905000317) |
| 2015 | McChrystal — *Team of Teams* | Classical | |
| 2023 | Hong et al. — *MetaGPT: Multi-Agent Collaborative Framework* | Modern | [arXiv](https://arxiv.org/abs/2308.00352) |
| 2025 | Kim et al. — *Scaling LLM Test-Time Compute with Multi-Agent Systems* | Modern | |

## Key Finding

Kim et al. (2025) showed that architecture selection explains more variance in multi-agent performance than model size -- topology matters more than intelligence. Yet no framework provides the graph-theoretic tools to *design* the right topology rather than guess it.
