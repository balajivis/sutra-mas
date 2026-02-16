# Pillar 14: Learning & Adaptation

> *Back to [main README](../README.md)*

## Overview

Can coordination simply be *learned*? This is the question that multi-agent reinforcement learning (MARL) has pursued for three decades. The answer determines when a builder should hand-craft coordination infrastructure and when they should train it away. MARL is the largest body of work in our taxonomy (2,386 papers), reflecting its dominance in recent MAS research. The answer turns out to be "partially": MARL has shown agents can learn *when and what* to communicate, but learned coordination still does not scale to open-ended tasks with non-stationary partners.

## Classical Foundations

**Dorigo et al.'s Ant System** (1996, 11,742 citations) formalized stigmergic learning: agents modify a shared environment (pheromone trails), and future agents learn from these modifications. **Bonabeau et al.'s *Swarm Intelligence*** (1999) unified bio-inspired approaches under a common framework. **Littman's Markov games** (1994) is a direct application of stochastic game theory to sequential multi-agent decision-making.

Three disciplines contributed:
- **Evolutionary biology**: Stable behavioral strategies emerge from competitive dynamics without central design -- but require *generations* of selection pressure
- **Game theory**: Cooperation emerges from self-interested interaction *if* agents have memory and expect future encounters
- **Control theory**: Adaptive control and distributed optimization with formal convergence guarantees

**Emergent communication** is the most striking MARL result: agents trained end-to-end learn *when*, *what*, and *to whom* to communicate. DIAL, CommNet, and TarMAC showed agents can learn communication protocols through backpropagation -- a learned version of the directed communication that Pillar 4 identifies as absent from modern protocols.

## Modern State

Self-play produced AlphaStar (grandmaster-level StarCraft II through multi-agent training leagues). But the conditions are restrictive: fixed game rules, millions of training episodes, and stationary reward functions. LLM agents satisfy none of these.

**The MARL-LLM gap**: MARL algorithms assume fixed action spaces, stationary co-players, and millions of training episodes. LLM agents have open-ended action spaces, non-stationary behavior, and expensive inference making millions of episodes impractical. Recent work on multiagent finetuning and socialized learning explores RL to improve LLM agents through structured multi-agent feedback, but without the formal convergence guarantees MARL provides.

## The Gap

The classical MARL toolkit assumes agents that can be trained for millions of episodes in simulation. LLM agents operate in the real world from the first interaction, with no training loop -- only in-context learning. The field needs adaptation mechanisms designed for **few-shot, high-cost-per-interaction settings** where agents improve through tens of interactions, not millions.

The core tension: learned coordination is powerful but brittle under distribution shift. Hand-coded coordination needs only a configuration update when the environment changes. Learned and designed coordination are complements, not substitutes.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1994 | Littman — *Markov Games as a Framework for Multi-Agent RL* | Classical | |
| 1996 | Dorigo et al. — *Ant System: Cooperating Agents* | Classical | [DOI](https://doi.org/10.1109/3477.484436) |
| 1999 | Bonabeau et al. — *Swarm Intelligence* | Classical | |
| 2008 | Busoniu et al. — *Comprehensive Survey of Multi-Agent RL* | Classical | |
| 2009 | Nedic & Ozdaglar — *Distributed Subgradient Methods for Multi-Agent Optimization* | Classical | [DOI](https://doi.org/10.1109/tac.2008.2009515) |
| 2016 | Foerster et al. — *DIAL: Learning to Communicate with Deep Multi-Agent RL* | Transition | |
| 2019 | Vinyals et al. — *AlphaStar: Grandmaster Level StarCraft II* | Transition | |
| 2021 | Zhang et al. — *Multi-Agent RL: A Selective Overview* | Transition | |
| 2025 | Subramaniam et al. — *Multiagent Finetuning: Self Improvement with Diverse Reasoning Chains* | Modern | [arXiv](https://arxiv.org/abs/2501.05707) |

## The Builder's Dilemma

For the practitioner building a multi-agent system today:
- MARL's emergent communication suggests learned protocols can outperform hand-designed ones -- but only when training is feasible
- Swarm intelligence's stigmergic learning connects directly to blackboard architectures
- MARL's credit assignment problem is the learning analogue of organizational design: how do you attribute team success to individual contributions?
- No benchmark compares learned vs. designed coordination on equivalent tasks
