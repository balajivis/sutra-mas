#!/usr/bin/env python3
"""Bulk Reference Harvester — mine all refs from enriched papers.

Collects all unique OpenAlex ref IDs from the refs JSONB column,
batch-fetches metadata from OpenAlex, filters for MAS relevance,
and inserts matches as 'collected' papers for Agent 2 to score.

This is a one-shot complement to Agent 4's real-time feedback loop.
While Agent 4 processes refs paper-by-paper during enrichment,
this script processes ALL accumulated refs in bulk.

Usage:
    python3 -m pipeline.assembly.bulk_ref_harvest [--dry-run] [--batch-size 50]
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, insert_paper
from pipeline.apis.openalex import get_references_detailed

# MAS keywords for title filtering (same as Agent 4 feedback loop)
MAS_KEYWORDS = [
    "multi-agent", "multiagent", "multi agent",
    "agent system", "agent coordination", "agent cooperation",
    "agent communication", "agent negotiation", "agent team",
    "autonomous agent", "intelligent agent", "software agent",
    "bdi", "contract net", "blackboard", "belief desire intention",
    "llm agent", "language model agent", "agentic",
    "agent framework", "agent architecture", "agent organization",
    "cooperative agent", "agent-based",
    # Additional keywords to cast a wider net than the feedback loop
    "multi-robot", "distributed problem solving", "distributed ai",
    "agent interaction", "agent collaboration", "agent planning",
    "agent learning", "agent simulation", "agent society",
    "swarm intelligence", "collective intelligence",
    "shared plan", "joint intention", "social choice",
    "mechanism design", "auction", "voting",
    "consensus protocol", "distributed consensus",
    "task allocation", "role assignment",
    "agent ontology", "agent platform", "agent middleware",
    "fipa", "kqml", "jade", "jason",
    "norm", "trust", "reputation", "agent",
]


def is_mas_relevant(title: str) -> bool:
    """Check if a title is MAS-relevant using keyword matching."""
    lower = title.lower()
    return any(kw in lower for kw in MAS_KEYWORDS)


def get_all_ref_ids() -> tuple[set[str], dict[str, int]]:
    """Collect all unique OpenAlex ref IDs from enriched papers.

    Returns:
        - set of OpenAlex IDs not already in corpus
        - dict mapping oa_id -> max parent generation
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get existing OpenAlex IDs in corpus
            cur.execute("SELECT openalex_id FROM papers WHERE openalex_id IS NOT NULL")
            existing = set()
            for (oa,) in cur.fetchall():
                existing.add(oa)
                # Also add full URL form
                if not oa.startswith("https://"):
                    existing.add(f"https://openalex.org/{oa}")

            # Get all refs from enriched+ papers
            cur.execute("""SELECT refs, generation FROM papers
                WHERE refs IS NOT NULL AND refs::text != '[]' AND refs::text != 'null'
                AND pipeline_status NOT IN ('archived')""")

            all_refs = {}  # oa_id -> max parent generation
            for refs, gen in cur.fetchall():
                if not isinstance(refs, list):
                    continue
                for r in refs:
                    if isinstance(r, dict) and r.get("oa_id"):
                        oa_id = r["oa_id"]
                        # Skip if already in corpus
                        if oa_id in existing or f"https://openalex.org/{oa_id}" in existing:
                            continue
                        # Track max parent generation
                        if oa_id not in all_refs or gen > all_refs[oa_id]:
                            all_refs[oa_id] = gen

    return set(all_refs.keys()), all_refs


def fetch_and_filter(oa_ids: list[str], batch_size: int = 50) -> list[dict]:
    """Batch-fetch metadata from OpenAlex and filter for MAS relevance."""
    relevant = []
    total = len(oa_ids)

    for i in range(0, total, batch_size):
        batch = oa_ids[i:i + batch_size]
        try:
            works = get_references_detailed(batch, batch_size=batch_size)
        except Exception as e:
            print(f"  [ERROR] Batch {i//batch_size}: {e}", flush=True)
            time.sleep(5)
            continue

        for work in works:
            title = work.get("title") or ""
            if not title:
                continue

            if is_mas_relevant(title):
                oa_id = (work.get("id") or "").split("/")[-1]
                year = work.get("publication_year")
                cited_by = work.get("cited_by_count", 0)

                # Extract DOI and ArXiv ID from ids dict
                ids = work.get("ids") or {}
                doi = ids.get("doi", "").replace("https://doi.org/", "") if ids.get("doi") else None
                arxiv_url = ids.get("openalex", "")  # OpenAlex doesn't directly give arxiv in batch

                relevant.append({
                    "title": title,
                    "year": year,
                    "openalex_id": oa_id,
                    "doi": doi,
                    "citation_count": cited_by,
                })

        processed = min(i + batch_size, total)
        if processed % 500 == 0 or processed == total:
            print(f"  Fetched {processed}/{total} refs, {len(relevant)} MAS-relevant so far",
                  flush=True)

        time.sleep(0.3)  # Stay well under rate limit

    return relevant


def main():
    parser = argparse.ArgumentParser(description="Bulk Reference Harvester")
    parser.add_argument("--dry-run", action="store_true", help="Don't insert, just count")
    parser.add_argument("--batch-size", type=int, default=50, help="OpenAlex batch size")
    parser.add_argument("--max-refs", type=int, default=0, help="Max refs to process (0=all)")
    parser.add_argument("--corpus-cap", type=int, default=20000, help="Stop if corpus exceeds this")
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("  BULK REFERENCE HARVESTER", flush=True)
    print("=" * 60, flush=True)

    # Step 1: Collect all ref IDs not in corpus
    print("\n[1/3] Collecting ref IDs from enriched papers...", flush=True)
    ref_ids, parent_gens = get_all_ref_ids()
    print(f"  Found {len(ref_ids)} unique refs not in corpus", flush=True)

    if not ref_ids:
        print("  Nothing to harvest.", flush=True)
        return

    # Limit if requested
    ref_list = sorted(ref_ids)
    if args.max_refs:
        ref_list = ref_list[:args.max_refs]
        print(f"  Processing first {args.max_refs}", flush=True)

    # Step 2: Batch-fetch and filter
    print(f"\n[2/3] Fetching metadata from OpenAlex ({len(ref_list)} refs)...", flush=True)
    relevant = fetch_and_filter(ref_list, batch_size=args.batch_size)
    print(f"  MAS-relevant papers found: {len(relevant)}", flush=True)

    if args.dry_run:
        print("\n[DRY RUN] Would insert:", flush=True)
        for p in relevant[:20]:
            print(f"  [{p['year']}] {p['title'][:70]} (cites: {p['citation_count']})")
        if len(relevant) > 20:
            print(f"  ... and {len(relevant) - 20} more")
        return

    # Step 3: Insert into pipeline as 'collected'
    print(f"\n[3/3] Inserting {len(relevant)} papers as 'collected'...", flush=True)

    # Check corpus cap
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM papers WHERE pipeline_status != 'archived'")
            corpus_size = cur.fetchone()[0]

    headroom = args.corpus_cap - corpus_size
    print(f"  Corpus: {corpus_size}, Cap: {args.corpus_cap}, Headroom: {headroom}", flush=True)

    if headroom <= 0:
        print("  [STOP] Corpus cap reached. Increase --corpus-cap to continue.", flush=True)
        return

    inserted = 0
    skipped = 0
    for paper in relevant:
        if inserted >= headroom:
            print(f"  [STOP] Reached headroom limit ({headroom})", flush=True)
            break

        oa_id = paper["openalex_id"]
        parent_gen = parent_gens.get(oa_id, 0)
        new_gen = min(parent_gen + 1, 3)  # Cap at gen 3

        result = insert_paper(
            title=paper["title"],
            year=paper["year"],
            openalex_id=oa_id,
            doi=paper.get("doi"),
            citation_count=paper["citation_count"],
            source="bulk_ref_harvest",
            generation=new_gen,
            pipeline_status="collected",
        )

        if result:
            inserted += 1
        else:
            skipped += 1

    print(f"\n  Inserted: {inserted}", flush=True)
    print(f"  Skipped (duplicates): {skipped}", flush=True)
    print(f"  New corpus size: ~{corpus_size + inserted}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("  HARVEST COMPLETE", flush=True)
    print(f"  Papers will flow through Agent 2 → 3 → 4 → 5", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
