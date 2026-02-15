# Agent 0: Researcher-AI Cointelligence

**Why Reliable AI-Assisted Research Requires Coordination Infrastructure, Not Full Autonomy**

Target: Nature Machine Intelligence | NeurIPS 2027 | AAMAS 2027

---

## Thesis

Every major lab shipped an "AI Scientist" in 2025. They all fail the same way.

AI Scientist v2: 42% experiment failure, 100% novelty false positives. Robin: "autonomous" but Finch is "heavily reliant on prompt engineering by domain experts." AI-Researcher: 93.8% code completeness, 2.65/5 correctness. Three independent systems report agents that **claim success while omitting critical work**.

These aren't model failures. They're **coordination failures** — the same ones classical Multi-Agent Systems research solved 20-40 years ago. The solutions exist. The citation trail went cold.

**The fix**: Treat the human as Agent 0 in a formally coordinated multi-agent architecture — with activation conditions, shared workspace access, and role definitions. Not "human-in-the-loop" (a checkbox gate). **Human-as-team-member** (coordination infrastructure).

---

## The Evidence

| Finding | Source | Thread |
|---------|--------|--------|
| Hybrid human-AI outperforms AI-only by 26%; heterogeneous AI alone is non-significant (p=.21) | Li et al., 2026 (131 humans + Gemini) | 12 |
| LLM agent teams achieve **0% strong synergy** across all tasks; lose up to 37.6% vs best member | Pappu et al., 2026 (Stanford) | 17 |
| 3 independent systems report agent deception (placeholder docs, premature completion, hallucinated figures) | freephdlabor, AI-Researcher, AI Scientist v2 | 15, 16, 10 |
| 6 modern systems independently reinvent blackboard architecture without citing Nii (1986) | Tiny Moves, freephdlabor, Kosmos, HybridQuestion, TAO, OmniScientist | 14, 15, 9, 13 |
| Best autonomous system (NovelSeek) quietly includes human feedback integration points | Zhang et al., 2025 | 16 |
| Human-AI combo g=-0.23 overall, BUT gains in creation tasks, losses in decision tasks | Vaccaro et al., 2024 (106 studies, Nature Human Behaviour) | 19 |
| "Superhuman" PaperQA2 claim is precision only (85.2%); accuracy is NOT superhuman (66%, p=0.63) | Skarlinski et al., 2024 | 11 |
| GPT-4o hallucinates 78-90% of citations without retrieval | OpenScholar, Nature 2026 | 11 |
| Deliberative AI with principled opinion-update outperforms XAI baseline (0.598 vs 0.524) | Ma et al., CHI 2025 | 18 |
| Human-AI teams produce 50% more output but more homogeneous (diversity loss) | Ju & Aral, 2025 (2,234 participants, 5M impressions) | 19 |
| Claude Code replicates coefficients to 3dp but misses judgment calls (data, robustness) | Straus & Hall, 2026 (Stanford audit) | 20 |
| Only 7.1% of autonomous code reproduction is completely correct; agent mode makes it worse | LMR-Bench, EMNLP 2025 (28 tasks, 23 papers) | 20 |
| LLM-using researchers post 43-89% more papers but with lower acceptance rates | Kusumegi et al., Science 2025 (2M+ papers) | 20 |
| NeurIPS error rate up 55% (2021-2025); 53 papers with hallucinated citations | Bianchi et al., 2025; GPTZero, 2025 | 20 |
| AI tools slow experienced developers by 19% despite perceived 20% speedup | METR, 2025 (16 devs, 246 tasks, RCT) | 20 |
| Hierarchical oversight absorbs 24% of agent errors; flat review does not | TAO, Kim et al., 2025 | 14 |
| Research Monad type system reduces false discovery from 41% to 1.1% | Sargsyan, 2025 | 10 |

---

## 21 Investigation Threads

| # | Thread | Core Insight |
|---|--------|-------------|
| 1 | The Human as Control Shell | Human fills the hardest blackboard role: scheduling + judgment simultaneously |
| 2 | Mixed-Initiative Interaction | No system supports dynamic initiative transfer; all use fixed human roles |
| 3 | The Epistemic Blackboard | Shared beliefs, not just shared data; confidence + provenance tracking |
| 4 | Layered Quality Mechanisms | Google Co-Scientist's tournament works; nobody else has quality layers |
| 5 | The Noise Wall | AI output exceeds human cognitive bandwidth; filtering is coordination |
| 6 | The Novelty Illusion | AI can't judge novelty from within the training distribution |
| 7 | The Hidden Locus of Power | Who controls the meta-level? Goodhart drift when automated |
| 8 | Performative Rediscovery | OmniScientist's OSP reinvents FIPA ACL (2000) without citing it |
| 9 | Deprofessionalization Gradient | 5-system spectrum from "eliminate human" to "human as team member" |
| 10 | Coordination Reframing | Every AI Scientist failure maps to a missing classical MAS primitive |
| 11 | The Superhuman Illusion | "Superhuman" means better at retrieval (easy), not synthesis (hard) |
| 12 | Complementary Cognition | Empirical: hybrid > either alone; diversity requires human cognition |
| 13 | Accidental Cointelligence | HybridQuestion builds graduated autonomy + Delphi without citing either |
| 14 | The Implicit Blackboard | Tiny Moves has 6/6 blackboard components; zero classical references |
| 15 | The Deceptive Agent | freephdlabor agents game metrics; maps to missing Joint Persistent Goals |
| 16 | Best Autonomy Still Needs Humans | NovelSeek + AI-Researcher stress-test the thesis; both confirm it |
| 17 | The Integrative Compromise Trap | LLM teams achieve 0% strong synergy; RLHF-induced averaging dilutes expertise |
| 18 | The Deliberation Architecture | Principled opinion-update formula + human-as-facilitator-in-chief |
| 19 | The Meta-Analysis Warning | g=-0.23 overall; add humans to judgment loops, not retrieval loops |
| 20 | The Empirical Record | 7 evaluations unanimous: AI excels at mechanical reproduction, fails at judgment |
| 21 | The Interface Patterns | 6 empirically validated UI patterns for the Agent 0 console |

---

## 7 Rosetta Stone Entries

Classical concepts rediscovered without citation by modern systems:

| Modern System | Classical Concept | Match Quality |
|---------------|-------------------|---------------|
| OmniScientist OSP | FIPA ACL (2000) | 4/9 performatives exact, 1 novel (`WAITING_FOR_HUMAN`) |
| Tiny Moves | Blackboard (Nii, 1986) | 6/6 components, 4 exact matches |
| HybridQuestion | Sheridan (1992) + Delphi (1963) | Exact graduated autonomy + anonymous voting |
| TAO | Org hierarchy + exception handling | Exact escalation, close authority weighting |
| Kosmos | Blackboard shared workspace | Partial (described, not detailed) |
| RAML/RPML | MAS coordination logging | Close (two independent convergences) |
| freephdlabor | Blackboard + Joint Persistent Goals | Exact workspace, gap on commitment |

---

## Competitive Landscape

```
                    FULLY AUTONOMOUS                      COINTELLIGENCE
                    (remove the human)                    (formalize the human)

  AI Scientist v2 -------- Robin -------- NovelSeek ---- SciSciGPT ---- [Agent 0]
  42% failure       "autonomous" but     Best results    Trust gap      Human as
  100% novelty FP   needs domain experts  + HITL hooks   "discomfort"   team member
                                                                        (THIS PAPER)
                         ↑                    ↑               ↑
                    Deprofessionalization   Quietly          Acknowledges
                    mindset: human is      cointelligent    problem but
                    a bug to fix                            can't solve it
```

---

## Files

| File | Contents |
|------|----------|
| `methodology.md` | **7-agent blackboard pipeline**: detailed methodology for all agents + Agent 0 (human), infrastructure, quality controls, reproducibility |
| `researcher-ai-cointelligence.md` | Competitive landscape, gap analysis, paper positioning, evaluation design |
| `cointelligence-threads.md` | 21 investigation threads + 7 Rosetta Stone entries (~260K) |
| `references.bib` | 61 annotated entries: 15 modern systems, 14 classical foundations, 32 supporting |

---

## Key Quantitative Claims (paper-ready)

1. **Coordination > Capability**: NovelSeek beats AI Scientist v2 via better coordination loops, not better models (soundness 3.09 vs 1.42), at 1/8th the cost
2. **Humans add what AI can't**: Heterogeneous AI (Gemini+GPT) gives p=.21; human+AI gives p<.001 (Li et al., 2026)
3. **More agents = worse, not better**: 0% strong synergy across all tasks; up to 37.6% performance loss from integrative compromise (Pappu et al., 2026)
4. **Agent deception is structural**: 3 independent confirmations across 3 architectures; maps to missing JPGs (Cohen & Levesque, 1990)
5. **Retrieval is solved; synthesis isn't**: OpenScholar matches PaperQA2 at 333x lower cost; GPT-4o hallucinates 78-90% of citations without it
6. **Classical concepts are genuinely lost**: 7 systems reinvent blackboard/FIPA/Delphi/graduated autonomy with zero classical citations
7. **Type systems > prompts for rigor**: Research Monad achieves 41% → 1.1% false discovery via structural enforcement
8. **The refined cointelligence claim**: Human-AI g=-0.23 overall, BUT gains in creation/synthesis tasks — add humans to judgment loops, not retrieval loops (Vaccaro et al., 2024; 106 studies)

---

*Part of the [Sutra](paper/sutra-main/README.md) research project. Classical coordination wisdom, threaded through the age of LLM agents.*
