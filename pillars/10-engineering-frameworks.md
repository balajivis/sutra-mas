# Pillar 10: Multi-Agent Engineering: Methodologies, Frameworks & Platforms

> *Back to [main README](../README.md)*

## Overview

How do you design, build, test, and maintain a system that composes coordination mechanisms into a reliable whole? This pillar addresses the engineering question that precedes all others. Classical Agent-Oriented Software Engineering (AOSE) addressed these problems systematically; modern LLM frameworks are rediscovering them from first principles. The two eras have minimal cross-citation, which is precisely what makes the gap analysis productive.

## Classical Foundations

AOSE emerged in the late 1990s with structured methodologies: **Gaia** (Wooldridge et al. 2000) for organizational analysis and design, **Tropos** (Bresciani et al. 2004) for requirements-driven agent development, and **Prometheus** (Padgham & Winikoff 2004) for the full lifecycle. **JADE** provided the reference implementation: FIPA-compliant communication, directory services, and interaction protocol libraries.

Three engineering traditions are directly transferable:
- **Software engineering**: Brooks' Law applies with even greater force to agents -- each additional agent introduces coordination cost, not just communication
- **Fault-tolerant distributed systems**: Erlang/OTP's *supervision trees* and "let it crash" philosophy -- individual processes fail; a supervisor hierarchy detects failures and restarts with known-good state
- **Ad hoc teamwork**: Stone et al. (2010) formalized coordination with previously unknown teammates -- precisely the default for LLM agents

## Modern State

The LLM framework landscape converges toward shared state, but none implements the classical coordination stack:

| Framework | Coordination Model | Classical Analogue |
|-----------|-------------------|-------------------|
| LangGraph | Graph state machine | Blackboard (no shell) |
| CrewAI | Role-based teams | Org. paradigms |
| AutoGen | Group chat | Actor model (flat) |
| MetaGPT | SOP documents | Stigmergy |
| Google ADK | Seq./par./loop | 2-level hierarchy |
| OpenAI Swarm | Agent handoff | --- |

MCP (agent-to-tool) has near-universal adoption. A2A (agent-to-agent) is adopted natively only by Google ADK and Microsoft.

## The Gap: 10 Missing Capabilities

Surveying every major LLM framework against classical AOSE reveals **10 capabilities present in the classical era that are absent from every current LLM framework**:

1. **Formal commitments** — No commitment stores, no violation detection
2. **Performative semantics** — No typed message acts (inform, request, propose)
3. **Shared ontologies** — Concepts implicit via natural language (partially obviated by LLMs)
4. **Argumentation-based belief revision** — Debate produces conformity, not logical revision (partially obviated)
5. **Runtime agent discovery** — No Yellow Pages service for capability advertisement
6. **Holonic self-organization** — Fixed hierarchies only; no dynamic group formation
7. **Interaction protocol verification** — No termination proofs, no safety proofs
8. **Social norms and institutional rules** — System prompts state norms but don't enforce them
9. **Protocol composability** — No nesting or sequential composition of interaction patterns
10. **Resource-bounded reasoning** — No token budgets, response-time constraints, or quality/cost trade-offs

Plus two cross-cutting concerns: *fault recovery* (no supervision trees) and *testing* (no principled multi-agent interaction coverage model).

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1975 | Brooks — *The Mythical Man-Month* | Classical | |
| 1996 | Bradshaw — *Software Agents* | Classical | |
| 2000 | Wooldridge et al. — *The Gaia Methodology* | Classical | [DOI](https://doi.org/10.1023/a:1010071910869) |
| 2002 | Wooldridge — *An Introduction to MultiAgent Systems* | Classical | |
| 2003 | Armstrong — *Making Reliable Distributed Systems (Erlang/OTP)* | Classical | |
| 2004 | Bresciani et al. — *Tropos Methodology* | Classical | |
| 2007 | Bellifemine et al. — *Developing Multi-Agent Systems with JADE* | Classical | |
| 2010 | Stone et al. — *Ad Hoc Autonomous Agent Teams* | Classical | |
| 2024 | LangGraph — *Resilient Language Agents as Graphs* | Modern | [GitHub](https://github.com/langchain-ai/langgraph) |
| 2025 | "Reliable Agent Engineering Should Integrate Machine-Compatible Organizational Principles" | Modern | |

## The Framework Graveyard

JADE's original team stopped maintenance in 2021. **SPADE 4.0** is the closest modern equivalent: FIPA-compliant, Python-native, async -- but no native LLM integration. The bifurcation is stark: classical frameworks have formal protocol support but no LLM integration; modern LLM frameworks have powerful models but no protocol formalism.
