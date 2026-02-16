# MAS Pattern Experiment Harness

**9 classical coordination patterns + 2 baselines, evaluated across 5 benchmarks. 58 experiment results with full traces.**

## What This Tests

The Sutra paper's thesis: *classical MAS research solved coordination problems that modern LLM agent builders are unknowingly re-encountering.* This harness tests that empirically -- do classical coordination patterns actually improve LLM agent performance?

Every experiment follows the same structure:
1. Take a **benchmark task** (a problem with known expected aspects and an evaluation rubric)
2. Give it to a **coordination pattern** (which configures agents, decides who talks to whom, and produces output)
3. Score the output with **LLM-as-judge** (0-100 against the rubric)
4. Record everything: quality score, tokens consumed, wall time, per-agent stats, full message traces

All results were produced with Claude Opus 4.6 via Azure Anthropic Foundry. N=1 per experiment (acknowledged limitation -- see below).

## Results Summary

See [`results/report.md`](results/report.md) for the full matrix and analysis, or [`results/results-matrix.csv`](results/results-matrix.csv) for a machine-readable export.

### Quality Score Matrix

| Pattern | Code Rev. | Res. Synth. | Planning | CF V1 | CF V2 | Mean |
|---------|-----------|-------------|----------|-------|-------|------|
| SingleAgent (baseline) | 92 | 50 | 50 | 82 | 62 | 67.2 |
| NaiveMultiAgent (baseline) | 92 | 50 | 72 | 72 | 62 | 69.6 |
| Blackboard V1 (static) | 62 | 50 | 50 | 72 | 72 | 61.2 |
| **Blackboard V2 (LLM shell)** | **95** | 88 | 72 | 82 | 82 | **83.8** |
| Contract Net | 88 | 62 | 72 | 88 | 42 | 70.4 |
| Stigmergy | 92 | 72 | 62 | 88 | 62 | 75.2 |
| BDI | 85 | 72 | 72 | 72 | 72 | 74.6 |
| Supervisor | 88 | 72 | 72 | 72 | 72 | 75.2 |
| Debate | 82 | 78 | 72 | 62 | 72 | 73.2 |
| Generator/Critic | 88 | 72 | 72 | 82 | 72 | 77.2 |
| Joint Persistent Goals | 90 | 82 | 62 | 82 | **52** | 73.6 |

### Star Result 1: The Control Shell Breakthrough

Blackboard V1 vs V2 on Code Review -- same agents, same benchmark, same model:

| | V1 (static) | V2 (LLM shell) | Delta |
|---|---|---|---|
| Quality | 62 | **95** | **+53%** |
| Tokens | 26,869 | 13,361 | **-50%** |

Nii (1986) identified three blackboard components: shared state, knowledge sources, **control shell**. Modern frameworks implement the first two but skip the third. The LLM control shell -- which reads the board and decides what to activate next -- is the most valuable component.

### Star Result 2: The Epistemic Failure Gap

JPG scored **52/100** on Cascading Failure V2 (the *lowest* of all patterns) despite using the *most* tokens (37,567). Cohen & Levesque's obligation-to-inform requires agents to detect when their goal is unachievable. LLMs cannot reliably do this -- they lack the metacognitive ability to detect their own epistemic limitations. This is a genuine architectural limitation, not a prompt engineering problem.

## The 5 Benchmarks

Each benchmark tests a different dimension of multi-agent coordination:

| Benchmark | What It Tests | Key Challenge |
|-----------|--------------|---------------|
| **Code Review** | Divide-and-conquer analysis | Flask app with ~12 planted issues (SQL injection, XSS, plaintext passwords). Can agents split the work and catch everything? |
| **Research Synthesis** | Building on each other's insights | 5 real MAS paper abstracts. Synthesize across sources -- find consensus, disagreements, gaps. Not just summarize each one. |
| **Planning** | Internal consistency across concerns | Multi-tenant SaaS architecture. The hard part: keeping auth, API, data model, and deployment consistent with each other. |
| **Cascading Failure V1** | Contradiction detection | Fintech pipeline with an *obvious* impossible requirement (10M events/sec on a $50/month t2.micro). Do agents catch it or build on it? |
| **Cascading Failure V2** | Epistemic honesty | Vector DB comparison report requiring *actual* benchmark data. LLMs can't run benchmarks. Do they fabricate numbers or honestly say "I can't produce this data"? |

**Why these 5:** Code Review and Research Synthesis test routine collaborative work. Planning tests coherence across concerns. The two Cascading Failure benchmarks are the novel ones -- V1 tests whether agents catch visible contradictions, V2 tests whether agents can detect that *they themselves* are incapable of completing a subtask. V2 is the critical one for JPG because the failure only emerges during execution, not during planning.

## The 11 Patterns

### Baselines (2)

| Pattern | What It Is | Purpose |
|---------|-----------|---------|
| **SingleAgent** | One agent, one shot, no coordination | Control condition. Is coordination even worth the overhead? |
| **NaiveMultiAgent** | 3 agents work independently, outputs concatenated | The "bag of agents" anti-pattern. Kim et al. (2025) showed this causes 17.2x error amplification. |

### Classical Patterns (9)

| Pattern | Classical Source | Key Mechanism | What It Tests |
|---------|----------------|---------------|---------------|
| **Blackboard V1** | Nii (1986) | Shared state + static round-robin scheduling | Baseline blackboard -- agents take turns regardless of board content |
| **Blackboard V2** | Nii (1986), faithful | Shared state + LLM control shell + incremental summarization + early stopping | Whether content-aware scheduling beats static scheduling |
| **Contract Net** | Smith (1980) | Manager decomposes, agents bid on subtasks, best bidder executes | Decentralized task allocation via market mechanisms |
| **Stigmergy** | Grasse (1959) | Indirect coordination through shared document modification | Whether agents can coordinate without direct communication |
| **BDI** | Rao & Georgeff (1995) | Belief-Desire-Intention deliberation cycle | Whether explicit mental state tracking improves decisions |
| **Supervisor** | Anthropic (2025) | Central coordinator routes tasks, reviews work, requests revisions | Hierarchical orchestration with quality gates |
| **Debate** | Du et al. (2023) | Agents take opposing positions, judge evaluates | Whether adversarial dialogue improves output quality |
| **Generator/Critic** | Google ADK (2025) | Generate, critique with typed feedback, revise | Iterative refinement via structured critique |
| **Joint Persistent Goals** | Cohen & Levesque (1990) | Mutual commitment with obligation-to-inform on failure | Whether agents can detect and report their own inability to complete a task |

## Quick Start

```bash
cd experiments
pip3 install -r requirements.txt

# Set your API key (one of these)
export ANTHROPIC_API_KEY="your-key"
# or for Azure-hosted Anthropic:
export AZURE_ANTHROPIC_ENDPOINT="https://your-endpoint"
export AZURE_API_KEY="your-key"

# Run the star result
python3 -m harness.runner --pattern blackboard_v2 --benchmark code_review

# Run with baseline comparison
python3 -m harness.runner --pattern blackboard_v2 --benchmark code_review --compare

# Run all benchmarks for a pattern
python3 -m harness.runner --pattern blackboard_v2 --benchmark all

# Run the full matrix (all patterns x all benchmarks)
python3 -m harness.runner --pattern all --benchmark all
```

Results are saved to `results/` as JSON with full traces.

## Architecture

```
experiments/
├── harness/                    # Core framework
│   ├── base.py                 # Abstract types: MASPattern, Agent, Message, BenchmarkTask
│   ├── llm_client.py           # Multi-provider LLM client (Anthropic + OpenAI)
│   ├── runner.py               # Experiment orchestrator + LLM-as-judge evaluator
│   └── reporter.py             # Markdown report generator
├── patterns/                   # 9 pattern implementations + 2 baselines
│   ├── baselines.py            # SingleAgent + NaiveMultiAgent (controls)
│   ├── blackboard.py           # Nii (1986) — static round-robin
│   ├── blackboard_v2.py        # Nii (1986) — LLM control shell + summarization
│   ├── contract_net.py         # Smith (1980) — announce/bid/award
│   ├── stigmergy.py            # Grasse (1959) — environment-mediated coordination
│   ├── bdi.py                  # Rao & Georgeff (1995) — belief-desire-intention
│   ├── supervisor.py           # Anthropic (2025) — orchestrator-worker
│   ├── debate.py               # Du et al. (2023) — structured argumentation
│   ├── generator_critic.py     # Google ADK (2025) — iterative refinement
│   └── joint_persistent_goals.py # Cohen & Levesque (1990) — obligation to inform
├── benchmarks/                 # 5 standardized evaluation tasks
│   ├── code_review.py          # Flask app with ~12 planted security issues
│   ├── research_synthesis.py   # 5 MAS paper abstracts to synthesize
│   ├── planning.py             # Multi-tenant SaaS architecture planning
│   ├── cascading_failure.py    # Obvious contradiction in requirements
│   └── cascading_failure_v2.py # Epistemic limitation (data LLMs can't produce)
├── results/                    # 58 JSON result files + summary exports
│   ├── results-matrix.csv      # Machine-readable: all scores, tokens, timing
│   ├── report.md               # Human-readable: matrices, rankings, findings
│   └── export_matrix.py        # Script to regenerate CSV + report from JSONs
└── requirements.txt
```

## Metrics

Every experiment captures:
- **Quality Score** (0-100): LLM-as-judge against task-specific rubric
- **Total Tokens**: Input + output across all agents and all rounds
- **Token Efficiency**: Quality points per 1,000 tokens
- **Rounds**: Number of coordination rounds
- **Wall Time**: Total execution time
- **Agent Stats**: Per-agent token usage, messages sent/received
- **Message Trace**: Full communication log with performatives (inform, request, cfp, propose, accept)

## Replicability

**What replicates:** The experiment infrastructure is fully self-contained. Anyone with an Anthropic or OpenAI API key can run the full matrix. All benchmarks are deterministic (same task, same rubric, same expected aspects). The pattern implementations are fixed.

**What varies:** LLM outputs are stochastic. Most patterns use temperature=0.7, some use 0.3. The LLM-as-judge uses temperature=0.0 but still has non-determinism. Expect scores to vary by ~10-15 points across runs. The qualitative findings (V2 >> V1, JPG fails on epistemic tasks) should replicate; exact numbers will not.

**Known limitations:**
- **N=1 per experiment**: No error bars. Statistical reruns planned for the journal version.
- **Single model**: All experiments on Claude Opus 4.6. Results may differ on GPT-5, Gemini 3, etc.
- **LLM-as-judge bias**: The judge is the same model that produced the output. Self-evaluation bias is possible.
- **50-point defaults**: When the judge fails to parse its own output, score defaults to 50. These are marked with `*` in the paper's table and excluded from mean calculations.

## Adding Patterns or Benchmarks

**New pattern:**
```python
# patterns/my_pattern.py
from harness.base import MASPattern, Agent, BenchmarkTask, ExperimentResult, Role

class MyPattern(MASPattern):
    name = "my_pattern"
    classical_source = "Author (Year)"
    description = "What this pattern does"

    def setup(self, task: BenchmarkTask) -> list[Agent]:
        self.agents = [Agent(name="agent_1", role=Role.SPECIALIST, system_prompt="...")]
        return self.agents

    async def run(self, task: BenchmarkTask) -> ExperimentResult:
        # Implement coordination logic
        ...
```
Register in `harness/runner.py` `PATTERN_REGISTRY`, then run:
```bash
python3 -m harness.runner --pattern my_pattern --benchmark all --compare
```

**New benchmark:**
```python
# benchmarks/my_benchmark.py
from harness.base import BenchmarkTask

def get_task() -> BenchmarkTask:
    return BenchmarkTask(
        id="my_bench_01",
        name="My Benchmark",
        description="What agents should do",
        input_data="The actual task prompt",
        expected_aspects=["Aspect 1", "Aspect 2"],
        evaluation_rubric={"criterion_1": "How to score this dimension"},
    )
```
Register in `harness/runner.py` `BENCHMARK_REGISTRY`, then run:
```bash
python3 -m harness.runner --pattern all --benchmark my_benchmark
```
