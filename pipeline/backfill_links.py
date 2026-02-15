#!/usr/bin/env python3
"""Backfill missing arxiv_id and doi for papers via Semantic Scholar + Crossref.

Finds papers without links, queries APIs by title, and updates the DB.
Prioritizes active papers by citation count.

Usage:
    python3 -m pipeline.backfill_links              # Backfill all missing
    python3 -m pipeline.backfill_links --limit 50   # First 50 only
    python3 -m pipeline.backfill_links --dry-run     # Preview without writing
"""

import argparse
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.assembly.db import get_conn

# Semantic Scholar: 100 requests per 5 min (free tier), ~1 per 3s is safe
S2_DELAY = 3.2
# Crossref: polite pool with mailto header
CROSSREF_DELAY = 1.0

MAILTO = "sutra-research@getkapi.com"


def _s2_by_id(s2_id: str) -> dict | None:
    """Lookup a paper directly by Semantic Scholar ID."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{s2_id}?fields=externalIds"
    req = urllib.request.Request(url)
    s2_key = os.environ.get("S2_API_KEY", "")
    if s2_key:
        req.add_header("x-api-key", s2_key)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data
    except Exception:
        return None


def _s2_search(title: str) -> dict | None:
    """Search Semantic Scholar by title. Returns best match or None."""
    q = urllib.parse.quote(title[:200])
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit=3&fields=paperId,title,externalIds,citationCount"
    req = urllib.request.Request(url)
    s2_key = os.environ.get("S2_API_KEY", "")
    if s2_key:
        req.add_header("x-api-key", s2_key)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    papers = data.get("data", [])
    if not papers:
        return None

    # Pick best match by title similarity
    target = _normalize(title)
    best = None
    best_sim = 0.0
    for p in papers:
        sim = _title_similarity(target, _normalize(p.get("title", "")))
        if sim > best_sim:
            best_sim = sim
            best = p

    if best_sim < 0.7:
        return None  # Too different, skip

    return best


def _crossref_search(title: str) -> dict | None:
    """Search Crossref by title. Returns best match or None."""
    q = urllib.parse.quote(title[:200])
    url = f"https://api.crossref.org/works?query.title={q}&rows=3&select=DOI,title"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", f"Sutra/1.0 (mailto:{MAILTO})")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    items = data.get("message", {}).get("items", [])
    if not items:
        return None

    target = _normalize(title)
    for item in items:
        item_title = " ".join(item.get("title", []))
        sim = _title_similarity(target, _normalize(item_title))
        if sim >= 0.75:
            return {"doi": item.get("DOI")}

    return None


def _normalize(s: str) -> str:
    """Normalize title for comparison."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _title_similarity(a: str, b: str) -> float:
    """Word-overlap Jaccard similarity."""
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def fetch_missing_papers(limit: int | None = None) -> list[dict]:
    """Fetch papers without arxiv_id and doi, ordered by importance."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            sql = """
                SELECT id, title, year, citation_count, pipeline_status,
                       semantic_scholar_id
                FROM papers
                WHERE (arxiv_id IS NULL OR arxiv_id = '')
                  AND (doi IS NULL OR doi = '')
                  AND pipeline_status NOT IN ('archived')
                ORDER BY
                    CASE WHEN pipeline_status IN ('seed', 'enriched', 'analyzed', 'scouted',
                         'planning_reproduction', 'reproduction_planned') THEN 0 ELSE 1 END,
                    citation_count DESC NULLS LAST
            """
            if limit:
                sql += f" LIMIT {limit}"
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def update_link(paper_id: int, arxiv_id: str | None, doi: str | None):
    """Update a paper's arxiv_id and/or doi."""
    parts = []
    values = []
    if arxiv_id:
        parts.append("arxiv_id = %s")
        values.append(arxiv_id)
    if doi:
        parts.append("doi = %s")
        values.append(doi)
    if not parts:
        return
    values.append(paper_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(f"UPDATE papers SET {', '.join(parts)} WHERE id = %s", values)
                conn.commit()
            except Exception:
                conn.rollback()
                # Retry with just arxiv_id if doi caused a unique violation
                if arxiv_id:
                    try:
                        cur.execute("UPDATE papers SET arxiv_id = %s WHERE id = %s", (arxiv_id, paper_id))
                        conn.commit()
                    except Exception:
                        conn.rollback()


def main():
    parser = argparse.ArgumentParser(description="Backfill missing paper links")
    parser.add_argument("--limit", type=int, help="Max papers to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    args = parser.parse_args()

    papers = fetch_missing_papers(args.limit)
    print(f"Papers missing links: {len(papers)}", flush=True)
    if not papers:
        return

    found_arxiv = 0
    found_doi = 0
    not_found = 0

    for i, p in enumerate(papers):
        title = p["title"]
        pid = p["id"]
        cites = p.get("citation_count") or 0
        status = p.get("pipeline_status", "?")
        s2_id = p.get("semantic_scholar_id")

        # Try direct S2 lookup by ID first (faster, more reliable)
        arxiv_id = None
        doi = None

        if s2_id:
            s2 = _s2_by_id(s2_id)
            if s2:
                ext = s2.get("externalIds") or {}
                arxiv_id = ext.get("ArXiv")
                doi = ext.get("DOI")

        # Fallback: search S2 by title
        if not arxiv_id and not doi:
            time.sleep(S2_DELAY)
            s2 = _s2_search(title)
            if s2:
                ext = s2.get("externalIds") or {}
                arxiv_id = ext.get("ArXiv")
                doi = ext.get("DOI")

        # Last resort: try Crossref for DOI
        if not doi and not arxiv_id:
            time.sleep(CROSSREF_DELAY)
            cr = _crossref_search(title)
            if cr:
                doi = cr.get("doi")

        # Report
        link_str = ""
        if arxiv_id:
            link_str += f" arxiv={arxiv_id}"
            found_arxiv += 1
        if doi:
            link_str += f" doi={doi}"
            found_doi += 1
        if not arxiv_id and not doi:
            not_found += 1
            link_str = " NOT FOUND"

        tag = "DRY" if args.dry_run else "SET"
        print(f"  [{i+1}/{len(papers)}] id={pid:>5} {cites:>5} cites [{status:<10}] {tag}{link_str}  {title[:55]}", flush=True)

        # Write
        if not args.dry_run and (arxiv_id or doi):
            update_link(pid, arxiv_id, doi)

        # Rate limit for S2
        time.sleep(S2_DELAY)

    print(f"\nDone: {found_arxiv} arxiv, {found_doi} doi, {not_found} not found out of {len(papers)}")


if __name__ == "__main__":
    main()
