"""Semantic Scholar API wrapper with interval-based rate limiting.

Free tier: 90 requests per 5 minutes (conservative, actual limit is 100).
With API key: 5000 requests per 5 minutes.

Uses minimum-interval pacing (not burst-then-wait) to avoid 429 errors.
"""

import json
import os
import threading
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Rate limiting: interval-based pacing (thread-safe)
_rate_lock = threading.Lock()
_last_request_time = 0.0
_FREE_RATE = 90   # requests per 5 minutes (conservative)
_KEY_RATE = 4500   # requests per 5 minutes (conservative)
_WINDOW = 300.0    # 5 minutes in seconds


def _get_api_key() -> Optional[str]:
    return os.environ.get("S2_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")


def _rate_limit():
    """Pace requests with minimum interval. Thread-safe, no bursting."""
    global _last_request_time
    api_key = _get_api_key()
    rate = _KEY_RATE if api_key else _FREE_RATE
    min_interval = _WINDOW / rate  # 3.33s for free tier, 0.067s with key

    with _rate_lock:
        now = time.time()
        earliest = _last_request_time + min_interval
        if now >= earliest:
            _last_request_time = now
            return
        else:
            # Reserve our slot
            _last_request_time = earliest
            wait = earliest - now

    # Sleep outside the lock so other threads can reserve their slots
    time.sleep(wait)


# Circuit breaker: stop retrying 429s after N consecutive failures
_consecutive_429s = 0
_429_lock = threading.Lock()
_MAX_CONSECUTIVE_429s = 3  # after 3 in a row, skip immediately for 60s
_429_cooldown_until = 0.0


def _request(url: str, max_retries: int = 2) -> dict:
    """Make a rate-limited request with retry logic and 429 circuit breaker."""
    global _consecutive_429s, _429_cooldown_until
    api_key = _get_api_key()
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    # Circuit breaker: if too many 429s, skip immediately
    with _429_lock:
        if _consecutive_429s >= _MAX_CONSECUTIVE_429s and time.time() < _429_cooldown_until:
            return {}

    for attempt in range(max_retries):
        _rate_limit()
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                with _429_lock:
                    _consecutive_429s = 0  # reset on success
                return data
        except HTTPError as e:
            if e.code == 429:
                with _429_lock:
                    _consecutive_429s += 1
                    if _consecutive_429s >= _MAX_CONSECUTIVE_429s:
                        _429_cooldown_until = time.time() + 60
                        print(f"[S2] Circuit breaker: {_consecutive_429s} consecutive 429s. "
                              f"Skipping S2 calls for 60s.", flush=True)
                        return {}
                wait = min(2 ** attempt * 3, 10)  # shorter backoff: 3s, 6s max
                print(f"[S2] 429. Retry in {wait}s ({attempt + 1}/{max_retries})", flush=True)
                time.sleep(wait)
                continue
            elif e.code == 404:
                return {}
            else:
                print(f"[S2] HTTP {e.code}: {e.reason}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        except (URLError, TimeoutError) as e:
            print(f"[S2] Network error: {e} ({attempt + 1}/{max_retries})", flush=True)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

    return {}


def search_paper(query: str, limit: int = 5, fields: Optional[str] = None) -> list[dict]:
    """Search for papers by title/query string.

    Returns list of paper dicts with requested fields.
    """
    if fields is None:
        fields = "paperId,title,year,citationCount,externalIds"
    params = urlencode({"query": query, "limit": limit, "fields": fields})
    url = f"{BASE_URL}/paper/search?{params}"
    data = _request(url)
    return data.get("data", [])


def get_paper(paper_id: str, fields: Optional[str] = None) -> dict:
    """Look up a paper by Semantic Scholar ID, DOI, or ArXiv ID.

    paper_id formats:
      - S2 ID: "649def34f8be52c8b66281af98ae884c09aef38b"
      - DOI: "DOI:10.1145/174666.174668"
      - ArXiv: "ARXIV:2503.13657"
      - Corpus ID: "CorpusID:123456"
    """
    if fields is None:
        fields = "paperId,title,year,citationCount,referenceCount,externalIds,abstract"
    params = urlencode({"fields": fields})
    url = f"{BASE_URL}/paper/{quote(paper_id, safe=':')}?{params}"
    return _request(url)


def get_references(paper_id: str, fields: Optional[str] = None, limit: int = 1000) -> list[dict]:
    """Fetch the reference list (papers this paper cites).

    Returns list of {citedPaper: {paperId, title, year, citationCount}}.
    """
    if fields is None:
        fields = "paperId,title,year,citationCount"
    params = urlencode({"fields": fields, "limit": limit})
    url = f"{BASE_URL}/paper/{quote(paper_id, safe=':')}/references?{params}"
    data = _request(url)
    if not data:
        return []
    return data.get("data", []) or []


def get_citations(paper_id: str, fields: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Fetch papers that cite this paper.

    Returns list of {citingPaper: {paperId, title, year}}.
    """
    if fields is None:
        fields = "paperId,title,year"
    params = urlencode({"fields": fields, "limit": limit})
    url = f"{BASE_URL}/paper/{quote(paper_id, safe=':')}/citations?{params}"
    data = _request(url)
    if not data:
        return []
    return data.get("data", []) or []


def get_citations_by_year(paper_id: str) -> dict[int, int]:
    """Fetch all citations and return a year -> count mapping.

    Useful for computing Modernity Score.
    """
    citations = get_citations(paper_id, fields="year", limit=50)
    year_counts: dict[int, int] = {}
    for entry in citations:
        citing = entry.get("citingPaper", {})
        year = citing.get("year")
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
    return year_counts


def modernity_score(year_counts: dict[int, int]) -> tuple[float, int, int]:
    """Compute Modernity Score from year counts.

    Returns (score, modern_count, total_count).
    Modern = 2023-2026.
    """
    total = sum(year_counts.values())
    modern = sum(count for year, count in year_counts.items() if 2023 <= year <= 2026)
    if total == 0:
        return 0.0, 0, 0
    return modern / total, modern, total


if __name__ == "__main__":
    # Quick smoke test
    print("=== Semantic Scholar API Smoke Test ===\n")

    print("1. Search for 'Contract Net Protocol'...")
    results = search_paper("Contract Net Protocol Smith 1980", limit=3)
    for r in results:
        print(f"   {r.get('year', '?')} | {r.get('citationCount', '?')} cites | {r.get('title', '?')}")
        print(f"   ID: {r.get('paperId', '?')}")

    if results:
        pid = results[0]["paperId"]
        print(f"\n2. Get paper details for {pid[:12]}...")
        paper = get_paper(pid)
        print(f"   Title: {paper.get('title')}")
        print(f"   Year: {paper.get('year')}")
        print(f"   Citations: {paper.get('citationCount')}")

        print(f"\n3. Get references (first 5)...")
        refs = get_references(pid, limit=5)
        for ref in refs[:5]:
            cited = ref.get("citedPaper", {})
            print(f"   {cited.get('year', '?')} | {cited.get('title', '?')}")

        print(f"\n4. Get citation year distribution...")
        yc = get_citations_by_year(pid)
        score, modern, total = modernity_score(yc)
        print(f"   Total citations: {total}")
        print(f"   Modern (2023-2026): {modern}")
        print(f"   Modernity Score: {score:.4f}")

    print("\n=== Done ===")
