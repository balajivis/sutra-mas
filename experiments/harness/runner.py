"""Experiment runner — orchestrates pattern execution on benchmark tasks."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Load .env from experiments/ directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from harness.base import BenchmarkTask, ExperimentResult, MASPattern
from harness.llm_client import LLMClient
from harness.reporter import generate_report, print_summary

# Pattern registry — maps name to module.class
PATTERN_REGISTRY: dict[str, str] = {
    "blackboard": "patterns.blackboard.BlackboardPattern",
    "blackboard_v2": "patterns.blackboard_v2.BlackboardV2Pattern",
    "contract_net": "patterns.contract_net.ContractNetPattern",
    "stigmergy": "patterns.stigmergy.StigmergyPattern",
    "bdi": "patterns.bdi.BDIPattern",
    "supervisor": "patterns.supervisor.SupervisorPattern",
    "debate": "patterns.debate.DebatePattern",
    "generator_critic": "patterns.generator_critic.GeneratorCriticPattern",
    "joint_persistent_goals": "patterns.joint_persistent_goals.JPGPattern",
    "baseline_single": "patterns.baselines.SingleAgentBaseline",
    "baseline_naive": "patterns.baselines.NaiveMultiAgentBaseline",
}

# Benchmark registry — maps name to module.function
BENCHMARK_REGISTRY: dict[str, str] = {
    "code_review": "benchmarks.code_review.get_task",
    "research_synthesis": "benchmarks.research_synthesis.get_task",
    "planning": "benchmarks.planning.get_task",
    "cascading_failure": "benchmarks.cascading_failure.get_task",
    "cascading_failure_v2": "benchmarks.cascading_failure_v2.get_task",
}


def load_class(dotted_path: str) -> type:
    """Dynamically import a class from a dotted path like 'module.ClassName'."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def load_function(dotted_path: str):
    """Dynamically import a function from a dotted path."""
    module_path, func_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


async def run_experiment(
    pattern_name: str,
    benchmark_name: str,
    model: str = "claude-opus-4-6",
    config: dict | None = None,
) -> ExperimentResult:
    """Run a single experiment: one pattern on one benchmark."""
    # Load pattern class
    pattern_path = PATTERN_REGISTRY.get(pattern_name)
    if not pattern_path:
        raise ValueError(f"Unknown pattern: {pattern_name}. Available: {list(PATTERN_REGISTRY.keys())}")

    # Load benchmark task
    benchmark_path = BENCHMARK_REGISTRY.get(benchmark_name)
    if not benchmark_path:
        raise ValueError(f"Unknown benchmark: {benchmark_name}. Available: {list(BENCHMARK_REGISTRY.keys())}")

    PatternClass = load_class(pattern_path)
    get_task = load_function(benchmark_path)

    # Initialize
    llm = LLMClient(model=model)
    pattern: MASPattern = PatternClass(llm_client=llm, config=config or {})
    task: BenchmarkTask = get_task()

    # Setup agents
    print(f"\n{'='*60}")
    print(f"  Pattern: {pattern_name}")
    print(f"  Benchmark: {benchmark_name}")
    print(f"  Model: {model}")
    print(f"{'='*60}")

    agents = pattern.setup(task)
    print(f"  Agents: {len(agents)} ({', '.join(a.name for a in agents)})")

    # Run
    start = time.time()
    result = await pattern.run(task)
    elapsed = time.time() - start

    # Enrich result
    result.pattern_name = pattern_name
    result.benchmark_name = benchmark_name
    result.model = model
    result.wall_time_seconds = elapsed
    result.total_tokens = llm.total_tokens_in + llm.total_tokens_out
    result.agent_stats = {
        agent.name: {
            "role": agent.role.value,
            "tokens_in": agent.total_tokens_in,
            "tokens_out": agent.total_tokens_out,
            "messages_sent": len([m for m in pattern.messages if m.sender == agent.name]),
            "messages_received": len([m for m in pattern.messages if m.receiver == agent.name]),
        }
        for agent in agents
    }
    result.metadata["llm_stats"] = llm.get_stats()

    # Evaluate quality (LLM-as-judge)
    result.quality_score = await evaluate_quality(llm, task, result.final_output)

    return result


async def evaluate_quality(
    llm: LLMClient,
    task: BenchmarkTask,
    output: str,
) -> float:
    """Use LLM-as-judge to score the output quality (0-100).

    Includes retry logic and robust JSON extraction to handle models
    that wrap JSON in markdown or add preamble text.
    """
    rubric_text = "\n".join(f"- {k}: {v}" for k, v in task.evaluation_rubric.items())
    aspects_text = "\n".join(f"- {a}" for a in task.expected_aspects)

    # Truncate long outputs to avoid overwhelming the judge
    output_trimmed = output[:8000] if len(output) > 8000 else output

    for attempt in range(3):
        response = await llm.chat(
            system=(
                "You are an expert evaluator. Score the output on a scale of 0-100.\n"
                "You MUST respond with ONLY a JSON object. No markdown, no explanation.\n"
                "Format: {\"score\": 85, \"reasoning\": \"brief explanation\"}"
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Task: {task.description}\n\n"
                    f"Expected aspects:\n{aspects_text}\n\n"
                    f"Rubric:\n{rubric_text}\n\n"
                    f"Output to evaluate:\n{output_trimmed}\n\n"
                    "Return ONLY JSON: {\"score\": <0-100>, \"reasoning\": \"...\"}"
                ),
            }],
            max_tokens=300,
            temperature=0.0,
        )

        score = _extract_score(response.content)
        if score is not None:
            return score

    print(f"  Warning: Could not parse quality score after 3 attempts, defaulting to 50")
    return 50.0


def _extract_score(text: str) -> float | None:
    """Robustly extract a score from LLM judge output.

    Handles: raw JSON, markdown-wrapped JSON, JSON embedded in text,
    and plain number responses.
    """
    import re

    text = text.strip()

    # Strip markdown code blocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    # Try direct JSON parse
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "score" in data:
            return float(data["score"])
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Try finding JSON object in text
    match = re.search(r'\{[^{}]*"score"\s*:\s*(\d+)[^{}]*\}', text)
    if match:
        return float(match.group(1))

    # Try finding "score": N pattern anywhere
    match = re.search(r'"score"\s*:\s*(\d+)', text)
    if match:
        return float(match.group(1))

    # Try finding bare number (some models just return "85")
    match = re.match(r'^(\d{1,3})$', text)
    if match:
        val = int(match.group(1))
        if 0 <= val <= 100:
            return float(val)

    return None


async def run_comparison(
    pattern_name: str,
    benchmark_name: str,
    model: str = "claude-opus-4-6",
) -> dict[str, ExperimentResult]:
    """Run a pattern + both baselines for comparison."""
    results = {}

    # Always run baselines
    for name in ["baseline_single", "baseline_naive", pattern_name]:
        print(f"\nRunning: {name} on {benchmark_name}...")
        results[name] = await run_experiment(name, benchmark_name, model)

    return results


def save_result(result: ExperimentResult, output_dir: Path) -> Path:
    """Save experiment result to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{result.pattern_name}_{result.benchmark_name}_{timestamp}.json"
    filepath = output_dir / filename

    data = {
        "experiment_id": result.experiment_id,
        "pattern": result.pattern_name,
        "benchmark": result.benchmark_name,
        "model": result.model,
        "num_agents": result.num_agents,
        "num_rounds": result.num_rounds,
        "total_tokens": result.total_tokens,
        "wall_time_seconds": result.wall_time_seconds,
        "quality_score": result.quality_score,
        "token_efficiency": result.token_efficiency,
        "final_output": result.final_output,
        "agent_stats": result.agent_stats,
        "metadata": result.metadata,
        "messages": [
            {
                "sender": m.sender,
                "receiver": m.receiver,
                "performative": m.performative,
                "content": m.content[:500],  # Truncate for storage
                "token_count": m.token_count,
            }
            for m in result.messages
        ],
    }

    filepath.write_text(json.dumps(data, indent=2))
    return filepath


async def main():
    parser = argparse.ArgumentParser(description="MAS Pattern Test Harness")
    parser.add_argument("--pattern", required=True, help="Pattern name or 'all'")
    parser.add_argument("--benchmark", required=True, help="Benchmark name or 'all'")
    parser.add_argument("--model", default="claude-opus-4-6", help="LLM model to use")
    parser.add_argument("--compare", action="store_true", help="Run with baselines for comparison")
    parser.add_argument("--output-dir", default="./results", help="Directory for results")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    patterns = list(PATTERN_REGISTRY.keys()) if args.pattern == "all" else [args.pattern]
    benchmarks = list(BENCHMARK_REGISTRY.keys()) if args.benchmark == "all" else [args.benchmark]

    all_results: list[ExperimentResult] = []

    for pattern in patterns:
        for benchmark in benchmarks:
            if args.compare:
                results = await run_comparison(pattern, benchmark, args.model)
                for name, result in results.items():
                    filepath = save_result(result, output_dir)
                    print(f"  Saved: {filepath}")
                    all_results.append(result)
            else:
                result = await run_experiment(pattern, benchmark, args.model)
                filepath = save_result(result, output_dir)
                print(f"  Saved: {filepath}")
                all_results.append(result)

    # Generate report
    if all_results:
        report = generate_report(all_results)
        report_path = output_dir / "report.md"
        report_path.write_text(report)
        print(f"\nReport saved: {report_path}")
        print_summary(all_results)


if __name__ == "__main__":
    asyncio.run(main())
