# Pillar 15: Modeling & Simulating Artificial Societies

> *Back to [main README](../README.md)*

## Overview

What happens when you scale multi-agent systems to 1,000 or 10,000 agents? At societal scale, coordination mechanisms interact in ways no designer anticipated: norms emerge that no one authored, hierarchies form that no one specified, and collective behaviors arise that no individual agent intended. This pillar surveys agent-based modeling and simulation (ABMS) as a scientific discipline and identifies why the MABS community's expertise in validating emergent behavior is directly relevant to anyone deploying LLM agents at scale.

## Classical Foundations

**Epstein and Axtell's *Growing Artificial Societies*** (1996) demonstrated that complex social phenomena -- trade, combat, cultural transmission, disease propagation -- emerge from simple agent rules on a spatial lattice. Sugarscape established the "generative" paradigm: if you can grow a social phenomenon from micro-rules, you have *explained* it.

Four disciplines contributed:
- **Sociology**: Schelling's segregation model (1971) -- individually mild preferences produce extreme macro-level segregation. The canonical proof that simple agent rules generate emergent patterns.
- **Economics**: Holland's artificial adaptive agents (1991) pioneered agent-based computational economics, replacing representative-agent equilibrium models with heterogeneous interacting agents.
- **Biology**: The **ODD protocol** (Overview, Design concepts, Details) -- a standardized methodology for describing agent-based models that ensures reproducibility. No LLM agent paper uses a comparable description standard.
- **Complex systems**: Deneubourg et al. (1993) on engineering local interaction rules to produce desired collective intelligence -- when emergence is desirable and how to control it.

## Modern State

**Park et al.'s Generative Agents** (2023) -- 25 LLM agents inhabiting a virtual town (Smallville). Without explicit coordination, agents formed social groups, spread gossip, organized a Valentine's Day party. 3,000+ citations, Best Paper at UIST 2023. But Park et al. built on no classical ABMS infrastructure -- no citation of Sugarscape, Swarm, ODD, or NetLogo.

The trajectory since Smallville is dramatic:
- Park et al.'s follow-up scales to **1,052 agents** calibrated against real individuals, replicating General Social Survey responses at 85% accuracy
- **AgentSociety** (Tsinghua, 2025) scales to **10,000+ agents** with Maslow-hierarchy-based motivation
- **"Infected Smallville"** uses the framework as a controlled experiment: agents exposed to disease-threat news reduced social engagement -- emergent behavior that was not explicitly prompted
- **"Homo Silicus"** (NBER 2023) asks whether LLM agents can substitute for human subjects in economic experiments

Critical self-reflection is also emerging: latent profile analysis reveals that LLM agents exhibit systematic personality-type clustering rather than the continuous variation that characterizes human populations -- a homogeneity problem Schelling's work shows can qualitatively change emergent dynamics.

## The Gap

The MABS and LLM engineering communities remain largely separate. MABS offers decades of experience in:
- **Designing** agent societies (interaction rules that produce desired emergent behavior)
- **Validating** emergent behavior (the ODD protocol, sensitivity analysis, parameter sweeps)
- **Reporting** results reproducibly (standardized model descriptions)
- Understanding when emergence is **desirable** (simulation) versus **dangerous** (production)

LLM agent builders could use ABMS techniques to validate multi-agent designs in simulation before production deployment -- but the connection is barely made. Our JPG finding is directly relevant: if LLM agents cannot detect their own epistemic failures in a 3-agent team, what happens in a 10,000-agent society?

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1971 | Schelling — *Dynamic Models of Segregation* | Classical | |
| 1987 | Reynolds — *Flocks, Herds and Schools* | Classical | [DOI](https://doi.org/10.1145/37401.37406) |
| 1991 | Holland — *Artificial Adaptive Agents in Economic Theory* | Classical | |
| 1996 | Epstein & Axtell — *Growing Artificial Societies: Social Science from the Bottom Up* | Classical | |
| 1996 | Minar et al. — *The Swarm Simulation System* | Classical | |
| 1998 | Axelrod — *The Complexity of Cooperation* | Classical | |
| 2006 | Grimm et al. — *A Standard Protocol for Describing ABMs (ODD)* | Classical | [DOI](https://doi.org/10.1016/j.ecolmodel.2006.04.023) |
| 2015 | Bicchieri — *The Grammar of Society: The Nature and Dynamics of Social Norms* | Classical | |
| 2023 | Park et al. — *Generative Agents: Interactive Simulacra of Human Behavior* | Modern | [arXiv](https://arxiv.org/abs/2304.03442) |
| 2023 | Horton — *Large Language Models as Simulated Economic Agents* | Modern | [DOI](https://doi.org/10.3386/w31122) |
| 2025 | AgentSociety — *10,000+ Agent Simulation (Tsinghua)* | Modern | |

## The Scale Challenge

Artificial societies are where coordination failure becomes most visible. When 10,000 agents interact through emergent social dynamics, the absence of organizational structure, joint intentions, commitment tracking, and discourse coherence produces the failure modes documented at small scale -- but at civilization scale.
