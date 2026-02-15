#!/usr/bin/env python3
"""Bulk import AAMAS proceedings from DBLP.

Imports all papers from:
- AAMAS (2002-2025)
- ICMAS (1995, 1996, 1998, 2000)
- AGENTS (1997, 1998, 1999, 2000, 2001)

Uses the DBLP search API. Deduplicates against existing corpus by
normalized title matching. Papers enter pipeline as 'collected'.

Usage:
    python3 -m pipeline.assembly.import_aamas_dblp [--dry-run]
"""

import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from pipeline.assembly.db import get_conn

DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
USER_AGENT = "sutra-research/1.0 (research@getkapi.com)"


def fetch_dblp_venue_year(venue: str, year: int, max_results: int = 500) -> list[dict]:
    """Fetch all papers for a venue+year from DBLP."""
    query = f"venue:{venue} year:{year}"
    params = urlencode({"q": query, "format": "json", "h": max_results})
    url = f"{DBLP_SEARCH_URL}?{params}"
    req = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [DBLP error] {venue} {year}: {e}")
        return []

    hits = data.get("result", {}).get("hits", {})
    papers = []
    for h in hits.get("hit", []):
        info = h.get("info", {})
        title = info.get("title", "").rstrip(".")
        if not title or len(title) < 5:
            continue

        # Extract authors
        authors_raw = info.get("authors", {}).get("author", [])
        if isinstance(authors_raw, dict):
            authors_raw = [authors_raw]
        authors = [a.get("text", a) if isinstance(a, dict) else str(a)
                    for a in authors_raw]

        # Extract DOI
        doi = None
        ee = info.get("ee", "")
        if isinstance(ee, list):
            for e in ee:
                if "doi.org" in str(e):
                    doi = str(e).split("doi.org/")[-1]
                    break
            ee = ee[0] if ee else ""
        elif "doi.org" in str(ee):
            doi = str(ee).split("doi.org/")[-1]

        papers.append({
            "title": title,
            "year": int(info.get("year", year)),
            "venue": info.get("venue", venue.upper()),
            "doi": doi,
            "authors": authors,
            "source_url": str(ee) if ee else None,
        })

    return papers


def normalize_title(title: str) -> str:
    """Normalize a title for dedup comparison."""
    import re
    t = title.lower().strip()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def main():
    dry_run = "--dry-run" in sys.argv

    # Define all venue+year combinations
    jobs = []

    # Pre-AAMAS: ICMAS
    for y in [1995, 1996, 1998, 2000]:
        jobs.append(("icmas", y, "ICMAS"))

    # Pre-AAMAS: AGENTS
    for y in [1997, 1998, 1999, 2000, 2001]:
        jobs.append(("agents", y, "AGENTS"))

    # AAMAS proper
    for y in range(2002, 2026):
        jobs.append(("aamas", y, "AAMAS"))

    print("=" * 80)
    print(f"DBLP AAMAS Import {'(DRY RUN)' if dry_run else ''}")
    print("=" * 80)

    # Step 1: Build existing title index for dedup
    print("\n1. Building existing title index...")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM papers")
        existing = {}
        for pid, title in cur.fetchall():
            norm = normalize_title(title)
            existing[norm] = pid
        print(f"   Indexed {len(existing)} existing papers")

    # Step 2: Fetch and collect all DBLP papers
    print("\n2. Fetching from DBLP...")
    all_papers = []
    for venue_q, year, venue_label in jobs:
        time.sleep(1.0)  # Polite rate limit
        papers = fetch_dblp_venue_year(venue_q, year)
        new_count = 0
        dup_count = 0
        for p in papers:
            norm = normalize_title(p["title"])
            if norm in existing:
                dup_count += 1
            else:
                new_count += 1
                p["venue_label"] = venue_label
                all_papers.append(p)
                existing[norm] = -1  # Mark as pending to avoid self-dups

        print(f"   {venue_label:6s} {year}: {len(papers):4d} fetched, "
              f"{new_count:4d} new, {dup_count:4d} already in corpus")

    print(f"\n   Total new papers to import: {len(all_papers)}")

    if dry_run:
        print("\n   [DRY RUN] No papers inserted.")
        # Show sample
        print("\n   Sample of papers to import:")
        for p in all_papers[:20]:
            print(f"     {p['year']} | {p['venue_label']:6s} | {p['title'][:60]}")
        return

    # Step 3: Insert into database
    print("\n3. Inserting into database...")
    inserted = 0
    skipped = 0

    with get_conn() as conn:
        cur = conn.cursor()
        for p in all_papers:
            try:
                cur.execute("""
                    INSERT INTO papers (title, year, venue, doi, authors, source,
                                        source_url, pipeline_status, is_classical,
                                        generation, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'collected', %s, 0, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """, (
                    p["title"],
                    p["year"],
                    p.get("venue", "AAMAS"),
                    p.get("doi"),
                    json.dumps(p.get("authors", [])),
                    f"dblp_{p['venue_label'].lower()}",
                    p.get("source_url"),
                    p["year"] < 2010,  # is_classical heuristic
                ))
                result = cur.fetchone()
                if result:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"   [ERROR] {p['title'][:50]}: {e}")
                conn.rollback()
                skipped += 1

        conn.commit()

    print(f"\n   Inserted: {inserted}")
    print(f"   Skipped (conflict): {skipped}")

    # Step 4: Summary by venue/decade
    print("\n4. Import summary by venue and decade:")
    by_decade = {}
    for p in all_papers:
        decade = (p["year"] // 5) * 5
        key = f"{p['venue_label']} {decade}-{decade+4}"
        by_decade[key] = by_decade.get(key, 0) + 1
    for k in sorted(by_decade.keys()):
        print(f"   {k}: {by_decade[k]} papers")

    print(f"\n   Done. Total corpus now includes AAMAS proceedings.")
    print(f"   Run the year-by-year recall test again to measure improvement.")


if __name__ == "__main__":
    main()
