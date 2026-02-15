# MAS Pattern Test Harness

Evaluate classical multi-agent coordination patterns through LLM agents. Bridge theory and practice.

## Quick Start

```bash
cd /Users/bv/Code/active/kapi-platform/docs/research/experiments

# Install dependencies
pip3 install -r requirements.txt

# Set API keys
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"

# Run a single experiment
python3 -m harness.runner --pattern blackboard --benchmark code_review --model claude-opus-4-6

# Run with baseline comparison
python3 -m harness.runner --pattern blackboard --benchmark code_review --model claude-opus-4-6 --compare

# Run all benchmarks for a pattern
python3 -m harness.runner --pattern blackboard --benchmark all --model claude-opus-4-6

# Run all patterns on all benchmarks (full matrix)
python3 -m harness.runner --pattern all --benchmark all --model claude-opus-4-6 --compare
```

## Architecture

```
experiments/
├── harness/                    # Core framework
│   ├── base.py                 # Abstract types: MASPattern, Agent, Message, BenchmarkTask
│   ├── llm_client.py           # Multi-provider LLM client (Anthropic + OpenAI)
│   ├── runner.py               # Experiment orchestrator
│   └── reporter.py             # Markdown report generator
├── patterns/                   # Pattern implementations
│   ├── baselines.py            # SingleAgent + NaiveMultiAgent (controls)
│   ├── blackboard.py           # Nii (1986) — shared state, knowledge sources
│   ├── contract_net.py         # Smith (1980) — announce/bid/award
│   ├── stigmergy.py            # Heylighen — environment-mediated coordination
│   ├── bdi.py                  # Rao & Georgeff (1995) — belief-desire-intention
│   ├── supervisor.py           # Anthropic orchestrator-worker pattern
│   ├── debate.py               # Du et al. (2023) — opposing positions + judge
│   └── generator_critic.py     # Google ADK Pattern #5 — iterative refinement
├── benchmarks/                 # Standardized evaluation tasks
│   ├── code_review.py          # Review Flask code for bugs/security
│   ├── research_synthesis.py   # Synthesize 5 MAS paper abstracts
│   └── planning.py             # Plan a multi-tenant SaaS app
├── discovery/                  # GitHub repo discovery per pattern
├── results/                    # Experiment output (JSON + Markdown)
└── requirements.txt
```

## Patterns

| Pattern | Classical Source | Key Mechanism | Agents |
|---------|----------------|---------------|--------|
| `baseline_single` | Control | One agent, one shot | 1 |
| `baseline_naive` | Anti-pattern | Independent agents, no coordination | 3 |
| `blackboard` | Nii (1986) | Shared state space, control shell activates agents | 3 |
| `contract_net` | Smith (1980) | Manager decomposes, agents bid, best bidder executes | 4 |
| `stigmergy` | Heylighen | Agents modify shared environment, no direct messaging | 4 |
| `bdi` | Rao & Georgeff (1995) | Belief-Desire-Intention deliberation cycle | 3 |
| `supervisor` | Anthropic (2025) | Central coordinator routes to specialists | 4 |
| `debate` | Du et al. (2023) | Proponent vs Opponent, Judge synthesizes | 3 |
| `generator_critic` | Google ADK (2025) | Generate, critique with typed feedback, iterate | 2 |

## Benchmarks

| Benchmark | Task | Expected Issues | Tokens |
|-----------|------|----------------|--------|
| `code_review` | Review Flask code with 12+ issues | SQL injection, XSS, plaintext passwords | ~30K |
| `research_synthesis` | Synthesize 5 MAS paper abstracts | Consensus, disagreements, gaps | ~40K |
| `planning` | Plan multi-tenant SaaS architecture | Architecture, security, roadmap | ~40K |

## Metrics

Every experiment reports:
- **Quality Score** (0-100): LLM-as-judge evaluation against task rubric
- **Total Tokens**: Input + output tokens across all agents
- **Token Efficiency**: Quality points per 1000 tokens
- **Rounds**: Number of coordination rounds
- **Wall Time**: Total execution time

## Adding a New Pattern

1. Create `patterns/my_pattern.py`
2. Implement `MASPattern` (see `base.py`):
   - `setup(task)` — configure agents
   - `run(task)` — execute coordination, return `ExperimentResult`
3. Register in `harness/runner.py` `PATTERN_REGISTRY`
4. Run: `python3 -m harness.runner --pattern my_pattern --benchmark all`

## Adding a New Benchmark

1. Create `benchmarks/my_benchmark.py`
2. Implement `get_task()` returning a `BenchmarkTask`
3. Register in `harness/runner.py` `BENCHMARK_REGISTRY`
4. Run: `python3 -m harness.runner --pattern all --benchmark my_benchmark`
