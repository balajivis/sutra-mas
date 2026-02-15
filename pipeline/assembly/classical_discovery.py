#!/usr/bin/env python3
"""Hybrid Classical Discovery -- Bottom-up meets Top-down.

Uses the entire modern corpus as a discovery lens to find classical MAS papers
that the community actually builds on. Then compares with the top-down seed
backward pass to partition into:

  - Validated Foundations: cited by BOTH seeds AND modern papers  (A intersection B)
  - Lost Canaries:        in seed backward pass, NOT cited by modern  (B minus A)
  - Community Additions:  cited by modern, NOT in seed backward pass  (A minus B)

The Lost Canary finding IS the set difference.

Dual-source reference fetching:
  - OpenAlex referenced_works: batch API, for papers with openalex_id (fast)
  - Semantic Scholar references: per-paper API, for papers with arxiv_id (slower)

Usage:
    python3 -m pipeline.assembly.classical_discovery --dry-run
    python3 -m pipeline.assembly.classical_discovery --threshold 5
    python3 -m pipeline.assembly.classical_discovery --analyze-only
    python3 -m pipeline.assembly.classical_discovery --s2-limit 500
"""

import argparse
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.apis.openalex import (
    _request as oa_request,
    get_references_detailed,
    BASE_URL as OA_BASE,
)
from pipeline.assembly.db import get_conn, insert_paper

import psycopg2.extras

# Cache file for S2 references (slow to fetch, save progress)
CACHE_DIR = os.path.join(os.path.dirname(__file__), "../../pipeline/data")
S2_REFS_CACHE = os.path.join(CACHE_DIR, "s2_refs_cache.json")

# MAS title keywords for filtering classical candidates
MAS_KEYWORDS = [
    "multi-agent", "multiagent", "multi agent",
    "agent system", "agent coordination", "agent cooperation",
    "agent communication", "agent negotiation", "agent team",
    "autonomous agent", "intelligent agent", "software agent",
    "bdi", "contract net", "blackboard", "belief desire intention",
    "llm agent", "language model agent", "agentic",
    "agent framework", "agent architecture", "agent organization",
    "cooperative agent", "agent-based", "agent based",
    "distributed problem solving", "distributed artificial intelligence",
    "coordination mechanism", "coordination protocol",
    "joint intention", "shared plan", "teamwork",
    "task allocation", "coalition formation", "auction mechanism",
    "speech act", "kqml", "fipa", "acl message",
    "organizational design", "holonic", "role assignment",
    "norm enforcement", "trust model", "reputation",
    "negotiation protocol", "mechanism design",
    "swarm", "multi-robot", "consensus",
    "social choice", "game theory", "nash equilibrium",
]


def is_mas_related(title: str) -> bool:
    """Check if a title is MAS-related."""
    lower = title.lower()
    return any(kw in lower for kw in MAS_KEYWORDS)


# ── OpenAlex reference fetching (batch, fast) ──

def fetch_oa_referenced_works(openalex_ids: list[str], batch_size: int = 50) -> dict[str, list[str]]:
    """Batch-fetch referenced_works from OpenAlex.

    Returns dict mapping paper_key -> list of referenced OpenAlex work IDs.
    """
    from urllib.parse import urlencode

    result = {}
    total = len(openalex_ids)

    for i in range(0, total, batch_size):
        batch = openalex_ids[i:i + batch_size]
        ids = [oid.split("/")[-1] if "/" in oid else oid for oid in batch]
        filter_str = "|".join(ids)

        params = urlencode({
            "filter": f"openalex_id:{filter_str}",
            "per_page": batch_size,
            "select": "id,referenced_works,publication_year",
        })
        url = f"{OA_BASE}/works?{params}"

        data = oa_request(url)
        for work in data.get("results", []):
            oa_id = work.get("id", "")
            refs = work.get("referenced_works", [])
            # Normalize refs to short IDs
            result[oa_id] = [r.split("/")[-1] if "/" in r else r for r in refs]

        processed = min(i + batch_size, total)
        if processed % 200 == 0 or processed == total:
            print(f"    OpenAlex: {processed}/{total}")

        time.sleep(0.15)

    return result


# ── Semantic Scholar reference fetching (per-paper, slower) ──

def load_s2_cache() -> dict[str, list[dict]]:
    """Load cached S2 references from disk."""
    cache_path = os.path.abspath(S2_REFS_CACHE)
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_s2_cache(cache: dict):
    """Save S2 references cache to disk."""
    cache_path = os.path.abspath(S2_REFS_CACHE)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(cache, f)


def fetch_s2_references(arxiv_ids: list[str], limit: int = 0) -> dict[str, list[dict]]:
    """Fetch references for papers via Semantic Scholar.

    Uses cache to avoid re-fetching. Each entry is a list of dicts with
    paperId, title, year, externalIds.

    Returns dict mapping arxiv_id -> list of reference dicts.
    Rate limited to ~18 req/min (3.3s between calls) for free tier safety.
    """
    from pipeline.apis.semantic_scholar import get_references

    cache = load_s2_cache()
    to_fetch = [aid for aid in arxiv_ids if aid not in cache]

    if limit > 0:
        to_fetch = to_fetch[:limit]

    total = len(to_fetch)
    if total == 0:
        print(f"    S2: All {len(arxiv_ids)} papers already cached")
        return cache

    print(f"    S2: {len(cache)} cached, {total} to fetch (rate: ~18/min)")
    errors = 0

    for i, arxiv_id in enumerate(to_fetch):
        try:
            refs = get_references(
                f"ARXIV:{arxiv_id}",
                fields="citedPaper.paperId,citedPaper.title,citedPaper.year,citedPaper.externalIds",
                limit=500,
            )
            # Extract cited papers
            ref_list = []
            for entry in refs:
                cited = entry.get("citedPaper", {})
                if cited and cited.get("paperId"):
                    ref_list.append({
                        "paperId": cited["paperId"],
                        "title": cited.get("title", ""),
                        "year": cited.get("year"),
                        "externalIds": cited.get("externalIds", {}),
                    })
            cache[arxiv_id] = ref_list

        except Exception as e:
            errors += 1
            cache[arxiv_id] = []  # Mark as attempted (empty)
            if errors <= 5:
                print(f"      Error for arxiv:{arxiv_id}: {e}")

        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"    S2: {i + 1}/{total} ({errors} errors)")
            save_s2_cache(cache)  # Checkpoint

        time.sleep(3.3)  # ~18 req/min (conservative for free tier)

    save_s2_cache(cache)
    print(f"    S2: Done. {total - errors} fetched, {errors} errors")
    return cache


# ── DB queries ──

def get_lens_papers(min_year: int) -> dict:
    """Get papers to use as the discovery lens.

    Returns dict with 'oa' (papers with OpenAlex IDs) and 's2' (papers with arxiv_id only).
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Papers with OpenAlex IDs
            cur.execute("""
                SELECT id, title, year, openalex_id
                FROM papers
                WHERE openalex_id IS NOT NULL
                  AND year >= %s
                  AND pipeline_status != 'archived'
            """, (min_year,))
            oa_papers = [dict(r) for r in cur.fetchall()]

            # Papers with arxiv_id but no OpenAlex ID (recent papers)
            cur.execute("""
                SELECT id, title, year, arxiv_id
                FROM papers
                WHERE arxiv_id IS NOT NULL
                  AND openalex_id IS NULL
                  AND year >= %s
                  AND pipeline_status != 'archived'
            """, (min_year,))
            s2_papers = [dict(r) for r in cur.fetchall()]

    return {"oa": oa_papers, "s2": s2_papers}


def get_seed_backward_papers() -> dict[str, dict]:
    """Get all papers from the r1 backward pass (top-down set B)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, year, openalex_id, citation_count, source, pipeline_status
                FROM papers
                WHERE source LIKE 'r1_backward_%%'
                   OR pipeline_status = 'seed'
            """)
            result = {}
            for row in cur.fetchall():
                d = dict(row)
                oa_id = d.get("openalex_id")
                if oa_id:
                    # Index by both full URL and short ID
                    result[oa_id] = d
                    short = oa_id.split("/")[-1] if "/" in oa_id else oa_id
                    result[short] = d
            return result


def get_existing_openalex_ids() -> set[str]:
    """Get all OpenAlex IDs already in the DB."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT openalex_id FROM papers WHERE openalex_id IS NOT NULL")
            return {row[0] for row in cur.fetchall()}


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Hybrid Classical Discovery")
    parser.add_argument("--threshold", type=int, default=0,
                        help="Min citations from lens papers (0=auto-select)")
    parser.add_argument("--min-year", type=int, default=2010,
                        help="Min year for lens papers (default: 2010)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze only, don't insert papers")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Just show the distribution, skip partitioning")
    parser.add_argument("--no-s2", action="store_true",
                        help="Skip Semantic Scholar reference fetching")
    parser.add_argument("--s2-limit", type=int, default=0,
                        help="Max new S2 papers to fetch (0=all, useful for testing)")
    parser.add_argument("--mas-only", action="store_true", default=True,
                        help="Only insert MAS-related classical papers")
    parser.add_argument("--output", type=str, default="pipeline/data/classical_discovery.json",
                        help="Output JSON path")
    args = parser.parse_args()

    print("=" * 65)
    print("  HYBRID CLASSICAL DISCOVERY")
    print("  Bottom-up (modern corpus) + Top-down (seed backward pass)")
    print("=" * 65)

    # ── Step 1: Get lens papers ──
    print(f"\n  Step 1: Loading lens papers (year >= {args.min_year})...")
    lens = get_lens_papers(args.min_year)
    oa_papers = lens["oa"]
    s2_papers = lens["s2"]
    total_lens = len(oa_papers) + len(s2_papers)
    print(f"    OpenAlex lens: {len(oa_papers)} papers")
    print(f"    S2/ArXiv lens: {len(s2_papers)} papers")
    print(f"    Total lens:    {total_lens} papers")

    if total_lens == 0:
        print("  ERROR: No lens papers found. Load papers first.")
        sys.exit(1)

    # ── Step 2: Fetch references from both sources ──
    # We unify everything into a reverse citation map keyed by OpenAlex work ID.
    # For S2 references, we map S2 paperId -> OpenAlex ID where possible.
    reverse_map = Counter()     # ref_key -> count of lens papers citing it
    total_refs = 0
    papers_with_refs = 0

    # 2a: OpenAlex referenced_works (batch, fast)
    if oa_papers:
        print(f"\n  Step 2a: Fetching OpenAlex referenced_works ({len(oa_papers)} papers)...")
        oa_ids = [p["openalex_id"] for p in oa_papers]
        oa_refs = fetch_oa_referenced_works(oa_ids)

        for oa_id, refs in oa_refs.items():
            if refs:
                papers_with_refs += 1
                total_refs += len(refs)
            for ref_id in refs:
                reverse_map[ref_id] += 1

        print(f"    OA papers with refs: {papers_with_refs}/{len(oa_papers)}")
        print(f"    OA total references: {total_refs}")

    # 2b: Semantic Scholar references (per-paper, slower)
    if s2_papers and not args.no_s2:
        print(f"\n  Step 2b: Fetching S2 references ({len(s2_papers)} papers)...")
        arxiv_ids = [p["arxiv_id"] for p in s2_papers]
        s2_refs = fetch_s2_references(arxiv_ids, limit=args.s2_limit)

        s2_with_refs = 0
        s2_total_refs = 0

        # For S2 references, we need to map back to OpenAlex IDs.
        # S2 externalIds may contain 'ARXIV' or 'DOI' which we can use.
        # But for now, use a composite key: "s2:{paperId}" for S2-only refs,
        # and OpenAlex ID if the ref has an ArXiv ID we can look up.
        # The important thing is that the reverse map is consistent.
        for arxiv_id in arxiv_ids:
            refs = s2_refs.get(arxiv_id, [])
            if refs:
                s2_with_refs += 1
                s2_total_refs += len(refs)

            for ref in refs:
                # Try to find an OpenAlex ID via externalIds
                ext = ref.get("externalIds", {}) or {}
                oa_id = ext.get("OpenAlex")
                if oa_id:
                    # Normalize to short form
                    key = oa_id.split("/")[-1] if "/" in oa_id else oa_id
                else:
                    # Use S2 paper ID as fallback key (won't match OA-keyed set B)
                    key = f"s2:{ref['paperId']}"

                reverse_map[key] += 1

        papers_with_refs += s2_with_refs
        total_refs += s2_total_refs
        print(f"    S2 papers with refs: {s2_with_refs}/{len(arxiv_ids)}")
        print(f"    S2 total references: {s2_total_refs}")
    elif s2_papers and args.no_s2:
        print(f"\n  Step 2b: Skipping S2 references (--no-s2)")

    unique_refs = len(reverse_map)
    oa_keyed = sum(1 for k in reverse_map if not k.startswith("s2:"))
    s2_keyed = sum(1 for k in reverse_map if k.startswith("s2:"))
    print(f"\n  Total unique referenced works: {unique_refs}")
    print(f"    OpenAlex-keyed: {oa_keyed}, S2-only-keyed: {s2_keyed}")

    # ── Step 3: Distribution ──
    print("\n  Step 3: Citation count distribution:")
    thresholds = [1, 2, 3, 5, 10, 15, 20, 30, 50, 100]
    for t in thresholds:
        count = sum(1 for v in reverse_map.values() if v >= t)
        print(f"    Cited by >= {t:3d} lens papers: {count:>5d} referenced works")

    if args.analyze_only:
        print(f"\n  Top 30 most-cited referenced works:")
        for ref_id, count in reverse_map.most_common(30):
            print(f"    {count:>4d}x | {ref_id}")
        return

    # ── Step 4: Select threshold and fetch metadata ──
    threshold = args.threshold
    if threshold == 0:
        for t in [20, 15, 10, 7, 5, 3, 2]:
            count = sum(1 for v in reverse_map.values() if v >= t)
            if count <= 500:
                threshold = t
                break
        else:
            threshold = 2
        n_candidates = sum(1 for v in reverse_map.values() if v >= threshold)
        print(f"\n  Auto-selected threshold: {threshold} (yields {n_candidates} candidates)")

    # Only fetch metadata for OpenAlex-keyed candidates (we can batch-fetch those)
    candidate_ids = [
        ref_id for ref_id, count in reverse_map.items()
        if count >= threshold and not ref_id.startswith("s2:")
    ]
    s2_only_candidates = [
        ref_id for ref_id, count in reverse_map.items()
        if count >= threshold and ref_id.startswith("s2:")
    ]

    print(f"\n  Step 4: Fetching metadata for {len(candidate_ids)} OA-keyed candidates...")
    if s2_only_candidates:
        print(f"    ({len(s2_only_candidates)} S2-only candidates without OA metadata)")

    candidate_urls = [f"https://openalex.org/{cid}" for cid in candidate_ids]
    candidate_metadata = get_references_detailed(candidate_urls, batch_size=50)
    print(f"    Fetched metadata for {len(candidate_metadata)} works")

    # ── Step 5: Filter to pre-2010 ──
    classical_candidates = []
    modern_bridge = []
    for work in candidate_metadata:
        year = work.get("publication_year")
        oa_id = work.get("id", "")
        oa_short = oa_id.split("/")[-1] if "/" in oa_id else oa_id
        cite_count = reverse_map.get(oa_short, 0)

        entry = {
            "openalex_id": oa_id,
            "title": work.get("title", ""),
            "year": year,
            "cited_by_count": work.get("cited_by_count", 0),
            "modern_corpus_citations": cite_count,
            "ids": work.get("ids", {}),
        }

        if year and year < 2010:
            classical_candidates.append(entry)
        elif year and year < 2020:
            modern_bridge.append(entry)

    classical_candidates.sort(key=lambda x: x["modern_corpus_citations"], reverse=True)

    print(f"\n  Pre-2010 classical candidates: {len(classical_candidates)}")
    print(f"  2010-2019 bridge papers: {len(modern_bridge)}")

    # ── Step 6: Compare with seed backward pass (top-down set B) ──
    print("\n  Step 5: Comparing with seed backward pass (top-down)...")
    seed_papers = get_seed_backward_papers()
    existing_oa_ids = get_existing_openalex_ids()

    # Build set of seed OpenAlex short IDs for comparison
    seed_oa_shorts = set()
    for key in seed_papers:
        if key.startswith("W"):
            seed_oa_shorts.add(key)
        elif key.startswith("https://openalex.org/"):
            seed_oa_shorts.add(key.split("/")[-1])

    validated_foundations = []  # A ∩ B
    community_additions = []   # A \ B

    for c in classical_candidates:
        oa_short = c["openalex_id"].split("/")[-1] if "/" in c["openalex_id"] else c["openalex_id"]
        if oa_short in seed_oa_shorts:
            validated_foundations.append(c)
        else:
            community_additions.append(c)

    # Lost canaries: seed backward papers NOT in the bottom-up set
    bottom_up_shorts = set()
    for c in classical_candidates:
        oa_short = c["openalex_id"].split("/")[-1] if "/" in c["openalex_id"] else c["openalex_id"]
        bottom_up_shorts.add(oa_short)

    lost_canaries = []
    seen_lost = set()
    for key, paper in seed_papers.items():
        oa_id = paper.get("openalex_id")
        if not oa_id:
            continue
        oa_short = oa_id.split("/")[-1] if "/" in oa_id else oa_id
        year = paper.get("year")

        if year and year >= 2010:
            continue
        if oa_short in bottom_up_shorts:
            continue
        if oa_short in seen_lost:
            continue
        seen_lost.add(oa_short)

        lost_canaries.append({
            "openalex_id": oa_id,
            "title": paper.get("title", ""),
            "year": year,
            "cited_by_count": paper.get("citation_count", 0),
            "modern_corpus_citations": 0,
            "source": paper.get("source", ""),
        })

    lost_canaries.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)

    # ── Print results ──
    print("\n" + "=" * 65)
    print("  RESULTS")
    print("=" * 65)

    print(f"\n  Validated Foundations (A ∩ B): {len(validated_foundations)}")
    print(f"    Classical papers cited by BOTH seeds AND modern corpus")
    for p in validated_foundations[:20]:
        mas = " [MAS]" if is_mas_related(p["title"]) else ""
        print(f"    {p['year'] or '?':>4} | {p['modern_corpus_citations']:>3}x | {p['cited_by_count']:>6} total | {p['title'][:50]}{mas}")
    if len(validated_foundations) > 20:
        print(f"    ... and {len(validated_foundations) - 20} more")

    mas_lost = [lc for lc in lost_canaries if is_mas_related(lc["title"])]
    non_mas_lost = [lc for lc in lost_canaries if not is_mas_related(lc["title"])]

    print(f"\n  Lost Canaries (B minus A): {len(lost_canaries)}")
    print(f"    In seed backward pass but NOT cited by lens (threshold={threshold})")
    print(f"    MAS-related: {len(mas_lost)}, Non-MAS: {len(non_mas_lost)}")
    for p in mas_lost[:25]:
        print(f"    {p['year'] or '?':>4} | {p['cited_by_count']:>6} total | {p['source']:30s} | {p['title'][:45]}")
    if len(mas_lost) > 25:
        print(f"    ... and {len(mas_lost) - 25} more MAS-related lost canaries")

    mas_additions = [ca for ca in community_additions if is_mas_related(ca["title"])]
    print(f"\n  Community Additions (A minus B): {len(community_additions)}")
    print(f"    Cited by lens but NOT in seed backward pass")
    print(f"    MAS-related: {len(mas_additions)} / {len(community_additions)} total")
    for p in mas_additions[:20]:
        print(f"    {p['year'] or '?':>4} | {p['modern_corpus_citations']:>3}x | {p['cited_by_count']:>6} total | {p['title'][:50]}")
    if len(mas_additions) > 20:
        print(f"    ... and {len(mas_additions) - 20} more MAS-related additions")

    # ── Insert new papers ──
    if not args.dry_run:
        print(f"\n  Step 6: Inserting new classical papers into DB...")
        inserted = 0
        skipped_existing = 0
        skipped_non_mas = 0

        for c in community_additions + validated_foundations:
            oa_id = c["openalex_id"]
            if oa_id in existing_oa_ids:
                skipped_existing += 1
                continue

            title = c.get("title", "")
            if args.mas_only and not is_mas_related(title):
                skipped_non_mas += 1
                continue

            ids = c.get("ids", {})
            doi = ids.get("doi", "").replace("https://doi.org/", "") if ids.get("doi") else None

            pid = insert_paper(
                title=title,
                year=c.get("year"),
                openalex_id=oa_id,
                doi=doi,
                citation_count=c.get("cited_by_count", 0),
                source="community_validated",
                is_classical=(c.get("year") or 2025) < 2010,
                pipeline_status="collected",
                generation=0,
            )
            if pid:
                inserted += 1
                existing_oa_ids.add(oa_id)

        print(f"    Inserted: {inserted}")
        print(f"    Skipped (already in DB): {skipped_existing}")
        print(f"    Skipped (non-MAS): {skipped_non_mas}")

    # ── Save output ──
    output_path = os.path.join(os.path.dirname(__file__), "../..", args.output)
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    output = {
        "metadata": {
            "lens_papers": total_lens,
            "lens_oa": len(oa_papers),
            "lens_s2": len(s2_papers),
            "papers_with_refs": papers_with_refs,
            "total_references": total_refs,
            "unique_referenced_works": unique_refs,
            "threshold": threshold,
            "min_year": args.min_year,
        },
        "validated_foundations": validated_foundations,
        "lost_canaries": lost_canaries,
        "community_additions": community_additions[:200],
        "distribution": {str(t): sum(1 for v in reverse_map.values() if v >= t) for t in thresholds},
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Output saved to {output_path}")

    print(f"\n  Summary:")
    print(f"    Lens papers (>= {args.min_year}):   {total_lens} ({len(oa_papers)} OA + {len(s2_papers)} S2)")
    print(f"    Unique references found:    {unique_refs}")
    print(f"    Classical candidates (>={threshold}x): {len(classical_candidates)}")
    print(f"    Validated Foundations:       {len(validated_foundations)}")
    print(f"    Lost Canaries:              {len(lost_canaries)} ({len(mas_lost)} MAS-related)")
    print(f"    Community Additions:        {len(community_additions)} ({len(mas_additions)} MAS-related)")


if __name__ == "__main__":
    main()
