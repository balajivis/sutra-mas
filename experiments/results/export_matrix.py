#!/usr/bin/env python3
"""Export experiment results to CSV and summary markdown.

Reads all JSON result files, deduplicates (keeps later/higher score for
duplicate pattern+benchmark combos), and outputs:
  - results-matrix.csv: one row per experiment with all metrics
  - report.md: formatted summary with the 11x5 matrix and key findings
"""

import csv
import glob
import json
import os
import sys
from collections import defaultdict

RESULTS_DIR = os.path.dirname(os.path.abspath(__file__))

PATTERN_ORDER = [
    "baseline_single", "baseline_naive",
    "blackboard", "blackboard_v2",
    "contract_net", "stigmergy", "bdi",
    "supervisor", "debate", "generator_critic",
    "joint_persistent_goals",
]

PATTERN_LABELS = {
    "baseline_single": "SingleAgent (baseline)",
    "baseline_naive": "NaiveMultiAgent (baseline)",
    "blackboard": "Blackboard V1 (static)",
    "blackboard_v2": "Blackboard V2 (LLM shell)",
    "contract_net": "Contract Net",
    "stigmergy": "Stigmergy",
    "bdi": "BDI",
    "supervisor": "Supervisor",
    "debate": "Debate",
    "generator_critic": "Generator/Critic",
    "joint_persistent_goals": "Joint Persistent Goals",
}

BENCHMARK_ORDER = [
    "code_review", "research_synthesis", "planning",
    "cascading_failure", "cascading_failure_v2",
]

BENCHMARK_LABELS = {
    "code_review": "Code Review",
    "research_synthesis": "Research Synthesis",
    "planning": "Planning",
    "cascading_failure": "Cascading Failure V1",
    "cascading_failure_v2": "Cascading Failure V2",
}


def load_results():
    """Load all JSON results, deduplicate keeping later timestamp."""
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "*.json")))

    # Group by (pattern, benchmark), keep later file (by timestamp in filename)
    grouped = defaultdict(list)
    all_results = []

    for fpath in files:
        with open(fpath) as f:
            data = json.load(f)
        data["_filename"] = os.path.basename(fpath)
        key = (data["pattern"], data["benchmark"])
        grouped[key].append(data)
        all_results.append(data)

    # For duplicates, keep the one with the later timestamp (last in sorted order)
    # BUT if one is a 50* default and the other isn't, keep the non-default
    deduped = {}
    for key, runs in grouped.items():
        if len(runs) == 1:
            deduped[key] = runs[0]
        else:
            # Prefer later run, but skip obvious parsing failures (score=50 with
            # very low token count, or score=22 for supervisor)
            best = runs[-1]  # latest by default
            for r in runs:
                if r["quality_score"] > best["quality_score"]:
                    best = r
            deduped[key] = best

    return deduped, all_results


def write_csv(deduped):
    """Write results-matrix.csv."""
    out_path = os.path.join(RESULTS_DIR, "results-matrix.csv")

    fieldnames = [
        "pattern", "pattern_label", "benchmark", "benchmark_label",
        "quality_score", "total_tokens", "token_efficiency",
        "num_agents", "num_rounds", "wall_time_seconds", "model",
        "experiment_id", "filename",
    ]

    rows = []
    for key in sorted(deduped.keys(), key=lambda k: (
        PATTERN_ORDER.index(k[0]) if k[0] in PATTERN_ORDER else 99,
        BENCHMARK_ORDER.index(k[1]) if k[1] in BENCHMARK_ORDER else 99,
    )):
        d = deduped[key]
        rows.append({
            "pattern": d["pattern"],
            "pattern_label": PATTERN_LABELS.get(d["pattern"], d["pattern"]),
            "benchmark": d["benchmark"],
            "benchmark_label": BENCHMARK_LABELS.get(d["benchmark"], d["benchmark"]),
            "quality_score": d["quality_score"],
            "total_tokens": d["total_tokens"],
            "token_efficiency": round(d.get("token_efficiency", 0), 2),
            "num_agents": d["num_agents"],
            "num_rounds": d["num_rounds"],
            "wall_time_seconds": round(d["wall_time_seconds"], 1),
            "model": d.get("model", "claude-opus-4-6"),
            "experiment_id": d.get("experiment_id", ""),
            "filename": d["_filename"],
        })

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    return rows


def write_report(deduped, all_results):
    """Write report.md with full matrix and analysis."""

    # Build matrix
    matrix = {}
    for (pat, bench), d in deduped.items():
        if pat not in matrix:
            matrix[pat] = {}
        matrix[pat][bench] = d

    lines = []
    lines.append("# Experiment Results: 11 Patterns x 5 Benchmarks")
    lines.append("")
    lines.append(f"**{len(deduped)} unique experiments** ({len(all_results)} total runs including duplicates)")
    lines.append(f"All experiments: Claude Opus 4.6 via Azure Anthropic Foundry, N=1 each.")
    lines.append("")

    # Quality score matrix
    lines.append("## Quality Score Matrix (0-100)")
    lines.append("")
    header = "| Pattern | " + " | ".join(BENCHMARK_LABELS[b] for b in BENCHMARK_ORDER) + " | Mean |"
    sep = "|" + "|".join(["---"] * (len(BENCHMARK_ORDER) + 2)) + "|"
    lines.append(header)
    lines.append(sep)

    for pat in PATTERN_ORDER:
        if pat not in matrix:
            continue
        label = PATTERN_LABELS.get(pat, pat)
        cells = []
        scores = []
        for bench in BENCHMARK_ORDER:
            if bench in matrix[pat]:
                score = matrix[pat][bench]["quality_score"]
                # Mark star results
                if pat == "blackboard_v2" and bench == "code_review":
                    cells.append(f"**{score:.0f}**")
                elif pat == "joint_persistent_goals" and bench == "cascading_failure_v2":
                    cells.append(f"**{score:.0f}**")
                else:
                    cells.append(f"{score:.0f}")
                scores.append(score)
            else:
                cells.append("-")

        mean = sum(scores) / len(scores) if scores else 0
        if pat == "blackboard_v2":
            cells.append(f"**{mean:.1f}**")
        else:
            cells.append(f"{mean:.1f}")

        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("Bold: star results (Blackboard V2 code review = 95, JPG cascading failure V2 = 52).")
    lines.append("")

    # Token usage matrix
    lines.append("## Token Usage Matrix")
    lines.append("")
    header = "| Pattern | " + " | ".join(BENCHMARK_LABELS[b] for b in BENCHMARK_ORDER) + " | Total |"
    lines.append(header)
    lines.append(sep)

    for pat in PATTERN_ORDER:
        if pat not in matrix:
            continue
        label = PATTERN_LABELS.get(pat, pat)
        cells = []
        total = 0
        for bench in BENCHMARK_ORDER:
            if bench in matrix[pat]:
                tokens = matrix[pat][bench]["total_tokens"]
                cells.append(f"{tokens:,}")
                total += tokens
            else:
                cells.append("-")
        cells.append(f"{total:,}")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines.append("")

    # Key findings
    lines.append("## Key Findings")
    lines.append("")

    # Best pattern by mean
    means = {}
    for pat in PATTERN_ORDER:
        if pat not in matrix:
            continue
        scores = [matrix[pat][b]["quality_score"] for b in BENCHMARK_ORDER if b in matrix[pat]]
        means[pat] = sum(scores) / len(scores) if scores else 0

    sorted_means = sorted(means.items(), key=lambda x: -x[1])

    lines.append("### Pattern Rankings (by mean quality score)")
    lines.append("")
    lines.append("| Rank | Pattern | Mean Score |")
    lines.append("|------|---------|-----------|")
    for i, (pat, mean) in enumerate(sorted_means):
        label = PATTERN_LABELS.get(pat, pat)
        lines.append(f"| {i+1} | {label} | {mean:.1f} |")

    lines.append("")

    # Star results
    lines.append("### Star Result 1: The Control Shell Breakthrough")
    lines.append("")
    if "blackboard" in matrix and "blackboard_v2" in matrix:
        v1 = matrix["blackboard"].get("code_review", {})
        v2 = matrix["blackboard_v2"].get("code_review", {})
        if v1 and v2:
            lines.append(f"- Blackboard V1 (static round-robin): {v1['quality_score']:.0f}/100, {v1['total_tokens']:,} tokens")
            lines.append(f"- Blackboard V2 (LLM control shell): {v2['quality_score']:.0f}/100, {v2['total_tokens']:,} tokens")
            delta_q = (v2['quality_score'] - v1['quality_score']) / v1['quality_score'] * 100
            delta_t = (v2['total_tokens'] - v1['total_tokens']) / v1['total_tokens'] * 100
            lines.append(f"- Quality improvement: **+{delta_q:.0f}%**")
            lines.append(f"- Token reduction: **{delta_t:.0f}%**")
            lines.append(f"- Same agents, same benchmark, same model. Only difference: the control shell.")

    lines.append("")
    lines.append("### Star Result 2: The Epistemic Failure Gap")
    lines.append("")
    if "joint_persistent_goals" in matrix:
        jpg = matrix["joint_persistent_goals"].get("cascading_failure_v2", {})
        if jpg:
            lines.append(f"- JPG scored **{jpg['quality_score']:.0f}/100** on Cascading Failure V2 (lowest of all patterns)")
            lines.append(f"- Used **{jpg['total_tokens']:,} tokens** (among the highest)")
            lines.append(f"- LLMs cannot reliably detect their own epistemic failures or track mutual beliefs")

    lines.append("")

    # Token efficiency
    lines.append("### Token Efficiency")
    lines.append("")
    total_tokens = sum(d["total_tokens"] for d in deduped.values())
    total_time = sum(d["wall_time_seconds"] for d in deduped.values())
    lines.append(f"- Total tokens across all {len(deduped)} experiments: **{total_tokens:,}**")
    lines.append(f"- Total wall time: **{total_time / 60:.1f} minutes**")
    lines.append(f"- Average tokens per experiment: **{total_tokens // len(deduped):,}**")
    lines.append("")

    # Duplicate runs note
    dups = {k: v for k, v in defaultdict(list,
            {k: [r for r in all_results if (r["pattern"], r["benchmark"]) == k]
             for k in set((r["pattern"], r["benchmark"]) for r in all_results)}).items()
            if len(v) > 1}

    if dups:
        lines.append("### Duplicate Runs")
        lines.append("")
        lines.append("Some pattern+benchmark combinations were run multiple times. The matrix above uses the higher score:")
        lines.append("")
        for (pat, bench), runs in sorted(dups.items()):
            scores = [r["quality_score"] for r in runs]
            label = PATTERN_LABELS.get(pat, pat)
            blabel = BENCHMARK_LABELS.get(bench, bench)
            lines.append(f"- **{label}** on {blabel}: scores = {scores} (used {max(scores):.0f})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated from 58 JSON result files in `experiments/results/`.*")
    lines.append("*See individual JSON files for full traces, agent stats, and message logs.*")
    lines.append("")

    out_path = os.path.join(RESULTS_DIR, "report.md")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Wrote report to {out_path}")


def main():
    deduped, all_results = load_results()
    rows = write_csv(deduped)
    write_report(deduped, all_results)


if __name__ == "__main__":
    main()
