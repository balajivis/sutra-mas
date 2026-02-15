#!/usr/bin/env python3
"""Agent 1: Collector — First station on the assembly line.

Collects ~5000 MAS papers from multiple sources:
  1. OpenAlex concept-filtered search (primary, bulk)
  2. Semantic Scholar citation expansion from seeds (backward + forward)
  3. OpenAlex keyword queries per MAS branch

Papers are inserted with pipeline_status='collected' for Agent 2 to pick up.

Usage:
    python3 -m pipeline.assembly.agent1_collector [--max-papers 5000] [--skip-openalex] [--skip-citations]
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import insert_paper, update_paper, count_by_status, total_papers, get_conn
from pipeline.apis.openalex import (
    _request as oa_request,
    BASE_URL as OA_BASE_URL,
    search_works as oa_search,
)
from pipeline.apis.semantic_scholar import (
    get_references,
    get_citations,
    get_paper as s2_get_paper,
)

# ── MAS Concept Filter ──────────────────────────────────────────────────────

# OpenAlex concept IDs for MAS-adjacent topics (verified Feb 2026)
MAS_CONCEPT_IDS = [
    "C41550386",    # Multi-agent system (L2, 62K works)
    "C74072328",    # Intelligent agent (L2, 21K works)
    "C5894958",     # Software agent (L2, 8K works)
    "C13687954",    # Autonomous agent (L2, 12K works)
    "C2775851571",  # Interaction protocol (L3, 1.4K works)
    "C2778956278",  # Agent-oriented software engineering (L4, 1K works)
]

MAS_CONCEPT_NAMES = {
    "multi-agent system", "intelligent agent", "software agent",
    "distributed artificial intelligence", "agent-based model",
    "multi-agent", "multiagent", "autonomous agent", "agent communication",
    "belief-desire-intention", "bdi", "contract net", "blackboard system",
    "agent coordination", "agent cooperation", "agent negotiation",
    "agent organization", "agent architecture", "agent framework",
    "agent-based", "multi-agent reinforcement learning",
}

# Venue whitelist — papers from these venues are MAS by definition
MAS_VENUES = {
    "aamas", "jaamas", "jair", "aaai", "ijcai", "ecai",
    "icmas", "agents", "prima", "coin", "atal",
    "autonomous agents and multi-agent systems",
    "international conference on autonomous agents",
    "proceedings of the international joint conference on autonomous agents",
}


def is_mas_paper(work: dict) -> bool:
    """Check if an OpenAlex work is MAS-related via concepts or venue."""
    # Check concepts
    for concept in work.get("concepts", []):
        name = concept.get("display_name", "").lower()
        if any(mas_name in name for mas_name in MAS_CONCEPT_NAMES):
            return True
        cid = concept.get("id", "").split("/")[-1] if concept.get("id") else ""
        if cid in MAS_CONCEPT_IDS:
            return True

    # Check topics (newer OpenAlex field)
    for topic in work.get("topics", []):
        name = topic.get("display_name", "").lower()
        if any(mas_name in name for mas_name in MAS_CONCEPT_NAMES):
            return True

    # Check venue
    venue = ""
    primary_loc = work.get("primary_location") or {}
    primary_source = primary_loc.get("source") or {}
    if primary_source:
        venue = primary_source.get("display_name", "").lower()
    if any(v in venue for v in MAS_VENUES):
        return True

    # Check title keywords as fallback
    title = work.get("title", "").lower()
    if any(kw in title for kw in ["multi-agent", "multiagent", "multi agent"]):
        return True

    return False


def extract_paper_data(work: dict, source_tag: str) -> dict:
    """Extract standardized paper data from an OpenAlex work object."""
    ids = work.get("ids") or {}
    doi_raw = ids.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None
    arxiv_id = None

    # Try to extract arxiv from locations
    for loc in work.get("locations") or []:
        if not loc or not isinstance(loc, dict):
            continue
        loc_source = loc.get("source") or {}
        if not isinstance(loc_source, dict):
            continue
        if loc_source.get("display_name") == "arXiv (Cornell University)":
            landing = loc.get("landing_page_url") or ""
            if "arxiv.org/abs/" in landing:
                arxiv_id = landing.split("arxiv.org/abs/")[-1].split("v")[0]

    oa_id = work.get("id", "").split("/")[-1] if work.get("id") else None

    # Extract concepts list
    concepts = []
    for c in work.get("concepts") or []:
        if isinstance(c, dict):
            concepts.append({
                "name": c.get("display_name", ""),
                "score": c.get("score", 0),
            })

    # Authors
    authors = []
    for a in (work.get("authorships") or [])[:10]:  # cap at 10
        if isinstance(a, dict):
            author = a.get("author") or {}
            name = author.get("display_name", "") if isinstance(author, dict) else ""
            if name:
                authors.append(name)

    # Venue
    venue = None
    pl = work.get("primary_location") or {}
    if isinstance(pl, dict):
        pl_source = pl.get("source") or {}
        if isinstance(pl_source, dict):
            venue = pl_source.get("display_name")

    title = work.get("title") or "Untitled"
    if not isinstance(title, str):
        title = str(title)

    return {
        "title": title,
        "year": work.get("publication_year"),
        "abstract": work.get("abstract") or _reconstruct_abstract(work),
        "doi": doi,
        "arxiv_id": arxiv_id,
        "openalex_id": oa_id,
        "citation_count": work.get("cited_by_count", 0) or 0,
        "authors": authors,
        "venue": venue,
        "concepts": concepts,
        "source": source_tag,
        "is_classical": (work.get("publication_year") or 2025) < 2010,
    }


def _reconstruct_abstract(work: dict) -> Optional[str]:
    """Reconstruct abstract from OpenAlex inverted index."""
    inv = work.get("abstract_inverted_index")
    if not inv:
        return None
    # Build word → position list, then sort by position
    words = []
    for word, positions in inv.items():
        for pos in positions:
            words.append((pos, word))
    words.sort()
    return " ".join(w for _, w in words)


# ── Collection Strategies ────────────────────────────────────────────────────

def collect_openalex_concept_search(max_papers: int = 3000) -> int:
    """Strategy 1: Search OpenAlex for papers with MAS concepts.

    Uses the OpenAlex filter API to find papers tagged with MAS concepts,
    sorted by citation count (most cited first).
    """
    print("\n=== Strategy 1: OpenAlex Concept Search ===")
    inserted = 0
    cursor = "*"
    page = 0

    # Multi-agent system concept filter + minimum citation bar
    concept_filter = "concepts.id:C41550386|C74072328|C5894958|C13687954"
    base_filter = f"{concept_filter},cited_by_count:>4"

    while inserted < max_papers and cursor:
        page += 1
        params = (
            f"filter={base_filter}"
            f"&per_page=200"
            f"&select=id,title,publication_year,cited_by_count,ids,concepts,authorships,"
            f"primary_location,locations,abstract_inverted_index,topics"
            f"&sort=cited_by_count:desc"
            f"&cursor={cursor}"
        )
        url = f"{OA_BASE_URL}/works?{params}"
        data = oa_request(url)

        results = data.get("results", [])
        if not results:
            break

        cursor = data.get("meta", {}).get("next_cursor")

        for work in results:
            try:
                if not is_mas_paper(work):
                    continue
                paper = extract_paper_data(work, "openalex_concept")
                pid = insert_paper(**paper)
                if pid:
                    inserted += 1
            except Exception as e:
                print(f"  [WARN] Skipping paper: {e}")
                continue

        print(f"  Page {page}: {len(results)} works fetched, {inserted} total inserted")
        time.sleep(0.15)  # Polite pause

        if inserted >= max_papers:
            break

    print(f"  → OpenAlex concept search: {inserted} papers inserted")
    return inserted


def collect_openalex_keyword_search(max_papers: int = 1000) -> int:
    """Strategy 2: Targeted keyword searches per MAS branch."""
    print("\n=== Strategy 2: OpenAlex Keyword Search ===")

    queries = [
        # Coordination
        ("multi-agent coordination LLM", "keyword_coordination"),
        ("agent cooperation distributed problem solving", "keyword_cooperation"),
        ("contract net protocol task allocation", "keyword_contract_net"),
        # Communication
        ("agent communication language performative", "keyword_communication"),
        ("KQML FIPA agent protocol", "keyword_fipa"),
        # Organization
        ("multi-agent organization hierarchy holonic", "keyword_organization"),
        ("agent team formation role allocation", "keyword_teams"),
        # Architecture
        ("BDI belief desire intention agent", "keyword_bdi"),
        ("blackboard system shared knowledge", "keyword_blackboard"),
        ("agent architecture reactive deliberative", "keyword_architecture"),
        # Modern MAS + LLM
        ("LLM multi-agent system coordination", "keyword_llm_mas"),
        ("large language model agent collaboration", "keyword_llm_collab"),
        ("multi-agent LLM failure", "keyword_llm_failure"),
        ("agentic framework orchestration", "keyword_agentic"),
        # Negotiation
        ("agent negotiation automated", "keyword_negotiation"),
        ("multi-agent auction mechanism design", "keyword_auction"),
    ]

    inserted = 0
    per_query = max(max_papers // len(queries), 50)

    for query, source_tag in queries:
        count = 0
        cursor = "*"
        while count < per_query and cursor:
            params = (
                f"search={query}"
                f"&per_page=100"
                f"&filter=cited_by_count:>2"
                f"&select=id,title,publication_year,cited_by_count,ids,concepts,authorships,"
                f"primary_location,locations,abstract_inverted_index,topics"
                f"&sort=relevance_score:desc"
                f"&cursor={cursor}"
            )
            url = f"{OA_BASE_URL}/works?{params}"
            data = oa_request(url)

            results = data.get("results", [])
            if not results:
                break

            cursor = data.get("meta", {}).get("next_cursor")

            for work in results:
                try:
                    if not is_mas_paper(work):
                        continue
                    paper = extract_paper_data(work, source_tag)
                    pid = insert_paper(**paper)
                    if pid:
                        count += 1
                        inserted += 1
                except Exception as e:
                    print(f"  [WARN] Skipping paper: {e}")
                    continue

            time.sleep(0.15)

            if count >= per_query:
                break

        print(f"  '{query}': {count} papers inserted")

    print(f"  → Keyword search: {inserted} total papers inserted")
    return inserted


def collect_citation_expansion(max_papers: int = 1500) -> int:
    """Strategy 3: Expand from seeds via Semantic Scholar citation graph.

    For each seed paper:
      - Fetch forward citations (papers citing the seed)
      - For each citation, check if MAS-related via title keywords
      - Insert MAS papers as 'collected'
    """
    print("\n=== Strategy 3: Citation Expansion from Seeds ===")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, semantic_scholar_id FROM papers WHERE source = 'r1_seeds' AND semantic_scholar_id IS NOT NULL"
            )
            seeds = cur.fetchall()

    inserted = 0
    for seed_id, seed_title, s2_id in seeds:
        if inserted >= max_papers:
            break

        print(f"  Expanding: {seed_title[:60]}...")

        # Forward citations (who cites this seed)
        try:
            citations = get_citations(
                s2_id,
                fields="paperId,title,year,citationCount,externalIds,abstract",
                limit=500,
            )
        except Exception as e:
            print(f"    Error fetching citations: {e}")
            continue

        seed_inserted = 0
        for entry in citations:
            citing = entry.get("citingPaper", {})
            if not citing or not citing.get("title"):
                continue

            title = citing["title"]
            title_lower = title.lower()

            # Quick MAS keyword check on title
            is_mas = any(kw in title_lower for kw in [
                "multi-agent", "multiagent", "multi agent",
                "agent system", "agent coordination", "agent cooperation",
                "agent communication", "agent negotiation", "agent team",
                "autonomous agent", "intelligent agent", "software agent",
                "bdi", "contract net", "blackboard", "belief desire intention",
                "llm agent", "language model agent", "agentic",
            ])
            if not is_mas:
                continue

            ext_ids = citing.get("externalIds", {}) or {}
            doi = ext_ids.get("DOI")
            arxiv_id = ext_ids.get("ArXiv")

            pid = insert_paper(
                title=title,
                year=citing.get("year"),
                abstract=citing.get("abstract"),
                doi=doi,
                arxiv_id=arxiv_id,
                semantic_scholar_id=citing.get("paperId"),
                citation_count=citing.get("citationCount", 0),
                source=f"citation_of_{seed_id}",
                is_classical=(citing.get("year") or 2025) < 2010,
            )
            if pid:
                seed_inserted += 1
                inserted += 1

        print(f"    → {seed_inserted} MAS papers from {len(citations)} citations")
        time.sleep(0.5)  # Be gentle with S2

    print(f"  → Citation expansion: {inserted} total papers inserted")
    return inserted


def collect_recent_high_venue(max_papers: int = 500) -> int:
    """Strategy 4: Recent papers from top venues (recency override for low-citation papers)."""
    print("\n=== Strategy 4: Recent High-Venue Papers (2024-2026) ===")

    top_venues = [
        "ICLR", "ICML", "NeurIPS", "AAAI", "IJCAI", "AAMAS",
        "ACL", "EMNLP", "NAACL", "COLM",
    ]
    inserted = 0

    for venue in top_venues:
        params = (
            f"filter=primary_location.source.display_name.search:{venue},"
            f"publication_year:2024-2026,"
            f"concepts.id:C41550386|C74072328|C5894958|C13687954"  # MAS concepts
            f"&per_page=100"
            f"&select=id,title,publication_year,cited_by_count,ids,concepts,authorships,"
            f"primary_location,locations,abstract_inverted_index,topics"
            f"&sort=cited_by_count:desc"
        )
        url = f"{OA_BASE_URL}/works?{params}"
        data = oa_request(url)

        results = data.get("results", [])
        venue_inserted = 0

        for work in results:
            try:
                paper = extract_paper_data(work, f"venue_{venue.lower()}")
                pid = insert_paper(**paper)
                if pid:
                    venue_inserted += 1
                    inserted += 1
            except Exception as e:
                continue

        if venue_inserted > 0:
            print(f"  {venue}: {venue_inserted} papers inserted")
        time.sleep(0.15)

    print(f"  → Recent high-venue: {inserted} total papers inserted")
    return inserted


def collect_from_csv(csv_path: str) -> int:
    """Strategy 0: Load papers from the pre-scraped papers-master.csv.

    This CSV has 8,817 papers already scraped from GitHub paper-list repos.
    96% have ArXiv URLs. Heavily modern (2024-2026).
    """
    import csv

    print(f"\n=== Strategy 0: CSV Import from {os.path.basename(csv_path)} ===")

    if not os.path.exists(csv_path):
        print(f"  [ERROR] CSV not found: {csv_path}")
        return 0

    inserted = 0
    skipped = 0

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("title") or "").strip()
            if not title:
                skipped += 1
                continue

            url = row.get("url", "") or ""
            arxiv_id = None
            if "arxiv.org/abs/" in url:
                arxiv_id = url.split("arxiv.org/abs/")[-1].split("v")[0].strip()

            year_str = (row.get("year") or "").strip()
            year = int(year_str) if year_str.isdigit() else None

            tags = [t.strip() for t in (row.get("sutra_tags") or "").split(";") if t.strip()]
            source_repo = (row.get("source_repo") or "").strip()
            code_url = (row.get("code_url") or "").strip()

            try:
                pid = insert_paper(
                    title=title,
                    year=year,
                    arxiv_id=arxiv_id,
                    source=f"csv_{source_repo}" if source_repo else "csv_import",
                    is_classical=(year or 2025) < 2010,
                    concepts=[{"name": t, "score": 1.0} for t in tags],
                    pipeline_status="collected",
                )
                if pid:
                    inserted += 1
                    # If we have a code URL, update it directly
                    if code_url:
                        update_paper(pid, "collector_csv", "collected",
                                     has_code=True, repo_url=code_url)
                else:
                    skipped += 1
            except Exception as e:
                skipped += 1
                continue

            if inserted % 500 == 0 and inserted > 0:
                print(f"  {inserted} inserted, {skipped} skipped (dupes/empty)...")

    print(f"  → CSV import: {inserted} papers inserted, {skipped} skipped")
    return inserted


# ── Main ─────────────────────────────────────────────────────────────────────

CSV_PATH = os.path.join(os.path.dirname(__file__), "../../corpus/papers-master.csv")


def main():
    parser = argparse.ArgumentParser(description="Agent 1: Collector")
    parser.add_argument("--max-papers", type=int, default=10000, help="Target paper count")
    parser.add_argument("--skip-csv", action="store_true", help="Skip CSV import")
    parser.add_argument("--skip-openalex", action="store_true", help="Skip OpenAlex concept search")
    parser.add_argument("--skip-keywords", action="store_true", help="Skip keyword search")
    parser.add_argument("--skip-citations", action="store_true", help="Skip citation expansion")
    parser.add_argument("--skip-venues", action="store_true", help="Skip venue search")
    parser.add_argument("--csv-path", type=str, default=CSV_PATH, help="Path to papers CSV")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    print("=" * 60)
    print("  AGENT 1: COLLECTOR")
    print("  Assembly Line — Station 1")
    print("=" * 60)
    print(f"\nTarget: ~{args.max_papers} MAS papers")
    print(f"Current DB: {total_papers()} papers")
    print(f"Status breakdown: {count_by_status()}")

    if args.dry_run:
        print("\n[DRY RUN] Would execute:")
        if not args.skip_csv:
            print(f"  0. CSV import from {args.csv_path}")
        if not args.skip_openalex:
            print(f"  1. OpenAlex concept search (classical MAS papers)")
        if not args.skip_keywords:
            print(f"  2. OpenAlex keyword search")
        if not args.skip_citations:
            print(f"  3. Citation expansion from 33 seeds")
        if not args.skip_venues:
            print(f"  4. Recent high-venue papers")
        return

    total_inserted = 0
    start = time.time()

    # Strategy 0: CSV import (the big one — 8,817 pre-scraped papers)
    if not args.skip_csv:
        n = collect_from_csv(args.csv_path)
        total_inserted += n

    # Strategy 1: OpenAlex concept search (fills classical gap — CSV is 99% modern)
    if not args.skip_openalex:
        n = collect_openalex_concept_search(max_papers=2500)
        total_inserted += n

    # Strategy 2: Targeted keyword searches
    if not args.skip_keywords:
        n = collect_openalex_keyword_search(max_papers=1000)
        total_inserted += n

    # Strategy 3: Citation graph expansion from seeds
    if not args.skip_citations:
        n = collect_citation_expansion(max_papers=1500)
        total_inserted += n

    # Strategy 4: Recent high-venue papers (recency override)
    if not args.skip_venues:
        remaining = args.max_papers - total_inserted
        if remaining > 0:
            n = collect_recent_high_venue(max_papers=min(remaining, 500))
            total_inserted += n

    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"  COLLECTOR COMPLETE")
    print(f"  Inserted: {total_inserted} new papers")
    print(f"  Total DB: {total_papers()} papers")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Status breakdown: {count_by_status()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
