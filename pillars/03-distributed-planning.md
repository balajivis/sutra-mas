# Pillar 3: Distributed Planning, Problem Solving & Teamwork

> *Back to [main README](../README.md)*

## Overview

Once agents are organized and assigned work, the critical question becomes: *how should they actually collaborate on shared problems?* Specifically, what should agents do with each other's interim and final outputs -- and when should they share them? This pillar traces the collaboration question from Lesser and Corkill's Functionally Accurate Cooperation (1983) through Grosz's SharedPlans to Durfee's four dimensions of result sharing, and identifies why modern LLM pipelines implement only the simpler half.

## Classical Foundations

Durfee's framework identifies the central distinction that modern LLM agent systems have almost entirely overlooked: **task sharing** vs. **result sharing**. Task sharing asks "who should do what?" Result sharing asks "how can what you've found help me do better?" Every major LLM framework implements task sharing; none explicitly implements result sharing.

Durfee identifies four ways result sharing improves group problem-solving:
1. **Confidence** — convergence from different methods signals reliability
2. **Completeness** — the union of shared results covers the solution space
3. **Precision** — agents refine work by incorporating peer constraints
4. **Timeliness** — early partial results let dependent work begin immediately

The **FA/C philosophy** (Functionally Accurate, Cooperative) says: let agents share their best current answers early, let other agents refine them, and let the system converge through iteration. This is *perfectly suited* to LLM agents, which are probabilistic by nature.

**Joint Persistent Goals** (Cohen & Levesque 1990) provide the most rigorous formal account of teamwork: a mutual commitment with an *obligation to inform* when the goal is achieved, becomes unachievable, or is no longer motivated.

## Modern State

Modern frameworks enforce the opposite of FA/C: nodes produce complete state updates before the next node executes. No streaming architecture implements the refinement cycle that makes FA/C powerful -- share, refine, re-share. Agentic coding tools (Claude Code, Cursor, Devin) come closest as single-agent FA/C.

## The Gap

No current LLM agent framework implements joint persistent goals, shared plans, or the obligation to inform. Our experiment reveals a deeper problem: **LLM agents cannot reliably detect their own epistemic failures**. On our epistemic honesty benchmark, JPG scored **52/100** -- the *lowest* of all patterns -- despite consuming the most tokens (37,567). The obligation-to-inform never triggers because the LLM does not know it has failed.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1983 | Lesser & Corkill — *Functionally Accurate Cooperation* | Classical | |
| 1987 | Durfee & Lesser — *Coherent Cooperation Among Problem Solvers* | Classical | |
| 1990 | Cohen & Levesque — *Intention is Choice with Commitment* | Classical | |
| 1995 | Decker & Lesser — *GPGP: Generalized Partial Global Planning* | Classical | |
| 1996 | Grosz & Kraus — *Collaborative Plans for Complex Group Action* | Classical | [DOI](https://doi.org/10.1016/0004-3702(95)00103-4) |
| 1997 | Tambe — *STEAM: Towards a Flexible Teamwork Framework* | Classical | |
| 1999 | Durfee — *Distributed Problem Solving and Planning* | Classical | |
| 2023 | Qian et al. — *ChatDev: Communicative Agents for Software Development* | Modern | [arXiv](https://arxiv.org/abs/2307.07924) |

## Experiment Results

From our harness -- the **Epistemic Failure Gap**:

| Pattern | CF V2 (Epistemic) | Tokens | Quality/1K Tokens |
|---------|-------------------|--------|-------------------|
| JPG | **52** | 37,567 | 1.38 |
| Blackboard V2 | **82** | 13,361 | 6.14 |

JPG's commitment protocol becomes actively harmful when agents cannot detect their own epistemic failures: they keep "committing" to fabricated work. The blackboard propagates *epistemic limits*, not just knowledge.
