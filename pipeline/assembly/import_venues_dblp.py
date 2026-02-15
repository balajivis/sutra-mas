#!/usr/bin/env python3
"""Bulk import MAS papers from major venues via DBLP.

Imports from:
- MAS-specific venues (all papers): PRIMA, ATAL, EUMAS
- General AI conferences (MAS keyword filtered): IJCAI, AAAI, ECAI, NeurIPS, ICML, ICLR
- Journals (MAS keyword filtered): JAAMAS, AIJ, JAIR

Deduplicates against existing corpus by normalized title matching.
Papers enter pipeline as 'collected'.

Usage:
    python3 -m pipeline.assembly.import_venues_dblp [--dry-run]
"""

import json
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote

from pipeline.assembly.db import get_conn

DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
USER_AGENT = "sutra-research/1.0 (research@getkapi.com)"


def fetch_dblp_query(query: str, max_results: int = 500) -> list[dict]:
    """Fetch papers from DBLP for an arbitrary query."""
    params = urlencode({"q": query, "format": "json", "h": max_results})
    url = f"{DBLP_SEARCH_URL}?{params}"
    req = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"    [DBLP error] {query[:50]}: {e}")
        return []

    hits = data.get("result", {}).get("hits", {})
    papers = []
    for h in hits.get("hit", []):
        info = h.get("info", {})
        title = info.get("title", "").rstrip(".")
        if not title or len(title) < 5:
            continue

        authors_raw = info.get("authors", {}).get("author", [])
        if isinstance(authors_raw, dict):
            authors_raw = [authors_raw]
        authors = [a.get("text", a) if isinstance(a, dict) else str(a)
                    for a in authors_raw]

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

        venue = info.get("venue", "")
        if isinstance(venue, list):
            venue = venue[0] if venue else ""

        papers.append({
            "title": title,
            "year": int(info.get("year", 0)),
            "venue": venue,
            "doi": doi,
            "authors": authors,
            "source_url": str(ee) if ee else None,
        })

    return papers


def normalize_title(title: str) -> str:
    """Normalize a title for dedup comparison."""
    t = title.lower().strip()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


# ============================================================
# Venue definitions
# ============================================================

# MAS-specific venues: import ALL papers (no keyword filter needed)
MAS_VENUES = [
    # (query, source_tag, description)
    ("venue:prima", "dblp_prima", "PRIMA (Principles and Practice of MAS)"),
    ("venue:atal", "dblp_atal", "ATAL (Agent Theories, Architectures, Languages)"),
    ("venue:eumas", "dblp_eumas", "EUMAS (European Workshop on MAS)"),
]

# General AI venues: need MAS keyword filter
# Multiple queries per venue to maximize coverage
GENERAL_VENUE_QUERIES = [
    # IJCAI
    ("venue:ijcai multi-agent", "dblp_ijcai", "IJCAI (multi-agent)"),
    ("venue:ijcai multiagent", "dblp_ijcai", "IJCAI (multiagent)"),
    ("venue:ijcai autonomous agent", "dblp_ijcai", "IJCAI (autonomous agent)"),
    ("venue:ijcai agent coordination", "dblp_ijcai", "IJCAI (agent coordination)"),
    ("venue:ijcai agent negotiation", "dblp_ijcai", "IJCAI (agent negotiation)"),
    ("venue:ijcai agent cooperation", "dblp_ijcai", "IJCAI (agent cooperation)"),
    ("venue:ijcai agent communication", "dblp_ijcai", "IJCAI (agent communication)"),
    # AAAI
    ("venue:aaai multi-agent", "dblp_aaai", "AAAI (multi-agent)"),
    ("venue:aaai multiagent", "dblp_aaai", "AAAI (multiagent)"),
    ("venue:aaai autonomous agent", "dblp_aaai", "AAAI (autonomous agent)"),
    ("venue:aaai agent coordination", "dblp_aaai", "AAAI (agent coordination)"),
    ("venue:aaai agent negotiation", "dblp_aaai", "AAAI (agent negotiation)"),
    ("venue:aaai agent cooperation", "dblp_aaai", "AAAI (agent cooperation)"),
    # ECAI
    ("venue:ecai multi-agent", "dblp_ecai", "ECAI (multi-agent)"),
    ("venue:ecai multiagent", "dblp_ecai", "ECAI (multiagent)"),
    ("venue:ecai autonomous agent", "dblp_ecai", "ECAI (autonomous agent)"),
    ("venue:ecai agent coordination", "dblp_ecai", "ECAI (agent coordination)"),
    # NeurIPS
    ("venue:neurips multi-agent", "dblp_neurips", "NeurIPS (multi-agent)"),
    ("venue:nips multi-agent", "dblp_neurips", "NeurIPS/NIPS (multi-agent)"),
    ("venue:neurips multiagent", "dblp_neurips", "NeurIPS (multiagent)"),
    # ICML
    ("venue:icml multi-agent", "dblp_icml", "ICML (multi-agent)"),
    ("venue:icml multiagent", "dblp_icml", "ICML (multiagent)"),
    # ICLR
    ("venue:iclr multi-agent", "dblp_iclr", "ICLR (multi-agent)"),
    ("venue:iclr multiagent", "dblp_iclr", "ICLR (multiagent)"),
]

# Journals
JOURNAL_QUERIES = [
    # JAAMAS (the premier MAS journal)
    ("Autonomous Agents and Multi-Agent Systems", "dblp_jaamas", "JAAMAS"),
    # AIJ with MAS filter
    ("Artificial Intelligence multi-agent", "dblp_aij", "AIJ (multi-agent)"),
    ("Artificial Intelligence multiagent", "dblp_aij", "AIJ (multiagent)"),
    ("Artificial Intelligence autonomous agent", "dblp_aij", "AIJ (autonomous agent)"),
    ("Artificial Intelligence agent coordination", "dblp_aij", "AIJ (agent coordination)"),
    # JAIR with MAS filter
    ("Journal of Artificial Intelligence Research multi-agent", "dblp_jair", "JAIR (multi-agent)"),
    ("Journal of Artificial Intelligence Research agent", "dblp_jair", "JAIR (agent)"),
]


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 80)
    print(f"DBLP Multi-Venue MAS Import {'(DRY RUN)' if dry_run else ''}")
    print("=" * 80)

    # Step 1: Build existing title index
    print("\n1. Building existing title index...")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM papers")
        existing = {}
        for pid, title in cur.fetchall():
            norm = normalize_title(title)
            existing[norm] = pid
        print(f"   Indexed {len(existing)} existing papers")

    # Step 2: Fetch from all sources
    all_new = {}  # norm_title -> paper dict (dedup across queries)
    stats = {}  # source_tag -> {fetched, new, dup}

    all_queries = (
        [(q, tag, desc, 500) for q, tag, desc in MAS_VENUES] +
        [(q, tag, desc, 500) for q, tag, desc in GENERAL_VENUE_QUERIES] +
        [(q, tag, desc, 500) for q, tag, desc in JOURNAL_QUERIES]
    )

    print(f"\n2. Fetching from DBLP ({len(all_queries)} queries)...\n")

    for query, source_tag, desc, max_r in all_queries:
        time.sleep(1.0)
        papers = fetch_dblp_query(query, max_results=max_r)

        new_count = 0
        dup_count = 0
        self_dup = 0

        for p in papers:
            norm = normalize_title(p["title"])
            if norm in existing:
                dup_count += 1
            elif norm in all_new:
                self_dup += 1
            else:
                new_count += 1
                p["source_tag"] = source_tag
                all_new[norm] = p

        if source_tag not in stats:
            stats[source_tag] = {"fetched": 0, "new": 0, "dup": 0}
        stats[source_tag]["fetched"] += len(papers)
        stats[source_tag]["new"] += new_count
        stats[source_tag]["dup"] += dup_count

        print(f"   {desc:45s} | {len(papers):4d} fetched | "
              f"{new_count:4d} new | {dup_count:4d} existing | {self_dup:3d} cross-dup")

    print(f"\n   Total new papers to import: {len(all_new)}")

    # Summary by source
    print(f"\n   --- By Source ---")
    for tag in sorted(stats.keys()):
        s = stats[tag]
        print(f"   {tag:20s}: {s['fetched']:5d} fetched, {s['new']:5d} new, {s['dup']:5d} already in corpus")

    if dry_run:
        print("\n   [DRY RUN] No papers inserted.")
        print("\n   Sample of papers to import:")
        for i, (norm, p) in enumerate(all_new.items()):
            if i >= 25:
                break
            print(f"     {p['year']} | {p['source_tag']:15s} | {p['title'][:55]}")
        return

    # Step 3: Insert
    print("\n3. Inserting into database...")
    inserted = 0
    skipped = 0

    with get_conn() as conn:
        cur = conn.cursor()
        for norm, p in all_new.items():
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
                    p.get("venue", ""),
                    p.get("doi"),
                    json.dumps(p.get("authors", [])),
                    p["source_tag"],
                    p.get("source_url"),
                    p["year"] < 2010,
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

    # Final corpus count
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM papers")
        total = cur.fetchone()[0]
        cur.execute("SELECT source, COUNT(*) FROM papers WHERE source LIKE 'dblp_%' GROUP BY source ORDER BY COUNT(*) DESC")
        dblp_sources = cur.fetchall()
        print(f"\n4. Corpus now: {total} papers")
        print(f"   DBLP sources:")
        for src, cnt in dblp_sources:
            print(f"     {src:20s}: {cnt:5d}")


if __name__ == "__main__":
    main()
