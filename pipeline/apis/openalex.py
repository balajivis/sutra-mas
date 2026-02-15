"""OpenAlex API wrapper.

100K credits/day with free API key (as of Feb 2026).
API key via OPENALEX_API_KEY env var; falls back to mailto polite pool.
"""

import json
import os
import time
from typing import Optional
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.openalex.org"
MAILTO = "research@getkapi.com"
API_KEY = os.environ.get("OPENALEX_API_KEY", "")


def _request(url: str, max_retries: int = 3) -> dict:
    """Make a request with API key (preferred) or mailto fallback."""
    separator = "&" if "?" in url else "?"
    if API_KEY:
        url = f"{url}{separator}api_key={API_KEY}"
    else:
        url = f"{url}{separator}mailto={MAILTO}"

    headers = {"Accept": "application/json"}

    for attempt in range(max_retries):
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt * 2
                print(f"[OpenAlex] 429 rate limited. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            elif e.code == 404:
                return {}
            else:
                print(f"[OpenAlex] HTTP {e.code}: {e.reason}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        except (URLError, TimeoutError, IncompleteRead) as e:
            print(f"[OpenAlex] Network error: {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    return {}


def search_works(query: str, limit: int = 5) -> list[dict]:
    """Search for works by query string."""
    params = urlencode({"search": query, "per_page": limit})
    url = f"{BASE_URL}/works?{params}"
    data = _request(url)
    return data.get("results", [])


def get_work_by_doi(doi: str) -> dict:
    """Look up a work by DOI."""
    url = f"{BASE_URL}/works/doi:{quote(doi, safe='')}"
    return _request(url)


def get_work_by_openalex_id(oa_id: str) -> dict:
    """Look up a work by OpenAlex ID (e.g., W2100837269)."""
    if oa_id.startswith("https://openalex.org/"):
        oa_id = oa_id.split("/")[-1]
    url = f"{BASE_URL}/works/{oa_id}"
    return _request(url)


def get_work_by_s2_id(s2_id: str) -> dict:
    """Try to find an OpenAlex work by Semantic Scholar paper ID.

    OpenAlex doesn't index by S2 ID directly, so we search by title
    from the S2 metadata.
    """
    # This requires a title search fallback — caller should use DOI when possible
    return {}


def get_references(oa_id: str) -> list[str]:
    """Get the referenced_works list for a work.

    Returns list of OpenAlex work IDs.
    """
    work = get_work_by_openalex_id(oa_id)
    return work.get("referenced_works", [])


def get_references_detailed(oa_ids: list[str], batch_size: int = 50) -> list[dict]:
    """Fetch metadata for a list of OpenAlex work IDs.

    Uses the filter API to batch-fetch up to 50 works at a time.
    Returns list of work dicts with title, year, cited_by_count, ids.
    """
    results = []
    for i in range(0, len(oa_ids), batch_size):
        batch = oa_ids[i:i + batch_size]
        # Extract just the ID part (W12345)
        ids = [oid.split("/")[-1] if "/" in oid else oid for oid in batch]
        filter_str = "|".join(ids)
        params = urlencode({
            "filter": f"openalex_id:{filter_str}",
            "per_page": batch_size,
            "select": "id,title,publication_year,cited_by_count,ids",
        })
        url = f"{BASE_URL}/works?{params}"
        data = _request(url)
        results.extend(data.get("results", []))
        if i + batch_size < len(oa_ids):
            time.sleep(0.2)

    return results


def resolve_s2_to_openalex(s2_id: str, doi: Optional[str] = None, title: Optional[str] = None, year: Optional[int] = None) -> Optional[str]:
    """Try to find the OpenAlex ID for a paper given S2 metadata.

    Strategy: DOI lookup > title search with year filter.
    Returns OpenAlex work ID or None.
    """
    # 1. Try DOI
    if doi:
        work = get_work_by_doi(doi)
        if work and work.get("id"):
            return work["id"]

    # 2. Title search
    if title:
        results = search_works(title, limit=5)
        for r in results:
            if year and r.get("publication_year") == year:
                return r["id"]
        # No year match — return highest cited
        if results:
            best = max(results, key=lambda r: r.get("cited_by_count", 0))
            return best["id"]

    return None


def get_work_with_counts(oa_id: str) -> dict:
    """Fetch a work including counts_by_year for citation time-series.

    Returns the full work object with counts_by_year field.
    counts_by_year gives per-year citation counts for the last ~10 years.
    """
    if oa_id.startswith("https://openalex.org/"):
        oa_id = oa_id.split("/")[-1]
    params = urlencode({
        "select": "id,title,publication_year,cited_by_count,counts_by_year,ids",
    })
    url = f"{BASE_URL}/works/{oa_id}?{params}"
    return _request(url)


def count_citing_works(oa_id: str, year_from: Optional[int] = None, year_to: Optional[int] = None) -> int:
    """Count works that cite a given work, optionally filtered by year range.

    Uses the 'cites' filter combined with publication_year to get an exact count.
    More accurate than counts_by_year for specific ranges.
    """
    if oa_id.startswith("https://openalex.org/"):
        oa_id = oa_id.split("/")[-1]
    filters = [f"cites:{oa_id}"]
    if year_from and year_to:
        filters.append(f"publication_year:{year_from}-{year_to}")
    elif year_from:
        filters.append(f"publication_year:>{year_from - 1}")
    elif year_to:
        filters.append(f"publication_year:<{year_to + 1}")
    filter_str = ",".join(filters)
    params = urlencode({"filter": filter_str, "per_page": 1})
    url = f"{BASE_URL}/works?{params}"
    data = _request(url)
    return data.get("meta", {}).get("count", 0)


def get_works_with_counts_batch(oa_ids: list[str], batch_size: int = 50) -> list[dict]:
    """Batch-fetch works including counts_by_year.

    Returns list of work dicts with title, year, cited_by_count, counts_by_year.
    """
    results = []
    for i in range(0, len(oa_ids), batch_size):
        batch = oa_ids[i:i + batch_size]
        ids = [oid.split("/")[-1] if "/" in oid else oid for oid in batch]
        filter_str = "|".join(ids)
        params = urlencode({
            "filter": f"openalex_id:{filter_str}",
            "per_page": batch_size,
            "select": "id,title,publication_year,cited_by_count,counts_by_year,ids",
        })
        url = f"{BASE_URL}/works?{params}"
        data = _request(url)
        results.extend(data.get("results", []))
        if i + batch_size < len(oa_ids):
            time.sleep(0.2)
    return results


if __name__ == "__main__":
    print("=== OpenAlex API Smoke Test ===\n")

    print("1. Search for 'Contract Net Protocol'...")
    results = search_works("Contract Net Protocol Smith 1980", limit=3)
    for r in results:
        print(f"   {r.get('publication_year', '?')} | {r.get('cited_by_count', '?')} cites | {r.get('title', '?')[:60]}")
        print(f"   ID: {r['id']}")

    print("\n2. DOI lookup: 10.1145/174666.174668...")
    work = get_work_by_doi("10.1145/174666.174668")
    if work:
        print(f"   Title: {work.get('title', '?')[:60]}")
        refs = work.get("referenced_works", [])
        print(f"   References: {len(refs)}")

    print("\n=== Done ===")
