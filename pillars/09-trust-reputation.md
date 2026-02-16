# Pillar 9: Trust, Reputation & Social Mechanisms

> *Back to [main README](../README.md)*

## Overview

As agents increasingly interact across organizational boundaries -- negotiating refunds, scheduling meetings, exchanging emails on behalf of principals with competing interests -- the question of *why an agent should trust another agent* becomes load-bearing infrastructure. This pillar focuses on the bottom-up mechanisms by which agents build, assess, and revise credibility, while governance (Pillar 5) addresses the institutional context.

## Classical Foundations

**Castelfranchi and Falcone's Trust Theory** argues that trust is not a single scalar but a **cognitive attitude** with five components:
1. **Competence belief** — the trustee can perform the action
2. **Willingness belief** — the trustee will choose to perform it
3. **Persistence belief** — the trustee will not abandon the task
4. **Predictability assessment** — the trustee's behavior is stable enough to model
5. **Delegation act** — the truster explicitly transfers responsibility

Modern LLM agents fail on different dimensions: they satisfy competence (large models are capable) but fail on persistence (no cross-session commitment tracking), willingness (no self-interest in completing your task), and predictability (temperature-dependent stochastic output).

**Computational trust mechanisms**: Marsh (1994) introduced trust as a continuous value on [-1, +1] distinguishing general trust from situational trust. Josang's Beta Reputation System modeled trust as a beta distribution updated from binary outcomes. Kamvar et al.'s EigenTrust provided scalable distributed reputation for P2P networks.

## Modern State

The most mature production implementations of graduated agent trust are agentic coding assistants. **Claude Code** implements a six-mode permission architecture with per-tool glob patterns and OS-level sandboxing. **OpenAI Codex** uses three sandbox modes crossed with four approval policies. **Microsoft Entra Agent ID** treats agents as first-class identity subjects. None cites classical trust literature, yet both independently arrive at graduated, multi-dimensional trust.

LLM agents introduce trust pathologies without classical precedent: **sycophancy** (integrity failure -- agreeing regardless of correctness), **hallucination** (competence failure appearing competent), and **miscalibration** (high confidence providing no signal).

## The Gap

No LLM agent framework implements trust as a first-class architectural component. Every agent interaction starts from zero trust -- there is no reputation history, no trust transfer between contexts, and no mechanism for building credibility through consistent behavior. The gap is not just technical but *prerequisite*: implementing trust requires BDI mental states (Pillar 7) for representing trust beliefs, communication protocols (Pillar 4) for exchanging trust assessments, and governance infrastructure (Pillar 5) for the institutional context.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1989 | Gambetta — *Trust: Making and Breaking Cooperative Relations* | Classical | |
| 1994 | Marsh — *Formalising Trust as a Computational Concept* | Classical | |
| 1995 | Mayer et al. — *An Integrative Model of Organizational Trust* | Classical | |
| 2003 | Kamvar et al. — *The EigenTrust Algorithm for P2P Networks* | Classical | [DOI](https://doi.org/10.1145/775152.775242) |
| 2005 | Sabater & Sierra — *Review on Computational Trust and Reputation* | Classical | [DOI](https://doi.org/10.1007/s10462-004-0041-5) |
| 2005 | Resnick et al. — *Reputation Systems* | Classical | |
| 2010 | Castelfranchi & Falcone — *Trust Theory: A Socio-Cognitive and Computational Model* | Classical | |
| 2024 | TrustLLM — *Trustworthiness in Large Language Models* | Modern | [arXiv](https://arxiv.org/abs/2401.05561) |
| 2025 | Microsoft — *Entra Agent ID* | Modern | |
| 2025 | Raza et al. — *TRiSM Framework for Agentic MAS* | Modern | |

## Graduated Trust in Practice

Claude Code's permission modes mapped to Parasuraman's automation levels:

| Mode | Agent Capability | Automation Level |
|------|-----------------|-----------------|
| `plan` | Read-only analysis | 1 |
| `dontAsk` | Pre-approved tools only | 3 |
| `default` | Per-tool human approval | 4 |
| `acceptEdits` | Auto-accept file edits | 6 |
| `delegate` | Coordinate sub-agents | 7 |
| `bypassPermissions` | Full autonomy (sandboxed) | 9 |
