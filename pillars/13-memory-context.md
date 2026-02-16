# Pillar 13: Memory & Context Management

> *Back to [main README](../README.md)*

## Overview

All the preceding pillars share a silent assumption: that agents can *remember*. BDI maintains a belief store -- yet never specifies when beliefs should expire. Negotiation protocols assume agents recall prior offers. Without explicit memory architecture, every coordination mechanism is one context-window overflow away from amnesia. With only **107 papers** (88% published since 2023), Memory is the smallest of our 16 pillars yet represents one of the fastest-growing research frontiers.

## Classical Foundations

Classical MAS hid memory inside other abstractions -- BDI beliefs, blackboard knowledge sources, corporate knowledge bases -- which explains the asymmetry: 2,616 papers address memory-adjacent concerns, yet only 107 treat memory as a first-class architectural concern.

Memory draws on deeper traditions than any other pillar:
- **Cognitive psychology**: Tulving's distinction between *episodic* and *semantic* memory is now the standard taxonomy in LLM agent memory research, though rarely cited
- **Organizational psychology**: Wegner's *transactive memory systems* -- effective teams develop specialized memory roles ("who knows what"), not duplicate knowledge
- **Philosophy**: The AGM framework formalized principles for rational belief change: *contraction* (removing a belief while preserving consistency) and *revision* (adding a belief while maintaining consistency) -- principles no LLM agent implements

Early work includes corporate memory systems (2000, 2002) using agent architectures to manage organizational knowledge, and Euzenat's (2003) agent memory and adaptation framework.

## Modern State

**MemGPT** (Packer et al. 2023) architected the LLM as an operating system managing main context and external storage -- mapping almost exactly to Baddeley's working memory model (central executive + slave systems). **A-MEM** (2025) achieves 85-93% token reduction over MemGPT through Zettelkasten-inspired dynamic indexing. **Memory-R1** (2025) enhances agents with reinforcement-learned memory management -- agents learn *when* to store, retrieve, and forget.

**Collaborative Memory** (2025) is the first work to treat multi-agent memory permissions as a first-class design concern, introducing private vs. shared memory with explicit access control. An ICLR 2026 workshop (MemAgents) is dedicated entirely to agent memory.

## The Gap

No major framework provides coordinated multi-agent memory management. Each agent manages its own context window independently. Three open challenges have no classical precedent:
1. **Write policies during interaction** -- when should an agent commit an observation to long-term memory?
2. **Temporal credit assignment** -- which past memory caused today's success?
3. **Provenance-aware retrieval** -- can I trust this memory, and where did it come from?

The small corpus size is itself the finding: classical MAS externalized memory to the blackboard or environment. Treating memory as a first-class architectural concern *of the individual agent* is genuinely new.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1983 | Tulving — *Elements of Episodic Memory* | Classical | |
| 1985 | AGM — *On the Logic of Theory Change* | Classical | |
| 1987 | Wegner — *Transactive Memory: A Contemporary Analysis of the Group Mind* | Classical | |
| 1992 | Baddeley — *Working Memory* | Classical | |
| 2002 | Gandon & Dieng-Kuntz — *Multi-Agent Corporate Memory Management System* | Classical | |
| 2023 | Packer et al. — *MemGPT: Towards LLMs as Operating Systems* | Modern | [arXiv](https://arxiv.org/abs/2310.08560) |
| 2025 | Xu et al. — *A-MEM: Agentic Memory with Zettelkasten Indexing* | Modern | |
| 2025 | Memory-R1 — *Enhancing LLM Agents via Reinforcement Learning* | Modern | |
| 2025 | Collaborative Memory — *Private vs. Shared Memory with Access Control* | Modern | |
| 2025 | Survey on Memory Mechanisms of LLM-based Agents | Modern | |

## Research Trajectory

Memory is where the field is going, not where it has been. A taxonomy that omitted this pillar would capture where MAS has been but miss where it is headed. The field is entering a phase transition from ad-hoc context management to principled memory architectures.
