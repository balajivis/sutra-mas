# Sutra: The Largest Structured Corpus of Multi-Agent Systems Research

**36,299 papers collected. 17,969 deep-analyzed. 16-cluster taxonomy. Structured embeddings. Rosetta Stone mappings.**

> *Sutra* (Sanskrit: "thread that connects") -- the Vedic texts that compress vast knowledge into essential threads.

The largest structured corpus of multi-agent systems research ever assembled -- spanning 30 years from classical MAS (1980-2010) through the LLM agent explosion (2023+). Every paper in the analyzed corpus carries coordination patterns, theoretical grounding, classical concept mappings, UMAP embeddings, and cluster assignments produced by an 8-agent LLM pipeline.

Modern LLM agent systems fail 40-80% of the time. Not because the models are weak -- because the coordination is naive. Thirty years of multi-agent systems research solved these exact problems. Then the citation trail went cold. This repository reconnects it.

**What makes this different from a paper list:**
- **36,299 candidate papers** collected from ArXiv, OpenAlex, DBLP, and Crossref (`data/full-paper-list.csv`)
- **17,969 papers** filtered for MAS relevance and deep-analyzed with structured metadata
- **Coordination patterns** extracted per paper (blackboard, supervisor, contract net, BDI, debate, stigmergy, ...)
- **Rosetta Stone entries** mapping each paper's modern concepts back to classical origins
- **UMAP embeddings** and **16-cluster taxonomy** for visual and programmatic exploration
- **Citation graph** with ~100K+ directed edges between corpus papers
- **Lost Canaries** -- high-citation classical papers with near-zero modern uptake

You can query: *"Show me all papers that use a blackboard pattern but don't cite Nii 1986"* -- and get a precise answer.

## The Problem

| Finding | Source |
|---------|--------|
| 17.2x error amplification in naive multi-agent systems | Kim et al., Google DeepMind 2025 |
| 90.2% improvement when coordination infrastructure is added | Anthropic Engineering Blog, 2025 |
| 13-57% quality improvement with blackboard architectures, 3x fewer tokens | LbMAS, 2025 |
| 87% accuracy predicting optimal architecture from task features alone | Kim et al., 2025 |

The next leap in agentic reliability will come not from better models, but from the re-adoption of coordination protocols that were solved decades ago.

## What's In This Repository

### 1. The Corpus (`data/`)

**36,299 collected → 17,969 analyzed** -- the full pipeline from candidate collection to structured analysis:

| File | Records | Description |
|------|---------|-------------|
| `full-paper-list.csv` | 36,299 | Complete candidate list -- every paper collected from ArXiv, OpenAlex, DBLP, Crossref with source, year, venue, external IDs, and whether it passed into the analyzed corpus |
| `corpus.jsonl` | 17,969 | Analyzed corpus -- one JSON object per paper with title, abstract, year, citations, coordination pattern, theoretical grounding, classical concepts cited, classical concepts *missing*, cluster assignment, UMAP coordinates, and Rosetta Stone entry |
| `corpus-lite.csv` | 17,969 | Lightweight view -- id, title, year, cluster, pattern, citations, UMAP position |
| `citation-edges.csv` | ~100K+ | Directed citation graph between corpus papers |
| `clusters.csv` | ~18K | Cluster assignment + 2D UMAP coordinates per paper |
| `cluster-meta.json` | 16 | Cluster labels, descriptions, paper counts, top concepts |
| `reinvention-map.csv` | ~500+ | Explicit classical-to-modern paper links with overlap scores |
| `lost-canaries.json` | ~20-30 | High-citation classical papers with near-zero modern uptake -- the forgotten knowledge |
| `reading-triples.json` | 48 | 3 entry-point papers per cluster (landmark, central, survey) |
| `corpus-stats.json` | 1 | Summary statistics |

### 2. The 16-Pillar Taxonomy

The corpus is organized into 16 clusters representing the major coordination mechanisms in MAS research. Each pillar has a classical landmark paper and a modern entry point -- start with any pair to understand both the origin and the current state of that coordination mechanism.

| # | Pillar | Papers | Classical Landmark | Modern Entry Point |
|---|--------|-------:|--------------------|--------------------|
| 0 | [**Shared Medium Coordination**](pillars/00-shared-medium.md) | 1,096 | [Blackboard Systems](https://doi.org/10.1007/978-1-4615-2211-9_2) (Nii 1986) | [LbMAS: Blackboard for LLM Agents](https://arxiv.org/abs/2503.10939) (2025) |
| 1 | [**Contract Net & Task Allocation**](pillars/01-contract-net.md) | 945 | [The Contract Net Protocol](https://doi.org/10.1109/TC.1980.1675516) (Smith 1980) | [AutoGen: Next-Gen LLM Applications](https://arxiv.org/abs/2308.08155) (Wu et al. 2023) |
| 2 | [**Organizational Design & Team Structures**](pillars/02-organizational-design.md) | 2,167 | [Survey of Multi-Agent Organizational Paradigms](https://doi.org/10.1017/s0269888905000317) (Horling & Lesser 2004) | [MetaGPT: Multi-Agent Collaboration](https://arxiv.org/abs/2308.00352) (Hong et al. 2023) |
| 3 | [**Distributed Planning & Teamwork**](pillars/03-distributed-planning.md) | 1,798 | [Collaborative Plans for Complex Group Action](https://doi.org/10.1016/0004-3702(95)00103-4) (Grosz & Kraus 1996) | [ChatDev: Communicative Agents for Software](https://arxiv.org/abs/2307.07924) (Qian et al. 2023) |
| 4 | [**Agent Communication Languages & Protocols**](pillars/04-agent-communication.md) | 281 | [KQML: Agent Communication Language](https://doi.org/10.1145/191246.191322) (Finin et al. 1994) | [Model Context Protocol](https://modelcontextprotocol.io/specification) (Anthropic 2025) |
| 5 | [**Governance, Norms & AI Safety**](pillars/05-governance-norms.md) | 370 | [Governing the Commons](https://doi.org/10.1017/CBO9780511807763) (Ostrom 1990) | [AgentSpec: Runtime Constraints](https://arxiv.org/abs/2503.18666) (2025) |
| 6 | [**Negotiation, Argumentation & Economic Paradigms**](pillars/06-negotiation-argumentation.md) | 1,555 | [Rules of Encounter](https://mitpress.mit.edu/9780262181570/) (Rosenschein & Zlotkin 1994) | [Human-Level Play in Diplomacy](https://doi.org/10.1126/science.ade9097) (Meta FAIR 2022) |
| 7 | [**BDI & Cognitive Agent Architectures**](pillars/07-bdi-cognitive.md) | 1,970 | [BDI Agents: From Theory to Practice](https://www.aaai.org/Papers/ICMAS/1995/ICMAS95-042.pdf) (Rao & Georgeff 1995) | [NatBDI: Natural-Language BDI](https://dl.acm.org/doi/10.5555/3635637.3663103) (2024) |
| 8 | [**Human-Agent Interaction & HITL**](pillars/08-human-agent-hitl.md) | 337 | [Types and Levels of Human Interaction with Automation](https://doi.org/10.1109/3468.844354) (Parasuraman et al. 2000) | [Building Effective Agents](https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns) (Anthropic 2025) |
| 9 | [**Trust, Reputation & Social Mechanisms**](pillars/09-trust-reputation.md) | 288 | [Review on Computational Trust and Reputation](https://doi.org/10.1007/s10462-004-0041-5) (Sabater & Sierra 2005) | [TrustLLM: Trustworthiness in LLMs](https://arxiv.org/abs/2401.05561) (2024) |
| 10 | [**Multi-Agent Engineering**](pillars/10-engineering-frameworks.md) | 2,411 | [The Gaia Methodology](https://doi.org/10.1023/a:1010071910869) (Wooldridge et al. 2000) | [LangGraph: Resilient Language Agents](https://github.com/langchain-ai/langgraph) (LangChain 2024) |
| 11 | [**Multi-Agent Robotics & Embodied Teams**](pillars/11-robotics-embodied.md) | 929 | [RoboCup: The Robot World Cup](https://doi.org/10.1609/aimag.v18i1.1276) (Kitano et al. 1997) | [LLM2Swarm: Robot Swarms that Reason and Collaborate](https://arxiv.org/abs/2410.11387) (2024) |
| 12 | [**Evaluation Benchmarks & Failure Analysis**](pillars/12-evaluation-benchmarks.md) | 955 | [A Multi-Agent Systems Turing Challenge](https://link.springer.com/chapter/10.1007/978-3-642-44927-7_1) (2013) | [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) (Cemri et al. 2025) |
| 13 | [**Memory & Context Management**](pillars/13-memory-context.md) | 107 | --- | [MemGPT: LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) (Packer et al. 2023) |
| 14 | [**Learning & Adaptation**](pillars/14-learning-adaptation.md) | 2,386 | [Ant System: Cooperating Agents](https://doi.org/10.1109/3477.484436) (Dorigo et al. 1996) | [Multiagent Finetuning: Self Improvement](https://arxiv.org/abs/2501.05707) (2025) |
| 15 | [**Modeling & Simulating Artificial Societies**](pillars/15-simulation-societies.md) | 374 | [Flocks, Herds and Schools](https://doi.org/10.1145/37401.37406) (Reynolds 1987) | [Generative Agents: Interactive Simulacra](https://arxiv.org/abs/2304.03442) (Park et al. 2023) |

The taxonomy was produced by a semi-supervised method: domain expertise defines the 16 cluster anchors (50-150 word descriptions covering classical and modern terminology), and cosine similarity over structured embeddings assigns papers to anchors. See `research/cluster-guide.md` for the full taxonomy rationale, including three generations of design iterations and the boundary decisions.

#### Era Distribution

The corpus spans 1948--2026. The 2000s peak reflects the golden age of classical MAS conferences (AAMAS, EUMAS, CEEMAS). The 2025+ surge reflects the LLM agent explosion.

| Era | Collected | High-Relevance | Avg Citations | Median Citations |
|-----|----------:|---------------:|--------------:|-----------------:|
| <1990 | 562 | 225 | 797 | 94 |
| 1990s | 2,788 | 1,884 | 125 | 30 |
| 2000s | 8,839 | 6,103 | 80 | 22 |
| 2010s | 9,407 | 3,541 | 64 | 14 |
| 2020--22 | 2,667 | 812 | 50 | 8 |
| 2023--24 | 3,853 | 1,588 | 54 | 3 |
| 2025+ | 7,261 | 3,574 | 115 | 2 |
| **Total** | **36,299** | **17,956** | **92** | **17** |

The high average citations for 2025+ (115) despite recency reflects highly-cited LLM agent papers (GPT-4, AutoGen, MetaGPT) that accumulated citations rapidly.

#### Per-Pillar Era Breakdown

Where do the classical and modern papers actually live? This table shows the era split per pillar (Classical = pre-2010, Transition = 2010--2022, Modern = 2023+). Pillars where classical dominates have deep established theory; pillars where modern dominates are frontier areas driven by LLM agents.

| # | Pillar | Total | Classical | Trans. | Modern | Character |
|---|--------|------:|----------:|-------:|-------:|-----------|
| 0 | Shared Medium | 1,093 | 502 | 160 | 424 | Balanced -- classical theory, modern revival |
| 1 | Contract Net & Task Alloc. | 945 | 649 | 235 | 58 | **Classical-dominated** -- mature theory, low modern uptake |
| 2 | Org. Design & Teams | 2,164 | 928 | 405 | 796 | Balanced -- large and active in both eras |
| 3 | Dist. Planning & Teamwork | 1,798 | 909 | 649 | 234 | Classical-leaning -- consensus/formation theory |
| 4 | ACL & Protocols | 281 | 233 | 28 | 18 | **Classical-dominated** -- FIPA/KQML era; MCP is the modern revival |
| 5 | Governance & Norms | 370 | 210 | 105 | 55 | Classical-leaning -- normative MAS, institutional design |
| 6 | Negotiation & Argumentation | 1,555 | 730 | 548 | 272 | Balanced -- game theory + LLM negotiation |
| 7 | BDI & Cognitive Arch. | 1,968 | 1,003 | 321 | 625 | Balanced -- classical BDI meets LLM reasoning |
| 8 | Human-Agent & HITL | 334 | 63 | 68 | 199 | Modern-leaning -- growing with AI safety focus |
| 9 | Trust & Reputation | 288 | 170 | 85 | 33 | **Classical-dominated** -- computational trust theory |
| 10 | Engineering & Frameworks | 2,411 | 1,489 | 343 | 553 | Classical-leaning -- JADE/JACK era, but LangGraph growing |
| 11 | Robotics & Embodied | 929 | 421 | 408 | 91 | Classical-leaning -- formation control, swarms |
| 12 | Eval. & Failure Analysis | 954 | 238 | 158 | 515 | **Modern-dominated** -- benchmarking is new |
| 13 | Memory & Context | 107 | 4 | 8 | 94 | **Modern-dominated** -- emerged with LLM agents |
| 14 | Learning & Adaptation | 2,385 | 483 | 726 | 1,116 | **Modern-dominated** -- MARL explosion post-2015 |
| 15 | Artificial Societies | 374 | 189 | 85 | 91 | Balanced -- ABMS meets Generative Agents |

The most striking contrasts: **Contract Net** (69% classical, 6% modern) -- the foundational task allocation protocol with almost no modern continuation. **Memory** (4% classical, 88% modern) -- a pillar that barely existed before LLM agents. **ACL & Protocols** (83% classical, 6% modern) -- FIPA/KQML built the theory; MCP/A2A are just beginning to rebuild it.

### 3. The Rosetta Stone

A concept-level mapping between classical MAS and modern LLM agent systems:

| Classical Concept | Year | Modern Reinvention | Status |
|-------------------|------|--------------------|--------|
| Blackboard (Nii) | 1986 | LangGraph state, Redis shared context | Control shell **lost** |
| Contract Net (Smith) | 1980 | A2A task lifecycle, agent dispatch | Partial |
| BDI (Rao & Georgeff) | 1995 | System prompt + RAG + CoT | Partial |
| FIPA ACL Performatives | 2000 | JSON schemas, A2A Parts, MCP | Partial |
| Holonic Organization (Horling) | 2004 | Hierarchical agent teams | Partial |
| Stigmergy (Grasse) | 1959 | MetaGPT SOPs, document-driven workflows | Partial |
| Argumentation (Dung) | 1995 | Generator/Critic, structured debate | Partial |
| Joint Persistent Goals (Cohen & Levesque) | 1990 | *(no equivalent)* | **GAP** |
| Discourse Coherence (Grosz & Sidner) | 1986 | *(no equivalent)* | **GAP** |
| Supervision Trees (Erlang/OTP) | 1986 | *(no equivalent)* | **GAP** |
| Functionally Accurate Cooperation (Durfee) | 1987 | *(no equivalent)* | **GAP** |

The `reinvention-map.csv` data file contains the paper-level evidence: which modern papers reinvent which classical concepts, whether they cite the original, and the concept overlap score.

### 4. The Experiment Harness (`experiments/`)

9 classical MAS coordination patterns + 2 baselines, implemented as LLM agent systems and evaluated across 5 standardized benchmarks. 58 reproducible experiment results with full traces.

| Pattern | Classical Source | Score | Key Finding |
|---------|----------------|-------|-------------|
| **Blackboard V2** | Nii 1986 + LLM control shell | **95/100** | The LLM control shell is the breakthrough |
| Supervisor | Anthropic 2025 | 80-88 | Solid hierarchical orchestration |
| BDI | Rao & Georgeff 1995 | 75-85 | Belief-Desire-Intention cycle translates well |
| Generator/Critic | Google ADK 2025 | 75-85 | Iterative refinement with typed feedback |
| Contract Net | Smith 1980 | 70-85 | Dynamic task allocation via bidding |
| Debate | Du et al. 2023 | 70-82 | Structured argumentation |
| Stigmergy | Grasse 1959 | 65-80 | Indirect coordination via shared document |
| Blackboard V1 | Nii 1986 (static round-robin) | 62/100 | Context bloat kills static scheduling |
| **Joint Persistent Goals** | Cohen & Levesque 1990 | **52/100** | **Novel negative**: LLMs cannot detect their own epistemic failures |

The star result: Blackboard V2 (with an LLM serving as the control shell) scores 95/100 on code review -- a +53% improvement over V1 (static round-robin). The control shell component, which Nii described in 1986 but which no modern framework implements, is what makes the difference.

The novel negative: Joint Persistent Goals requires agents to monitor each other's beliefs and report when conditions change. LLMs score 52/100 -- they cannot reliably track mutual beliefs or detect their own epistemic failures. This is a genuine architectural limitation, not a prompt engineering problem.

```bash
# Run a single experiment
cd experiments
pip3 install -r requirements.txt
python3 -m harness.runner --pattern blackboard_v2 --benchmark code_review

# Compare against baselines
python3 -m harness.runner --pattern blackboard_v2 --benchmark code_review --compare

# Full matrix (all patterns x all benchmarks)
python3 -m harness.runner --pattern all --benchmark all --compare
```

### 5. The Collection Pipeline (`pipeline/`)

The 8-agent blackboard system that built the corpus. Each agent reads from and writes to a shared PostgreSQL workspace using `FOR UPDATE SKIP LOCKED` for safe concurrency:

```
Agent 1 (Collector)  -->  Agent 2 (Filter)  -->  Agent 3b (Analyst)  -->  Agent 4 (Enricher)
                                                                               |
Agent 0 (Human)  <--  Agent 8 (Clustering)  <--  Agent 6 (Reproducer)  <--  Agent 5 (Scout)
```

| Agent | Purpose | LLM |
|-------|---------|-----|
| Agent 1 | Collect papers from OpenAlex, Crossref, DBLP, CSV seed lists | -- |
| Agent 2 | Relevance filtering (1-5 score + MAS branch classification) | GPT-5-mini |
| Agent 3b | Deep structured analysis (coordination pattern, theoretical grounding, Rosetta entry) | GPT-5.1 |
| Agent 4 | Citation graph enrichment via OpenAlex API | -- |
| Agent 5 | Code discovery via Papers with Code + GitHub | -- |
| Agent 6 | Reproduction feasibility assessment | -- |
| Agent 8 | Semi-supervised clustering + UMAP projection | text-embedding-3-small |
| Agent 0 | Human researcher -- taxonomy design, quality review, anchor refinement | -- |

The pipeline itself is the case study for our companion paper on human-AI co-research (Agent 0).

### 6. The Research Knowledge Base (`research/`)

14 structured research documents (~200KB) formalizing the bridge between classical and modern MAS:

| Document | Content |
|----------|---------|
| `cluster-guide.md` | Full 16-cluster taxonomy with boundary rationale |
| `why-mas-works.md` | 8 design principles grounded in failure analysis |
| `theoretical-foundations.md` | Formal treatment of each MAS pillar |
| `classical-mas-llm-bridge.md` | Direct concept mapping table |
| `organizational-principles.md` | Human team science transferred to agent teams |
| `evolution-from-classics-to-mcp.md` | Protocol evolution: KQML --> FIPA --> A2A --> MCP |

## Quick Start

### Browse the data (no setup required)

The `data/` directory contains pre-exported static files. No database needed:

```python
import json

# Load the corpus
with open('data/corpus.jsonl') as f:
    papers = [json.loads(line) for line in f]

# Find Lost Canaries -- classical papers the modern world forgot
with open('data/lost-canaries.json') as f:
    canaries = json.load(f)
    for c in canaries[:5]:
        print(f"{c['title']} ({c['year']}) -- {c['citation_count']} citations, "
              f"modernity score: {c['modernity_score']}")

# Papers using blackboard pattern that don't cite Nii 1986
blackboard_papers = [p for p in papers
    if p.get('coordination_pattern') == 'blackboard'
    and p.get('year', 0) >= 2023]
print(f"\n{len(blackboard_papers)} modern blackboard papers")
```

### Run experiments

```bash
cd experiments
pip3 install -r requirements.txt

# Set your API key (Anthropic or OpenAI)
export ANTHROPIC_API_KEY="your-key"

# Run the star result
python3 -m harness.runner --pattern blackboard_v2 --benchmark code_review --compare
```

### Run the collection pipeline

```bash
cd pipeline
pip3 install -r requirements.txt

# Set up Postgres (see schema.sql)
export SUTRA_DB_URL="postgresql://user:pass@host/sutra"

# Collect papers from OpenAlex
python3 -m assembly.agent1_collector --max-papers 100

# Filter for MAS relevance
python3 -m assembly.agent2_filter

# Deep analysis
python3 -m assembly.agent3b_analyst_async
```

## The Papers

### Paper 1: Sutra

**"Sutra: Threading Classical Coordination Through the Age of LLM Agents"**

A survey of 17,969 papers across 30 years of MAS research, organized into 16 pillars. Introduces the Lost Canary Algorithm for detecting forgotten concepts, the Rosetta Stone mapping between classical and modern terminology, and 8 design principles for reliable multi-agent coordination. Provides empirical evidence that classical coordination patterns (particularly the blackboard control shell) significantly outperform naive approaches.

Target: ArXiv (cs.MA + cs.AI), AAMAS 2027.

### Paper 2: Agent 0

**"Agent 0: Why Reliable AI-Assisted Research Requires Coordination Infrastructure, Not Full Autonomy"**

Formalizes the human researcher as Agent 0 -- a first-class team member in a multi-agent research system, not a passive supervisor. Presents evidence from failure analysis of 6 systems, performative rediscovery in 7 frameworks, and a self-referential ablation of the 8-agent pipeline used to build this corpus.

Target: Nature Machine Intelligence, NeurIPS 2027.

## Corpus Construction and Validation

The corpus was built by a multi-source pipeline and validated through 6 recall tests:

| Test | Method | Recall |
|------|--------|--------|
| AAMAS Best Papers (2011-2025) | 7 MAS-relevant winners | 100% (after DBLP supplement) |
| AAMAS 2025, 6 subfields | 20 papers sampled | 100% (after DBLP supplement) |
| Year-by-Year, 30 years | 20 samples/year | 97-100% (after DBLP supplement) |
| Dorri et al. 2018 survey bibliography | 159 refs (clean room) | 96% (MAS-adjusted) |
| Zhang et al. 2025 survey bibliography | 181 refs (clean room) | 81% (MAS-adjusted) |

The initial automated pipeline (ArXiv + OpenAlex) had systematic bias: 75% recall for LLM-agent papers but only 5-25% for AAMAS proceedings. A targeted DBLP import of 9,003 proceedings papers plus 2,314 papers from 12 additional venues resolved the gap. The bias pattern itself -- modern papers found easily, classical proceedings missed entirely -- is direct evidence of the publication ecosystem disconnect this project characterizes.

**Known limitations**:

- **Abstract availability**: 9,879 of 17,969 papers (55%) include full abstracts sourced from open-access repositories (ArXiv, OpenAlex, Semantic Scholar). The remaining 8,090 papers (45%) are title-only -- predominantly proceedings imports from DBLP (AAMAS, AAAI, IJCAI) where abstracts are behind publisher paywalls. We do not redistribute copyrighted abstracts. 98.3% of papers (17,655/17,969) carry at least one external identifier (DOI, OpenAlex ID, ArXiv ID, or Semantic Scholar ID) linking to the original source where the full text can be accessed. Coverage: OpenAlex 96.9%, DOI 49.2%, ArXiv 22.3%, Semantic Scholar 3.5%. All 17,969 papers have rich structured analysis (coordination pattern, theoretical grounding, Rosetta Stone entry) produced by Agent 3b -- for title-only papers, analysis was performed using title, citation context, and metadata.
- **Scope**: Applied MAS from domain-specific venues (IEEE Transactions, defense journals) has ~80% recall. Single-agent RL foundations cited by MAS surveys (DQN, A3C) are excluded by scope.

## Database Schema

For those running the pipeline or dashboard with a local Postgres instance:

| Table | Description |
|-------|-------------|
| `papers` | Core table: title, year, abstract, DOIs, citation count, analysis JSONB, pipeline status, modernity score |
| `paper_clusters` | Cluster assignment + UMAP (x, y) coordinates per paper |
| `cluster_meta` | 16 cluster labels, descriptions, paper counts |
| `citation_edges` | Directed citation graph (citing_id, cited_id) |
| `reinvention_edges` | Classical-to-modern paper pairs with overlap scores |
| `clustering_runs` | Clustering execution history |
| `paper_sources` | Source provenance per paper |

The `papers.analysis` JSONB column (populated by Agent 3b) contains:
- `coordination_pattern`: supervisor, blackboard, contract_net, bdi, debate, etc.
- `theoretical_grounding`: strong / moderate / weak / none
- `classical_concepts`: concepts the paper cites
- `classical_concepts_missing`: concepts the paper *should* cite but doesn't
- `rosetta_entry`: the classical-to-modern mapping for this paper
- `key_contribution_summary`: 3-5 sentence summary

See `pipeline/schema.sql` for full CREATE TABLE statements.

## Project Structure

```
sutra/
├── data/                    # Pre-exported corpus data (JSONL, CSV, JSON)
├── experiments/             # 9 MAS patterns + 2 baselines, 5 benchmarks, 58 results
│   ├── harness/             #   Test framework (base types, runner, reporter)
│   ├── patterns/            #   Pattern implementations (~2,200 lines Python)
│   ├── benchmarks/          #   5 standardized evaluation tasks
│   └── results/             #   58 JSON experiment results with full traces
├── pipeline/                # 8-agent paper collection and analysis system
│   ├── assembly/            #   Agent implementations
│   ├── apis/                #   OpenAlex, Crossref, LLM wrappers
│   └── schema.sql           #   Postgres table definitions
├── research/                # 10 structured knowledge base documents (~200KB)
└── scripts/
    └── export-corpus.sh     # Export data from Postgres to static files
```

## Adding Your Own Patterns

The experiment harness is designed for extension:

```python
# patterns/my_pattern.py
from harness.base import MASPattern, Agent, ExperimentResult, BenchmarkTask

class MyPattern(MASPattern):
    name = "my_pattern"
    description = "My coordination mechanism"
    classical_source = "Author (Year)"

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        # Define your agents
        ...

    def run(self, task: BenchmarkTask) -> ExperimentResult:
        # Implement coordination logic
        ...
```

Register in `harness/runner.py` and run:
```bash
python3 -m harness.runner --pattern my_pattern --benchmark all --compare
```

## Citation

If you use this corpus, taxonomy, or experiment harness in your research:

```bibtex
@article{viswanathan2026sutra,
  title={Sutra: Threading Classical Coordination Through the Age of LLM Agents},
  author={Viswanathan, Balaji},
  journal={arXiv preprint},
  year={2026}
}
```

## License

Apache 2.0. Use the data, patterns, and tools freely. Attribution appreciated.

---

*Part of the [Kapi AI](https://getkapi.com) research portfolio.*
