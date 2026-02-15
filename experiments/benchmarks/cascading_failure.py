"""Cascading Failure Benchmark — Tests resilience to contradictions and dependent failures.

Designed to measure whether coordination patterns prevent or propagate failures.

The task has three dependent subtasks:
1. Data ingestion layer design (contains embedded CONTRADICTION — impossible requirements)
2. Transformation layer design (depends on #1's output)
3. Storage/query layer design (depends on #1 and #2)

WITHOUT failure resilience: Agent 1 ignores/glosses over the contradiction →
Agent 2 builds on flawed assumptions → Agent 3 compounds the errors → cascade.

WITH failure resilience (e.g., JPG): Agent 1 reports BLOCKED when it hits the
contradiction → Planner replans with relaxed constraints → Agents 2 and 3 build
on a consistent foundation → no cascade.

The evaluation rubric specifically measures:
- Contradiction detection (did the system spot it?)
- Contradiction resolution (did it resolve rather than ignore?)
- Internal consistency (are downstream components coherent?)
- Cascade prevention (did false assumptions propagate?)
"""

from harness.base import BenchmarkTask


def get_task() -> BenchmarkTask:
    return BenchmarkTask(
        id="cascading_failure_01",
        name="Cascading Failure",
        description=(
            "Design a real-time data pipeline architecture for a fintech startup. "
            "The requirements contain deliberate contradictions that must be identified "
            "and resolved — not ignored — for the design to be internally consistent."
        ),
        input_data=(
            "Design a real-time data pipeline for a fintech startup with these requirements:\n\n"
            "## Requirement Group A: Ingestion Layer\n"
            "- Must ingest and process **10 million events per second** with sub-100ms latency\n"
            "- Must handle bursty traffic (50x spikes during market open)\n"
            "- Must guarantee exactly-once delivery with zero data loss\n"
            "- **Infrastructure budget: $50/month total, using a single AWS t2.micro instance**\n"
            "- Must be horizontally scalable across regions\n\n"
            "## Requirement Group B: Transformation Layer\n"
            "- Real-time enrichment: join each event with user profile data (10M profiles)\n"
            "- Apply fraud detection ML model (200ms SLA) to every transaction\n"
            "- Aggregate running totals per user per 1-minute windows\n"
            "- The transformation layer MUST build on the ingestion layer's output format\n\n"
            "## Requirement Group C: Storage & Query Layer\n"
            "- Store 2 years of historical data with sub-second query latency\n"
            "- Support both real-time dashboards and batch analytics\n"
            "- Must be consistent with the ingestion and transformation layer designs\n"
            "- Data format must match transformation layer output schema\n\n"
            "## Deliverable\n"
            "Produce a complete, internally consistent architecture document covering all "
            "three layers. If any requirements conflict, you MUST identify the conflict "
            "explicitly and propose a resolution — do NOT silently ignore contradictions."
        ),
        expected_aspects=[
            "CONTRADICTION DETECTED: 10M events/sec is impossible on a single t2.micro at $50/month",
            "CONTRADICTION DETECTED: horizontal scalability conflicts with single-instance constraint",
            "CONTRADICTION DETECTED: exactly-once + sub-100ms at 10M/sec requires significant infrastructure",
            "Resolution proposed: either relax throughput requirement OR increase budget",
            "Ingestion layer design is technically feasible with the resolved constraints",
            "Transformation layer references actual ingestion output format (not assumed)",
            "Storage layer references actual transformation output schema (not assumed)",
            "Internal consistency: all three layers use compatible data formats",
            "Internal consistency: capacity assumptions match across all layers",
            "No downstream layer builds on the impossible $50/t2.micro assumption",
            "Fraud detection SLA (200ms) is feasible with the chosen ingestion throughput",
            "Technology choices are appropriate and justified for fintech (e.g., Kafka, Flink)",
        ],
        evaluation_rubric={
            "contradiction_detection": (
                "Did the system identify the core contradiction? "
                "(10M events/sec on a $50/month t2.micro is physically impossible.) "
                "Score 0 if ignored, 50 if mentioned but not resolved, 100 if identified AND resolved."
            ),
            "cascade_prevention": (
                "Did downstream layers (B, C) build on the resolved constraints or on the "
                "impossible original ones? If transformation/storage layers assume 10M/sec on "
                "t2.micro, that's a cascaded failure. Score 0 for full cascade, 50 for partial, "
                "100 for full prevention."
            ),
            "internal_consistency": (
                "Are all three layers internally consistent? Data formats match across layers? "
                "Capacity assumptions agree? Technology choices are compatible?"
            ),
            "technical_quality": (
                "Is the architecture technically sound with the resolved constraints? "
                "Appropriate technology choices for fintech? Reasonable trade-offs?"
            ),
            "completeness": (
                "Does the design cover all three layers with sufficient detail? "
                "Ingestion, transformation, storage — each with technology choices, "
                "data formats, and capacity planning?"
            ),
        },
        max_rounds=5,
        max_tokens=40000,
    )
