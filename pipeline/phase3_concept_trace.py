"""Phase 3: Concept Tracing — Anti-False-Positive Module.

For each Lost Canary candidate, determine whether the concept is:

1. **Genuinely Lost** — No modern presence under any name
2. **Known but Ignored** — Appears in surveys/reviews but not implementation papers
3. **Renamed** — The concept persists under different terminology

Uses Claude to generate modern synonyms/renamings, then searches
OpenAlex for those terms in 2023-2026 papers.

Usage:
    python3 pipeline/phase3_concept_trace.py                    # Full run
    python3 pipeline/phase3_concept_trace.py --cached           # Use cached LLM results
    python3 pipeline/phase3_concept_trace.py --all              # Include below-threshold papers
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, ".")
from pipeline.apis import openalex as oa
from pipeline.apis import llm

MODERNITY_FILE = "pipeline/data/modernity_scores.json"
TRACE_CACHE = "pipeline/data/concept_trace_cache.json"
OUTPUT_FILE = "pipeline/data/lost_canaries.json"

SYNONYM_SYSTEM_PROMPT = """You are an expert in both classical Multi-Agent Systems (MAS) research (1980-2005) and modern LLM agent systems (2023-2026).

Your task: Given a classical MAS paper, identify what modern terms and concepts correspond to its core ideas. Modern LLM agent builders often reinvent classical concepts without knowing they existed.

Return your response as a JSON object with this exact structure:
{
  "core_concept": "The key idea from this paper in 1-2 sentences",
  "modern_synonyms": [
    {"term": "modern term or phrase", "context": "how this maps to the classical concept"}
  ],
  "search_queries": ["5-8 specific search queries to find modern papers using this concept"],
  "likely_classification": "lost | known_but_ignored | renamed",
  "reasoning": "Why you think this classification, based on your knowledge of modern LLM agent research"
}

Be specific with search queries. Think about:
- Direct terminology matches (e.g., "negotiation protocol" -> "tool selection", "agent routing")
- Framework features that implement the concept (e.g., LangGraph, CrewAI, AutoGen features)
- Modern papers that describe the same mechanism differently
- Arxiv papers from 2023-2026 in cs.AI, cs.MA, cs.CL that touch on these ideas"""

CLASSIFY_SYSTEM_PROMPT = """You are a research classification expert. Given:
1. A classical MAS paper (title, year, core concept)
2. Modern synonym searches and their results (number of papers found)
3. Sample titles from found papers

Classify the concept into one of three categories:

- **genuinely_lost**: The concept has NO meaningful modern presence. Zero or near-zero relevant papers found under any synonym. The idea has been truly forgotten by the LLM agent community.

- **known_but_ignored**: The concept appears in survey papers, tutorials, or review articles but NOT in implementation/systems papers. People know it exists but don't use it.

- **renamed**: The concept is actively used in modern LLM agent systems but under different terminology. The underlying mechanism is the same even if the name changed.

Return JSON:
{
  "classification": "genuinely_lost | known_but_ignored | renamed",
  "confidence": "high | medium | low",
  "evidence_summary": "2-3 sentences explaining the classification",
  "modern_equivalent": "If renamed, what is the modern term? null if genuinely_lost",
  "key_papers_found": ["List 0-3 most relevant modern papers found that relate to this concept"]
}"""


def load_candidates(include_below_threshold: bool = False) -> list[dict]:
    """Load Lost Canary candidates from modernity scores."""
    with open(MODERNITY_FILE) as f:
        data = json.load(f)

    candidates = []
    for item in data["results"]:
        if item["classification"] == "lost_canary_candidate":
            candidates.append(item)
        elif include_below_threshold and item["classification"] == "below_citation_threshold":
            # Include papers below threshold that have very low modernity
            if item["modernity_score"] < 0.01:
                candidates.append(item)

    print(f"Loaded {len(candidates)} candidates for concept tracing")
    return candidates


def generate_synonyms(candidate: dict, cache: dict) -> dict:
    """Use Claude to generate modern synonyms for a classical concept."""
    oa_id = candidate["openAlexId"]
    if oa_id in cache:
        return cache[oa_id]

    title = candidate["title"]
    year = candidate.get("year", "?")
    branches = ", ".join(candidate.get("citing_branches", []))

    prompt = f"""Classical MAS Paper:
- Title: "{title}"
- Year: {year}
- MAS branches that cite it: {branches}
- Total citations: {candidate['total_citations']}
- Modern citations (2023-2026): {candidate['modern_citations_2023_2026']}
- Modernity Score: {candidate['modernity_score']:.4f}

Generate modern synonyms and search queries for this paper's core concepts."""

    print(f"  Generating synonyms for: {title[:50]}...")
    result = llm.chat_json(SYNONYM_SYSTEM_PROMPT, prompt)
    cache[oa_id] = result
    return result


def search_modern_papers(queries: list[str]) -> list[dict]:
    """Search OpenAlex for modern papers matching synonym queries.

    Filters to 2023-2026 papers only.
    """
    all_results = []
    seen_ids = set()

    for query in queries[:8]:  # Cap at 8 queries
        print(f"    Searching: '{query[:50]}'...")
        # Search with year filter
        from urllib.parse import urlencode
        params = urlencode({
            "search": query,
            "filter": "publication_year:2023-2026",
            "per_page": 10,
            "select": "id,title,publication_year,cited_by_count,type",
        })
        url = f"{oa.BASE_URL}/works?{params}"
        data = oa._request(url)
        results = data.get("results", [])

        for r in results:
            rid = r.get("id", "")
            if rid not in seen_ids:
                seen_ids.add(rid)
                all_results.append({
                    "id": rid,
                    "title": r.get("title", ""),
                    "year": r.get("publication_year"),
                    "cited_by_count": r.get("cited_by_count", 0),
                    "type": r.get("type", ""),
                    "matched_query": query,
                })

        time.sleep(0.3)

    return all_results


def classify_candidate(candidate: dict, synonyms: dict, search_results: list[dict]) -> dict:
    """Use Claude to classify a candidate based on search evidence."""
    title = candidate["title"]
    year = candidate.get("year", "?")
    core_concept = synonyms.get("core_concept", "Unknown")

    # Summarize search results
    total_found = len(search_results)
    # Filter to likely relevant (exclude very low-cited papers)
    relevant = [r for r in search_results if r.get("cited_by_count", 0) >= 5]
    sample_titles = [r["title"] for r in sorted(relevant, key=lambda x: -x.get("cited_by_count", 0))[:10]]

    # Separate by type
    articles = [r for r in search_results if r.get("type") == "article"]
    reviews = [r for r in search_results if r.get("type") in ("review", "book-chapter")]

    prompt = f"""Classical Paper: "{title}" ({year})
Core Concept: {core_concept}

Modern synonym searches found {total_found} papers total (2023-2026):
- Research articles: {len(articles)}
- Reviews/book chapters: {len(reviews)}
- Papers with 5+ citations: {len(relevant)}

LLM's initial guess: {synonyms.get('likely_classification', 'unknown')}
LLM's reasoning: {synonyms.get('reasoning', 'none')}

Sample titles of found papers (sorted by citations):
{chr(10).join(f'- {t}' for t in sample_titles[:10]) if sample_titles else '- (none found)'}

Modern synonyms tried: {', '.join(s['term'] for s in synonyms.get('modern_synonyms', []))}

Based on this evidence, classify this concept."""

    print(f"  Classifying: {title[:50]}...")
    result = llm.chat_json(CLASSIFY_SYSTEM_PROMPT, prompt)
    return result


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Concept Tracing")
    parser.add_argument("--cached", action="store_true", help="Use cached LLM results")
    parser.add_argument("--all", action="store_true", help="Include below-threshold papers with MS < 0.01")
    args = parser.parse_args()

    print("=" * 60)
    print("PHASE 3: CONCEPT TRACING — Anti-False-Positive Analysis")
    print("=" * 60)

    # Load candidates
    candidates = load_candidates(include_below_threshold=args.all)

    # Load LLM cache
    cache = {}
    if args.cached and os.path.exists(TRACE_CACHE):
        with open(TRACE_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached synonym results")

    results = []
    for i, candidate in enumerate(candidates):
        print(f"\n{'─' * 60}")
        print(f"[{i+1}/{len(candidates)}] {candidate['title']}")
        print(f"  {candidate.get('year', '?')} | {candidate['total_citations']} cites | MS={candidate['modernity_score']:.4f}")

        # Step 1: Generate modern synonyms
        synonyms = generate_synonyms(candidate, cache)
        print(f"  Core concept: {synonyms.get('core_concept', '?')[:60]}")
        print(f"  Synonyms: {', '.join(s['term'] for s in synonyms.get('modern_synonyms', []))}")

        # Step 2: Search for modern papers
        queries = synonyms.get("search_queries", [])
        search_results = search_modern_papers(queries)
        print(f"  Found {len(search_results)} modern papers")

        # Step 3: Classify
        classification = classify_candidate(candidate, synonyms, search_results)
        print(f"  Classification: {classification.get('classification', '?')} ({classification.get('confidence', '?')})")
        print(f"  Evidence: {classification.get('evidence_summary', '?')[:80]}")

        results.append({
            "openAlexId": candidate["openAlexId"],
            "title": candidate["title"],
            "year": candidate.get("year"),
            "total_citations": candidate["total_citations"],
            "modern_citations_2023_2026": candidate["modern_citations_2023_2026"],
            "modernity_score": candidate["modernity_score"],
            "original_classification": candidate["classification"],
            "core_concept": synonyms.get("core_concept", ""),
            "modern_synonyms": synonyms.get("modern_synonyms", []),
            "search_queries": queries,
            "modern_papers_found": len(search_results),
            "classification": classification.get("classification", "unknown"),
            "confidence": classification.get("confidence", "low"),
            "evidence_summary": classification.get("evidence_summary", ""),
            "modern_equivalent": classification.get("modern_equivalent"),
            "key_papers_found": classification.get("key_papers_found", []),
            "citing_seeds": candidate.get("citing_seeds", []),
            "citing_branches": candidate.get("citing_branches", []),
        })

        time.sleep(1)  # Pause between LLM calls

    # Save LLM cache
    with open(TRACE_CACHE, "w") as f:
        json.dump(cache, f, indent=2)

    # Save results
    output = {
        "metadata": {
            "description": "Lost Canary candidates with concept tracing classification",
            "method": "LLM synonym generation + OpenAlex search (2023-2026) + LLM classification",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "stats": {
            "total_candidates": len(results),
            "genuinely_lost": sum(1 for r in results if r["classification"] == "genuinely_lost"),
            "known_but_ignored": sum(1 for r in results if r["classification"] == "known_but_ignored"),
            "renamed": sum(1 for r in results if r["classification"] == "renamed"),
        },
        "results": results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("CONCEPT TRACING RESULTS")
    print(f"{'=' * 60}")

    genuinely_lost = [r for r in results if r["classification"] == "genuinely_lost"]
    known_but_ignored = [r for r in results if r["classification"] == "known_but_ignored"]
    renamed = [r for r in results if r["classification"] == "renamed"]

    print(f"\n  Total analyzed: {len(results)}")
    print(f"  Genuinely Lost: {len(genuinely_lost)}")
    print(f"  Known but Ignored: {len(known_but_ignored)}")
    print(f"  Renamed: {len(renamed)}")

    if genuinely_lost:
        print(f"\n{'─' * 60}")
        print("GENUINELY LOST (the real Lost Canaries)")
        print(f"{'─' * 60}")
        for r in genuinely_lost:
            print(f"  - {r['title']} ({r['year']})")
            print(f"    {r['total_citations']} cites | MS={r['modernity_score']:.4f}")
            print(f"    Core concept: {r['core_concept'][:70]}")
            print(f"    Evidence: {r['evidence_summary'][:80]}")

    if known_but_ignored:
        print(f"\n{'─' * 60}")
        print("KNOWN BUT IGNORED")
        print(f"{'─' * 60}")
        for r in known_but_ignored:
            print(f"  - {r['title']} ({r['year']})")
            print(f"    {r['evidence_summary'][:80]}")

    if renamed:
        print(f"\n{'─' * 60}")
        print("RENAMED (concept alive under new terminology)")
        print(f"{'─' * 60}")
        for r in renamed:
            print(f"  - {r['title']} ({r['year']}) -> {r.get('modern_equivalent', '?')}")
            print(f"    {r['evidence_summary'][:80]}")

    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
