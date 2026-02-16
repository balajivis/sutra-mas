# Pillar 12: Evaluation, Benchmarking & Failure Analysis

> *Back to [main README](../README.md)*

## Overview

A coordination mechanism is only as good as the evidence that it works. This pillar asks the evaluation question: *how do you know your multi-agent system is coordinating well, and not merely producing correct output by accident?* Every major LLM agent benchmark -- GAIA, SWE-Bench, WebArena, HumanEval -- evaluates *task output* alone, with no metric for retrieval relevance, information flow efficiency, role adherence, or failure recovery quality.

## Classical Foundations

Two competition platforms operationalized coordination evaluation:

**RoboCup** (est. 1997) evaluated multi-agent coordination under physical constraints. Teams of robots playing soccer had to communicate, assign roles dynamically, and recover from failures. Evaluation criteria were inherently relational: a team of individually excellent robots that could not coordinate lost to an inferior team with superior coordination.

**Trading Agent Competition (TAC)** (est. 2001) evaluated strategic multi-agent interaction in market settings. Success required modeling other agents' strategies, not just optimizing one's own.

**Stone et al.'s ad hoc teamwork** (2010) introduced a third paradigm: coordination with *previously unknown* teammates -- precisely the situation when LLM agents from different frameworks collaborate.

Both platforms shared a critical property absent from modern benchmarks: they evaluated **process**, not just outcome. On the verification side, Fisher et al. provided *a priori* evaluation: proving that coordination protocols satisfy safety and liveness properties *before deployment*.

## Modern State

**Cemri et al.** (2025) provide the most systematic failure analysis: 14 unique failure modes across 3 categories, with **36.9% of failures from inter-agent misalignment** -- a coordination problem, not a capability problem. **Kim et al.** (2025) complement this with scaling analysis: 180 configurations across 5 topology types, demonstrating that architecture selection explains more variance than model size.

**LLM-as-Judge** (Zheng et al. 2023) established the paradigm but documented systematic biases: position bias, verbosity bias, and self-enhancement bias. From a metrology perspective, this is an uncalibrated instrument whose error correlates with the measurement target.

**RAGAS** decomposes evaluation into distinct dimensions (faithfulness, answer relevance, context precision, context recall) -- echoing classical multi-dimensional evaluation but targeting single-agent RAG, not multi-agent coordination.

## The Gap

The field needs a **three-level evaluation framework**:
1. **Task performance**: Did the system produce correct output? (Modern benchmarks handle this)
2. **Coordination quality**: How efficiently did agents coordinate? Token efficiency, error propagation, recovery time, coordination overhead. (Classical platforms evaluated this; no modern benchmark does)
3. **Governance compliance**: Are norms enforced, violations detected, decisions auditable? (EU AI Act requires this; classical electronic institutions provided it; no modern framework implements it)

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1993 | Cohen — *Benchmarks, Test Beds, Controlled Experimentation* | Classical | |
| 1997 | Kitano et al. — *RoboCup: The Robot World Cup Initiative* | Classical | [DOI](https://doi.org/10.1609/aimag.v18i1.1276) |
| 2001 | Goldman & Zilberstein — *Communication in Multi-Agent Cooperation* | Classical | |
| 2001 | Wellman et al. — *Trading Agent Competition (TAC)* | Classical | |
| 2009 | Lomuscio et al. — *MCMAS: Model Checker for Multi-Agent Systems* | Classical | |
| 2010 | Stone et al. — *Ad Hoc Autonomous Agent Teams* | Classical | |
| 2013 | Dix et al. — *A Multi-Agent Systems Turing Challenge* | Classical | [Springer](https://link.springer.com/chapter/10.1007/978-3-642-44927-7_1) |
| 2023 | Zheng et al. — *Judging LLM-as-a-Judge (MT-Bench, Chatbot Arena)* | Modern | |
| 2024 | RAGAS — *Evaluation Framework for RAG Pipelines* | Modern | |
| 2025 | Cemri et al. — *Why Do Multi-Agent LLM Systems Fail?* | Modern | [arXiv](https://arxiv.org/abs/2503.13657) |
| 2025 | Kim et al. — *Scaling LLM Test-Time Compute with Multi-Agent Systems* | Modern | |

## Our Contribution

The experiment harness (Section 4 of the paper) introduces benchmarks that specifically test coordination quality:
- **Cascading Failure V1**: Tests whether agents propagate detected contradictions
- **Cascading Failure V2**: Tests whether agents acknowledge epistemic uncertainty rather than fabricating data

These benchmarks measure *how* agents coordinate, not just *what* they produce.
