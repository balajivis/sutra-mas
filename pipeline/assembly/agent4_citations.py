#!/usr/bin/env python3
"""Agent 4: Citation Enricher — Fourth station on the assembly line.

Polls papers with pipeline_status='analyzed' (after Agent 3 deep analysis),
fetches citation data from OpenAlex, computes modernity scores.

Uses OpenAlex (100K requests/day, no auth) instead of Semantic Scholar.
Key advantage: counts_by_year gives modernity score data in one field,
and referenced_works gives backward citations directly.

Feedback loop: When references reveal new MAS papers not in the DB,
inserts them as 'collected' so they re-enter the pipeline at Station 1.

Safety bounds (all three enforced):
  1. Generation depth cap: new papers get parent_generation + 1, refuse if >= 3
  2. Corpus size cap: stop inserting when non-archived papers > 5,000
  3. Diminishing returns: if <5% new papers for 3 consecutive cycles, disable feedback

Throughput: ~30 papers/min (1-2 OpenAlex calls per paper, 0.2s pacing)
            = ~1,800 papers/hour

Usage:
    python3 -m pipeline.assembly.agent4_citations [--once] [--no-feedback]
    python3 -m pipeline.assembly.agent4_citations --gen-cap 3 --corpus-cap 5000
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, update_paper, insert_paper, count_by_status
from pipeline.apis.openalex import (
    search_works,
    get_work_by_doi,
    get_work_by_openalex_id,
    get_references_detailed,
    get_work_with_counts,
)

import psycopg2.extras

# MAS title keywords for the feedback loop filter
MAS_KEYWORDS = [
    "multi-agent", "multiagent", "multi agent",
    "agent system", "agent coordination", "agent cooperation",
    "agent communication", "agent negotiation", "agent team",
    "autonomous agent", "intelligent agent", "software agent",
    "bdi", "contract net", "blackboard", "belief desire intention",
    "llm agent", "language model agent", "agentic",
    "agent framework", "agent architecture", "agent organization",
    "cooperative agent", "agent-based",
]

# Safety bound defaults
DEFAULT_GEN_CAP = 3
DEFAULT_CORPUS_CAP = 20000
DIMINISHING_RETURNS_THRESHOLD = 0.05
DIMINISHING_RETURNS_STREAK = 3

# Pacing: OpenAlex polite pool allows ~10 req/sec.
# With published-version fallback we do ~5 calls/paper, so 1s keeps us safe.
REQUEST_INTERVAL = 1.0  # seconds between OpenAlex calls


def is_mas_title(title: str) -> bool:
    """Quick check if a title is MAS-related."""
    lower = title.lower()
    return any(kw in lower for kw in MAS_KEYWORDS)


def get_corpus_size() -> int:
    """Count non-archived papers in the corpus."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM papers WHERE pipeline_status != 'archived'")
            return cur.fetchone()[0]


def try_insert_feedback_paper(
    title: str,
    year: int | None,
    doi: str | None,
    arxiv_id: str | None,
    openalex_id: str | None,
    citation_count: int,
    source: str,
    parent_generation: int,
    gen_cap: int,
    corpus_cap: int,
) -> int | None:
    """Try to insert a feedback paper, respecting safety bounds."""
    new_gen = parent_generation + 1
    if new_gen > gen_cap:
        return None
    if get_corpus_size() >= corpus_cap:
        return None

    return insert_paper(
        title=title,
        year=year,
        doi=doi,
        arxiv_id=arxiv_id,
        openalex_id=openalex_id,
        citation_count=citation_count,
        source=source,
        is_classical=(year or 2025) < 2010,
        pipeline_status="collected",
        generation=new_gen,
    )


def modernity_score(counts_by_year: list[dict]) -> tuple[float, int, int]:
    """Compute Modernity Score from OpenAlex counts_by_year.

    counts_by_year is like: [{"year": 2024, "cited_by_count": 45}, ...]
    Returns (score, modern_count, total_count).
    Modern = 2023-2026.
    """
    total = sum(entry.get("cited_by_count", 0) for entry in counts_by_year)
    modern = sum(
        entry.get("cited_by_count", 0)
        for entry in counts_by_year
        if 2023 <= entry.get("year", 0) <= 2026
    )
    if total == 0:
        return 0.0, 0, 0
    return modern / total, modern, total


class LookupFailed(Exception):
    """Raised when OpenAlex can't resolve a paper — keep in analyzed for retry."""
    pass


def enrich_paper(
    paper: dict,
    enable_feedback: bool = True,
    gen_cap: int = DEFAULT_GEN_CAP,
    corpus_cap: int = DEFAULT_CORPUS_CAP,
) -> dict:
    """Fetch citation data from OpenAlex and compute modernity score.

    Returns dict of columns to update.
    Raises LookupFailed if OpenAlex can't find the paper.

    API calls per paper:
      1. search_works (title search) — resolve OpenAlex ID + citation count + counts_by_year
      2. get_references_detailed (batch) — fetch metadata for referenced works (for feedback loop)
    """
    parent_gen = paper.get("generation") or 0
    result: dict = {
        "citation_count": paper.get("citation_count", 0),
    }
    new_papers_inserted = 0

    # --- Step 1: Resolve OpenAlex ID via DOI / ArXiv DOI / title search ---
    title = paper.get("title", "")
    doi = paper.get("doi")
    arxiv_id = paper.get("arxiv_id")
    year = paper.get("year")

    oa_work = None

    # Try DOI first (most accurate)
    if doi:
        time.sleep(REQUEST_INTERVAL)
        oa_work = get_work_by_doi(doi)
        if not oa_work or not oa_work.get("id"):
            oa_work = None

    # Try ArXiv synthetic DOI (10.48550/arXiv.XXXX.XXXXX)
    if not oa_work and arxiv_id:
        arxiv_doi = f"10.48550/arXiv.{arxiv_id}"
        time.sleep(REQUEST_INTERVAL)
        oa_work = get_work_by_doi(arxiv_doi)
        if not oa_work or not oa_work.get("id"):
            oa_work = None

    # Fall back to title search
    if not oa_work and title:
        time.sleep(REQUEST_INTERVAL)
        matches = search_works(title, limit=5)
        for m in matches:
            if year and m.get("publication_year") == year:
                oa_work = m
                break
        if not oa_work and matches:
            # Take the best match (first result from search)
            oa_work = matches[0]

    if not oa_work or not oa_work.get("id"):
        raise LookupFailed(f"Could not resolve OpenAlex ID for: {title[:60]}")

    oa_id = oa_work["id"]
    oa_short = oa_id.split("/")[-1] if "/" in oa_id else oa_id
    result["openalex_id"] = oa_short
    result["citation_count"] = oa_work.get("cited_by_count", 0)

    # --- Step 2: Modernity score from counts_by_year ---
    counts_by_year = oa_work.get("counts_by_year")
    if not counts_by_year:
        # Some search results don't include counts_by_year; fetch full work
        time.sleep(REQUEST_INTERVAL)
        full_work = get_work_with_counts(oa_short)
        counts_by_year = full_work.get("counts_by_year", [])

    if counts_by_year:
        score, modern, total = modernity_score(counts_by_year)
        result["modernity_score"] = score

    # --- Step 3: References (backward pass) + feedback loop ---
    referenced_works = oa_work.get("referenced_works", [])

    # ArXiv preprint records often have 0 refs. Try to find a published version
    # with the same title that has refs (e.g., journal/conference version).
    if not referenced_works and title:
        time.sleep(REQUEST_INTERVAL)
        alt_matches = search_works(title, limit=5)
        for alt in alt_matches:
            alt_id = alt.get("id", "")
            if alt_id == oa_id:
                continue  # skip the same record
            alt_refs = alt.get("referenced_works", [])
            alt_ref_count = alt.get("referenced_works_count", 0)
            alt_title = (alt.get("title") or "").lower()
            if (alt_refs or alt_ref_count > 0) and alt_title == title.lower():
                # Found a published version with refs — use it
                if not alt_refs and alt_ref_count > 0:
                    time.sleep(REQUEST_INTERVAL)
                    alt_full = get_work_by_openalex_id(alt_id.split("/")[-1])
                    alt_refs = alt_full.get("referenced_works", [])
                if alt_refs:
                    referenced_works = alt_refs
                    # Also pick up better citation count if the published version has more
                    alt_cites = alt.get("cited_by_count", 0)
                    if alt_cites > result.get("citation_count", 0):
                        result["citation_count"] = alt_cites
                    break

    if referenced_works:
        # Batch-fetch metadata for references (50 at a time)
        time.sleep(REQUEST_INTERVAL)
        ref_details = get_references_detailed(referenced_works[:200], batch_size=50)

        ref_list = []
        for ref in ref_details:
            ref_id = ref.get("id", "")
            ref_short = ref_id.split("/")[-1] if "/" in ref_id else ref_id
            ref_list.append({
                "oa_id": ref_short,
                "title": ref.get("title", ""),
                "year": ref.get("publication_year"),
                "citations": ref.get("cited_by_count", 0),
            })

            # Feedback loop: insert new MAS papers
            if enable_feedback and ref.get("title") and is_mas_title(ref["title"]):
                ref_ids = ref.get("ids", {}) or {}
                pid = try_insert_feedback_paper(
                    title=ref["title"],
                    year=ref.get("publication_year"),
                    doi=ref_ids.get("doi", "").replace("https://doi.org/", "") if ref_ids.get("doi") else None,
                    arxiv_id=None,
                    openalex_id=ref_short,
                    citation_count=ref.get("cited_by_count", 0),
                    source=f"ref_of_{paper['id']}",
                    parent_generation=parent_gen,
                    gen_cap=gen_cap,
                    corpus_cap=corpus_cap,
                )
                if pid:
                    new_papers_inserted += 1

        result["refs"] = psycopg2.extras.Json(ref_list[:200])

    if new_papers_inserted:
        print(f"    -> Feedback: +{new_papers_inserted} new MAS papers", flush=True)

    return result


def _enrich_one(paper: dict, enable_feedback: bool, gen_cap: int, corpus_cap: int) -> tuple[int, int]:
    """Enrich a single paper. Returns (1, new_inserted) or (0, 0) on skip."""
    try:
        result = enrich_paper(paper, enable_feedback=enable_feedback, gen_cap=gen_cap, corpus_cap=corpus_cap)
    except LookupFailed as e:
        print(f"    [SKIP] {e}", flush=True)
        # Mark as enriched (with no refs) so it doesn't loop — downstream agents can still use it
        update_paper(paper["id"], agent_name="agent4_citations", new_status="enriched")
        return (0, 0)

    count_before = get_corpus_size()
    update_paper(paper["id"], agent_name="agent4_citations", new_status="enriched", **result)
    count_after = get_corpus_size()
    return (1, max(0, count_after - count_before))


def poll_and_enrich(
    enable_feedback: bool = True,
    gen_cap: int = DEFAULT_GEN_CAP,
    corpus_cap: int = DEFAULT_CORPUS_CAP,
    batch_size: int = 1,
    workers: int = 1,
) -> tuple[int, int]:
    """Poll for analyzed papers and enrich them.

    With workers=1 (default), processes serially.
    With workers>1, processes batch_size papers concurrently using threads.
    Returns (papers_processed, new_papers_inserted).
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, title, year, doi, arxiv_id, openalex_id, semantic_scholar_id,
                          citation_count, generation
                   FROM papers
                   WHERE pipeline_status = 'analyzed'
                   ORDER BY citation_count DESC
                   LIMIT %s
                   FOR UPDATE SKIP LOCKED""",
                (batch_size,),
            )
            rows = cur.fetchall()
            if not rows:
                return (0, 0)
            papers = [dict(r) for r in rows]

            for p in papers:
                cur.execute(
                    "UPDATE papers SET pipeline_status = 'enriching' WHERE id = %s",
                    (p["id"],),
                )

    total_processed = 0
    total_new = 0

    if workers <= 1:
        for paper in papers:
            processed, new = _enrich_one(paper, enable_feedback, gen_cap, corpus_cap)
            total_processed += processed
            total_new += new
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_enrich_one, paper, enable_feedback, gen_cap, corpus_cap): paper
                for paper in papers
            }
            for future in as_completed(futures):
                processed, new = future.result()
                total_processed += processed
                total_new += new

    return (total_processed, total_new)


def main():
    parser = argparse.ArgumentParser(description="Agent 4: Citation Enricher (OpenAlex)")
    parser.add_argument("--poll-interval", type=int, default=5, help="Seconds between polls when idle")
    parser.add_argument("--once", action="store_true", help="Process one paper and exit")
    parser.add_argument("--max-papers", type=int, default=0, help="Max papers (0=unlimited)")
    parser.add_argument("--no-feedback", action="store_true", help="Disable feedback loop")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent workers (default: 5)")
    parser.add_argument("--batch-size", type=int, default=10, help="Papers per batch (default: 10)")
    parser.add_argument("--gen-cap", type=int, default=DEFAULT_GEN_CAP, help="Max generation depth for feedback (default: 3)")
    parser.add_argument("--corpus-cap", type=int, default=DEFAULT_CORPUS_CAP, help="Max non-archived papers before stopping feedback (default: 5000)")
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("  AGENT 4: CITATION ENRICHER (OpenAlex)", flush=True)
    print("  Assembly Line — Station 4", flush=True)
    print("=" * 60, flush=True)
    print(f"  API:         OpenAlex (100K req/day, no auth)", flush=True)
    print(f"  Workers:     {args.workers} concurrent, batch size {args.batch_size}", flush=True)
    print(f"  Feedback:    {'disabled' if args.no_feedback else 'enabled'}", flush=True)
    print(f"  Safety:      gen_cap={args.gen_cap}, corpus_cap={args.corpus_cap}", flush=True)
    print(f"  Status:      {count_by_status()}", flush=True)

    total_processed = 0
    total_skipped = 0
    total_new_inserted = 0
    cycle_stats = []
    feedback_disabled_by_diminishing = False
    start_time = time.time()

    while True:
        current_feedback = (not args.no_feedback) and (not feedback_disabled_by_diminishing)
        processed, new_inserted = poll_and_enrich(
            enable_feedback=current_feedback,
            gen_cap=args.gen_cap,
            corpus_cap=args.corpus_cap,
            batch_size=args.batch_size,
            workers=args.workers,
        )

        if processed > 0:
            total_processed += processed
            total_new_inserted += new_inserted
            cycle_stats.append((processed, new_inserted))

            if total_processed % 10 == 0:
                elapsed = time.time() - start_time
                rate = total_processed / elapsed * 60 if elapsed > 0 else 0
                print(f"  Enriched {total_processed} papers ({rate:.0f}/min), "
                      f"+{total_new_inserted} feedback. "
                      f"Queue: ~{count_by_status().get('analyzed', '?')}",
                      flush=True)

            # Safety bound 3: Diminishing returns check
            if not args.no_feedback and not feedback_disabled_by_diminishing and len(cycle_stats) >= 10:
                windows = []
                for i in range(max(0, len(cycle_stats) - 30), len(cycle_stats), 10):
                    chunk = cycle_stats[i:i+10]
                    if len(chunk) == 10:
                        chunk_processed = sum(p for p, _ in chunk)
                        chunk_inserted = sum(n for _, n in chunk)
                        ratio = chunk_inserted / chunk_processed if chunk_processed > 0 else 0
                        windows.append(ratio)

                if len(windows) >= DIMINISHING_RETURNS_STREAK:
                    recent = windows[-DIMINISHING_RETURNS_STREAK:]
                    if all(r < DIMINISHING_RETURNS_THRESHOLD for r in recent):
                        print(f"  ** Diminishing returns: disabling feedback loop.", flush=True)
                        feedback_disabled_by_diminishing = True

            if args.once:
                break
            if args.max_papers and total_processed >= args.max_papers:
                break
        else:
            if args.once:
                print("  No analyzed papers to enrich.", flush=True)
                break
            print(f"  Waiting for analyzed papers... (polling every {args.poll_interval}s)", flush=True)
            time.sleep(args.poll_interval)

    print(f"\n  Enricher complete. Processed: {total_processed}, Skipped: {total_skipped}, "
          f"Feedback: +{total_new_inserted}", flush=True)


if __name__ == "__main__":
    main()
