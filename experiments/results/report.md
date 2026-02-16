# Experiment Results: 11 Patterns x 5 Benchmarks

**55 unique experiments** (58 total runs including duplicates)
All experiments: Claude Opus 4.6 via Azure Anthropic Foundry, N=1 each.

## Quality Score Matrix (0-100)

| Pattern | Code Review | Research Synthesis | Planning | Cascading Failure V1 | Cascading Failure V2 | Mean |
|---|---|---|---|---|---|---|
| SingleAgent (baseline) | 92 | 50 | 50 | 82 | 62 | 67.2 |
| NaiveMultiAgent (baseline) | 92 | 50 | 72 | 72 | 62 | 69.6 |
| Blackboard V1 (static) | 62 | 50 | 50 | 72 | 72 | 61.2 |
| Blackboard V2 (LLM shell) | **95** | 88 | 72 | 82 | 82 | **83.8** |
| Contract Net | 88 | 62 | 72 | 88 | 42 | 70.4 |
| Stigmergy | 92 | 72 | 62 | 88 | 62 | 75.2 |
| BDI | 85 | 72 | 72 | 72 | 72 | 74.6 |
| Supervisor | 88 | 72 | 72 | 72 | 72 | 75.2 |
| Debate | 82 | 78 | 72 | 62 | 72 | 73.2 |
| Generator/Critic | 88 | 72 | 72 | 82 | 72 | 77.2 |
| Joint Persistent Goals | 90 | 82 | 62 | 82 | **52** | 73.6 |

Bold: star results (Blackboard V2 code review = 95, JPG cascading failure V2 = 52).

## Token Usage Matrix

| Pattern | Code Review | Research Synthesis | Planning | Cascading Failure V1 | Cascading Failure V2 | Total |
|---|---|---|---|---|---|---|
| SingleAgent (baseline) | 3,185 | 4,055 | 8,417 | 8,520 | 8,705 | 32,882 |
| NaiveMultiAgent (baseline) | 5,644 | 11,445 | 12,975 | 13,281 | 13,835 | 57,180 |
| Blackboard V1 (static) | 26,869 | 27,895 | 30,249 | 28,571 | 33,706 | 147,290 |
| Blackboard V2 (LLM shell) | 13,361 | 12,079 | 15,237 | 13,882 | 28,003 | 82,562 |
| Contract Net | 36,623 | 41,225 | 38,756 | 41,695 | 35,873 | 194,172 |
| Stigmergy | 92,623 | 95,529 | 96,365 | 96,465 | 96,652 | 477,634 |
| BDI | 7,347 | 51,918 | 34,054 | 63,419 | 74,236 | 230,974 |
| Supervisor | 138,425 | 93,626 | 118,013 | 120,131 | 118,530 | 588,725 |
| Debate | 21,587 | 33,406 | 34,290 | 34,800 | 35,722 | 159,805 |
| Generator/Critic | 8,440 | 11,053 | 44,163 | 44,670 | 44,385 | 152,711 |
| Joint Persistent Goals | 34,005 | 22,718 | 47,019 | 27,129 | 37,567 | 168,438 |

## Key Findings

### Pattern Rankings (by mean quality score)

| Rank | Pattern | Mean Score |
|------|---------|-----------|
| 1 | Blackboard V2 (LLM shell) | 83.8 |
| 2 | Generator/Critic | 77.2 |
| 3 | Stigmergy | 75.2 |
| 4 | Supervisor | 75.2 |
| 5 | BDI | 74.6 |
| 6 | Joint Persistent Goals | 73.6 |
| 7 | Debate | 73.2 |
| 8 | Contract Net | 70.4 |
| 9 | NaiveMultiAgent (baseline) | 69.6 |
| 10 | SingleAgent (baseline) | 67.2 |
| 11 | Blackboard V1 (static) | 61.2 |

### Star Result 1: The Control Shell Breakthrough

- Blackboard V1 (static round-robin): 62/100, 26,869 tokens
- Blackboard V2 (LLM control shell): 95/100, 13,361 tokens
- Quality improvement: **+53%**
- Token reduction: **-50%**
- Same agents, same benchmark, same model. Only difference: the control shell.

### Star Result 2: The Epistemic Failure Gap

- JPG scored **52/100** on Cascading Failure V2 (lowest of all patterns)
- Used **37,567 tokens** (among the highest)
- LLMs cannot reliably detect their own epistemic failures or track mutual beliefs

### Token Efficiency

- Total tokens across all 55 experiments: **2,292,373**
- Total wall time: **289.5 minutes**
- Average tokens per experiment: **41,679**

### Duplicate Runs

Some pattern+benchmark combinations were run multiple times. The matrix above uses the higher score:

- **NaiveMultiAgent (baseline)** on Code Review: scores = [50.0, 92.0] (used 92)
- **SingleAgent (baseline)** on Code Review: scores = [90.0, 92.0] (used 92)
- **Supervisor** on Code Review: scores = [22.0, 88.0] (used 88)

---

*Generated from 58 JSON result files in `experiments/results/`.*
*See individual JSON files for full traces, agent stats, and message logs.*
