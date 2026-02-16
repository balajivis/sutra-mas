# Pillar 0: Shared Medium Coordination

> *Back to [main README](../README.md)*

## Overview

Coordination requires a shared information substrate. Agents must externalize preferences, constraints, interim results, goals, and final outputs into a medium that other agents can observe and act upon -- without this, each agent operates in isolation and "multi-agent" is a misnomer for parallel single-agent runs. The blackboard architecture, originating in Hearsay-II (1980) and formalized by Nii (1986), defined three components: a **blackboard** (shared state), **knowledge sources** (specialist agents), and a **control shell** (scheduler that decides which agent to activate based on blackboard state).

## Classical Foundations

The blackboard's power lies in its communication complexity: agents interact through shared state rather than pairwise messages, reducing token flow from O(n²) to O(n) as team size grows. Star's *boundary objects* provide a sociological foundation: coordination succeeds not because agents agree on meaning but because the shared artifact constrains interaction. Stigmergy -- coordination through environmental modification rather than direct communication -- is the blackboard's decentralized sibling, sharing its O(n) communication complexity.

## Modern State

Every major LLM framework converges toward shared-state coordination: LangGraph's `StateGraph`, Redis pub/sub channels, shared documents. LbMAS (2025) provides the strongest quantitative evidence, reporting 13-57% quality improvement with 3x fewer tokens compared to message-passing baselines. MetaGPT implements stigmergy through documents (PRDs, designs, code); ChatDev uses code as the coordination artifact.

## The Gap

Modern frameworks implement the blackboard (shared state) and knowledge sources (agents) but skip the **control shell** -- the most valuable component. Without a control shell, agents execute in static round-robin order regardless of blackboard content. Our experiments quantify this directly: Blackboard V1 (static scheduling) scores 62/100 on code review; Blackboard V2 (LLM control shell) scores **95/100 -- a +53% improvement at half the tokens**. No framework implements selective sharing (access-controlled regions), and no framework provides first-class artifact support.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1980 | Erman et al. — *The Hearsay-II Speech-Understanding System* | Classical | [DOI](https://doi.org/10.1145/356810.356816) |
| 1985 | Hayes-Roth — *A Blackboard Architecture for Control (BB1)* | Classical | [DOI](https://doi.org/10.1016/0004-3702(85)90063-3) |
| 1986 | Nii — *The Blackboard Model of Problem Solving* | Classical | [DOI](https://doi.org/10.5555/13437.13438) |
| 1989 | Star & Griesemer — *Boundary Objects and Heterogeneous Problem Solving* | Classical | [DOI](https://doi.org/10.1016/b978-1-55860-092-8.50006-x) |
| 1990 | Malone & Crowston — *What Is Coordination Theory?* | Classical | [DOI](https://doi.org/10.1145/99332.99367) |
| 2006 | Weyns et al. — *Environment as a First Class Abstraction in MAS* | Classical | [DOI](https://doi.org/10.1007/s10458-006-0012-0) |
| 2016 | Heylighen — *Stigmergy as a Universal Coordination Mechanism* | Transition | |
| 2023 | Hong et al. — *MetaGPT: Multi-Agent Collaborative Framework* | Modern | [arXiv](https://arxiv.org/abs/2308.00352) |
| 2025 | LbMAS — *Blackboard Pattern for LLM Agents* | Modern | [arXiv](https://arxiv.org/abs/2503.10939) |
| 2025 | CodeCRDT — *CRDTs for Multi-Agent Code Coordination* | Modern | |

## Experiment Results

From our harness (Claude Opus 4.6, N=1):

| Pattern | Code Review | Research Synth. | Mean |
|---------|-------------|-----------------|------|
| Blackboard V1 (static) | 62 | 50 | 61.2 |
| **Blackboard V2 (LLM shell)** | **95** | **88** | **83.8** |
| Stigmergy | 92 | 72 | 75.2 |

The V1→V2 jump is the paper's star result: same agents, same benchmark, same model -- the only difference is the control shell.
