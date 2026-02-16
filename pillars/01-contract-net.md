# Pillar 1: Contract Net & Task Allocation

> *Back to [main README](../README.md)*

## Overview

How should tasks be distributed among agents? Classical MAS identified five allocation paradigms: role-based, centralized dispatch, market-based, self-organized, and emergent. Smith's Contract Net Protocol (1980) provided the foundational market-based mechanism: a **manager** announces a task, potential **contractors** evaluate the announcement and submit bids based on their capabilities and current load, and the manager **awards** the contract to the most suitable bidder. The protocol's power lies in what it does *not* require: no central scheduler, no global knowledge of agent capabilities, no pre-assigned task-to-agent mapping.

## Classical Foundations

The Contract Net spawned a rich mechanism design literature: TRACONET added decommitment penalties, combinatorial auctions handled task bundles, and incentive contracting provided formal efficiency guarantees. The protocol's enduring relevance rests on an information-theoretic property: it converts allocation from a centralized O(n)-knowledge problem to a distributed market where each agent needs to know only itself. Smith's *iterated* Contract Net -- where contractors further decompose tasks via sub-announcements -- creates recursive task decomposition mirroring holonic organizations.

## Modern State

Despite the dominance of centralized dispatch, three recent projects reconnect with market-based allocation. **DALA** (2025) implements a VCG auction mechanism where agents bid for communication opportunities using a token-budget currency, achieving 84.32% accuracy on MMLU with only 6.25M tokens. **Mechanism Design for LLMs** (Google Research 2025) proposes token auction mechanisms. **Magentic Marketplace** (Microsoft Research 2025) provides an open-source environment for agentic markets.

## The Gap

The entire allocation design space is collapsed to a single point: centralized dispatch. No production framework exposes allocation paradigm as a configurable architectural choice. A builder cannot say "use role-based allocation for routine tasks, market-based for novel tasks, and coalition formation when a task exceeds any single agent's capability." No production framework implements formal cost models for agent bidding, marginal-cost-based self-selection, or the decommitment protocols that handle the real-world case where an agent accepts a task and then discovers it cannot complete it.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1980 | Smith — *The Contract Net Protocol* | Classical | [DOI](https://doi.org/10.1109/TC.1980.1675516) |
| 1983 | Davis & Smith — *Negotiation as a Metaphor for Distributed Problem Solving* | Classical | |
| 1993 | Sandholm — *TRACONET: Automated Contracting* | Classical | |
| 1998 | Shehory & Kraus — *Methods for Task Allocation via Agent Coalition Formation* | Classical | [DOI](https://doi.org/10.1016/s0004-3702(98)00045-9) |
| 1998 | de Vries & Vohra — *Computationally Manageable Combinatorial Auctions* | Classical | [DOI](https://doi.org/10.1287/mnsc.44.8.1131) |
| 2023 | Wu et al. — *AutoGen: Next-Gen LLM Applications via Multi-Agent Conversation* | Modern | [arXiv](https://arxiv.org/abs/2308.08155) |
| 2025 | DALA — *Dynamic Agent-Level Allocation via VCG Auctions* | Modern | |
| 2025 | Google Research — *Mechanism Design for LLMs* | Modern | |
| 2025 | Microsoft Research — *Magentic Marketplace* | Modern | |

## Experiment Results

From our harness (Claude Opus 4.6, N=1):

| Pattern | Code Review | Cascading Failure V1 | Mean |
|---------|-------------|---------------------|------|
| SingleAgent (baseline) | 92 | 82 | 67.2 |
| Contract Net | 88 | 88 | 70.4 |

Contract Net's announce/bid/award cycle performed well on the cascading failure benchmark (88), suggesting market mechanisms help agents detect contradictions through competitive evaluation.
