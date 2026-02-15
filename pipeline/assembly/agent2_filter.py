#!/usr/bin/env python3
"""Agent 2: Relevance Filter — Second station on the assembly line.

Polls papers with pipeline_status='collected', batches 10 abstracts,
sends to GPT-5-mini for MAS coordination relevance scoring.

Now uses concurrent.futures to run multiple LLM batches in parallel.
Each batch grabs its own papers via FOR UPDATE SKIP LOCKED (no overlap).

Updates:
  - relevance_score (1-5)
  - relevance_rationale (1-line reason)
  - mas_branch (communication|organization|coordination|architecture|negotiation|engineering)
  - pipeline_status → 'relevant' (score >= 4), 'marginal' (score 3), 'archived' (score <= 2)

Usage:
    python3 -m pipeline.assembly.agent2_filter [--batch-size 10] [--concurrent 8]
"""

import argparse
import concurrent.futures
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, update_paper, count_by_status, total_papers
from pipeline.apis.llm import gpt_chat_json

import psycopg2.extras

SYSTEM_PROMPT = """You are a research paper classifier for a survey on Multi-Agent Systems (MAS) coordination.

Your task: Given a batch of paper titles and abstracts, rate each paper's relevance to this specific research question:

"How do classical MAS coordination patterns (1980-2010) map to modern LLM agent systems (2023-2026)? Which coordination concepts have been lost or reinvented?"

For EACH paper, provide:
1. relevance_score (1-5):
   5 = Directly about MAS coordination patterns, agent communication protocols, or multi-agent organization
   4 = About multi-agent coordination in LLM/AI systems, agent frameworks, or agent failure analysis
   3 = Tangentially related (general agent architecture, single-agent systems with multi-agent potential)
   2 = Peripherally related (uses "multi-agent" but about robotics swarms, traffic, or simulations unrelated to software coordination)
   1 = Not relevant (wrong field entirely)

2. rationale: One sentence explaining the rating

3. mas_branch: Which MAS branch this paper belongs to (pick the BEST fit):
   - communication: Agent languages, protocols, message passing, performatives
   - organization: Team formation, roles, hierarchies, holonic structures
   - coordination: Task allocation, scheduling, shared plans, joint intentions
   - architecture: BDI, blackboard, reactive, hybrid agent architectures
   - negotiation: Auctions, contract net, game-theoretic interactions
   - engineering: Agent-oriented SE, verification, testing, deployment
   - llm_agents: Modern LLM-based agent systems (frameworks, benchmarks, failures)
   - other: Doesn't fit any branch

Return a JSON array with one object per paper:
[
  {"paper_id": 123, "relevance_score": 5, "rationale": "...", "mas_branch": "coordination"},
  ...
]"""


def filter_batch(papers: list[dict]) -> list[dict]:
    """Send a batch of papers to LLM for relevance classification."""
    batch_text = ""
    for p in papers:
        abstract = (p.get("abstract") or "No abstract available.")[:500]
        batch_text += f"\n---\npaper_id: {p['id']}\ntitle: {p['title']}\nyear: {p.get('year', '?')}\nabstract: {abstract}\n"

    user_msg = f"Classify these {len(papers)} papers:\n{batch_text}"

    try:
        result = gpt_chat_json(
            system=SYSTEM_PROMPT,
            user_message=user_msg,
            model="gpt-5-mini",
            max_tokens=4096,
        )
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        print(f"  [Filter] LLM error: {e}", flush=True)
        return []


def poll_batch(batch_size: int = 10) -> list[dict]:
    """Grab a batch of collected papers (FOR UPDATE SKIP LOCKED)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, title, year, abstract, venue
                   FROM papers
                   WHERE pipeline_status = 'collected'
                   ORDER BY citation_count DESC
                   LIMIT %s
                   FOR UPDATE SKIP LOCKED""",
                (batch_size,),
            )
            papers = [dict(r) for r in cur.fetchall()]

            if not papers:
                return []

            # Mark as processing to avoid double-pickup
            ids = [p["id"] for p in papers]
            cur.execute(
                "UPDATE papers SET pipeline_status = 'filtering' WHERE id = ANY(%s)",
                (ids,),
            )

    return papers


def process_batch(papers: list[dict]) -> int:
    """Filter a batch: call LLM, then update DB. Returns count processed."""
    results = filter_batch(papers)

    # Map results back to paper IDs
    result_map = {}
    for r in results:
        pid = r.get("paper_id")
        if pid:
            result_map[int(pid)] = r

    # Update each paper
    processed = 0
    for p in papers:
        r = result_map.get(p["id"])
        if r:
            score = r.get("relevance_score", 1)
            if score >= 4:
                new_status = "relevant"
            elif score == 3:
                new_status = "marginal"
            else:
                new_status = "archived"

            update_paper(
                p["id"],
                agent_name="agent2_filter",
                new_status=new_status,
                relevance_score=score,
                relevance_rationale=r.get("rationale", ""),
                mas_branch=r.get("mas_branch", "other"),
            )
        else:
            # LLM didn't return a result for this paper — put it back
            update_paper(p["id"], agent_name="agent2_filter", new_status="collected")

        processed += 1

    return processed


def _run_one_batch(batch_size: int) -> int:
    """Poll + filter one batch. Called from thread pool."""
    papers = poll_batch(batch_size)
    if not papers:
        return 0
    return process_batch(papers)


def main():
    parser = argparse.ArgumentParser(description="Agent 2: Relevance Filter")
    parser.add_argument("--batch-size", type=int, default=10, help="Papers per LLM call")
    parser.add_argument("--concurrent", type=int, default=8, help="Max concurrent LLM batches (default: 8)")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls when idle")
    parser.add_argument("--once", action="store_true", help="Process one round and exit")
    parser.add_argument("--max-batches", type=int, default=0, help="Max batches (0=unlimited)")
    args = parser.parse_args()

    print("=" * 60)
    print("  AGENT 2: RELEVANCE FILTER (concurrent)")
    print("  Assembly Line — Station 2")
    print("=" * 60)
    print(f"  Batch size:  {args.batch_size} papers per LLM call")
    print(f"  Concurrent:  {args.concurrent} parallel batches")
    print(f"  Throughput:  ~{args.batch_size * args.concurrent} papers / LLM round-trip")
    print(f"  Model:       gpt-5-mini")
    print(f"  Status:      {count_by_status()}", flush=True)

    total_processed = 0
    rounds = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        while True:
            # Submit N concurrent batches
            futures = []
            for _ in range(args.concurrent):
                futures.append(executor.submit(_run_one_batch, args.batch_size))

            # Collect results
            round_total = 0
            for f in concurrent.futures.as_completed(futures):
                try:
                    n = f.result()
                    round_total += n
                except Exception as e:
                    print(f"  [Filter] Batch error: {e}", flush=True)

            if round_total > 0:
                total_processed += round_total
                rounds += 1
                print(f"  Round {rounds}: filtered {round_total} papers "
                      f"(total: {total_processed}, "
                      f"queue: ~{count_by_status().get('collected', '?')})",
                      flush=True)

                if args.once:
                    break
                if args.max_batches and rounds >= args.max_batches:
                    break
            else:
                if args.once:
                    print("  No papers to filter.", flush=True)
                    break
                print(f"  Waiting for papers... (polling every {args.poll_interval}s)", flush=True)
                time.sleep(args.poll_interval)

    print(f"\n  Filter complete. Processed: {total_processed} papers in {rounds} rounds.", flush=True)


if __name__ == "__main__":
    main()
