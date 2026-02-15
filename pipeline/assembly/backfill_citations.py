#!/usr/bin/env python3
"""Backfill citation counts for papers that went through Agent 4 hollow.

These papers were promoted to 'enriched'/'scouted' during S2 rate limiting
and have no S2 ID, no citation count, no modernity score. This script does
a lightweight S2 title search to resolve just the citation count and S2 ID
— no full forward/backward pass.

Usage:
    python3 -m pipeline.assembly.backfill_citations [--dry-run] [--limit 100]
    python3 -m pipeline.assembly.backfill_citations --batch-size 50

Throughput: ~18 papers/min on free tier (1 S2 call per paper, 3.33s pacing)
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn
from pipeline.apis.semantic_scholar import search_paper, _consecutive_429s, _MAX_CONSECUTIVE_429s, _429_cooldown_until

import psycopg2.extras


def backfill_batch(batch_size: int = 50, dry_run: bool = False) -> tuple[int, int, int]:
    """Fetch a batch of hollow papers and resolve S2 IDs + citation counts.

    Returns (attempted, resolved, skipped).
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, title, year, citation_count
                   FROM papers
                   WHERE semantic_scholar_id IS NULL
                     AND pipeline_status IN ('enriched','scouted','scouting',
                                             'planning_reproduction','reproduction_planned')
                   ORDER BY RANDOM()
                   LIMIT %s""",
                (batch_size,),
            )
            rows = cur.fetchall()

    if not rows:
        return (0, 0, 0)

    resolved = 0
    skipped = 0

    for paper in rows:
        # Check circuit breaker
        if _consecutive_429s >= _MAX_CONSECUTIVE_429s and time.time() < _429_cooldown_until:
            wait = int(_429_cooldown_until - time.time()) + 1
            print(f"  [WAIT] Circuit breaker active, sleeping {wait}s", flush=True)
            time.sleep(wait)

        title = paper.get("title", "")
        if not title:
            skipped += 1
            continue

        matches = search_paper(title, limit=3, fields="paperId,title,year,citationCount")
        if not matches:
            skipped += 1
            continue

        # Find best match (prefer year match)
        best = None
        for m in matches:
            if m.get("year") == paper.get("year"):
                best = m
                break
        if not best:
            best = matches[0]

        s2_id = best.get("paperId")
        cite_count = best.get("citationCount", 0)

        if not s2_id:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] id={paper['id']} | {title[:50]} | s2={s2_id[:12]}... cites={cite_count}")
        else:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE papers
                           SET semantic_scholar_id = %s,
                               citation_count = %s,
                               updated_at = NOW()
                           WHERE id = %s""",
                        (s2_id, cite_count, paper["id"]),
                    )

        resolved += 1

    return (len(rows), resolved, skipped)


def main():
    parser = argparse.ArgumentParser(description="Backfill citation counts for hollow papers")
    parser.add_argument("--batch-size", type=int, default=50, help="Papers per batch (default: 50)")
    parser.add_argument("--limit", type=int, default=0, help="Max papers total (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be updated without writing")
    args = parser.parse_args()

    # Count how many need backfilling
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM papers
                   WHERE semantic_scholar_id IS NULL
                     AND pipeline_status IN ('enriched','scouted','scouting',
                                             'planning_reproduction','reproduction_planned')"""
            )
            total_hollow = cur.fetchone()[0]

    print("=" * 60, flush=True)
    print("  BACKFILL: Citation Count Resolution", flush=True)
    print("=" * 60, flush=True)
    print(f"  Hollow papers to fix:  {total_hollow}", flush=True)
    print(f"  Batch size:            {args.batch_size}", flush=True)
    print(f"  Limit:                 {args.limit or 'all'}", flush=True)
    print(f"  Dry run:               {args.dry_run}", flush=True)
    print(f"  Est. time (free tier): {total_hollow * 3.33 / 60:.0f} min", flush=True)
    print(flush=True)

    total_attempted = 0
    total_resolved = 0
    total_skipped = 0

    while True:
        if args.limit and total_attempted >= args.limit:
            break

        remaining = args.limit - total_attempted if args.limit else args.batch_size
        batch = min(args.batch_size, remaining) if args.limit else args.batch_size

        attempted, resolved, skipped = backfill_batch(batch_size=batch, dry_run=args.dry_run)

        if attempted == 0:
            print("  No more hollow papers to process.", flush=True)
            break

        total_attempted += attempted
        total_resolved += resolved
        total_skipped += skipped

        pct = 100 * total_resolved / total_attempted if total_attempted > 0 else 0
        print(
            f"  Batch done: {attempted} attempted, {resolved} resolved, {skipped} skipped. "
            f"Total: {total_resolved}/{total_attempted} ({pct:.0f}% hit rate). "
            f"Remaining: ~{total_hollow - total_attempted}",
            flush=True,
        )

    print(f"\n  Backfill complete. Resolved: {total_resolved}/{total_attempted} "
          f"({100 * total_resolved / total_attempted:.0f}% hit rate)" if total_attempted > 0
          else "\n  Nothing to backfill.",
          flush=True)


if __name__ == "__main__":
    main()
