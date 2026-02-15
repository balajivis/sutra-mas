"""Crossref API wrapper using the Polite pool.

No auth required. Include mailto header for priority access.
"""

import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.crossref.org"
MAILTO = "research@getkapi.com"


def _request(url: str, max_retries: int = 3) -> dict:
    """Make a request with the Polite pool mailto header."""
    headers = {
        "Accept": "application/json",
        "User-Agent": f"Sutra-Research/1.0 (mailto:{MAILTO})",
    }

    for attempt in range(max_retries):
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt * 2
                print(f"[Crossref] 429 rate limited. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            elif e.code == 404:
                return {}
            else:
                print(f"[Crossref] HTTP {e.code}: {e.reason}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        except (URLError, TimeoutError) as e:
            print(f"[Crossref] Network error: {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    return {}


def search_by_title(title: str, limit: int = 5) -> list[dict]:
    """Search Crossref works by title query.

    Returns list of work items with title, DOI, year, etc.
    """
    params = urlencode({
        "query.bibliographic": title,
        "rows": limit,
        "mailto": MAILTO,
    })
    url = f"{BASE_URL}/works?{params}"
    data = _request(url)
    items = data.get("message", {}).get("items", [])
    return items


def get_by_doi(doi: str) -> dict:
    """Look up a work by DOI.

    Returns the Crossref work item.
    """
    url = f"{BASE_URL}/works/{quote(doi, safe='')}"
    data = _request(url)
    return data.get("message", {})


def extract_metadata(item: dict) -> dict:
    """Extract key metadata from a Crossref work item."""
    title_list = item.get("title", [])
    title = title_list[0] if title_list else ""

    # Year extraction: prefer published-print, then published-online, then created
    year = None
    for date_field in ["published-print", "published-online", "created"]:
        date_parts = item.get(date_field, {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
            break

    authors = []
    for author in item.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        authors.append(f"{given} {family}".strip())

    return {
        "doi": item.get("DOI", ""),
        "title": title,
        "year": year,
        "authors": authors,
        "type": item.get("type", ""),
        "container_title": (item.get("container-title", [None]) or [None])[0],
        "citation_count": item.get("is-referenced-by-count", 0),
    }


if __name__ == "__main__":
    print("=== Crossref API Smoke Test ===\n")

    print("1. Search for 'Contract Net Protocol'...")
    results = search_by_title("Contract Net Protocol Smith", limit=3)
    for item in results:
        meta = extract_metadata(item)
        print(f"   {meta['year']} | {meta['citation_count']} cites | {meta['title'][:80]}")
        print(f"   DOI: {meta['doi']}")

    doi = "10.1145/174666.174668"
    print(f"\n2. Look up DOI: {doi}...")
    item = get_by_doi(doi)
    if item:
        meta = extract_metadata(item)
        print(f"   Title: {meta['title']}")
        print(f"   Year: {meta['year']}")
        print(f"   Authors: {', '.join(meta['authors'][:3])}")

    print("\n=== Done ===")
