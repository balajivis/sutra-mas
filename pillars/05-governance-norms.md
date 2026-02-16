# Pillar 5: Governance, Norms & AI Safety

> *Back to [main README](../README.md)*

## Overview

When agents interact across organizational boundaries, who sets the rules? Governance addresses the institutional infrastructure that constrains agent behavior: norms (what agents should and shouldn't do), sanctions (consequences for violations), and institutional rules (the organizational context within which agents operate). This pillar connects classical normative MAS -- Ostrom's commons governance, electronic institutions, deontic logic -- with modern AI safety concerns including the EU AI Act's requirements for human oversight and accountability.

## Classical Foundations

Ostrom's *Governing the Commons* (1990) demonstrated that communities can self-govern shared resources without either privatization or central authority -- through **institutional rules** that emerge from repeated interaction. This directly informs how agent communities might develop coordination norms. Electronic institutions (Sierra & Esteva) formalized this for MAS: structured interaction environments with defined roles, scenes (interaction contexts), and normative constraints.

Deontic logic provided the formal apparatus: **obligations** (what an agent must do), **permissions** (what it may do), and **prohibitions** (what it must not do). Castelfranchi's work on social commitments grounded norms in observable behavior rather than private mental states -- anticipating the exact challenge LLM agents present, where internal states are opaque.

## Modern State

Modern LLM agents use system prompts to *state* norms ("you are a helpful assistant who never...") but do not *enforce* them. There is no violation detection, no sanction mechanism, no formal social contract between agents. **AgentSpec** (2025) represents the most direct attempt to bridge the gap, providing runtime constraint specifications for LLM agents. The EU AI Act introduces regulatory requirements (Article 9: risk management, Article 14: human oversight, Article 52: transparency) that map directly to classical normative MAS capabilities.

## The Gap

The gap operates at three levels. First, *specification*: norms are embedded in natural-language prompts rather than formal constraint languages. Second, *enforcement*: no framework provides violation detection, graduated sanctions, or formal accountability. Third, *emergence*: classical ABMS research (Bicchieri, Axelrod) studied how norms emerge, spread, and collapse in agent populations -- directly relevant to the safety challenges of autonomous LLM agents at scale. The connection to Trust (Pillar 9) is direct: norms without enforcement erode trust, and trust without norms has no institutional anchor.

## Key Papers

| Year | Paper | Type | Link |
|------|-------|------|------|
| 1990 | Ostrom — *Governing the Commons* | Classical | [DOI](https://doi.org/10.1017/CBO9780511807763) |
| 2000 | Ostrom — *Collective Action and the Evolution of Social Norms* | Classical | [DOI](https://doi.org/10.1257/jep.14.3.137) |
| 2001 | Esteva et al. — *Electronic Institutions* | Classical | |
| 2004 | Boella & van der Torre — *Regulative and Constitutive Norms in Normative MAS* | Classical | |
| 2009 | Alechina et al. — *Normative Monitoring Framework* | Classical | |
| 2024 | EU AI Act — *Regulation (EU) 2024/1689* | Modern | |
| 2025 | AgentSpec — *Runtime Constraints for LLM Agents* | Modern | [arXiv](https://arxiv.org/abs/2503.18666) |

## Cross-Pillar Dependencies

Governance is the most cross-connected pillar:
- **ACL (Pillar 4)**: Norm communication requires typed performatives
- **Trust (Pillar 9)**: Norms without enforcement erode trust
- **HITL (Pillar 8)**: Human oversight is a governance mechanism
- **Evaluation (Pillar 12)**: Compliance verification is a governance evaluation
- **Simulation (Pillar 15)**: Norm emergence is studied through agent-based simulation
