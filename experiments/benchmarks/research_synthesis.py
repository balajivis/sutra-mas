"""Research Synthesis Benchmark — Agents synthesize multiple paper abstracts."""

from harness.base import BenchmarkTask

PAPER_ABSTRACTS = """
## Paper 1: "Why Do Multi-Agent LLM Systems Fail?" (Cemri et al., ICLR 2025)
Multi-agent AI systems hold the promise of tackling complex real-world tasks by
leveraging the diverse expertise of specialized agents. Despite their potential,
our analysis reveals a concerning finding: these systems often fail even when
individual agents within them possess the capability to solve the underlying
tasks independently. We analyze 14 unique failure modes that multi-agent systems
can exhibit, grouping them into three categories -- intra-agent, inter-agent,
and system-level failures. We find that inter-agent misalignment accounts for
36.9% of all failures, suggesting that the coordination overhead often exceeds
the benefit of specialization.

## Paper 2: "Towards a Science of Scaling Agent Systems" (Kim et al., Google DeepMind 2025)
We conduct a systematic empirical study of multi-agent scaling across 180 configurations.
Our key findings: (1) Independent agents exhibit 17.2x error amplification compared to
single agents. (2) Centralized coordination reduces this to 4.4x. (3) Multi-agent systems
show 80.9% improvement on parallelizable tasks but 39-70% degradation on sequential tasks.
(4) Beyond a 45% individual capability threshold, adding more agents hurts performance.
(5) Task decomposability predicts optimal architecture with 87% accuracy.

## Paper 3: "Multi-Agent Collaboration Mechanisms: A Survey of LLMs" (Tran et al., 2025)
This survey categorizes 47 multi-agent LLM systems across three dimensions: communication
topology (centralized, decentralized, hierarchical), task decomposition strategy (static,
dynamic, negotiated), and quality assurance mechanism (self-reflection, peer review,
external evaluation). We find that systems with structured communication protocols
outperform free-form dialogue by 23% on average, and that the combination of hierarchical
topology with dynamic task decomposition achieves the best results on complex tasks.

## Paper 4: "How We Built Our Multi-Agent Research System" (Anthropic, 2025)
We describe our production multi-agent system for automated research. Key findings:
(1) The orchestrator-worker pattern with a lead agent achieved 90.2% improvement over
single-agent on complex research tasks. (2) 80% of performance variance is explained
by token budget, not agent count. (3) Structured critique (generator/critic) outperforms
unstructured multi-agent debate. (4) The most important design choice is not how many
agents to use, but how to allocate tokens across them.

## Paper 5: "LbMAS: LLM-based Multi-Agent System with Blackboard Architecture" (2025)
We introduce a blackboard-based coordination mechanism for LLM agents. Results: (1) 13-57%
improvement over supervisor patterns on knowledge-intensive tasks. (2) 3x fewer tokens
consumed due to shared state eliminating redundant communication. (3) The blackboard
architecture naturally supports asynchronous agent activation, unlike sequential supervisor
patterns. (4) Quality correlates with the diversity of knowledge sources, not their number.
"""


def get_task() -> BenchmarkTask:
    return BenchmarkTask(
        id="research_synth_01",
        name="Research Synthesis",
        description=(
            "Synthesize the following 5 research paper abstracts into a coherent analysis. "
            "Identify: (1) areas of consensus, (2) areas of disagreement, (3) the key "
            "quantitative findings that matter most, (4) gaps in the collective research, "
            "and (5) practical recommendations for someone building multi-agent systems."
        ),
        input_data=f"Synthesize these papers:\n{PAPER_ABSTRACTS}",
        expected_aspects=[
            "Consensus: naive MAS fails, coordination matters more than agent count",
            "Consensus: token allocation > agent count (Anthropic + Kim et al.)",
            "Consensus: structured communication > free-form (Tran + Anthropic)",
            "Disagreement: centralized vs blackboard (Kim prefers centralized, LbMAS prefers blackboard)",
            "Key finding: 17.2x error amplification is the headline number",
            "Key finding: 45% capability threshold for MAS benefit",
            "Key finding: 87% architecture prediction accuracy from task features",
            "Gap: no paper addresses failure recovery or rollback",
            "Gap: limited discussion of human-in-the-loop integration",
            "Practical: start with single agent, scale token budget before agent count",
            "Practical: use task decomposability analysis before choosing architecture",
            "Practical: blackboard for knowledge-intensive, supervisor for parallel tasks",
        ],
        evaluation_rubric={
            "synthesis_quality": "Does it genuinely synthesize (find connections, contradictions) or just summarize each paper?",
            "quantitative_accuracy": "Are the specific numbers (17.2x, 90.2%, 13-57%, etc.) cited correctly?",
            "insight_depth": "Does it identify non-obvious connections between papers?",
            "practical_value": "Are the recommendations actionable and specific?",
            "gaps_identified": "Does it identify what the research collectively misses?",
        },
        max_rounds=5,
        max_tokens=40000,
    )
