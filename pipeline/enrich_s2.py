#!/usr/bin/env python3
"""T09: Bulk Semantic Scholar Enrichment.

Fills semantic_scholar_id, citation_count, venue, abstract, and doi
for all papers that have an arxiv_id but no semantic_scholar_id yet.
Falls back to title search for papers without arxiv_id.

Rate limits to 100 req/5min (S2 free tier) by sleeping 3.1s between calls.
Checkpoints progress so it can resume after interruption.

Usage:
    python3 -m pipeline.enrich_s2 [--resume] [--batch-size 100] [--dry-run]
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.apis.semantic_scholar import get_paper, search_paper
from pipeline.assembly.db import get_conn

CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "data", "enrich_s2_checkpoint.json")
SLEEP_BETWEEN = 3.1  # seconds — keeps us well under 100 req/5min


def load_checkpoint() -> int:
    """Load the last processed paper ID from checkpoint file."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
            return data.get("last_id", 0)
    return 0


def save_checkpoint(last_id: int, enriched: int, skipped: int):
    """Save progress to checkpoint file."""
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({
            "last_id": last_id,
            "enriched": enriched,
            "skipped": skipped,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f, indent=2)


def fetch_papers_with_arxiv(after_id: int, limit: int = 500) -> list[dict]:
    """Get papers that have arxiv_id but no semantic_scholar_id."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, year, arxiv_id, abstract, citation_count, venue, doi
                   FROM papers
                   WHERE arxiv_id IS NOT NULL
                     AND semantic_scholar_id IS NULL
                     AND id > %s
                   ORDER BY id
                   LIMIT %s""",
                (after_id, limit),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_papers_without_arxiv(after_id: int, limit: int = 500) -> list[dict]:
    """Get papers without arxiv_id AND without semantic_scholar_id (title-search fallback)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, year, arxiv_id, abstract, citation_count, venue, doi
                   FROM papers
                   WHERE arxiv_id IS NULL
                     AND semantic_scholar_id IS NULL
                     AND id > %s
                   ORDER BY id
                   LIMIT %s""",
                (after_id, limit),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def enrich_from_s2(paper: dict, s2_data: dict, dry_run: bool = False) -> dict:
    """Build the update dict from S2 data, filling NULLs only."""
    updates = {}

    s2_id = s2_data.get("paperId")
    if s2_id:
        updates["semantic_scholar_id"] = s2_id

    # Fill NULLs only — don't overwrite existing data
    if not paper.get("abstract") and s2_data.get("abstract"):
        updates["abstract"] = s2_data["abstract"]

    if not paper.get("citation_count") and s2_data.get("citationCount"):
        updates["citation_count"] = s2_data["citationCount"]
    elif s2_data.get("citationCount") and s2_data["citationCount"] > (paper.get("citation_count") or 0):
        # Update citation count if S2 has a higher number (more authoritative)
        updates["citation_count"] = s2_data["citationCount"]

    if not paper.get("venue") and s2_data.get("venue"):
        updates["venue"] = s2_data["venue"]

    if not paper.get("doi"):
        ext_ids = s2_data.get("externalIds") or {}
        doi = ext_ids.get("DOI")
        if doi:
            updates["doi"] = doi

    return updates


def apply_updates(paper_id: int, updates: dict):
    """Apply updates to the database."""
    if not updates:
        return
    set_parts = []
    values = []
    for col, val in updates.items():
        set_parts.append(f"{col} = %s")
        values.append(val)
    set_parts.append("updated_at = NOW()")
    values.append(paper_id)

    sql = f"UPDATE papers SET {', '.join(set_parts)} WHERE id = %s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)


def main():
    parser = argparse.ArgumentParser(description="T09: Bulk S2 Enrichment")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--batch-size", type=int, default=100, help="Commit checkpoint every N papers")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB, just show what would change")
    parser.add_argument("--title-fallback", action="store_true", help="Also search by title for papers without arxiv_id")
    args = parser.parse_args()

    print("=" * 60)
    print("  T09: BULK SEMANTIC SCHOLAR ENRICHMENT")
    print("=" * 60)

    after_id = load_checkpoint() if args.resume else 0
    if after_id > 0:
        print(f"  Resuming from paper ID > {after_id}")
    else:
        print("  Starting from the beginning")

    if args.dry_run:
        print("  DRY RUN — no database writes")

    s2_fields = "paperId,title,year,venue,abstract,citationCount,externalIds"

    enriched = 0
    skipped = 0
    errors = 0
    total_processed = 0

    # Phase 1: Papers with arxiv_id
    print("\n  Phase 1: Enriching papers with arxiv_id...")
    while True:
        papers = fetch_papers_with_arxiv(after_id, limit=args.batch_size)
        if not papers:
            break

        for paper in papers:
            arxiv_id = paper["arxiv_id"].split("v")[0]  # Strip version
            s2_data = get_paper(f"ARXIV:{arxiv_id}", fields=s2_fields)
            time.sleep(SLEEP_BETWEEN)

            total_processed += 1

            if not s2_data or not s2_data.get("paperId"):
                skipped += 1
                after_id = paper["id"]
                continue

            updates = enrich_from_s2(paper, s2_data, args.dry_run)
            if updates and not args.dry_run:
                apply_updates(paper["id"], updates)
                enriched += 1
            elif updates:
                print(f"    [DRY] Would update paper {paper['id']}: {list(updates.keys())}")
                enriched += 1
            else:
                skipped += 1

            after_id = paper["id"]

            if total_processed % 50 == 0:
                print(f"  Progress: {total_processed} processed, {enriched} enriched, {skipped} skipped, {errors} errors")

            if total_processed % args.batch_size == 0:
                save_checkpoint(after_id, enriched, skipped)

        save_checkpoint(after_id, enriched, skipped)

    print(f"\n  Phase 1 complete: {enriched} enriched, {skipped} skipped from arxiv_id lookups")

    # Phase 2: Title-search fallback for papers without arxiv_id
    if args.title_fallback:
        print("\n  Phase 2: Title-search fallback for papers without arxiv_id...")
        after_id_fallback = 0
        fallback_enriched = 0
        fallback_skipped = 0

        while True:
            papers = fetch_papers_without_arxiv(after_id_fallback, limit=args.batch_size)
            if not papers:
                break

            for paper in papers:
                results = search_paper(paper["title"], limit=3, fields=s2_fields)
                time.sleep(SLEEP_BETWEEN)

                total_processed += 1
                matched = False

                for r in results:
                    # Accept only if year matches
                    if r.get("year") == paper.get("year") and r.get("paperId"):
                        updates = enrich_from_s2(paper, r, args.dry_run)
                        if updates and not args.dry_run:
                            apply_updates(paper["id"], updates)
                            fallback_enriched += 1
                            matched = True
                        elif updates:
                            print(f"    [DRY] Would update paper {paper['id']}: {list(updates.keys())}")
                            fallback_enriched += 1
                            matched = True
                        break

                if not matched:
                    fallback_skipped += 1

                after_id_fallback = paper["id"]

                if total_processed % 50 == 0:
                    print(f"  Progress: {total_processed} total, fallback {fallback_enriched} enriched, {fallback_skipped} skipped")

        enriched += fallback_enriched
        skipped += fallback_skipped
        print(f"\n  Phase 2 complete: {fallback_enriched} enriched, {fallback_skipped} skipped from title search")

    # Final summary
    print("\n" + "=" * 60)
    print(f"  ENRICHMENT COMPLETE")
    print(f"  Total processed: {total_processed}")
    print(f"  Enriched:        {enriched}")
    print(f"  Skipped:         {skipped}")
    print(f"  Errors:          {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
