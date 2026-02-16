# Pillar 4: Agent Communication Languages & Protocols

> *Back to [main README](../README.md)*

## Overview

What vocabulary do agents use? What distinguishes a request from a proposal, a commitment from an observation, a bid from a report? Without typed communicative acts, agents can exchange tokens but cannot coordinate with precision. This pillar traces agent communication from philosophy of language (speech acts) through KQML and FIPA to today's MCP and A2A protocols, and maps precisely which semantic capabilities survived and which were lost.

## Classical Foundations

Agent communication drew on three intellectual traditions: **philosophy of language** (Austin's speech acts, Searle's illocutionary force categories), **pragmatics** (Grice's cooperative principle -- quantity, quality, relevance, manner), and **organizational communication** (communication structure constrains performance).

KQML (1994) introduced the critical separation: *what* is communicated (content) is distinct from *how* (protocol). FIPA refined this with **22 typed performatives** and standardized interaction protocols. But classical ACLs failed for three reasons: the ontology alignment problem (shared vocabularies were prohibitively expensive), Singh's verifiability critique (mentalistic semantics were untestable), and ecosystem fragmentation (JADE was the only widely adopted platform).

**The semantics debate** between FIPA and Singh proves prophetic for LLM agents: LLMs have no beliefs in any meaningful sense. Singh's commitment-based semantics -- where agents incur public obligations rather than private beliefs -- map naturally to opaque LLM agents.

## Modern State

The **2026 Agent Protocol Stack**:

| Layer | Function | Protocol | Classical Ancestor |
|-------|----------|----------|--------------------|
| 4 | Discovery | ANP (W3C DID) | FIPA DF |
| 3 | Agent-agent | A2A (Google) | FIPA ACL |
| 2 | Agent-tool | MCP (Anthropic) | KQML `achieve` |
| 1 | Intra-app | SDKs (LG, ADK) | JADE |

MCP standardizes agent-tool access (6 primitives over JSON-RPC 2.0). A2A standardizes agent-to-agent communication (Agent Cards, Task lifecycle, typed message Parts). LLMs dissolve the ontology alignment problem entirely -- they function as universal ontology aligners.

## The Gap

The patterns survive but the formal semantics are lost. FIPA's Request protocol specified preconditions and postconditions; modern equivalents specify transport and message format but not conversational *meaning*. The negotiation performatives (`cfp`, `propose`, `accept-proposal`, `reject-proposal`) have no modern equivalents in either MCP or A2A. MCP has near-universal adoption; A2A is adopted natively only by Google ADK and Microsoft -- precisely the gap where classical MAS protocols have the most to contribute.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1969 | Searle — *Speech Acts* | Classical | [DOI](https://doi.org/10.1017/cbo9781139173438) |
| 1975 | Austin — *How To Do Things With Words* | Classical | [DOI](https://doi.org/10.1093/acprof:oso/9780198245537.001.0001) |
| 1975 | Grice — *Logic and Conversation* | Classical | |
| 1994 | Finin et al. — *KQML as an Agent Communication Language* | Classical | [DOI](https://doi.org/10.1145/191246.191322) |
| 1998 | Singh — *Agent Communication Languages: Rethinking the Principles* | Classical | |
| 2000 | Singh — *A Social Semantics for Agent Communication Languages* | Classical | |
| 2002 | FIPA ACL Specification | Classical | |
| 2025 | Anthropic — *Model Context Protocol (MCP) Specification* | Modern | [Spec](https://modelcontextprotocol.io/specification) |
| 2025 | Google — *Agent-to-Agent Protocol (A2A) Specification* | Modern | |

## Classical vs. Modern Trade-offs

| Classical | Modern | Gained | Lost |
|-----------|--------|--------|------|
| Formal BDI semantics | Natural language + JSON | Flexibility | Formal guarantees |
| 22 typed performatives | Typed Parts (Text/File/Data) | Simplicity | Semantic precision |
| Shared ontologies required | LLMs handle alignment | Lower overhead | Occasional ambiguity |
| Hand-crafted knowledge bases | LLM world knowledge | Generalization | Hallucination risk |
