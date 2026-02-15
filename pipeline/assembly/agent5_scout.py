#!/usr/bin/env python3
"""Agent 5: Reproduction Scout — Fifth station on the assembly line.

Polls papers with pipeline_status='enriched' (output of Agent 4),
searches for implementations on Papers with Code and GitHub.

Now uses concurrent.futures to run multiple scouts in parallel.
Each thread grabs its own paper via FOR UPDATE SKIP LOCKED (no overlap).

Pipeline: ... -> Agent 4 (enriched) -> Agent 5 (scouted)

Updates:
  - has_code: whether an implementation exists
  - repo_url: GitHub/GitLab URL
  - reproduction_feasibility: 1-5 scale
  - experiment_notes: what's available and what's needed
  - pipeline_status -> 'scouted'

Usage:
    python3 -m pipeline.assembly.agent5_scout [--concurrent 6] [--once]
"""

import argparse
import concurrent.futures
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, update_paper, count_by_status

import psycopg2.extras

PWC_BASE = "https://paperswithcode.com/api/v1"
GITHUB_SEARCH = "https://api.github.com/search/repositories"

# Blacklisted repos — known garbage that pollute results
BLACKLISTED_REPOS = {
    "jettbrains/-L-", "Aryia-Behroziuan/References", "Aryia-Behroziuan/Other-sources",
    "rprokap/pset-9", "danderfer/Comp_Sci_Sem_2", "Rastaman4e/-1",
    "ruvnet/claude-flow", "zero-equals-false/awesome-programming-books",
    "chrisneagu/FTC-Skystone", "Sfedfcv/redesigned-pancake",
    "Exampl33/Sovereign-Wealth", "Mdshobu/Liberty-House",
    "Anaswarapyarilal/Mathematics", "SheikhRabiul",
}

# Repo name patterns that indicate garbage (homework, bibliographies, etc.)
GARBAGE_NAME_PATTERNS = {
    "pset", "homework", "assignment", "coursework", "references",
    "bibliography", "whitepaper", "awesome-", "redesigned-",
}

# Minimum star count for GitHub search results (PwC results are pre-vetted)
MIN_GITHUB_STARS = 3


def _is_blacklisted(url: str) -> bool:
    """Check if a repo URL matches any blacklisted pattern."""
    for bl in BLACKLISTED_REPOS:
        if bl in url:
            return True
    # Check repo name patterns
    repo_name = url.rstrip("/").split("/")[-1].lower() if "/" in url else ""
    owner_name = url.rstrip("/").split("/")[-2].lower() if url.count("/") >= 4 else ""
    for pattern in GARBAGE_NAME_PATTERNS:
        if pattern in repo_name or pattern in owner_name:
            return True
    return False


def _title_keywords(title: str) -> set[str]:
    """Extract meaningful keywords from a paper title for relevance matching."""
    stop = {
        "a", "an", "the", "of", "in", "for", "and", "or", "with", "on", "to",
        "from", "by", "is", "are", "that", "this", "its", "can", "we", "our",
        "using", "based", "towards", "via", "how", "what", "when", "where",
        "new", "novel", "approach", "method", "system", "systems", "framework",
    }
    words = set()
    for w in title.lower().split():
        cleaned = w.strip(".:,;!?()[]\"'")
        if cleaned and cleaned not in stop and len(cleaned) > 2:
            words.add(cleaned)
    return words


def _repo_relevance(repo: dict, title_keywords: set[str]) -> float:
    """Score 0-1 how relevant a repo is to a paper based on name/description overlap."""
    text = (repo.get("url", "").split("/")[-1].replace("-", " ").replace("_", " ") + " " +
            (repo.get("description") or "")).lower()
    repo_words = set(text.split())
    if not title_keywords:
        return 0.0
    overlap = title_keywords & repo_words
    return len(overlap) / len(title_keywords)


def _http_get(url: str, headers: dict | None = None, timeout: int = 15) -> dict | None:
    """Simple HTTP GET returning parsed JSON or None."""
    hdrs = {"Accept": "application/json", "User-Agent": "SutraResearch/1.0"}
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token and "github.com" in url:
        hdrs["Authorization"] = f"token {gh_token}"
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None


def search_papers_with_code(title: str, arxiv_id: str | None = None) -> list[dict]:
    """Search Papers with Code for implementations.

    PwC results via ArXiv ID are high-confidence (direct paper match).
    PwC title search results are filtered for blacklist but otherwise trusted.
    """
    repos = []

    # Strategy 1: ArXiv ID lookup (most reliable — direct paper match)
    if arxiv_id:
        clean_id = arxiv_id.split("v")[0]
        data = _http_get(f"{PWC_BASE}/papers/?arxiv_id={clean_id}")
        if data and data.get("results"):
            paper = data["results"][0]
            paper_id = paper.get("id")
            if paper_id:
                repo_data = _http_get(f"{PWC_BASE}/papers/{paper_id}/repositories/")
                if repo_data and repo_data.get("results"):
                    for r in repo_data["results"]:
                        url = r.get("url", "")
                        if not _is_blacklisted(url):
                            repos.append({
                                "url": url,
                                "stars": r.get("stars", 0),
                                "framework": r.get("framework", ""),
                                "source": "papers_with_code_arxiv",
                                "confidence": "high",
                            })

    # Strategy 2: Title search (lower confidence — verify title match)
    if not repos:
        params = urlencode({"q": title[:100]})
        data = _http_get(f"{PWC_BASE}/papers/?{params}")
        if data and data.get("results"):
            title_lower = title.lower().strip()
            for paper in data["results"][:3]:
                # Only accept if PwC paper title closely matches our paper title
                pwc_title = (paper.get("title") or "").lower().strip()
                if not pwc_title:
                    continue
                # Require exact or near-exact title match
                if pwc_title != title_lower and title_lower not in pwc_title and pwc_title not in title_lower:
                    continue
                paper_id = paper.get("id")
                if paper_id:
                    repo_data = _http_get(f"{PWC_BASE}/papers/{paper_id}/repositories/")
                    if repo_data and repo_data.get("results"):
                        for r in repo_data["results"]:
                            url = r.get("url", "")
                            if not _is_blacklisted(url):
                                repos.append({
                                    "url": url,
                                    "stars": r.get("stars", 0),
                                    "framework": r.get("framework", ""),
                                    "source": "papers_with_code_title",
                                    "confidence": "medium",
                                })

    return repos


def search_github(title: str, max_results: int = 5) -> list[dict]:
    """Search GitHub for repositories matching the paper title.

    Results are filtered for:
    - Blacklisted repos
    - Minimum star count
    - Name/description relevance to paper title
    """
    # Extract key terms from title (skip common words)
    stop = {"a", "an", "the", "of", "in", "for", "and", "or", "with", "on", "to", "from", "by"}
    terms = [w for w in title.split() if w.lower() not in stop][:6]
    query = " ".join(terms)

    params = urlencode({"q": query, "sort": "stars", "per_page": max_results})
    data = _http_get(f"{GITHUB_SEARCH}?{params}")

    title_kw = _title_keywords(title)
    repos = []
    if data and data.get("items"):
        for item in data["items"][:max_results]:
            url = item.get("html_url", "")
            stars = item.get("stargazers_count", 0)
            description = (item.get("description") or "")[:200]
            language = item.get("language", "")

            # Filter: blacklist
            if _is_blacklisted(url):
                continue

            # Filter: minimum stars
            if stars < MIN_GITHUB_STARS:
                continue

            repo = {
                "url": url,
                "stars": stars,
                "description": description,
                "language": language,
                "source": "github_search",
            }

            # Filter: relevance — repo name/description must overlap with paper title
            relevance = _repo_relevance(repo, title_kw)
            if relevance < 0.15:
                continue

            repo["relevance"] = round(relevance, 2)
            repo["confidence"] = "high" if relevance > 0.4 else "medium" if relevance > 0.25 else "low"
            repos.append(repo)

    return repos


def assess_feasibility(paper: dict, repos: list[dict]) -> tuple[int, str]:
    """Assess reproduction feasibility (1-5) and generate notes."""
    has_arxiv = bool(paper.get("arxiv_id"))
    has_analysis = bool(paper.get("analysis"))
    analysis = paper.get("analysis") or {}
    pattern = analysis.get("coordination_pattern", "none")

    if repos:
        best = max(repos, key=lambda r: r.get("stars", 0))
        stars = best.get("stars", 0)
        if stars > 100:
            feasibility = 5
            notes = f"Official/popular implementation found: {best['url']} ({stars} stars)"
        elif stars > 10:
            feasibility = 4
            notes = f"Implementation found: {best['url']} ({stars} stars)"
        else:
            feasibility = 3
            notes = f"Low-activity implementation: {best['url']} ({stars} stars). May need adaptation."
    elif has_arxiv and pattern != "none":
        feasibility = 2
        notes = f"No code found. Pattern '{pattern}' is reproducible from paper description. ArXiv source available."
    elif has_arxiv:
        feasibility = 2
        notes = "No code found. ArXiv source available for methodology extraction."
    else:
        feasibility = 1
        notes = "No code, no ArXiv source. Would require significant interpretation."

    return feasibility, notes


def _poll_one() -> dict | None:
    """Grab one enriched paper for scouting. Thread-safe via SKIP LOCKED."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, title, arxiv_id, analysis
                   FROM papers
                   WHERE pipeline_status = 'enriched'
                   ORDER BY citation_count DESC
                   LIMIT 1
                   FOR UPDATE SKIP LOCKED""",
                (),
            )
            row = cur.fetchone()
            if not row:
                return None
            paper = dict(row)

            cur.execute(
                "UPDATE papers SET pipeline_status = 'scouting' WHERE id = %s",
                (paper["id"],),
            )
    return paper


def _pick_best_repo(repos: list[dict]) -> dict | None:
    """Pick the best repo from candidates, preferring PwC and high-confidence matches."""
    if not repos:
        return None

    # Confidence priority: high > medium > low
    conf_score = {"high": 3, "medium": 2, "low": 1}

    # Source priority: PwC arxiv (direct match) > PwC title > GitHub
    source_score = {"papers_with_code_arxiv": 3, "papers_with_code_title": 2, "github_search": 1}

    def score(r):
        return (
            conf_score.get(r.get("confidence", "low"), 0),
            source_score.get(r.get("source", ""), 0),
            r.get("stars", 0),
        )

    return max(repos, key=score)


def _run_one() -> int:
    """Poll + scout one paper. Called from thread pool. Returns 1 if processed, 0 if idle."""
    paper = _poll_one()
    if not paper:
        return 0

    # Search for implementations — PwC first (higher quality), then GitHub fallback
    repos = search_papers_with_code(paper["title"], paper.get("arxiv_id"))
    time.sleep(1)

    if not repos:
        repos = search_github(paper["title"])
        time.sleep(2)  # GitHub rate limit is strict

    best = _pick_best_repo(repos)
    has_code = best is not None
    repo_url = best["url"] if best else None
    feasibility, notes = assess_feasibility(paper, repos)

    update_paper(
        paper["id"],
        agent_name="agent5_scout",
        new_status="scouted",
        has_code=has_code,
        repo_url=repo_url,
        reproduction_feasibility=feasibility,
        experiment_notes=notes,
    )
    return 1


def main():
    parser = argparse.ArgumentParser(description="Agent 5: Reproduction Scout (concurrent)")
    parser.add_argument("--concurrent", type=int, default=6, help="Max concurrent scout threads (default: 6)")
    parser.add_argument("--poll-interval", type=int, default=15, help="Seconds between polls when idle")
    parser.add_argument("--once", action="store_true", help="Process one round and exit")
    parser.add_argument("--max-papers", type=int, default=0, help="Max papers (0=unlimited)")
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("  AGENT 5: REPRODUCTION SCOUT (concurrent)", flush=True)
    print("  Assembly Line — Station 5", flush=True)
    print("=" * 60, flush=True)
    print(f"  Concurrent:  {args.concurrent} parallel threads", flush=True)
    print(f"  Sources:     Papers with Code + GitHub", flush=True)
    print(f"  Status:      {count_by_status()}", flush=True)

    total_processed = 0
    rounds = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrent) as executor:
        while True:
            # Submit N concurrent scout tasks
            futures = []
            for _ in range(args.concurrent):
                futures.append(executor.submit(_run_one))

            # Collect results
            round_total = 0
            for f in concurrent.futures.as_completed(futures):
                try:
                    n = f.result()
                    round_total += n
                except Exception as e:
                    print(f"  [Scout] Thread error: {e}", flush=True)

            if round_total > 0:
                total_processed += round_total
                rounds += 1
                print(f"  Round {rounds}: scouted {round_total} papers "
                      f"(total: {total_processed}, "
                      f"queue: ~{count_by_status().get('enriched', '?')})",
                      flush=True)

                if args.once:
                    break
                if args.max_papers and total_processed >= args.max_papers:
                    break
            else:
                if args.once:
                    print("  No papers to scout.", flush=True)
                    break
                print(f"  Waiting for enriched papers... (polling every {args.poll_interval}s)", flush=True)
                time.sleep(args.poll_interval)

    print(f"\n  Scout complete. Processed: {total_processed} papers in {rounds} rounds.", flush=True)


if __name__ == "__main__":
    main()
