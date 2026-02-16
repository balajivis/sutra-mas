# Pillar 8: Human-Agent Interaction & HITL

> *Back to [main README](../README.md)*

## Overview

In every production deployment, a human is somewhere in the system -- approving, correcting, escalating, or simply watching. The question is not *whether* humans participate but *how*: as supervisors reviewing every output, as peers collaborating on shared tasks, or as absent principals whose intent the agents must infer. This pillar traces how classical MAS formalized human-agent interaction as a design problem -- adjustable autonomy, mixed-initiative protocols, shared task models -- and reveals that modern "approve/reject" gates discard thirty years of research.

## Classical Foundations

**Parasuraman, Sheridan, and Wickens** (2000) formalized the definitive taxonomy: a 4x10 matrix crossing four information-processing stages with **ten levels of automation**. The critical insight: automation levels should vary by *function type within an agent*, not just by agent. An agent might autonomously gather information (Level 8) but require human approval for consequential decisions (Level 4).

**Bainbridge's "Ironies of Automation"** (1983): the more reliable the agent becomes, the less vigilant the human overseer, and the more catastrophic the eventual failure. **Klein et al.'s "Ten Challenges"** (2004) identifies four prerequisites for joint activity: basic compact, mutual predictability, mutual directability, and common ground. **Horvitz's Principles of Mixed-Initiative UIs** (1999) established twelve design principles, at least four of which current LLM agent systems violate.

High-stakes precedents from aviation (Crew Resource Management), surgery (WHO Safety Checklist reducing mortality by 47%), and submarine operations (reader-worker pattern) solve the same problems LLM agent HITL must address.

## Modern State

Current LLM agent systems implement HITL as **approval queues**: a human reviews and approves/rejects agent output. This models the human as a *gate* rather than a *teammate*. The human can say yes or no but cannot bid for tasks, contribute partial results, or participate in the coordination protocol. LangGraph's `interrupt()` offers only continue-or-abort semantics. Production data confirms: 68% of production agents perform at most 10 steps before human handover -- but the handover is a hard boundary, not a graduated transition.

**The cognitive problem**: Bucinca et al. (2021) demonstrated that showing humans an AI recommendation *before* they form their own judgment induces systematic overreliance -- and adding explanations does *not* reduce this effect.

## The Gap

The HITL gap has three levels:
1. **Interaction model**: No framework implements humans as protocol participants who can bid, contribute to blackboards, or maintain joint intentions with AI teammates
2. **Authority management**: Modern HITL provides binary approve/reject; classical work established ten-level graduated autonomy
3. **Interaction design**: The human factors community's solutions to authority gradients, structured verification, and role-based pause points remain entirely uncited

The gap between ten classical levels and two modern levels represents one of the starkest fidelity losses in our Rosetta Stone analysis.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1983 | Bainbridge — *Ironies of Automation* | Classical | |
| 1992 | Sheridan — *Telerobotics, Automation, and Human Supervisory Control* | Classical | |
| 1999 | Horvitz — *Principles of Mixed-Initiative User Interfaces* | Classical | |
| 2000 | Parasuraman et al. — *Types and Levels of Human Interaction with Automation* | Classical | [DOI](https://doi.org/10.1109/3468.844354) |
| 2002 | Scerri et al. — *Adjustable Autonomy for the Real World* | Classical | |
| 2004 | Klein et al. — *Ten Challenges for Making Automation a Team Player* | Classical | |
| 2010 | Bradshaw et al. — *Coactive Design* | Classical | |
| 2019 | Amershi et al. — *Guidelines for Human-AI Interaction* | Modern | |
| 2021 | Bucinca et al. — *Cognitive Forcing Experiments* | Modern | |
| 2025 | Anthropic — *Building Effective Agents* | Modern | [Docs](https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns) |

## The Human Role Spectrum

```
Gate ←→ Monitor ←→ Collaborator ←→ Peer Agent
 ↑                                      ↑
 Modern LLM frameworks          Classical MAS vision
 implement only these           formalized these
```

Current frameworks implement only the two leftmost positions; the classical literature formalized the two rightmost.
