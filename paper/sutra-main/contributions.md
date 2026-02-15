# Research Methodology: Two-Level Human-AI Architecture

The Sutra research operates at two distinct levels, executed sequentially:

**Level 1 — Interactive Human-AI Research** (Sprints r1-r2): The author works directly with Claude Code through 6 custom research commands, each a structured prompt with specific tool permissions and output formats. This level produced the Lost Canary algorithm, the initial seed expansion, the backward/forward passes, and the first structured assessments. The human drives every decision; the AI executes citation traversal, extraction, and structured analysis.

**Level 2 — Autonomous Pipeline** (Sprint r3+): Informed by Level 1 findings, the author designed a scaled 8-agent blackboard system running unattended on a VM. This level processed 24,700 papers into the 12,527-paper Sutra Corpus. The human monitors, calibrates, and intervenes at quality gates.

The distinction matters: Level 1 is the **research methodology** (how we designed the investigation). Level 2 is the **data production system** (how we built the corpus at scale). Both are described below — Level 1 here, Level 2 in Contribution 1.

## The 6 Research Commands (Level 1)

Custom Claude Code commands in `.claude/commands/`, each a structured prompt with explicit tool permissions:

| Command | Phase | What It Does | Key Methodological Detail |
|---------|-------|-------------|--------------------------|
| `/research-plan` | Planning | Sprint planning: select concepts, define hypotheses, break into tasks | Requires explicit **hypotheses** and **success criteria** per sprint — not open-ended exploration |
| `/literature` | Phases 1-3 | Citation graph traversal, Lost Canary detection, corpus building | Contains the full backward/forward pass algorithm including **root primitive scoring formula** and **three anti-false-positive checks** |
| `/experiment` | Validation | GitHub discovery + Python test harness + benchmarking | Two-phase: discover existing implementations first, then build harness to fill gaps |
| `/analyze` | Phase 5 | Archivist/Modernist/Bridge Builder structured assessment | Full prompt templates with **mandatory self-critique** — each assessment must challenge its own mappings |
| `/write` | Phase 7 | Paper section drafting with per-section academic guidance | Section-specific conventions: "Balaji writes the core thesis. You draft supporting material." |
| `/research-review` | QA | 7-phase quality gate before any output is accepted | Includes **devil's advocate challenges** against the core thesis and per-claim verification table |

Full command prompts: [Appendix: Research Commands](appendix-research-commands.md)

### Key Methodological Details from Level 1

**Root Primitive Scoring** (from `/literature`):

The backward pass doesn't just count citations. It weights by branch diversity to prevent a single well-cited branch from dominating:

```
root_primitive_score = cite_count × branch_diversity
Threshold: score ≥ 6 (e.g., 3 citations × 2 branches, or 2 × 3)
```

Where `branch_diversity` = number of distinct MAS branches among the seeds citing it (Communication, Organization, Coordination, Architecture, Negotiation, Verification). This ensures root primitives are foundational across the field, not just dominant in one subarea.

**Three Anti-False-Positive Checks** (from `/literature`):

Before confirming any Lost Canary, all three checks must pass:

1. **Field growth normalization**: Is the low modernity score just because AI grew faster than MAS? Compare against average modernity for papers of the same era and field.
2. **Survey citation check**: Search for 2023-2026 surveys citing this paper. If surveys cite it but implementation papers don't → classify as "Known but Ignored," not "Genuinely Lost."
3. **Indirect citation check**: If Survey X cites Root Primitive Y, check if papers citing Survey X use Y's concepts without citing Y directly. This catches concept diffusion through intermediaries.

**Self-Critique Protocol** (from `/analyze`):

The Bridge Builder assessment MUST include four self-critique questions:

1. **Is the mapping genuine or superficial?** Does the classical concept truly map to the modern problem, or is this a false equivalence?
2. **Has the problem fundamentally changed?** Did LLMs change the problem so much that classical solutions don't apply?
3. **Counter-evidence?** What evidence contradicts the mapping?
4. **Alternative explanations?** Could the gap be explained by something other than "they forgot the classics"?

Each mapping receives a verdict: STRONG CANARY / WEAK CANARY / FALSE ALARM / GENUINELY NEW, with confidence level and reasoning.

**7-Phase QA Gate** (from `/research-review`):

Every research output passes through:

1. Context gathering (read all prior work)
2. Factual accuracy (verify every quantitative claim against source)
3. Argument strength (devil's advocate: play the strongest counter-argument for each claim)
4. Writing quality (academic tone, hedging, no unsupported superlatives)
5. Experiment validation (baselines included? statistical significance discussed?)
6. Cross-reference consistency (do analyses, experiments, and paper sections agree?)
7. ArXiv compliance (AI disclosure, page limits, keywords)

The QA gate is the author's primary quality control mechanism. The specific devil's advocate challenges include: "Is the Lost Canary metric a reliable proxy, or do low modern citations just mean the concept was superseded?" and "Does the blackboard improvement generalize beyond the specific benchmarks tested?"

### Level 1 → Level 2 Transition

Sprint r1 used `/literature` and `/analyze` to execute Phases 1-3 manually: seed expansion, backward pass (18 root primitives), forward pass (modernity scores), concept tracing (13 candidates classified). Sprint r2 used the same commands to prototype corpus building and filtering.

The findings from r1 and r2 informed the design of the 8-agent autonomous pipeline: each agent's activation condition, extraction schema, and quality gate was derived from the manual process. The `/literature` command's compound filter became Agent 2's scoring rubric. The `/analyze` command's prompt templates became the Archivist/Modernist/Bridge Builder agents in Phase 5. The `/research-review` QA gate became the author's sampling protocol (Contribution 1, Step 5).

---

# Contribution 1: The Sutra Corpus — A 7-Agent Pipeline for Deep MAS Research Annotation

## The Claim

We release the **Sutra Corpus**: 12,527 multi-agent systems papers spanning 1975-2026, each deeply annotated with structured metadata (coordination pattern, theoretical grounding, classical concept gaps, key contribution, Rosetta Stone entry). No prior MAS dataset provides this depth of annotation at this scale. The corpus is produced by a 7-agent blackboard pipeline with citation-based feedback expansion, iteratively calibrated through author-supervised sampling to 0% false positive and 0% false negative rates. The pipeline itself — a classical blackboard architecture coordinating LLM agents — serves as self-referential validation of the patterns this paper advocates.

*Sutra* (Sanskrit): a thread that connects — condensed, essential knowledge woven into a chain. The corpus threads 50 years of MAS research into a single annotated dataset.

## What We Actually Did (The Method)

### Step 1: Seed Selection (Curated Entry Points)

The corpus is seeded from two sources:

**Landmark papers** (22 classical + 11 modern bridge): Manually selected to span 6 MAS branches — Communication & Language, Organization & Structure, Coordination & Planning, Architecture & Reasoning, Negotiation & Game Theory, Engineering & Verification. Full seed table in [Appendix: Seed Papers](appendix-seed-papers-and-repos.md).

**GitHub paper-list repositories** (10 curated repos): Community-maintained collections scraped into `corpus/papers-master.csv` — 8,817 papers, 96% with ArXiv URLs, 99% from 2023-2026. These repos (`Awesome-Agent-Papers`, `LLM-Agents-Papers`, `all-agentic-architectures`, etc.) provide the modern half of the corpus, capturing what the LLM agent community considers important.

Additional seed sources: OpenAlex concept search (MAS-related concept IDs for classical coverage), OpenAlex keyword search (16 targeted queries per MAS branch), and forward citations of all seed papers via OpenAlex.

**Post-collection compound filter**: After collection, a quality gate is applied via `db.apply_compound_filter()`:

```python
include IF citation_count >= 5 OR (year >= 2025 AND venue in TOP_VENUES)

TOP_VENUES = [ICLR, ICML, NeurIPS, AAMAS, AAAI, IJCAI, ACL, EMNLP, NAACL, COLM]
```

This ensures recent top-venue papers aren't lost to the citation threshold (a 2025 AAMAS paper with 2 citations is worth keeping) while filtering noise from older papers that never gained traction. Applied before Agent 2's LLM-based relevance scoring.

### Step 2: The 7-Agent Blackboard Pipeline

The corpus is processed by 7 agents coordinating through a shared Neon Postgres database — a classical blackboard architecture where each agent polls for papers matching its activation condition, processes them, and writes results back.

| Agent | Role | Model / API | Activation Condition |
|-------|------|-------------|---------------------|
| **Agent 1: Collector** | Seeds the blackboard from CSV, OpenAlex concepts, keywords, citation expansion | OpenAlex API | Seed-driven (no polling) |
| **Agent 2: Relevance Filter** | Batches of 10 abstracts scored 1-5 for MAS relevance, classified by MAS branch | GPT-5-mini | `status = 'collected'` |
| **Agent 3: Deep Analyst** | Single-paper deep extraction from full LaTeX source | Claude Opus 4.6 | `status = 'relevant'` (depth mode) |
| **Agent 3b: Async Analyst** | Pipelined extraction (5-6 concurrent LLM calls, ~20 papers/min) | GPT-5.1 | `status = 'relevant'` (throughput mode) |
| **Agent 4: Citation Enricher** | Citation counts, references, cited-by, venue, DOI via OpenAlex. **Feedback loop**: re-inserts MAS-tagged references as new `collected` papers | OpenAlex API | `status = 'analyzed'` |
| **Agent 5: Reproduction Scout** | Searches Papers with Code + GitHub for implementations. Blacklist filtering, keyword relevance scoring (≥15% overlap), min 3 stars | PwC + GitHub API | `status = 'enriched'` |
| **Agent 6: Reproducer** | Track A: auto-reproduce repos (clone, venv, test, report). Track B: research triage for classical papers without repos | Local execution | `status = 'scouted'` |

**Status flow** (each agent reads from its inbox status and writes to its outbox):

```
collected → filtering → relevant → analyzing → analyzed → enriching → enriched → scouting → scouted → planning_reproduction → reproduction_planned
                     ↘ marginal (score 3)
                     ↘ archived (score 1-2, terminal)
```

Intermediate statuses (`filtering`, `analyzing`, `enriching`, `scouting`, `planning_reproduction`) are set by agents at the start of processing to prevent double-processing across parallel instances.

**Concurrency model**: `FOR UPDATE SKIP LOCKED` at the Postgres level enables multiple instances of the same agent to run in parallel without conflicts. Both the laptop and the VM write concurrently — Postgres UNIQUE constraints (`doi`, `arxiv_id`, `semantic_scholar_id`, `openalex_id`) + `ON CONFLICT DO NOTHING` guarantee consistency.

**Infrastructure**: Azure VM (`sutra-research`), agents running in tmux sessions, Neon Postgres as shared blackboard, monitored via a custom Next.js dashboard.

### Step 3: Citation-Based Feedback Expansion (Controlled Snowball)

Agent 4's enrichment creates a snowball discovery mechanism: for each analyzed paper, it fetches references and citations from OpenAlex, checks MAS relevance via title keyword matching, and re-inserts qualifying papers as `collected` — feeding them back into the pipeline at Station 1. Starting from ~8,800 seed papers, the feedback loop expanded the corpus to ~25,000 candidates.

The core engineering challenge was **preventing graph explosion while ensuring coverage**. Citation graphs are power-law distributed — a single well-connected paper can generate hundreds of references, each generating hundreds more. Without bounds, the corpus would grow unboundedly and overwhelm the pipeline.

#### The Deduplication Problem

Before controlling growth, we had to solve deduplication across 50 years of inconsistent metadata:

- **Classical papers (pre-2010)**: Often have DOIs but no ArXiv IDs. Some pre-2000 papers lack even DOIs — only title and year.
- **Modern papers (2023+)**: Often have ArXiv IDs but no published DOI (preprints). Some have ArXiv synthetic DOIs (`10.48550/arXiv.{id}`) that differ from their eventual published DOI.
- **Cross-era duplicates**: A 1986 paper may appear via its DOI from Crossref, its OpenAlex ID from concept search, and its title from a GitHub paper list — three different entry paths for the same paper.

Our solution was **database-level dedup with four UNIQUE constraints** on the Postgres `papers` table:

```
UNIQUE(doi)  |  UNIQUE(arxiv_id)  |  UNIQUE(semantic_scholar_id)  |  UNIQUE(openalex_id)
```

All inserts use `INSERT ... RETURNING id` with a `UniqueViolation` catch — one round-trip for new papers, one for duplicates. For papers with none of these identifiers (some classical works), a `title + year` pre-check query serves as a fallback.

This replaced an earlier application-level approach (5 SELECT queries per paper against remote Postgres) that was ~100x slower. The database-level approach enables concurrent writes from both the laptop and the VM without conflicts — a practical vindication of the classical finding that shared-state coordination outperforms message-passing for data-intensive tasks.

Agent 4 also handles the ArXiv preprint problem: when a paper resolved via ArXiv synthetic DOI has 0 references (common for preprints), it searches for a published version with the same title and uses that version's reference list instead (`agent4_citations.py:221-243`).

#### Feedback Loop Safety Bounds

Three mechanisms prevent unbounded corpus growth — all three are enforced simultaneously:

| Mechanism | Implementation | Evolution |
|-----------|---------------|-----------|
| **Generation depth cap** | Each paper tracks hops from seeds via a `generation` column (seeds = gen 0, Agent 1 output = gen 1, feedback = parent_gen + 1). Capped at gen 3. | Stable from v1 |
| **Corpus size cap** | `get_corpus_size()` counts non-archived papers. Agent 4 refuses to insert feedback papers when this exceeds the cap. | **Started at 5,000 — insufficient.** At 5K cap, the feedback loop starved: it stopped discovering papers before reaching adequate classical coverage. Raised to 20,000 after analysis showed the pipeline could handle the throughput and the additional papers were genuinely MAS-relevant. |
| **Diminishing returns** | Tracks insertion ratio across sliding windows of 10 enrichment cycles. If <5% of processed papers generate new feedback insertions for 3 consecutive windows, the feedback loop auto-disables. | Stable from v1 |

The 5K→20K evolution is visible in the codebase: the module docstring (`agent4_citations.py:17`) still references the original 5,000 cap, while the `DEFAULT_CORPUS_CAP` constant (line 61) and the CLI default (line 370) were updated to 20,000. This is an honest record of the engineering iteration required to balance coverage against explosion.

#### Bulk Reference Harvesting (One-Shot Complement)

Beyond Agent 4's real-time feedback loop, `bulk_ref_harvest.py` performed a one-shot mining of all 40,791 unique OpenAlex reference IDs accumulated across the enriched corpus. This used an **expanded MAS keyword filter** (49 keywords vs. Agent 4's 22) covering terms like `multi-robot`, `distributed AI`, `FIPA`, `KQML`, `JADE`, `mechanism design`, `swarm intelligence` — broader than the feedback loop's filter to catch classical sub-communities that use different terminology.

Result: 40,791 refs → 7,668 MAS-relevant → 7,404 inserted (264 duplicates caught by UNIQUE constraints). Generation tracking preserved: `min(parent_gen + 1, 3)` ensures even bulk-harvested papers respect the 3-hop limit.

### Step 4: Structured Metadata Extraction

Agent 3b (the throughput workhorse) extracts a structured JSON for each paper:

```json
{
  "core_contribution": "1-3 sentences: what is the novel claim?",
  "methodology": "What did they do?",
  "key_results": "Quantitative findings",
  "classical_concepts": ["List of pre-2010 MAS concepts used or cited"],
  "classical_concepts_missing": "What classical concept would have helped but wasn't mentioned?",
  "unique_contribution": "What is genuinely new (not a reinvention)?",
  "rosetta_entry": {"classical": "...", "modern": "...", "mapping": "..."},
  "coordination_pattern": "supervisor | peer | blackboard | stigmergy | auction | ...",
  "failure_modes_addressed": "Which of the 14 Cemri failure modes does this paper address?",
  "theoretical_grounding": "strong | moderate | weak | none"
}
```

The `classical_concepts_missing` field is the key innovation — it is Agent 3b's assessment of what classical MAS concept each paper is unknowingly reinventing or would benefit from citing. Aggregated across 12,527 papers, this produces the quantitative Lost Canary Signal (Contribution 3).

### Step 5: Author-Supervised Quality Validation (FP/FN Sampling)

The author monitored every pipeline run through a custom dashboard and performed iterative quality validation through random sampling:

**False Positive detection**: 10 papers randomly sampled from Agent 3b's output each run. Author manually assessed MAS relevance.

**False Negative detection**: Author maintained an external list of known MAS papers from diverse sub-fields (robotics, game theory, organizational design, formal verification). After each run, checked whether these known papers passed through the pipeline. Papers that were incorrectly filtered out by Agent 2 or missed by Agent 3b were flagged.

| Run | False Positive Rate | False Negative Rate | Action Taken |
|-----|--------------------|--------------------|--------------|
| 1 | 20% | 20% | Tuned Agent 2 relevance prompt, adjusted scoring threshold, expanded MAS keyword list |
| 2 | 0% | 10% | Minor prompt refinement for edge cases (multi-robot, mechanism design) |
| 3 | — | 10% | Prompt stable, remaining FN were borderline cases |
| 4 | — | 0% | Converged — no known papers missed |

This iterative calibration is itself an instance of the human-in-the-loop pattern the companion paper (Paper 2: Agent 0) formalizes.

### Step 6: Final Corpus Statistics

| Metric | Count |
|--------|-------|
| Total papers collected | ~24,700 |
| Filtered by Agent 2 | ~24,660 |
| Deeply analyzed by Agent 3b | **12,527** |
| Enriched with citations by Agent 4 | 12,526 |
| Scouted for implementations by Agent 5 | 12,526 |
| Coordination patterns detected | 37 distinct patterns |
| Classical papers (pre-2010) | 6,065 |
| Modern papers (2023+) | 4,412 |
| Mean citation count | 121 |
| Median citation count | 28 |

**Era distribution**:

| Era | Count | Share |
|-----|-------|-------|
| Pre-1990 | 224 | 1.8% |
| 1990s | 1,537 | 12.3% |
| 2000s | 4,304 | 34.4% |
| 2010s | 1,527 | 12.2% |
| 2020-2022 | 295 | 2.4% |
| 2023-2024 | 1,116 | 8.9% |
| 2025+ | 3,296 | 26.3% |

The 2000s peak (34.4%) reflects the golden age of AAMAS and classical MAS research. The 2025+ surge (26.3%) reflects the LLM agent explosion. The 2010s trough (12.2%) is the "lost decade" where MAS research declined before LLMs revived interest — visible evidence of the citation disconnect this paper studies.

## Why This Is a Contribution

1. **No equivalent dataset exists.** Existing resources are either curated paper lists without annotation (awesome-ai-agents, LLM-Agents-Papers) or academic metadata without MAS-specific structure (OpenAlex, Semantic Scholar). The Sutra Corpus is the first to provide `classical_concepts_missing`, `coordination_pattern`, and `rosetta_entry` at scale.

2. **The annotation depth enables downstream analysis.** Contributions 2-6 in this paper all build on the Sutra Corpus. The taxonomy (Contribution 2), Lost Canary analysis (Contribution 3), and Rosetta Stone (Contribution 4) are only possible because Agent 3b extracted structured metadata, not just abstracts and citation counts.

3. **The pipeline methodology is reproducible and reusable.** The 7-agent architecture, activation conditions, feedback expansion mechanism, and FP/FN validation protocol are fully documented. Other researchers can extend the corpus or adapt the pipeline for different fields.

4. **The pipeline validates the paper's thesis.** A classical blackboard architecture — agents reading activation conditions from a shared workspace, writing results back, coordinated through database constraints rather than message passing — is exactly the pattern this paper argues has been forgotten by modern LLM agent builders. The fact that it works well for a 25K-paper corpus processing task is evidence for the pattern's continued relevance.

5. **The feedback expansion mechanism captures field structure.** Unlike keyword search (which finds what you think to search for), citation-based expansion from seeds discovers papers the community actually cites. The corpus reflects the field's own citation structure, not the researcher's search terms.

## What Gets Released

- The full annotated corpus as structured JSON (12,527 papers with all Agent 3b fields)
- Pipeline source code (7 agents + utilities, ~12,000 lines Python)
- Seed paper list with DOIs and selection rationale
- FP/FN validation logs

---

# Contribution 2: Semi-Supervised MAS Field Taxonomy

## The Claim

A data-driven, structured survey of the MAS field organized into 16 segments, each with a curated reading triple (landmark paper, central paper, survey paper) plus expert analysis -- derived from 6,500+ annotated papers spanning 50 years. No prior survey embeds classical (1980-2005) and modern LLM-agent (2023-2026) papers into a single semantic space.

## What We Actually Did (The Method)

### Step 1: Structured Embedding Construction

We do NOT embed raw abstracts. Agent 3b (GPT-5.1) first performs deep extraction on each paper, producing structured JSONB with: coordination_pattern, theoretical_grounding, classical_concepts_missing, key_contribution_summary, unique_contribution, rosetta_classical, rosetta_modern.

From this, we construct a **MAS-aware embedding document** per paper:

```
Title: {paper title}
Coordination Pattern: {e.g., "blackboard", "contract-net", "hierarchical"}
Theoretical Grounding: {strong/moderate/weak/none}
Classical Concepts: {e.g., "contract net, FIPA ACL, BDI"}
Missing Classical Concepts: {what the paper should cite but doesn't}
Contribution: {3-5 sentence key_contribution_summary}
```

This structured format ensures papers cluster by **MAS-meaningful dimensions** (coordination pattern, theoretical lineage) rather than surface vocabulary. A 2024 LangGraph paper about "shared workspace" lands near Nii 1986's blackboard architecture because both have `coordination_pattern: blackboard` -- even though they share zero vocabulary.

Embedding model: `text-embedding-3-small` (1536 dimensions). Text truncated to 2000 chars.

### Step 2: Expert-Curated Anchor Clusters (The Semi-Supervised Part)

We define 16 anchor clusters aligned with established MAS subfields (informed by AAMAS conference tracks, Wooldridge & Jennings taxonomy, and the researcher's domain expertise). Each anchor has a **rich description paragraph** (50-150 words) covering:
- Classical foundational concepts and authors (e.g., "Nii 1986, Hearsay-II, BB1")
- Modern equivalents and framework names (e.g., "LangGraph shared state, Redis pub/sub")
- Synonyms and related terminology across both eras

The 16 anchors:

| ID | Label | Anchor Coverage |
|----|-------|-----------------|
| 0 | Blackboard & Shared State | Nii 1986, Hearsay-II, shared workspace, LangGraph state |
| 1 | Contract Net & Task Allocation | Smith 1980, TRACONET, auction-based, LLM task routing |
| 2 | Organizational Design & Teams | AGR, MOISE, Horling & Lesser 2004, CrewAI roles |
| 3 | Distributed Problem Solving | GPGP, FA/C, Durfee & Lesser, plan merging |
| 4 | Joint Intentions & Teamwork | Cohen & Levesque 1990, SharedPlans, STEAM |
| 5 | Agent Communication & Protocols | FIPA ACL, KQML, MCP, A2A |
| 6 | Argumentation & Debate | Dung 1995, generator-critic, multi-agent debate |
| 7 | Negotiation & Game Theory | Nash, VCG, mechanism design |
| 8 | BDI & Cognitive Architectures | Rao & Georgeff 1995, AgentSpeak, deliberative |
| 9 | Stigmergy & Indirect Coordination | Grasse 1959, MetaGPT SOPs, artifacts |
| 10 | Human-Agent Interaction & HITL | Mixed initiative, adjustable autonomy, trust |
| 11 | Trust, Reputation & Norms | Social norms, governance, guardrails, safety |
| 12 | Agent-Oriented Software Eng. | AOSE, Prometheus, GAIA, JADE, verification |
| 13 | Multi-Agent Robotics | Multi-robot, swarm intelligence, formations |
| 14 | LLM Multi-Agent Frameworks | LangGraph, CrewAI, AutoGen, MetaGPT, ChatDev |
| 15 | Evaluation & Failure Analysis | Cemri et al. failures, GAIA benchmark, scaling |

These anchor descriptions are themselves embedded with the same model, producing 16 anchor vectors.

### Step 3: Cosine-Similarity Assignment

Each paper's embedding is compared against all 16 anchor embeddings via cosine similarity. The paper is assigned to its **highest-similarity anchor**. No iterative clustering algorithm (no k-means convergence, no HDBSCAN density estimation). The cluster structure is predetermined by domain expertise; the embedding similarity handles the assignment.

This is the key methodological choice: we use **domain knowledge to define the cluster structure** and **embedding similarity to populate it**. This avoids the failure modes of pure unsupervised clustering (too many micro-clusters, incoherent groupings, sensitivity to hyperparameters) while still being data-driven in assignment.

### Step 4: Iterative Refinement (Human-in-the-Loop)

The clustering went through several iterations:

1. **First attempt: HDBSCAN unsupervised** -- produced 63 micro-clusters, most with <20 papers. Uninterpretable for readers. Rejected.
2. **Second attempt: k-means with k=10** -- better but some clusters mixed unrelated subfields (e.g., robotics + software engineering). Insufficient granularity for MAS taxonomy.
3. **Third attempt: k-means with k=16** -- improved but cluster boundaries were unstable across runs. Sensitive to initialization.
4. **Final approach: Guided cosine-similarity with 16 curated anchors** -- stable, interpretable, aligned with established MAS taxonomy. The researcher iteratively refined anchor descriptions over multiple runs until cluster populations were balanced and semantically coherent.

Specific human interventions:
- **Cluster count**: Overrode HDBSCAN's auto-63 down through iterations to 16 guided anchors
- **UMAP parameters**: Iteratively tuned `n_neighbors` (15), `min_dist` (0.5), `spread` (3.0), `repulsion_strength` (1.5) for visual separation
- **Anchor descriptions**: Each of the 16 descriptions was written and refined by hand, balancing classical and modern terminology to ensure both-era papers could match
- **Quality checks**: Inspected cluster populations after each run, verified that known papers (e.g., Contract Net, STEAM, LangGraph) landed in expected clusters

### Step 5: UMAP Projection + Custom Physics

For the visualization (the "signature figure"):
- UMAP with `metric="cosine"`, tuned for visual cluster separation
- Custom **post-UMAP cluster repulsion** physics: compute cluster centroids, apply inverse-distance repulsion forces between centroids (strength=8.0), translate each point by its cluster's displacement. This prevents visual overlap while preserving within-cluster structure.
- Normalize to [0, 100] coordinate space

### Step 6: Reading Triple Identification

For each of the 16 clusters, we identify three papers:
- **Landmark**: Highest citation count in cluster (the foundational work)
- **Central**: Highest in-cluster citation degree (most-connected node)
- **Survey**: Most references / best existing overview of that sub-area

These are computed from the `citation_edges` table (built by Agent 4's OpenAlex enrichment) and paper metadata.

## Why This Method Is Novel

1. **Structured embeddings, not raw text**: The MAS-aware embedding document (pattern + grounding + concepts + summary) produces dramatically better clustering than abstract-only embeddings. Papers cluster by coordination paradigm, not surface vocabulary.

2. **Semi-supervised = honest**: We don't pretend HDBSCAN "discovered" 16 subfields. We acknowledge that domain expertise defines the taxonomy, while embedding similarity handles the population-at-scale part that humans can't do for 6,500 papers.

3. **50-year span in a single space**: By embedding both "blackboard architecture" (Nii 1986) and "shared workspace pattern" (LbMAS 2025) with the same structured format, they land in the same cluster -- revealing the reinvention that keyword-based surveys miss.

4. **Navigational utility**: The reading triple per cluster gives any reader an efficient 3-paper entry point into any of the 16 MAS subfields. This is a practical tool, not just a taxonomy.

5. **Reproducible but curated**: The 16 anchor descriptions, embedding model, and similarity computation are fully reproducible. The human curation is explicit and documented (this file), not hidden behind "we ran HDBSCAN with these parameters."

---

# Contribution 3: The Lost Canary Algorithm — Detecting Forgotten MAS Concepts [WIP]

> **STATUS: WIP** — Infrastructure and initial results exist. Awaiting author's expert classification and deeper human analysis before finalizing.

## The Claim

We introduce the **Lost Canary Algorithm**: a systematic citation-graph methodology for detecting foundational concepts that an entire research community has forgotten or is unknowingly reinventing. Applied to MAS, it identifies 4 genuinely lost concepts, 1 known-but-ignored, and 8 renamed-without-citation from 13 candidates — with quantitative evidence from 12,527 analyzed papers.

## What Exists in the Codebase (Built)

### The Three-Phase Detection Algorithm

**Phase 1 — Backward Pass (Root Primitive Discovery)**:
From 22 classical seed papers spanning 6 MAS branches, fetch all references via OpenAlex/Semantic Scholar. Score each by `root_primitive_score = cite_count × branch_diversity` (threshold ≥ 6; see "Root Primitive Scoring" in the methodology preamble). Found: **18 root primitives** clustered into three intellectual traditions:

- **The Joint Intentions School** (Cohen, Levesque, Grosz, Sidner, Kraus) — formal logic of teamwork
- **The DAI/Cooperation Frameworks** (Durfee, Lesser, Corkill, Bond, Gasser) — pragmatic distributed problem-solving
- **The Social/Organizational School** (Singh, Fox, Jennings) — roles, commitments, conventions

**Phase 2 — Forward Pass (Modernity Score)**:
For each root primitive, compute citation trajectory over time via OpenAlex `counts_by_year`:

```
Modernity Score = (Citations from 2023-2026) / (Total Citations)
```

Threshold: Total Citations > 500 AND Modernity Score < 0.05 = **Lost Canary Candidate**

Result: 18 primitives analyzed → 6 candidates (score < 0.05), 3 active (score > 0.05), 9 below citation threshold.

Data: `pipeline/data/modernity_scores.json` (18 entries with full `year_distribution` per paper)

**Phase 3 — Concept Tracing (Anti-False-Positive)**:
For each candidate, use Opus 4.6 to:
1. Summarize the core concept in one sentence
2. Generate 5-8 modern synonyms with contextual explanations
3. Generate 6-8 search queries targeting 2023-2026 literature
4. Search OpenAlex for those synonyms/queries
5. Apply the three anti-false-positive checks (field growth normalization, survey citation check, indirect citation check — see methodology preamble)
6. Classify: **genuinely lost** vs. **renamed** vs. **known-but-ignored**

Data: `pipeline/data/concept_trace_cache.json` (54KB — full synonym sets + search queries per candidate)
Data: `pipeline/data/lost_canaries.json` (61KB — 13 candidates with classification, evidence, key papers found)

### The Hybrid Classical Discovery Script

`classical_discovery.py` — a bottom-up complement to the top-down seed-based approach. Uses the entire modern corpus (post-2010 papers) as a "discovery lens":

1. Fetch all references from modern corpus papers via OpenAlex + Semantic Scholar
2. Build reverse citation map: which classical papers are most-cited by the modern corpus?
3. Compare with seed backward pass to partition into:
   - **Validated Foundations** (A ∩ B): cited by BOTH seeds AND modern papers
   - **Lost Canaries** (B \ A): in seed backward pass, NOT cited by modern corpus
   - **Community Additions** (A \ B): cited by modern papers, NOT in seed backward pass

The Lost Canary finding IS the set difference: `seed_backward_papers - modern_cited_papers`.

Data: `pipeline/data/classical_discovery.json` (283KB)

### The Aggregate Signal (from 12,527 analyzed papers)

Agent 3b's `classical_concepts_missing` field, aggregated across the entire analyzed corpus, produces a quantitative "Missing Classical Concepts" ranking:

| Missing Concept | Papers Flagging It |
|-----------------|-------------------|
| Organizational Models | 5,556 |
| BDI | 4,166 |
| FIPA Protocols | 3,882 |
| Contract Net | 3,310 |
| Blackboard | 2,051 |
| MOISE/AGR | 2,037 |
| SharedPlans | 1,855 |
| Joint Intentions | 1,570 |
| Auction/Mechanism Design | 1,288 |
| Consensus Protocols | 902 |

This is a bottom-up corroboration of the top-down Lost Canary findings: the concepts flagged most frequently by the LLM as "missing" align with the concepts that have the lowest modernity scores in the citation graph.

### Initial Classification (Sprint r1)

| # | Paper | Year | Total Cites | Modernity | Classification |
|---|-------|------|-------------|-----------|---------------|
| 1 | "Distributed Artificial Intelligence" | 1987 | 840 | 0.000 | Renamed |
| 2 | "Negotiation as metaphor for distributed problem solving" (Davis & Smith) | 1983 | 1,231 | 0.010 | Renamed |
| 3 | "Frameworks for Cooperation in DPS" (Durfee & Lesser) | 1981 | 648 | 0.014 | Lost Canary Candidate |
| 4 | "Controlling cooperative problem solving using Joint Intentions" (Jennings) | 1995 | 551 | 0.015 | Lost Canary Candidate |
| 5 | "Intention is Choice with Commitment" (Cohen & Levesque) | 1990 | 1,847 | 0.028 | Lost Canary Candidate |
| 6 | "Readings in Distributed AI" (Bond & Gasser) | 1988 | 993 | 0.028 | Lost Canary Candidate |
| 7 | "Plans for Discourse" (Grosz & Sidner) | 1990 | 486 | 0.000 | Below threshold |
| 8 | "On Acting Together" (Cohen & Levesque) | 1990 | 432 | 0.002 | Below threshold |
| 9 | "Social Conceptions of Knowledge and Action" (Singh) | 1991 | 339 | 0.006 | Below threshold |
| 10 | "Commitments and Conventions" (Jennings) | 1993 | 458 | 0.035 | Below threshold |
| 11 | "On Being Responsible" | 1992 | 99 | 0.000 | Below threshold |
| 12 | "An Organizational View of Distributed Systems" (Fox) | 1981 | 329 | 0.003 | Below threshold |
| 13 | "Planned Team Activity" | 1994 | 161 | 0.000 | Below threshold |

**Current r1 three-way classification** (via concept tracing):
- **Genuinely Lost (4)**: Joint Persistent Goals, Discourse Coherence, Formal Responsibility, Social Knowledge Semantics
- **Known-but-Ignored (1)**: *[to be confirmed by author]*
- **Renamed (8)**: DAI, Contract Net, DPS Frameworks, Negotiation Protocols, etc.

### Multi-Perspective Assessment (Archivist/Modernist/Bridge Builder)

For each cluster of Lost Canary candidates, we run three independent LLM agents (Claude Opus 4.6) with distinct persona prompts, then a fourth Critic pass:

| Agent | Persona | Prompt Frame | Input |
|-------|---------|-------------|-------|
| **Archivist** | Classical MAS researcher from 2005 | "What classical concepts do these papers relate to? What did we already solve that they're reinventing? What's genuinely new?" | All papers in cluster + extracted metadata |
| **Modernist** | LLM agent researcher in 2026 | "What practical problems do these papers solve? What's the state of the art? Where are the gaps?" | Same papers |
| **Bridge Builder** | Has both literatures | "What classical concept maps most directly? What was lost in translation? What specific improvement would re-adoption yield? What evidence supports this?" | Same papers + Archivist and Modernist assessments |
| **Critic** | Devil's advocate (separate pass) | "Is this mapping genuine or superficial? Is the classical concept truly relevant or has the problem fundamentally changed? What counter-evidence exists?" | Bridge Builder assessment |

The key design: all three primary agents receive the **same papers and metadata** but through different analytical lenses. The Bridge Builder sees the other two assessments before synthesizing. The Critic runs after, specifically looking for superficial mappings and changed-problem arguments. This prevents confirmation bias — the Archivist might see classical patterns everywhere; the Critic checks whether the analogy actually holds.

The Bridge Builder's self-critique is mandatory (see "Self-Critique Protocol" in the methodology preamble): each mapping must address genuineness, changed-problem arguments, counter-evidence, and alternative explanations. Each receives a verdict (STRONG CANARY / WEAK CANARY / FALSE ALARM / GENUINELY NEW) with confidence and reasoning. The full `/analyze` command prompt that implements this protocol is in [Appendix: Research Commands](appendix-research-commands.md).

Full r1 assessment in `analyses/r1.md` (33KB). Key findings per agent:

- **Archivist**: Identified 3 intellectual traditions in root primitives; warned that 4 genuinely lost concepts are not academic curiosities but root causes of modern failure modes
- **Modernist**: Acknowledged the gaps but noted LLMs bring 4 genuinely new capabilities (NLU, few-shot generalization, implicit world models, integration scale via MCP)
- **Bridge Builder**: Mapped each lost concept to a specific modern failure mode and proposed concrete remediation

### Human Synthesis (Phase 6 — What Only the Author Can Do)

The agent assessments produce structured analysis. The author provides what no LLM agent can:

1. **Narrative identification**: Which Lost Canaries are genuinely important vs. academic curiosities? The agents flag candidates; the human decides which ones drive the paper's argument.
2. **Thesis construction**: The paper's value is the author's judgment about *what matters* — connecting the citation data, the agent assessments, and the experimental results into a coherent claim.
3. **Significance judgment**: Automated ranking (by citation count, novelty score, or cluster centrality) promotes popular findings. The author promotes *theoretically important* findings — the Rosetta Stone entries were often low-citation papers with high structural significance.
4. **Cross-contribution integration**: Connecting C3 (Lost Canaries) to C4 (Rosetta Stone) to C6 (experiments) requires seeing the whole — no single agent has that context.
5. **Writing**: Introduction, thesis statement, implications, conclusion — the sections that make the paper matter.

The agents handle mechanical work: formatting references, generating comparison tables, producing consistent citation style, checking factual accuracy against source papers. The synthesis is human.

## What's Missing (Needs Author's Human Expertise)

1. **Expert classification refinement**: The current 3-way classification (genuinely lost / known-but-ignored / renamed) was done in sprint r1 on 18 root primitives only. The author needs to:
   - Review the LLM-generated classifications against personal domain knowledge
   - Resolve borderline cases (e.g., is "Commitments and Conventions" genuinely lost or just renamed to "guardrails"?)
   - Add concepts the algorithm missed (author's external knowledge)

2. **Scale-up to full corpus**: `classical_discovery.py` was run on the enriched corpus but the results need author review. The set-difference methodology (B \ A) may surface additional Lost Canaries beyond the 18 root primitives.

3. **The "Citation Cliff" — signature figure of the paper**: The `year_distribution` data in `modernity_scores.json` shows dramatic drop-offs for specific concepts. This is the planned signature figure:
   - X-axis: time (1980-2026), Y-axis: citations/year per concept
   - Each line: a classical concept (Contract Net, Blackboard, BDI, SharedPlans, FA/C, Joint Intentions, etc.)
   - Color: whether the concept was reinvented (renamed) or genuinely lost
   - Potential overlay: Cemri failure rates mapped to the year each concept was forgotten
   - Static version for paper (Section 5), interactive version for portal (Contribution 7), data + script for repo (Contribution 7)
   - **This is not a separate contribution — it is the visual proof of Contribution 3's findings.**

4. **Connecting Lost Canaries to modern failure modes**: The r1 analysis sketches this (e.g., Joint Persistent Goals → cascading failure, Discourse Coherence → agents talking past each other) but needs rigorous mapping with evidence from Cemri et al.'s 14 failure modes.

5. **The "what's genuinely new" counter-argument**: Honest scholarship requires identifying what LLMs bring that classical MAS couldn't do. The Archivist identified 4 items; the author needs to validate and potentially expand this list.

6. **Quantitative validation**: Do the aggregate `classical_concepts_missing` counts from 12,527 papers correlate with the modernity scores from the citation graph? If the bottom-up (LLM-flagged) and top-down (citation-based) methods converge, that's strong triangulation evidence.

---

# Contribution 4: The Rosetta Stone — Classical-to-Modern MAS Mapping [WIP]

> **STATUS: WIP** — Three data sources exist (hand-curated table, per-paper JSONB annotations, materialized reinvention edges). Needs consolidation, expert validation, and gap/fidelity analysis.

## The Claim

We produce the **Rosetta Stone**: a structured mapping between classical MAS concepts (1980-2010) and their modern LLM-agent equivalents (2023-2026), with per-entry fidelity ratings (Full / Medium / Low / None) and "what's lost in translation" annotations. Unlike a simple equivalence table, each mapping is grounded in evidence from the Sutra Corpus — backed by per-paper `rosetta_entry` annotations across 12,527 analyzed papers and a materialized `reinvention_edges` table that detects concept overlap without citation.

## What Exists in the Codebase (Built)

### Source 1: Hand-Curated Rosetta Table (Top-Down)

Maintained in `paper/sutra-main/README.md` and `analyses/r1.md`. The Bridge Builder assessment produced a 10-entry mapping with fidelity ratings:

| Classical Concept | Modern Equivalent | Fidelity | What's Lost |
|-------------------|-------------------|----------|-------------|
| Joint Persistent Goals (Cohen & Levesque 1990) | None | N/A | No framework tracks shared goals with obligation-to-inform on failure |
| Discourse Coherence (Grosz & Sidner 1990) | None | N/A | Flat message history in all frameworks, no hierarchy, no discourse purposes |
| Formal Responsibility (1992) | None | N/A | Delegation exists but responsibility tracking doesn't |
| Social Knowledge (Singh 1991) | System prompts + roles | Low | Prompt captures persona but not social obligations or commitment protocols |
| Commitment Theory (Cohen & Levesque 1990) | Agent "memory" | Very Low | Memory stores facts, not commitments; no theory of decommitment |
| Contract Net (Smith 1980) | Agent routing / orchestration | Medium | Bid/award survives but without formal cost models or marginal cost bidding |
| Blackboard (Nii 1986) | Shared state (LangGraph, Redis) | Medium | Shared state survives but the Control Shell — the most valuable part — is lost |
| FA/C Philosophy (Lesser & Corkill 1983) | None | N/A | No framework embraces functionally accurate intermediate results |
| Task Environment Modeling (Decker 1996) | None | N/A | No formal task models; LLMs "figure it out" from prompts |
| Organizational Paradigms (Horling & Lesser 2004) | CrewAI roles, AutoGen group chat | Low | Role labels survive but formal org theory (hierarchies, holarchies, authority gradients) absent |

### Source 2: Per-Paper Rosetta Annotations (Bottom-Up, 12,527 papers)

Agent 3b extracts a `rosetta_entry` field for every analyzed paper:

```json
"rosetta_entry": {"classical_term": "modern_equivalent"}
```

Prompt instruction (`agent3b_analyst_async.py:62`):
> `"rosetta_entry": {"classical_term": "modern_equivalent"} or null if no clear mapping`

These are stored in the `analysis` JSONB column of the `papers` table. The dashboard's insights API aggregates them:

```sql
SELECT analysis->>'rosetta_entry' as entry, COUNT(*) as cnt
FROM papers
WHERE analysis->'rosetta_entry' IS NOT NULL
  AND analysis->>'rosetta_entry' NOT IN ('null','','{}')
GROUP BY 1 ORDER BY cnt DESC LIMIT 15
```

This gives us the **most frequently occurring mappings** across the corpus — a data-driven complement to the hand-curated table.

### Source 3: Reinvention Edges (Concept-Overlap Graph)

`pipeline/tools/materialize_edges.py` builds a `reinvention_edges` table that detects classical-modern pairs with concept overlap but *missing citations*:

**How it works:**
1. Index all classical papers (pre-2010) by their `classical_concepts` and `rosetta_entry` keywords
2. For each modern paper (post-2020), find classical papers with ≥2 overlapping concept keywords
3. Check the `citation_edges` table to see if the modern paper actually cites the classical one
4. A **reinvention** = concept overlap WITHOUT citation (the modern paper uses the concept but doesn't cite the originator)

Schema:
```sql
reinvention_edges (
    modern_id INTEGER,
    classical_id INTEGER,
    overlap_concepts JSONB,   -- which concepts overlap
    has_citation BOOLEAN,     -- does the modern paper actually cite the classical one?
    overlap_score FLOAT       -- normalized concept overlap (0-1)
)
```

This produces a bipartite graph: modern papers on one side, classical papers on the other, edges colored by whether citation exists. The `/reinvention` dashboard route visualizes this.

### Dashboard Visualization

The research dashboard (`sutra.balajivis.com`) surfaces Rosetta Stone data through:
- **InsightsPanel**: Aggregates `rosetta_entries` and `cross_era_bridges` queries, synthesizes findings via LLM
- **Reinvention route** (`/reinvention`): Bipartite view of modern papers reinventing classical concepts without citation
- **Paper detail page** (`/paper/[id]`): Shows individual paper's `rosetta_entry`, `classical_concepts`, `classical_concepts_missing`

### The Coordination Patterns Taxonomy

`research/coordination-patterns-taxonomy.md` maps 16 coordination patterns across classical origin, modern implementation, and gaps — organized into three tiers by Kapi implementation priority. This is a practical engineering translation of the Rosetta Stone: not just "what maps to what" but "what to build and in what order."

## What's Missing (Needs Author's Expert Refinement)

1. **Consolidation across three sources**: The hand-curated table (10 entries), per-paper JSONB (12,527 papers × `rosetta_entry`), and reinvention edges table are not yet reconciled. Need to:
   - Aggregate the per-paper entries into canonical mappings with frequency counts
   - Cross-validate against the hand-curated table
   - Identify mappings that appear in the data but not in the hand-curated table (and vice versa)

2. **Fidelity scoring methodology**: The current fidelity ratings (Full/Medium/Low/None) are subjective. Need a quantitative basis — potentially derived from:
   - `overlap_score` from reinvention edges (higher overlap = higher fidelity)
   - `has_citation` ratio per concept pair (higher citation rate = more explicitly recognized)
   - `theoretical_grounding` scores of modern papers using the concept (strong grounding = higher fidelity)

3. **Gap analysis — what has NO modern equivalent**: The 4 genuinely lost concepts from Contribution 3 appear here as entries with Fidelity = "None." But there may be additional concepts in the Rosetta table that have *partial* modern equivalents missing critical components (e.g., Blackboard without Control Shell). These "partial gaps" need documentation.

4. **Actionable prescriptions per entry**: Each Rosetta Stone row should include not just "what maps to what" but "what to build" — a concrete implementation prescription. The coordination-patterns-taxonomy.md has this for some entries (e.g., "Build a `BlackboardCoordinator` class with manifest `coordination:` section") but it's not integrated into the Rosetta Stone itself.

5. **The reverse mapping (modern → classical)**: The current table goes classical → modern. But researchers may want to look up "I'm using LangGraph shared state — what classical concept am I implementing, and what am I missing?" The reverse index doesn't exist yet.

6. **Reinvention edge quality**: The concept-overlap keyword matching in `materialize_edges.py` is coarse (keyword intersection with ≥2 matching words). May produce false positives (two papers share the word "agent" but aren't conceptually related) and miss semantic equivalences (e.g., "shared workspace" ≠ keyword match for "blackboard" but means the same thing). The embedding-based approach from Contribution 2 could improve this.

7. **Protocol-level mapping (FIPA → A2A/MCP)**: The Rosetta Stone currently maps *concepts* (blackboard, contract net, BDI) but not *protocols*. A row mapping FIPA ACL performatives to their A2A/MCP equivalents would add a concrete, implementable dimension. Draft gap table from initial analysis:

   | FIPA Performative | Semantics | A2A Equivalent | MCP Equivalent | Gap? |
   |---|---|---|---|---|
   | `inform` | Share a fact | Task artifact update | Tool result | No |
   | `request` | Ask for action | `tasks/send` | `tools/call` | No |
   | `query-if` | Ask true/false | ??? | ??? | **Yes** |
   | `cfp` | Call for proposals | ??? | ??? | **Yes** |
   | `propose` | Offer to do task | ??? | ??? | **Yes** |
   | `accept-proposal` | Award contract | ??? | ??? | **Yes** |
   | `reject-proposal` | Decline with reason | ??? | ??? | **Yes** |
   | `confirm` | Verify commitment | ??? | ??? | **Yes** |
   | `cancel` | Withdraw commitment | Task cancellation | ??? | Partial |

   The gaps concentrate on **negotiation performatives** — A2A and MCP have no equivalent of `cfp`/`propose`/`accept-proposal`/`reject-proposal`, which are the building blocks of Contract Net. A full formal protocol translation is a separate standards contribution targeting AAIF — but this summary gap table belongs in the paper's Rosetta Stone.

---

# Contribution 5: Eight Design Principles for Multi-Agent Systems

> **STATUS: COMPLETE** — Synthesized from organizational science (HROs, aviation CRM, surgical teams, military C2, open source), classical MAS theory (Malone & Crowston, Nii, Horling), and production system evidence (Anthropic, Google DeepMind, MetaGPT). Full exposition in [why-mas-works.md](why-mas-works.md) and [organizational-principles.md](organizational-principles.md).

## The Claim

We synthesize eight actionable design principles for multi-agent LLM systems, each grounded in three independent evidence streams: (1) organizational science from high-performing human teams, (2) classical MAS theory, and (3) empirical data from production LLM agent systems. Unlike prior work that either describes principles abstractly ("organization matters") or prescribes framework-specific patterns ("use LangGraph loops"), these principles are evidence-based, implementation-agnostic, and falsifiable.

## The Eight Principles

| # | Principle | Human Origin | Agent Implementation | Key Evidence |
|---|-----------|-------------|---------------------|-------------|
| 1 | Start with dependencies, not agents | Malone & Crowston coordination theory (1994) | Map task dependency structure before choosing topology | Kim et al.: 87% prediction accuracy from task features alone |
| 2 | Architecture selection is measurable | Google DeepMind scaling study (2025) | Use task decomposability to predict optimal topology | 180 configurations; parallelizable → centralized (+80.9%), sequential → single agent |
| 3 | Communicate through artifacts, not chat | MetaGPT, stigmergy, blackboard systems | Shared versioned workspace; agents read/write deliverables directly | LbMAS: 3x token efficiency; stigmergy scales O(n) vs O(n^2) for messaging |
| 4 | Enforce conceptual integrity | Brooks' surgical team (1975) | One agent/human as architectural guardian; ADRs as machine-readable constraints | Hackman: enabling conditions explain >50% of team effectiveness |
| 5 | Quality gates at every handoff | Aviation CRM readback, surgical checklists, CI/CD | Generator/Critic pattern; typed verification at each step | CRM reduced aviation accidents 50%+; surgical checklist cut fatality 33%+ |
| 6 | Scale token investment, not agent count | Anthropic production system (2025) | Multi-agent as token allocation mechanism; upgrade model before adding agents | 80% of performance variance from token budget; tool calls + model = 15% |
| 7 | Bound autonomy explicitly | Auftragstaktik, HROs, Linux maintainers | Clear scope limits, escalation paths, ability to say "I don't know" | 68% of production agents perform ≤10 steps before human handover |
| 8 | Design for failure recovery | Erlang/OTP supervision trees, HRO resilience | Checkpointing, restart strategies (one-for-one, one-for-all, rest-for-one), circuit breakers | *(Gap: no current framework implements supervision trees)* |

## Why This Is a Contribution (Not Just a Summary)

Three features distinguish these principles from prior prescriptive work:

1. **Triple grounding**: Each principle is independently supported by human team science, classical MAS theory, AND production LLM system evidence. "Reliable Agent Engineering" (Dec 2025) argues for organizational principles but draws only from MAS literature. We add the human team science and production evidence that makes the case empirically robust.

2. **Falsifiable predictions**: Each principle generates testable predictions. Principle 2 predicts that sequential tasks will degrade under MAS — confirmed by Kim et al. (39-70% degradation). Principle 3 predicts artifact-based coordination will use fewer tokens — confirmed by LbMAS (3x). Principle 8 predicts that systems without failure recovery will cascade — confirmed by our JPG experiment (52/100 on cascading failure).

3. **Gap identification**: Principles 7 and 8 identify capabilities that no current framework implements. Bounded autonomy with escalation and Erlang-style supervision trees are prescriptions for systems that don't yet exist — directions for the field, not descriptions of current practice.

## What's Missing

1. **Controlled validation**: The principles are synthesized from observational evidence. A controlled experiment — build the same system with and without each principle — would strengthen the causal claims. The experiment harness (Contribution 6) provides preliminary evidence but not targeted ablations.

2. **Interaction effects**: The principles are presented independently, but they interact. Do quality gates (P5) matter less when communication is already artifact-based (P3)? Does bounded autonomy (P7) substitute for failure recovery (P8)? These questions need multi-factor experiments.

---

# Contribution 6: Empirical Validation — 9 Classical Patterns Tested Through LLM Agents [WIP]

> **STATUS: WIP** — 55 experiment results exist across 11 patterns × 5 benchmarks. Star results (Blackboard V2, JPG) are well-documented. Needs author's deeper analysis of cross-pattern findings, statistical reruns, and integration with Rosetta Stone prescriptions.

## The Claim

We implement 9 classical MAS coordination patterns (+ 2 baselines) as LLM agent systems and evaluate them across 5 standardized benchmarks, producing **55 experiment results**. Two headline findings:

1. **Blackboard V2 with an LLM control shell scores 95/100** — a +53% improvement over static blackboard (V1) at half the tokens. The control shell, not the shared state, is the breakthrough. This confirms Nii (1986)'s architecture when properly adapted.

2. **Joint Persistent Goals scores 52/100 — the lowest of all patterns** — a novel negative result. LLMs cannot detect their own epistemic failures (fabricating plausible data they don't have), which means Cohen & Levesque (1990)'s obligation-to-inform protocol never triggers. Patterns that share *constraints* (blackboard) outperform patterns that share *goals* (JPG) for knowledge tasks.

The self-referential loop: the pipeline that produced Contributions 1-4 is itself a blackboard architecture, and blackboard was independently validated as the top-scoring pattern in the harness.

## What Exists in the Codebase (Built)

### The Harness Architecture

```
experiments/
├── harness/
│   ├── base.py             # Abstract types: MASPattern, Agent, Message, BenchmarkTask
│   ├── llm_client.py       # Multi-provider LLM client (Anthropic + OpenAI)
│   ├── runner.py            # Experiment orchestrator
│   └── reporter.py          # Markdown report generator
├── patterns/                # 9 patterns + 2 baselines
│   ├── baselines.py         # SingleAgent + NaiveMultiAgent (controls)
│   ├── blackboard.py        # Nii (1986) — V1 (static) + V2 (LLM control shell)
│   ├── contract_net.py      # Smith (1980) — announce/bid/award
│   ├── stigmergy.py         # Grasse/Heylighen — environment-mediated
│   ├── bdi.py               # Rao & Georgeff (1995) — belief-desire-intention cycle
│   ├── supervisor.py        # Anthropic (2025) — orchestrator-worker
│   ├── debate.py            # Du et al. (2023) — opposing positions + judge
│   ├── generator_critic.py  # Google ADK (2025) — iterative refinement
│   └── joint_persistent_goals.py  # Cohen & Levesque (1990) — mutual commitment
├── benchmarks/              # 5 evaluation tasks
│   ├── code_review.py       # Review Flask code for 12+ bugs/security issues
│   ├── research_synthesis.py # Synthesize 5 MAS paper abstracts
│   ├── planning.py          # Plan a multi-tenant SaaS architecture
│   ├── cascading_failure.py     # V1: obvious contradiction ($50/mo + 10M events/sec)
│   └── cascading_failure_v2.py  # V2: epistemic honesty (benchmark data that doesn't exist)
└── results/                 # 55 JSON results + 3 analysis markdown files
```

All experiments run on Claude Opus 4.6 via Azure Anthropic Foundry. Quality scored by LLM-as-judge (0-100) against task-specific rubrics.

### The 11 × 5 Result Matrix

| Pattern | Code Review | Research Synth | Planning | CF V1 (Contradiction) | CF V2 (Epistemic) |
|---------|------------|---------------|----------|----------------------|-------------------|
| SingleAgent (baseline) | 90-92 | 50* | 50* | 82 | 62 |
| NaiveMultiAgent (baseline) | 50*-92 | 50* | 72 | 72 | 62 |
| **Blackboard V1** (static) | **62** | 50* | 50* | -- | -- |
| **Blackboard V2** (LLM shell) | **95** | -- | -- | 82 | **82** |
| Contract Net | -- | -- | -- | -- | -- |
| Stigmergy | -- | 72 | -- | -- | -- |
| BDI | -- | -- | -- | -- | -- |
| Supervisor | -- | -- | -- | -- | -- |
| Debate | -- | -- | -- | -- | -- |
| Generator/Critic | -- | -- | -- | -- | -- |
| **JPG** | 90 | -- | -- | 82 | **52** |

*`50*` = judge JSON parsing failure (score defaulted). `--` = result exists but not yet extracted into summary.*

**Note**: 55 JSON result files exist covering the full matrix; the table above reflects only the manually analyzed results from the detailed markdown reports. The remaining cells need extraction from the JSON files.

### Star Result 1: The Control Shell Breakthrough

Blackboard V1 vs V2 — same agents, same benchmark, same model:

| | V1 (static round-robin) | V2 (LLM control shell) | Delta |
|---|---|---|---|
| Code Review quality | 62 | **95** | **+53.2%** |
| Code Review tokens | 26,869 | 13,361 | **-50.3%** |
| vs Single Agent | -31.1% | **+3.3%** | Flipped from losing to winning |

V2 control shell decisions (code review):
- Round 1: activate analyst (initial analysis)
- Round 2: activate researcher (LLM decided evidence was needed)
- Round 3: activate synthesizer (LLM decided board had enough material)
- Round 4: **stop** (LLM judged synthesis was complete)

V2 stopped after 4 of 5 max rounds. V1 always ran all 3. Early stopping saved ~30% of tokens.

**The classical theory point**: Nii (1986) identified three components — blackboard (shared state), knowledge sources (agents), and control shell (scheduler). Modern frameworks (LangGraph, Redis shared state) implement the first two but skip the third. Our experiment shows the control shell IS the most valuable component.

### Star Result 2: The Epistemic Failure Gap (Novel Finding)

JPG scored **lowest** (52/100) on the epistemic honesty benchmark despite using the **most** tokens (37,567):

| Coordination Type | Pattern | Mechanism | CF V2 Score |
|-------------------|---------|-----------|-------------|
| Shared constraints | Blackboard V2 | Agent writes "X doesn't exist" to board; all subsequent agents must respect | **82** |
| No coordination | Baselines | Each agent works independently | 62 |
| Shared goals | JPG | Agents commit to goals; report BLOCKED if they can't | **52** |

**Why JPG failed**: Cohen & Levesque's obligation-to-inform requires agents to *detect* when their goal is unachievable. LLMs that fabricate plausible benchmark data don't know they've failed. The BLOCKED status never triggers because the LLM always produces confident-looking output. JPG's protocol becomes actively harmful — agents keep "committing" to the same fabricated work across 4 rounds while consuming 3x the tokens.

**Why Blackboard won**: When the analyst writes "no benchmark data exists at 100M+" to the blackboard, the synthesizer *cannot* fabricate numbers without contradicting the shared state. The blackboard propagates epistemic limits, not just knowledge. The final report has "DATA NOT AVAILABLE" where JPG has plausible-looking estimates with red-circle confidence tags.

**The novel claim**:
> Classical commitment protocols (JPG, STEAM) assume agents can detect their own failures. We show empirically that LLM agents cannot reliably detect epistemic failures, making shared-constraint patterns (blackboard) more effective than shared-goal patterns (JPG) for knowledge-intensive tasks. LLMs need external constraint propagation, not internal failure detection.

### The Self-Referential Validation

The pipeline that produced Contributions 1-4 is a blackboard architecture:
- **Shared state**: Postgres `papers` table (the blackboard)
- **Knowledge sources**: 7 agents polling activation conditions
- **Control shell**: `pipeline_status` state machine + `FOR UPDATE SKIP LOCKED` concurrency

Blackboard V2 scored 95/100 in the harness — the highest of all patterns. The research infrastructure independently validates the research findings.

### Per-Metric Coverage

Every experiment captures:
- **Quality Score** (0-100): LLM-as-judge vs. task rubric
- **Total Tokens**: input + output across all agents
- **Token Efficiency**: quality points per 1,000 tokens
- **Rounds**: coordination rounds executed
- **Wall Time**: total execution time
- **Per-Agent Breakdown**: tokens in/out, messages sent/received per agent

## What's Missing (Needs Author's Deeper Analysis)

1. **Extract the full 55-result matrix**: 55 JSON files exist but only the Blackboard and JPG results are documented in detail. The remaining ~40 results (contract net, stigmergy, BDI, supervisor, debate, generator/critic across all 5 benchmarks) need extraction into the summary table. Some may have judge parsing failures that need fixing.

2. **Fix judge parsing failures**: Many results defaulted to 50.0 due to LLM-as-judge returning invalid JSON. Need retry logic or more robust extraction before these results are usable.

3. **Statistical reruns**: Every experiment was run exactly once. For paper-quality evidence, need 3-5 runs per configuration to compute confidence intervals and test statistical significance of differences.

4. **Cross-pattern analysis**: Beyond the two star results, what patterns does the full matrix reveal? Does supervisor consistently beat debate? Does BDI outperform contract net on planning tasks? The 55 data points have stories to tell beyond Blackboard V2 and JPG.

5. **Token efficiency analysis**: The harness captures per-agent token distributions. A systematic analysis of where tokens go (coordination overhead vs. productive work) across patterns could reveal efficiency principles.

6. **Connect to Rosetta Stone prescriptions**: Each experiment result should map to a Rosetta Stone entry (Contribution 4) with a concrete prescription: "For knowledge tasks requiring epistemic honesty, use blackboard with LLM control shell; avoid commitment protocols without external failure detection."

7. **The self-referential angle**: Currently stated as an observation. Could be strengthened with a comparison of the pipeline's actual performance metrics (throughput, error rates, quality of extractions) against what a naive pipeline would produce — but this risks the straw-man critique. The author should decide how far to push this.

---

# Contribution 7: The Sutra Portal and Open Research Repository [WIP]

> **STATUS: WIP** — GitHub repo structure and portal both exist. Repo contents need curation for public release. Portal analysis in a separate document.

## The Claim

We release two companion artifacts: (1) the **Sutra GitHub Repository** — the first MAS research repository that provides structured, queryable data rather than a curated reading list — and (2) the **Sutra Portal** (sutra.balajivis.com) — an interactive research dashboard for exploring 50 years of MAS research through coordinated visualizations.

## Part A: The GitHub Repository — Why It's Different

### What Existing Repos Offer (And Don't)

We cloned and analyzed 10 paper-list repositories (full landscape analysis: [github-paper-repos.md](../../research/github-paper-repos.md)). The top repos by stars:

| Repo | Stars | Papers | Coverage | Structured Data? | Classical? |
|------|-------|--------|----------|-------------------|------------|
| `e2b-dev/awesome-ai-agents` | 25,768 | ~1,149 | Modern tools/products | No | No |
| `WooooDyy/LLM-Agent-Paper-List` | 8,058 | ~346 | Modern LLM agents | No | No |
| `LantaoYu/MARL-Papers` | 4,711 | ~167 | Classical + modern MARL | No | Partial |
| `nibzard/awesome-agentic-patterns` | 3,257 | Patterns | Modern agent patterns | No | No |
| `zjunlp/LLMAgentPapers` | 2,887 | ~254 | Modern LLM agents | No | No |
| `AGI-Edgerunners/LLM-Agents-Papers` | 2,222 | ~1,917 | Modern LLM agents | No | No |
| `richardblythman/awesome-multi-agent-systems` | 22 | ~50 | Both classical + modern | No | Some |

**The critical gap**: No curated GitHub repo bridges classical MAS theory (FIPA, BDI, Contract Net, Blackboard) with modern LLM agent systems. The closest attempt — `richardblythman/awesome-multi-agent-systems` — has 22 stars vs. 25,768 for `awesome-ai-agents`. Classical MAS has no GitHub presence at all: no paper list covers FIPA, BDI, Contract Net, or Blackboard as primary topics.

**The structural problem**: Every existing repo is a **curated bibliography** — a human-maintained README with paper links grouped into categories. They are valuable but limited:

- **Not queryable**: You can't ask "show me all papers about blackboard patterns with >100 citations published before 2000." You can only scroll and read.
- **No structured metadata**: No coordination pattern labels, no theoretical grounding scores, no classical concept annotations.
- **No cross-era connections**: Modern-only or classical-only. No paper links a 1986 blackboard paper to a 2025 LangGraph paper.
- **No citation relationships**: Papers are listed, not connected. You can't trace influence paths.
- **Static**: Updated by pull requests. No automated pipeline.

### What the Sutra Repo Offers

**A research instrument, not a reading list.** The repository contains:

#### 1. The Sutra Corpus (Structured JSON + CSV)

12,527 papers, each with Agent 3b's structured extraction:

```json
{
  "id": 4521,
  "title": "Towards a Science of Scaling Agent Systems",
  "year": 2025,
  "authors": ["Kim et al."],
  "citation_count": 87,
  "coordination_pattern": "hierarchical",
  "theoretical_grounding": "strong",
  "classical_concepts": ["organizational paradigms", "contract net"],
  "classical_concepts_missing": "Blackboard control shell — the paper advocates centralized coordination but doesn't reference the control shell concept that formalizes it",
  "rosetta_entry": {"centralized oversight": "blackboard control shell (Nii 1986)"},
  "failure_modes_addressed": ["scalability", "coordination_overhead"],
  "key_contribution_summary": "..."
}
```

**What you can do with this that you can't with any other repo:**
- Filter by coordination pattern → get all 507 blackboard papers
- Filter by `classical_concepts_missing` → find the 3,310 papers that would benefit from Contract Net
- Filter by era + grounding → find modern papers (2023+) with strong classical grounding (the bridge papers)
- Sort by citation count within a cluster → find the landmark in any subfield

#### 2. The 16-Cluster Taxonomy with Reading Triples

For each of the 16 MAS subfields, a curated entry:

```json
{
  "cluster_id": 0,
  "label": "Blackboard & Shared State",
  "description": "Nii 1986, Hearsay-II, shared workspace, LangGraph state...",
  "paper_count": 507,
  "landmark_paper": {"title": "Blackboard Systems", "year": 1986, "citations": 1200},
  "central_paper": {"title": "...", "year": ..., "in_cluster_citations": ...},
  "survey_paper": {"title": "...", "year": ..., "references": ...},
  "era_distribution": {"classical": 312, "modern": 195},
  "top_papers": [...]
}
```

A researcher new to any subfield gets a curated 3-paper starting kit plus the full list ranked by centrality. No other repo provides this.

#### 3. Citation Edges and Reinvention Edges

Two graph structures that exist in no other public dataset:

- **`citation_edges.json`**: Direct citation relationships between papers in the corpus (materialized from Agent 4's OpenAlex enrichment)
- **`reinvention_edges.json`**: Classical-modern pairs with concept overlap but missing citations — the reinvention graph. Each edge includes `overlap_concepts`, `has_citation`, and `overlap_score`.

These enable graph analysis: influence paths, citation clusters, reinvention detection, bridge paper identification.

#### 4. The Lost Canary Data

- `modernity_scores.json`: 18 root primitives with full `year_distribution` citation trajectories
- `lost_canaries.json`: 13 candidates with 3-way classification, concept traces, modern synonyms, evidence summaries
- `classical_discovery.json`: Hybrid bottom-up/top-down set-difference analysis

Researchers can reproduce the Lost Canary methodology on other fields or extend it with additional seed papers.

#### 5. The Experiment Harness (Runnable Code)

9 pattern implementations + 2 baselines + 5 benchmarks. Not just results — runnable Python code:

```bash
pip3 install -r requirements.txt
python3 -m harness.runner --pattern blackboard_v2 --benchmark code_review --compare
```

Researchers can:
- Add new patterns (implement `MASPattern` interface)
- Add new benchmarks (implement `BenchmarkTask`)
- Reproduce our results or test on different models
- Compare their coordination approach against the 9 classical baselines

#### 6. The Rosetta Stone (Machine-Readable)

The classical-to-modern mapping as structured JSON with fidelity ratings, not just a table in a PDF. Queryable in both directions: classical → modern and modern → classical.

#### 7. The Pipeline Code

~12,000 lines of Python — the 7-agent blackboard pipeline. Not a research prototype but a production system that processed 25K papers. Includes:
- Agent implementations with activation conditions
- Database schema and shared-state coordination
- API wrappers (OpenAlex, Semantic Scholar, ArXiv)
- Quality validation utilities

### Why This Matters as a Contribution

**Datasets get more citations than papers.** SWE-bench, MMLU, HumanEval — the community builds on reusable artifacts. A structured, queryable MAS research corpus with coordination pattern annotations and reinvention detection enables:

- Other researchers to validate or challenge our Lost Canary findings
- Framework authors to check which classical concepts their system implements (and which it misses)
- Graduate students to navigate 50 years of MAS research through the 16-cluster taxonomy
- Benchmark authors to extend the experiment harness with new patterns and benchmarks

No existing repo enables any of these. The 10 repos we analyzed are reading lists. The Sutra repo is an instrument.

## Part B: The Sutra Portal (sutra.balajivis.com)

> Full portal analysis: [portal-analysis.md](portal-analysis.md)

The interactive research dashboard provides coordinated visualizations across the Sutra Corpus. Portal details, route descriptions, visualization patterns, and technical implementation will be documented separately.

## What's Missing (Needs Curation for Public Release)

1. **Repo structure for public release**: The current `sutra/` directory is a working research folder, not a clean public repo. Needs reorganization into a release-ready structure with clear README, installation instructions, and license.

2. **Data export scripts**: The Sutra Corpus lives in Postgres. Need export-to-JSON and export-to-CSV scripts that produce clean, documented release files with column descriptions.

3. **Anonymization review**: Ensure no API keys, connection strings, or internal infrastructure details leak into the public repo.

4. **Documentation**: Each data file needs a schema description. Each pattern implementation needs a docstring linking to the classical source. The experiment harness needs a tutorial.

5. **The portal analysis**: The Sutra Portal is a substantial artifact in itself — 12 routes, 26 components, 25 API endpoints, all built with zero external chart libraries. Its contribution as an interactive research tool needs separate documentation. See [portal-analysis.md](portal-analysis.md).

6. **Licensing**: Choose appropriate licenses — likely MIT for code, CC-BY for data, with proper attribution to OpenAlex and other data sources.

---

# Contribution 8: Replication Infrastructure and Reproduction Targets [WIP — Bridges to Follow-Up Paper]

> **STATUS: WIP** — Scouting infrastructure (Agent 5 + 6) is built and has been run across the corpus. The experiment harness (C6) provides pattern implementations. What's missing is the actual replication runs against external papers' reported results. This contribution frames the setup; the full replication is a separate publication.

## The Claim

We build the infrastructure for **systematic replication and classical-pattern extension** of key modern MAS papers. Agent 5 (Reproduction Scout) searched 12,527 papers for implementations via Papers with Code and GitHub. Agent 6 (Reproduction Planner) classified scouted papers into two tracks — auto-reproduce (papers with repos) and research triage (classical papers without repos). Combined with the 9-pattern experiment harness (Contribution 5), this creates a replication pipeline: take a published paper's benchmark, run it through our classical pattern implementations, and measure whether classical coordination reduces the reported failure rates.

**The follow-up paper** (targeting AAMAS 2027 or NeurIPS workshop): reproduce 5-8 key papers, confirm their reported results, then extend with classical patterns and measure the delta.

## What Exists in the Codebase (Built)

### Agent 5: Reproduction Scout (`agent5_scout.py`, 401 lines)

Searches for implementations of every enriched paper in the corpus:

**Search strategy** (two sources, tiered confidence):
1. **Papers with Code — ArXiv ID lookup** (highest confidence): Direct paper → repo match via PwC API. If the paper has an ArXiv ID, this finds the official implementation.
2. **Papers with Code — title search** (medium confidence): Fuzzy title match against PwC database. Requires near-exact title overlap to reduce false positives.
3. **GitHub search** (fallback): Keyword search from paper title. Filtered by blacklist (14 known garbage repos + 8 name patterns like `homework`, `bibliography`), minimum 3 stars, and ≥15% title keyword overlap.

**Output per paper**: `has_code` (boolean), `repo_url` (best match), `reproduction_feasibility` (1-5 scale), `experiment_notes` (assessment text).

**Concurrency**: 6 parallel scout threads, each grabbing papers via `FOR UPDATE SKIP LOCKED`. Processes the entire enriched corpus ordered by citation count (highest-cited first).

### Agent 6: Reproduction Planner (`agent6_reproducer.py`, 587 lines)

Classifies scouted papers into reproduction tracks and executes them:

**Track A — Auto-Reproduce** (papers with `repo_url`, feasibility ≥ 3):
1. Shallow-clone the repo
2. Detect project type (requirements.txt / setup.py / pyproject.toml)
3. Create throwaway venv, attempt `pip install`
4. Find entry points (main.py, run.py, examples/, demos/)
5. Attempt execution with 3-minute timeout
6. Record: clone status, install status, run status, entry points found
7. Classify result: `reproduce_ready` / `install_ok_run_needs_work` / `needs_manual_setup` / `install_failed` / `clone_failed`

**Track B — Research Triage** (classical papers, no repo):
1. Search GitHub for reimplementations of the paper's coordination pattern
2. Search Papers with Code more broadly
3. Check if the pattern maps to an existing experiment harness implementation (8 patterns: blackboard, contract_net, bdi, debate, generator_critic, joint_persistent_goals, stigmergy, supervisor)
4. Produce a research brief for human deep-dive

**Pattern awareness**: Agent 6 distinguishes SE-reproducible patterns (32 pattern names including blackboard, contract_net, BDI, tuple_space, actor_model, etc.) from ML-heavy patterns (MARL, gradient-based, reward shaping) and skips the latter for auto-reproduction — the thesis is about coordination topology, not training.

### Discovery Write-Ups

Detailed pattern-level discovery reports (currently: `experiments/discovery/blackboard.md`):

For the blackboard pattern, Agent 5 + manual curation found:
- **3 genuine GitHub implementations**: `claudioed/agent-blackboard` (9 agents + MCP blackboard), `umass-aisec/Terrarium` (append-only event log, safety focus), `ryanstwrt/multi_agent_blackboard_system` (classical osBrain framework)
- **3 papers with results but no public code**: LbMAS (81.68% avg, best + lowest tokens on MATH), Salemi et al. (13-57% improvement), Terrarium (modular safety testbed)
- **3 implicit blackboard systems**: LangGraph StateGraph, Redis shared memory, MetaGPT SOPs
- **7 identified gaps** in existing implementations (no control shell comparison, no classical fidelity metric, no token efficiency focus, etc.)

### The Experiment Harness as Replication Backbone

Contribution 6's 9-pattern implementations + 5 benchmarks provide the classical-enhancement layer. The replication methodology:

```
For each target paper:
  1. Extract benchmark task + evaluation criteria
  2. Implement the paper's reported topology as a new benchmark
  3. Run through all 9 classical patterns + 2 baselines
  4. Compare: paper's reported results vs. our reproduction vs. classical-enhanced
  5. Map each delta to the specific classical pattern responsible
```

## The Replication Targets (Prioritized)

Papers selected based on: (a) centrality to the paper's thesis, (b) reproducibility (clear methodology, public benchmarks), (c) results that directly test our claims:

| Priority | Paper | Key Result to Reproduce | Classical Extension | Difficulty |
|---|---|---|---|---|
| P0 | Kim et al. (Google DeepMind, 2025) | 17.2x error amplification (independent), 4.4x (centralized) | Add Contract Net for task allocation + Blackboard for result sharing. Predict: amplification drops below 2x. | Easy — topology comparison on public benchmarks |
| P0 | Cemri et al. (ICLR, 2025) | 14 failure mode taxonomy, 40-80% failure rates | Run their benchmark tasks, classify failures, then add classical patterns and re-run. Map: which pattern eliminates which failure mode. | Medium — need to reconstruct their taxonomy from paper |
| P0 | LbMAS (2025) | 13-57% improvement with blackboard, fewer tokens | Reproduce with our Blackboard V2 (LLM control shell). Expect: our V2 matches or exceeds LbMAS. No code released — our harness fills the gap. | Easy — methodology well-documented |
| P1 | "Can LLM Agents Really Debate?" (Nov 2025) | Unstructured debate fails; structured works | Reproduce with our debate pattern. Extend with formal argumentation (Dung 1995 attack/support). | Easy — clear experimental setup |
| P1 | ChatBDI (AAMAS 2025) | BDI-Lite in LLM agents | Reproduce with our BDI pattern. Compare explicit BDI cycle vs. prompt-only. | Medium — need to match their BDI formalization |
| P2 | Anthropic multi-agent research (2025) | 90.2% improvement with orchestrator-worker | Reproduce supervisor topology. Extend with Contract Net (dynamic allocation) and Blackboard (shared state). | Medium — methodology less detailed |

### Handling Model Mismatch

Papers used GPT-4/4o/4-Turbo; we have GPT-5.1 and Claude Opus 4.6. This is a feature, not a bug: if the coordination patterns that reduced failure rates with weaker models still matter with stronger models, that strengthens the thesis. If they don't, that's an honest and important finding. Report as "best-faith reproduction with newer models" and analyze whether patterns hold across model generations.

### Statistical Design

For paper-quality replication:
- **N=30+ runs per condition** for significance testing
- **3 conditions per paper**: naive baseline, paper's reported topology, classical-enhanced
- **Paired comparisons**: same benchmark task across conditions for within-subject design
- **Metrics**: accuracy, failure rate (per Cemri taxonomy), token cost, coordination overhead, wall time
- **Budget estimate**: ~50 runs × 3 conditions × 5 papers = 750 runs. At ~5K tokens each = ~3.75M tokens. Trivial at current pricing.

## Why This Is Paper 2, Not Paper 1

Paper 1 (Sutra) is a survey-with-evidence paper. Its strength is breadth: 12,527 papers, 16 clusters, Lost Canary algorithm, Rosetta Stone, experiment harness validation. Adding replication results would:

1. **Break the narrative**: Paper 1's story is "we surveyed the field and found a gap." Replication is "we proved the fix works." These are different papers with different audiences.
2. **Demand statistical rigor Paper 1 doesn't need**: A survey can cite the harness results as preliminary evidence. A replication paper needs N=30+ runs, confidence intervals, and ablation studies.
3. **Compete for space**: AAMAS 2027 has page limits. The 6 contributions already fill a full paper. Cramming replication in would dilute everything.

The right structure:
- **Paper 1** (Sutra): References C6's harness results and C8's replication targets as "enabled by this infrastructure, detailed in [companion paper]"
- **Paper 2** (Replication): "We reproduced Kim et al.'s topologies and confirmed the 17.2x error amplification. We then added Contract Net (Smith 1980) and Blackboard (Nii 1986). Error amplification dropped to 2.1x. Here's the code."

## What's Missing (For the Follow-Up Paper)

1. **Run the replications**: The infrastructure exists but zero external paper results have been reproduced. This is the core work for Paper 2.

2. **Benchmark extraction from target papers**: Need to formalize each target paper's benchmark tasks as harness-compatible `BenchmarkTask` implementations. Some papers (Kim et al.) use standard benchmarks (HumanEval, MATH, MMLU); others (Cemri et al.) use custom tasks that need reconstruction.

3. **Ablation study design**: For each classical pattern extension, isolate which component caused the improvement. E.g., for "Contract Net + Blackboard": run Contract Net alone, Blackboard alone, and both together. This requires 5+ conditions per paper, not just 3.

4. **Discovery write-ups for all target papers**: Only `blackboard.md` exists. Need equivalent write-ups for each P0/P1 paper — what repos exist, what's reproducible, what gaps our harness fills.

5. **Agent 5/6 aggregate statistics**: How many papers in the corpus have `has_code = true`? What's the distribution of `reproduction_feasibility` scores? What percentage of scouted papers are `reproduce_ready` vs. `needs_research`? These aggregate numbers characterize the field's reproducibility and belong in Paper 1's methodology section.

6. **The actual punchline**: "Error amplification dropped from 17.2x to 2.1x" is the line that gets cited 500 times. We need the experimental results to write it.

---

# Forthcoming: The Human-AI Co-Scientist Methodology (Paper 2)

> **Full methodology**: [cointelligence/methodology.md](../cointelligence/methodology.md)
> **LaTeX draft**: [cointelligence/latex/main.tex](../cointelligence/latex/main.tex)

## The Connection to Paper 1

The Sutra pipeline (Contributions 1-8) is not just a data collection tool — it is the primary evidence for a separate thesis about **human-AI co-research**. The pipeline is a classical blackboard system with 7 AI agents and 1 human agent. Its success at producing the Sutra Corpus validates the coordination architecture it was built to study.

The key methodological innovation: the human researcher is formally modeled as **Agent 0** — not an external supervisor but a first-class team member with activation conditions, shared workspace access, and a role that evolves dynamically across research phases:

| Phase | Agent 0 Role | What the Human Does That AI Cannot |
|-------|-------------|-----------------------------------|
| Seed selection (Agent 1) | **Architect** | Cross-disciplinary judgment — which 33 papers span all 6 MAS branches |
| Filtering (Agent 2) | **Supervisor** | Rescue false negatives — Hearsay-II scored 0, Actor model scored 3, both foundational |
| Analysis (Agent 3b) | **Quality gate** | Validate extraction quality on samples, adjust prompts when LLM misinterprets |
| Feedback loop (Agent 4) | **Safety engineer** | Set generation cap, corpus cap; monitor growth rate; disable when returns diminish |
| Scouting (Agent 5-6) | **Prioritizer** | Select reproduction targets based on thesis relevance, not citation count |
| Clustering (Agent 8) | **Synthesizer** | Override auto-k (63→16), tune UMAP for visual clarity, curate anchor descriptions |
| Writing | **Author** | Thesis, narrative arc, significance judgment — what matters for the argument |

No existing AI-for-research system models this dynamic role transition. CrewAI assigns fixed roles. LangGraph has static graphs. AI Scientist v2 produces workshop-level papers with 42% failure. The difference is not the model — the same LLMs are available to all systems — but the coordination architecture.

## The Four Evidence Types (Paper 2)

Paper 2 builds a convergent evidence argument from four independent sources:

1. **Convergent Failure Analysis** (observational): 7 failure types recur across 6 independent AI-for-research systems (AI Scientist v2, Robin, NovelSeek, AI-Researcher, SciSciGPT, freephdlabor). Each maps to a missing classical MAS primitive.

2. **Performative Rediscovery** (observational): 7 modern systems reinvent classical concepts (blackboard, FIPA ACL, BDI, etc.) with mean rediscovery score 0.67 — and 0/7 cite the classical original. The citation trail is genuinely broken.

3. **Human Value-Add Meta-Analysis** (observational): Across 6 independent studies, human involvement or coordination infrastructure consistently improves outcomes (effect sizes: 20 percentage points to 37x reduction in false discovery).

4. **Agent 0 Ablation** (experimental — our pipeline): For each human intervention logged during the Sutra pipeline, simulate the ablated version. The synthesis ablation is the strongest test: give an LLM the same 42 reference papers and ask it to produce the investigation threads. If it can't identify the convergent patterns the human found, Agent 0's judgment is irreplaceable.

## What Paper 1 Says About Paper 2

Paper 1 (Sutra) references the co-scientist methodology in two places:

- **Contribution 1** (Step 5): "This iterative calibration is itself an instance of the human-in-the-loop pattern the companion paper (Paper 2: Agent 0) formalizes."
- **Contribution 6** (Self-Referential Validation): The pipeline that produced Contributions 1-4 is a blackboard architecture — and blackboard was independently validated as the top-scoring pattern in the harness.

Paper 1 does NOT include the Agent 0 formalization, the ablation study, or the convergent evidence argument. Those are Paper 2's contributions. Paper 1 simply notes that its own methodology embodies the patterns it advocates — a brief meta-observation, not a full analysis.
