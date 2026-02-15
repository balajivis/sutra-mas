"""T04: Resolve all 33 seed papers to Semantic Scholar IDs.

Strategy:
1. If seed already has a semantic_scholar_id, verify it via lookup.
2. If seed has a DOI, look up via "DOI:{doi}".
3. If seed has an arxiv_id, look up via "ARXIV:{arxiv_id}".
4. Otherwise, search by title and pick the best match (year + citation count heuristic).
5. Fallback: search Crossref for DOI, then retry S2 with DOI.

Output: pipeline/data/seeds_resolved.json
"""

import json
import sys
import time

# Add parent to path for imports
sys.path.insert(0, ".")

from pipeline.apis import semantic_scholar as s2
from pipeline.apis import crossref as cr


def resolve_one(seed: dict, is_modern: bool = False) -> dict:
    """Resolve a single seed paper to its Semantic Scholar ID."""
    result = {
        **seed,
        "resolution_method": None,
        "resolution_status": "unresolved",
        "s2_citation_count": None,
        "s2_reference_count": None,
    }

    title = seed["title"]
    seed_id = seed["id"]
    year = seed.get("year")

    # 1. Already has S2 ID — verify it
    if seed.get("semantic_scholar_id"):
        print(f"  [{seed_id}] Has S2 ID, verifying...")
        paper = s2.get_paper(seed["semantic_scholar_id"], fields="paperId,title,year,citationCount,referenceCount,externalIds")
        if paper and paper.get("paperId"):
            result["semantic_scholar_id"] = paper["paperId"]
            result["s2_citation_count"] = paper.get("citationCount")
            result["s2_reference_count"] = paper.get("referenceCount")
            result["resolution_method"] = "existing_id"
            result["resolution_status"] = "resolved"
            # Extract DOI if available
            ext = paper.get("externalIds", {})
            if ext and ext.get("DOI"):
                result["doi"] = ext["DOI"]
            print(f"  [{seed_id}] Verified: {paper.get('title', '?')[:60]} ({paper.get('citationCount', '?')} cites)")
            return result

    # 2. Has DOI — look up by DOI
    if seed.get("doi"):
        print(f"  [{seed_id}] Looking up by DOI: {seed['doi']}...")
        paper = s2.get_paper(f"DOI:{seed['doi']}", fields="paperId,title,year,citationCount,referenceCount,externalIds")
        if paper and paper.get("paperId"):
            result["semantic_scholar_id"] = paper["paperId"]
            result["s2_citation_count"] = paper.get("citationCount")
            result["s2_reference_count"] = paper.get("referenceCount")
            result["resolution_method"] = "doi_lookup"
            result["resolution_status"] = "resolved"
            print(f"  [{seed_id}] Resolved via DOI: {paper.get('title', '?')[:60]} ({paper.get('citationCount', '?')} cites)")
            return result

    # 3. Has ArXiv ID — look up by ArXiv
    if seed.get("arxiv_id"):
        print(f"  [{seed_id}] Looking up by ArXiv: {seed['arxiv_id']}...")
        paper = s2.get_paper(f"ARXIV:{seed['arxiv_id']}", fields="paperId,title,year,citationCount,referenceCount,externalIds")
        if paper and paper.get("paperId"):
            result["semantic_scholar_id"] = paper["paperId"]
            result["s2_citation_count"] = paper.get("citationCount")
            result["s2_reference_count"] = paper.get("referenceCount")
            result["resolution_method"] = "arxiv_lookup"
            result["resolution_status"] = "resolved"
            ext = paper.get("externalIds", {})
            if ext and ext.get("DOI"):
                result["doi"] = ext["DOI"]
            print(f"  [{seed_id}] Resolved via ArXiv: {paper.get('title', '?')[:60]} ({paper.get('citationCount', '?')} cites)")
            return result

    # 4. Title search on Semantic Scholar
    print(f"  [{seed_id}] Searching S2 by title: {title[:50]}...")
    results = s2.search_paper(title, limit=5, fields="paperId,title,year,citationCount,referenceCount,externalIds")
    if results:
        # Pick best match: prefer exact year match with highest citations
        best = None
        for r in results:
            if year and r.get("year") == year:
                if best is None or (r.get("citationCount") or 0) > (best.get("citationCount") or 0):
                    best = r
        if best is None:
            # No year match — take highest cited
            best = max(results, key=lambda r: r.get("citationCount") or 0)

        result["semantic_scholar_id"] = best["paperId"]
        result["s2_citation_count"] = best.get("citationCount")
        result["s2_reference_count"] = best.get("referenceCount")
        result["resolution_method"] = "title_search"
        result["resolution_status"] = "resolved"
        ext = best.get("externalIds", {})
        if ext and ext.get("DOI"):
            result["doi"] = ext["DOI"]
        print(f"  [{seed_id}] Resolved via title: {best.get('title', '?')[:60]} ({best.get('citationCount', '?')} cites)")
        return result

    # 5. Fallback: Crossref DOI lookup, then retry S2
    print(f"  [{seed_id}] S2 search failed. Trying Crossref...")
    cr_results = cr.search_by_title(title, limit=3)
    for item in cr_results:
        meta = cr.extract_metadata(item)
        if meta.get("doi") and (not year or meta.get("year") == year):
            print(f"  [{seed_id}] Found DOI via Crossref: {meta['doi']}")
            paper = s2.get_paper(f"DOI:{meta['doi']}", fields="paperId,title,year,citationCount,referenceCount,externalIds")
            if paper and paper.get("paperId"):
                result["semantic_scholar_id"] = paper["paperId"]
                result["doi"] = meta["doi"]
                result["s2_citation_count"] = paper.get("citationCount")
                result["s2_reference_count"] = paper.get("referenceCount")
                result["resolution_method"] = "crossref_doi"
                result["resolution_status"] = "resolved"
                print(f"  [{seed_id}] Resolved via Crossref→S2: {paper.get('title', '?')[:60]} ({paper.get('citationCount', '?')} cites)")
                return result

    print(f"  [{seed_id}] FAILED to resolve: {title[:60]}")
    return result


def main():
    with open("pipeline/data/seeds.json") as f:
        seeds = json.load(f)

    resolved = {
        "metadata": {
            "description": "Seeds resolved to Semantic Scholar IDs",
            "source": "pipeline/data/seeds.json",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "classical_seeds": [],
        "modern_bridge": [],
        "stats": {
            "total": 0,
            "resolved": 0,
            "failed": 0,
            "by_method": {},
        },
    }

    # Resolve classical seeds
    print("=" * 60)
    print("RESOLVING CLASSICAL SEEDS (22 papers)")
    print("=" * 60)
    for seed in seeds["classical_seeds"]:
        r = resolve_one(seed, is_modern=False)
        resolved["classical_seeds"].append(r)
        resolved["stats"]["total"] += 1
        if r["resolution_status"] == "resolved":
            resolved["stats"]["resolved"] += 1
            method = r["resolution_method"]
            resolved["stats"]["by_method"][method] = resolved["stats"]["by_method"].get(method, 0) + 1
        else:
            resolved["stats"]["failed"] += 1
        # Brief pause to be gentle on the API
        time.sleep(0.5)

    # Resolve modern bridge papers
    print("\n" + "=" * 60)
    print("RESOLVING MODERN BRIDGE PAPERS (11 papers)")
    print("=" * 60)
    for seed in seeds["modern_bridge"]:
        r = resolve_one(seed, is_modern=True)
        resolved["modern_bridge"].append(r)
        resolved["stats"]["total"] += 1
        if r["resolution_status"] == "resolved":
            resolved["stats"]["resolved"] += 1
            method = r["resolution_method"]
            resolved["stats"]["by_method"][method] = resolved["stats"]["by_method"].get(method, 0) + 1
        else:
            resolved["stats"]["failed"] += 1
        time.sleep(0.5)

    # Save results
    with open("pipeline/data/seeds_resolved.json", "w") as f:
        json.dump(resolved, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("RESOLUTION SUMMARY")
    print("=" * 60)
    print(f"Total:    {resolved['stats']['total']}")
    print(f"Resolved: {resolved['stats']['resolved']}")
    print(f"Failed:   {resolved['stats']['failed']}")
    print(f"Methods:  {json.dumps(resolved['stats']['by_method'], indent=2)}")

    # List failures
    failures = [s for s in resolved["classical_seeds"] + resolved["modern_bridge"] if s["resolution_status"] != "resolved"]
    if failures:
        print(f"\nUNRESOLVED ({len(failures)}):")
        for f_item in failures:
            print(f"  {f_item['id']}: {f_item['title'][:60]}")


if __name__ == "__main__":
    main()
