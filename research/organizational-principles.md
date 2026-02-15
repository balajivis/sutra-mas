# Organizational Principles for Agent Team Design

> What high-performing human teams teach us about building AI agent systems that produce remarkable output.

The central finding across all domains: **the structure and conditions surrounding a team matter more than the individual capability of team members**. Hackman's research quantifies this: enabling conditions explain over 50% of team effectiveness variance. Google's Project Aristotle confirmed it: psychological safety, not individual talent, is the #1 predictor. This is the most important insight for agent system design.

---

## Principle 1: Preoccupation with Failure

### Human Evidence

**High-Reliability Organizations** (nuclear power plants, aircraft carriers, air traffic control) don't avoid failure -- they are obsessed with detecting it early. Karl Weick and Kathleen Sutcliffe identified this as the foundational HRO principle.

HROs treat all failures -- no matter how minor -- as critical signals. 90% of reports in HRO-influenced healthcare systems are filed in the absence of significant harm. The data comes from proactive detection, not post-disaster forensics.

Atul Gawande's WHO Surgical Safety Checklist cut fatality rates by over a third -- not as a memory aid but as a failure detection mechanism that forces teams to surface problems before the knife touches skin.

### Agent Design Mapping

- **Mandatory anomaly logging**: Every agent emits structured signals for unexpected outcomes. A response 3x slower than expected, a contradiction in outputs, an empty tool call return -- these are "near misses" that HROs would investigate.
- **No silent error swallowing**: Catch-and-continue is fine for resilience, but you must record and surface that something unexpected happened.
- **Post-mortem traces**: When a workflow produces suboptimal results, the entire trace must be reviewable. Comprehensive observability (Langfuse tracing, cost tracking, latency) is the agent "black box."
- **Pre-flight checklist gates**: Before an agent begins complex work, validate preconditions explicitly. The surgical Time-Out: confirm the agent has the right context, tools, and permissions.

---

## Principle 2: Structured Communication Protocols

### Human Evidence

**Crew Resource Management (CRM)** in aviation is perhaps the most successful human factors intervention in history. Before CRM, 70%+ of crashes involved human error from communication breakdowns. The 1977 Tenerife disaster (583 dead) was the catalyst -- the captain proceeded ignoring signals because protocols were informal and the authority gradient too steep.

CRM introduced:
- **Readback/hearback**: Pilot reads back clearance; ATC confirms. Closed-loop communication.
- **Challenge-and-response checklists**: One reads, another verifies. Neither can skip steps.
- **Sterile cockpit rule**: Below 10,000 feet, only mission-critical communication flows.
- **SBAR** (Situation-Background-Assessment-Recommendation): Structured four-part handoff protocol, originally from US Navy submarines.

Result: CRM reduced aviation accidents by 50%+.

### Agent Design Mapping

- **Typed message schemas**: Just as CRM mandates structured phraseology (not "okay" but "affirmative"), inter-agent communication should use structured schemas, not free-form text. Handoffs should include: what was done, what remains, what was uncertain, what to watch for (SBAR).
- **Closed-loop confirmation**: Agent B confirms receipt and restates the task (readback). Agent A confirms the restatement (hearback). Catches misinterpretation before work begins.
- **Sterile cockpit for critical operations**: During high-stakes operations (database migrations, financial transactions), restrict information flowing to the executing agent. No tangential queries.
- **Gate-based workflows**: The surgical checklist maps to workflows where each phase requires explicit verification before proceeding.

---

## Principle 3: Authority Gradient Management

### Human Evidence

A steep authority gradient means the captain's word is unquestioned. Too flat means no accountability. The optimal is a moderate gradient where authority exists but can be challenged.

CRM teaches **assertive followership**: "Captain, I see our altitude deviating. Could you verify?" Amy Edmondson's research found teams with high psychological safety reported more errors -- not because they made more, but because they surfaced them.

Google's Project Aristotle (180+ teams): psychological safety is the #1 factor. Sales teams with high safety exceeded targets by 17%; those with low safety fell short by 19%.

HRO's **deference to expertise**: the expert is not the person with the highest rank, but the person with the most relevant knowledge. On an aircraft carrier, a 19-year-old ordnance handler can halt flight operations if they see a safety issue.

### Agent Design Mapping

- **Validator/challenger agents**: Agents whose explicit role is to critique and find flaws. Not format validators -- adversarial reviewers testing substance.
- **No "god" agents**: Avoid architectures where one orchestrator's decisions are never questioned. Consequential outputs should be reviewable.
- **Deference to local context**: When a specialized agent disagrees with a general planning agent on domain-specific questions, weight the specialist.
- **Escalation protocols**: Log -> flag -> escalate -> halt. Graduated assertiveness.
- **HITL as authority gradient management**: Not just approving actions -- ensuring the gradient between AI agents and humans remains navigable.

---

## Principle 4: Shared Mental Models

### Human Evidence

DeChurch and Mesmer-Magnus (meta-analysis, 23 studies): shared mental models are significantly correlated with team performance. The effect is about having compatible interpretive frameworks so team members can predict each other's behavior without explicit communication.

McChrystal's **Team of Teams** was built on **shared consciousness**: JSOC's daily O&I briefing connected 7,000 people across dozens of locations in a 90-minute call -- every day. Not to give orders; to ensure everyone had the same picture. McChrystal's embedding program sent each team's best members to embed with other teams for up to six months, creating lateral trust.

**Network-centric warfare** doctrine: shared situational awareness enables self-synchronization -- units coordinate without explicit orders because they see the same picture and understand the commander's intent.

### Agent Design Mapping

- **Shared context objects**: All agents read from and write to a common state representation -- the "situation board." The agent O&I briefing.
- **Mission-intent prompts**: Specify intent not method. "Ensure the user can log in within 2 seconds" not "first do X, then do Y." This is Auftragstaktik for agents.
- **Shared schemas and ontologies**: When agents use different representations for the same concepts, coordination breaks down.
- **Full context propagation across handoffs**: Not just the output -- the full reasoning context (history, assessment, uncertainty). SBAR for agents.

---

## Principle 5: Bounded Autonomy with Clear Roles

### Human Evidence

**Hackman's Five Conditions**: bounded teams, compelling direction, enabling structure, supportive context, expert coaching. These enabling conditions controlled over half of performance variation in intelligence community teams.

**Boyd's OODA Loop**: The Orient phase -- where information is synthesized through mental models -- is the most important and most neglected. The side that completes OODA cycles faster with better orientation wins.

**Auftragstaktik** (mission command): Commander specifies intent and boundaries; subordinate chooses method. Enables rapid adaptation because decisions are made by the person closest to the situation.

**Linux kernel maintainers**: MAINTAINERS file defines who owns each subsystem. Full authority within domain; must submit to umbrella maintainers for cross-cutting changes.

### Agent Design Mapping

- **Explicit role definitions**: Each agent has a clearly defined scope. What is mine, what requires escalation, what is out of scope.
- **OODA-structured loops**: Observe (gather state) -> Orient (synthesize with knowledge and goals) -> Decide (select action) -> Act (execute). The Orient phase is where value is created.
- **Hierarchical delegation with lateral communication**: Orchestrator delegates to specialists with full domain autonomy; cross-domain decisions get escalated. But lateral communication between specialists is also possible.

---

## Principle 6: Quality Gates and Redundant Review

### Human Evidence

**Linus's Law**: "Given enough eyeballs, all bugs are shallow." But Heartbleed persisted for 2 years in OpenSSL despite open code. The distinction: passive availability vs. active review. Structured review processes (mandatory code review, CI/CD, named reviewers) are what actually work.

The **pull request workflow** is a formalized quality gate: propose -> automated tests -> human review -> iterate -> merge.

The WHO surgical checklist creates three gates within a single procedure: Sign-In, Time-Out, Sign-Out. Each requires active verbal confirmation from multiple team members.

**Wu et al. (Nature 2019)**: Small teams disrupt; large teams develop. Flat teams produce more novel combinations than hierarchical teams. Match review structure to output type.

### Agent Design Mapping

- **Multi-agent review chains**: Consequential output passes through at least two agents with different perspectives. The PR model: proposer, automated checks, reviewer.
- **Automated evaluation as CI/CD**: Agent outputs pass through evaluators (factuality, format, safety) before reaching the next stage.
- **Heterogeneous review panels**: Different models or prompt strategies for review. Different "viewpoints" catch different errors.
- **Stage-appropriate scrutiny**: Routine outputs get lightweight checks; high-stakes outputs get full review; final deliverables get comprehensive validation.

---

## Principle 7: Adaptive Resilience

### Human Evidence

HRO **commitment to resilience**: Reliable organizations don't avoid errors -- they continue operating despite them. They function as adaptable learning organizations maintaining capability under degraded conditions.

McChrystal replaced efficiency (optimized for known problems) with adaptability (capable of responding to unknown problems). His metaphor: a leader should be a **gardener**, not a chess master. A chess master controls every piece; a gardener creates conditions for growth.

Linux kernel's two-branch model: current-release and next-release. Failure in development never threatens stable release.

### Agent Design Mapping

- **Graceful degradation**: When an agent fails, have fallback strategies. Switch model, simplify request, use cached results, escalate to human.
- **Circuit breakers**: If an agent is failing repeatedly, stop sending requests. Engineering equivalent of surgical "stop the line."
- **Rollback capability**: Checkpoints that allow rolling back to known-good states.
- **"Gardener" orchestration**: Set conditions (goals, constraints, resources) and monitor outcomes. Intervene only when things deviate beyond bounds.
- **Post-failure learning**: Every failure updates knowledge. The HRO near-miss analysis for agents.

---

## Principle 8: Constructive Intellectual Friction

### Human Evidence

The best teams disagree most productively, not most harmoniously. Conditions for productive conflict: psychological safety, shared goals, task conflict over relationship conflict, and structured resolution processes.

Google designates "naysayers" on projects. Military uses **red teams**. Scientific research relies on peer review and replication.

Wu et al.: Small teams (1-3) produce disruptive work. Large teams produce incremental development. Flat teams produce more novel combinations than hierarchical ones.

### Agent Design Mapping

- **Red team agents**: Agents whose purpose is to critique, find flaws, argue against outputs. Not validators -- adversarial reviewers.
- **Multi-model ensembles**: Different LLMs create genuine diversity. Different training data, different biases, different strengths.
- **Small teams for novelty**: 2-3 agents with high autonomy for creative/novel tasks. Larger structured workflows for development of known patterns.
- **Structured disagreement resolution**: When agents conflict, use explicit evaluation against criteria, not majority vote.

---

## Principle 9: Shared Artifacts and Representations

### Human Evidence

Every high-performing team domain uses shared artifacts:
- **Aircraft carriers**: The "Ouija board" -- tabletop model of the flight deck updated in real-time
- **Military C2**: Common Operating Picture (COP) -- shared map showing all positions
- **Surgery**: Patient chart, imaging displays, physical checklist on the wall
- **Open source**: The repository, issue tracker, CI dashboard, MAINTAINERS file
- **Scientific research**: Lab notebooks, shared data repositories

Network-centric warfare doctrine: the shared artifact is the mechanism through which collective intelligence emerges.

### Agent Design Mapping

- **Shared state stores**: Centralized, versioned representation of current state. Not a message queue (ephemeral) -- a persistent "Ouija board."
- **Observable execution traces**: Real-time view of what each agent is doing. Langfuse is a direct implementation.
- **First-class artifact handoff**: When one agent produces output for another, the artifact is inspectable and versioned, not just text in a message stream.
- **Orchestrator situation board**: High-level workflow state view that any agent or human can consult.

---

## Principle 10: Conditions Over Individual Capability

### The Convergent Evidence

| Domain | Key Finding |
|--------|-------------|
| HROs | Five organizational principles, not individual heroism, produce reliability |
| Aviation CRM | Structured protocols reduced accidents 50%+, not better pilots |
| Surgical Teams | Psychological safety predicts learning more than surgeon skill |
| Military C2 | Mission command (structural) beats detailed orders (individual control) |
| Open Source | Maintainer hierarchy + review beats any individual contributor |
| Scientific Teams | Team structure (flat vs hierarchical) predicts innovation independent of talent |
| Google Aristotle | Psychological safety #1, dependability #2, structure/clarity #3 -- all conditions |

**This is the most important insight for agent system design.** The instinct is to focus on making each agent "smarter." The evidence says: invest instead in coordination infrastructure, communication protocols, review mechanisms, and shared representations.

A team of moderately capable agents with excellent coordination will outperform a team of individually brilliant agents with poor coordination.

---

## Summary Table

| Principle | Human Domain | Human Mechanism | Agent Mechanism |
|-----------|-------------|-----------------|-----------------|
| Preoccupation with Failure | HROs, Aviation | Near-miss reporting | Anomaly logging, trace review |
| Structured Communication | CRM, Surgery | Readback, SBAR, checklists | Typed schemas, closed-loop confirmation |
| Authority Gradient | CRM, HROs | Assertive followership | Challenger agents, escalation protocols |
| Shared Mental Models | Military C2, JSOC | O&I briefings, shared COP | Shared state, mission-intent prompts |
| Bounded Autonomy | Military, Linux | Auftragstaktik, maintainer hierarchy | Role-scoped agents, OODA loops |
| Quality Gates | Open Source, Surgery | Code review, checklists, peer review | Multi-agent review, automated eval |
| Adaptive Resilience | HROs, JSOC | Commitment to resilience | Circuit breakers, rollback, fallbacks |
| Constructive Friction | Science, Red Teams | Devil's advocate, peer review | Red team agents, multi-model ensembles |
| Shared Artifacts | All domains | COP, Ouija board, repos | Observable traces, versioned artifacts |
| Conditions > Capability | All domains | Structure predicts more than talent | Invest in coordination over agent power |

---

## References

- Edmondson, "Psychological Safety and Learning Behavior in Work Teams" 1999
- Weick & Sutcliffe, "Managing the Unexpected" (HRO principles) 2001/2015
- McChrystal, "Team of Teams" 2015
- Gawande, "The Checklist Manifesto" 2009
- Hackman, "Leading Teams" (Five Conditions) 2002
- Wu, Wang, Evans, "Large Teams Develop and Small Teams Disrupt" Nature 2019
- Xu & Wu, "Flat Teams Drive Scientific Innovation" PNAS 2022
- Google Project Aristotle -- [re:Work](https://rework.withgoogle.com/intl/en/guides/understanding-team-effectiveness)
- CRM -- [SKYbrary](https://skybrary.aero/articles/crew-resource-management-crm)
- Authority Gradients -- [SKYbrary](https://skybrary.aero/articles/authority-gradients)
- Boyd's OODA Loop -- [Reference](https://github.com/joelparkerhenderson/ooda-loop)
- Auftragstaktik -- [Army University Press](https://www.armyupress.army.mil/Portals/7/military-review/Archives/English/Matzenbacher-Mission-Command.pdf)
- Network-Centric Warfare -- [Army War College](https://csl.armywarcollege.edu/SLET/mccd/CyberSpacePubs/Network-Centric%20Warfare%20-%20Leveraging%20the%20Power%20of%20Information.pdf)
