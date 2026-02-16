# Pillar 7: BDI & Cognitive Agent Architectures

> *Back to [main README](../README.md)*

## Overview

All coordination infrastructure assumes that individual agents have a principled internal architecture for reasoning about beliefs, goals, and commitments. Without such an architecture, agents are black boxes that happen to produce text -- they can participate in coordination protocols but cannot reason *about* their own participation. The BDI (Belief-Desire-Intention) framework provides precisely this missing cognitive substrate, and its absence from modern LLM agents explains why so many coordination mechanisms fail at the individual-agent level.

## Classical Foundations

The BDI architecture (Rao & Georgeff 1995) formalized a cognitive loop: an agent *perceives* its environment, *updates beliefs*, *generates desires* from goals, *filters intentions* through commitment strategies, *executes plans*, and loops. It drew from Bratman's philosophy of action (intentions as conduct-controlling pro-attitudes), folk psychology (belief-desire reasoning for interpretability), and cognitive science (production systems like SOAR and ACT-R).

The most consequential contribution is the **commitment strategy** governing intention persistence:
- **Blind commitment**: persist until success or exhaustion
- **Single-minded commitment**: persist until achieved or *impossible*
- **Open-minded commitment**: reconsider whenever beliefs change

Cohen and Levesque's axiom: drop an intention when (and only when) you believe it is achieved, impossible, or its motivating desire no longer holds. In multi-agent settings, this extends to the **obligation to inform**.

## Modern State

Modern LLM agents implement BDI components without the architecture: beliefs ≈ RAG/context (but not persistent or revisable), desires ≈ system prompt goals (but static), intentions ≈ chain-of-thought + tool-use (but without commitment). **ReAct** is the closest modern analogue, but it lacks the formal apparatus: within an episode, agents are implicitly open-minded (reconsider every cycle); across episodes, they are amnesiac.

Explicit bridges are emerging: **ChatBDI** (AAMAS 2025) extends BDI agents on Jason/JaCaMo with LLM-powered natural language communication. **NatBDI** (AAMAS 2024) expresses beliefs, desires, and intentions in natural language with RL bootstrapping. **CoALA** (Sumers et al.) provides the most comprehensive mapping to cognitive architectures.

## The Gap

The BDI gap operates at three levels:
1. **Commitment management**: No explicit commitment strategies -- agents cannot be configured as single-minded or open-minded
2. **Belief infrastructure**: Beliefs remain implicit in the context window, not queryable/revisable stores with contradiction detection
3. **Cross-pillar dependency**: BDI mental states are the *foundation* on which FIPA semantics, norm reasoning, joint intentions, and trust calibration all depend

The empirical cost: on SWE-Bench Verified, agents resolve 72% of single-issue bugs, but on SWE-EVO (multi-commit evolution), the same agents collapse to 19-21% -- a 3.4x drop measuring *intention persistence failure*. Cemri et al.'s 14 failure modes: **10 of 14 have direct BDI equivalents** -- problems the classical literature solved architecturally.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1987 | Bratman — *Intention, Plans, and Practical Reason* | Classical | |
| 1990 | Newell — *Unified Theories of Cognition (SOAR)* | Classical | |
| 1995 | Rao & Georgeff — *BDI Agents: From Theory to Practice* | Classical | [AAAI](https://www.aaai.org/Papers/ICMAS/1995/ICMAS95-042.pdf) |
| 1995 | Wooldridge & Jennings — *Intelligent Agents: Theory and Practice* | Classical | |
| 2007 | Bordini et al. — *Programming Multi-Agent Systems in Jason* | Classical | |
| 2023 | Yao et al. — *ReAct: Synergizing Reasoning and Acting* | Modern | |
| 2023 | Shinn et al. — *Reflexion: Language Agents with Verbal Reinforcement* | Modern | |
| 2024 | NatBDI — *Natural-Language BDI* | Modern | [ACM](https://dl.acm.org/doi/10.5555/3635637.3663103) |
| 2025 | ChatBDI — *BDI Agents with LLM Communication (AAMAS 2025)* | Modern | |
| 2025 | Wray et al. — *Cognitive Design Patterns for LLM Agents* | Modern | |

## The Wooldridge Insight

Wooldridge and Jennings distinguished *weak agency* (autonomy, social ability, reactivity, pro-activeness) from *strong agency* (mentalistic notions: beliefs, desires, intentions). Modern LLMs possess strong agency *capabilities* but are deployed in weak agency *architectures*. The BDI framework is precisely the missing infrastructure.
