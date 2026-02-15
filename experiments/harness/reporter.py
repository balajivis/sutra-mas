"""Report generation for experiment results."""

from __future__ import annotations

from datetime import datetime

from harness.base import ExperimentResult


def generate_report(results: list[ExperimentResult]) -> str:
    """Generate a Markdown report from experiment results."""
    lines = []
    lines.append(f"# MAS Pattern Experiment Report")
    lines.append(f"")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")

    # Group by benchmark
    benchmarks: dict[str, list[ExperimentResult]] = {}
    for r in results:
        benchmarks.setdefault(r.benchmark_name, []).append(r)

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Pattern | Benchmark | Quality | Tokens | Efficiency | Agents | Rounds | Time |")
    lines.append("|---------|-----------|---------|--------|------------|--------|--------|------|")
    for r in sorted(results, key=lambda x: (x.benchmark_name, x.pattern_name)):
        lines.append(
            f"| {r.pattern_name} | {r.benchmark_name} | {r.quality_score:.1f} | "
            f"{r.total_tokens:,} | {r.token_efficiency:.2f} | {r.num_agents} | "
            f"{r.num_rounds} | {r.wall_time_seconds:.1f}s |"
        )
    lines.append("")

    # Per-benchmark comparison
    for bench_name, bench_results in benchmarks.items():
        lines.append(f"## Benchmark: {bench_name}")
        lines.append("")

        # Find baselines
        single = next((r for r in bench_results if r.pattern_name == "baseline_single"), None)
        naive = next((r for r in bench_results if r.pattern_name == "baseline_naive"), None)
        patterns = [r for r in bench_results if not r.pattern_name.startswith("baseline_")]

        if single or naive:
            lines.append("### Baselines")
            lines.append("")
            if single:
                lines.append(f"- **Single Agent**: Quality {single.quality_score:.1f}, {single.total_tokens:,} tokens")
            if naive:
                lines.append(f"- **Naive Multi-Agent**: Quality {naive.quality_score:.1f}, {naive.total_tokens:,} tokens")
            lines.append("")

        if patterns:
            lines.append("### Pattern Results")
            lines.append("")
            lines.append("| Pattern | Quality | vs Single | vs Naive | Tokens | Efficiency |")
            lines.append("|---------|---------|-----------|----------|--------|------------|")

            for r in patterns:
                delta_single = ""
                delta_naive = ""
                if single and single.quality_score > 0:
                    d = ((r.quality_score - single.quality_score) / single.quality_score) * 100
                    delta_single = f"{d:+.1f}%"
                if naive and naive.quality_score > 0:
                    d = ((r.quality_score - naive.quality_score) / naive.quality_score) * 100
                    delta_naive = f"{d:+.1f}%"

                lines.append(
                    f"| {r.pattern_name} | {r.quality_score:.1f} | {delta_single} | "
                    f"{delta_naive} | {r.total_tokens:,} | {r.token_efficiency:.2f} |"
                )
            lines.append("")

        # Agent-level stats
        for r in patterns:
            if r.agent_stats:
                lines.append(f"### Agent Stats: {r.pattern_name}")
                lines.append("")
                lines.append("| Agent | Role | Tokens In | Tokens Out | Messages Sent | Messages Received |")
                lines.append("|-------|------|-----------|------------|---------------|-------------------|")
                for name, stats in r.agent_stats.items():
                    lines.append(
                        f"| {name} | {stats.get('role', '?')} | "
                        f"{stats.get('tokens_in', 0):,} | {stats.get('tokens_out', 0):,} | "
                        f"{stats.get('messages_sent', 0)} | {stats.get('messages_received', 0)} |"
                    )
                lines.append("")

    # Token budget analysis
    lines.append("## Token Budget Analysis")
    lines.append("")
    total = sum(r.total_tokens for r in results)
    lines.append(f"- **Total tokens used**: {total:,}")
    lines.append(f"- **Total experiments**: {len(results)}")
    lines.append(f"- **Average tokens per experiment**: {total // max(len(results), 1):,}")
    lines.append("")

    return "\n".join(lines)


def print_summary(results: list[ExperimentResult]) -> None:
    """Print a concise summary to stdout."""
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT SUMMARY")
    print(f"{'='*60}")
    print(f"  Experiments run: {len(results)}")
    print(f"  Total tokens:   {sum(r.total_tokens for r in results):,}")
    print(f"  Total time:     {sum(r.wall_time_seconds for r in results):.1f}s")
    print(f"")
    print(f"  {'Pattern':<20} {'Benchmark':<20} {'Quality':>8} {'Tokens':>10} {'Eff':>8}")
    print(f"  {'-'*18:<20} {'-'*18:<20} {'-'*6:>8} {'-'*8:>10} {'-'*6:>8}")
    for r in sorted(results, key=lambda x: -x.quality_score):
        print(
            f"  {r.pattern_name:<20} {r.benchmark_name:<20} "
            f"{r.quality_score:>7.1f} {r.total_tokens:>10,} {r.token_efficiency:>7.2f}"
        )
    print(f"{'='*60}")
