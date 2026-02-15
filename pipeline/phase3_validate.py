"""Phase 3: Validate Lost Canaries against Modern Bridge Papers.

Check whether any "genuinely lost" papers are actually cited by our
11 modern bridge papers. If so, reclassify as "known_but_ignored."

This is a cross-validation step — if a modern survey paper cites a
concept, it's not truly "lost," just not being implemented.

Usage:
    python3 pipeline/phase3_validate.py
"""

import json
import os
import sys
import time

sys.path.insert(0, ".")
from pipeline.apis import openalex as oa

SEEDS_FILE = "pipeline/data/seeds_resolved.json"
LOST_CANARIES_FILE = "pipeline/data/lost_canaries.json"
OA_IDS_CACHE = "pipeline/data/seeds_openalex_ids.json"
BRIDGE_REFS_CACHE = "pipeline/data/bridge_refs_cache.json"


def load_bridge_papers() -> list[dict]:
    """Load the 11 modern bridge papers."""
    with open(SEEDS_FILE) as f:
        data = json.load(f)
    bridge = [s for s in data["modern_bridge"] if s.get("resolution_status") == "resolved"]
    print(f"Loaded {len(bridge)} resolved modern bridge papers")
    return bridge


def load_lost_canaries() -> dict:
    """Load the Lost Canaries results."""
    with open(LOST_CANARIES_FILE) as f:
        return json.load(f)


def resolve_bridge_to_openalex(bridge_papers: list[dict]) -> dict[str, str]:
    """Resolve bridge papers to OpenAlex IDs."""
    mapping = {}
    for paper in bridge_papers:
        sid = paper["id"]
        doi = paper.get("doi")
        title = paper.get("title", "")
        year = paper.get("year")

        print(f"  [{sid}] Resolving: {title[:45]}...")
        oa_id = oa.resolve_s2_to_openalex(
            s2_id=paper.get("semantic_scholar_id", ""),
            doi=doi,
            title=title,
            year=year,
        )
        if oa_id:
            mapping[sid] = oa_id
            print(f"  [{sid}] -> {oa_id}")
        else:
            print(f"  [{sid}] FAILED")
        time.sleep(0.3)

    return mapping


def fetch_bridge_references(bridge_papers: list[dict], oa_ids: dict[str, str]) -> dict[str, list[str]]:
    """Fetch reference lists for all bridge papers. Returns {paper_id: [ref_oa_ids]}."""
    # Check cache
    if os.path.exists(BRIDGE_REFS_CACHE):
        with open(BRIDGE_REFS_CACHE) as f:
            cache = json.load(f)
        if len(cache) >= len(oa_ids):
            print(f"Using cached bridge references ({len(cache)} papers)")
            return cache

    results = {}
    for paper in bridge_papers:
        sid = paper["id"]
        oa_id = oa_ids.get(sid)
        if not oa_id:
            results[sid] = []
            continue

        work_id = oa_id.split("/")[-1] if "/" in oa_id else oa_id
        print(f"  [{sid}] Fetching refs: {paper['title'][:40]}...")
        work = oa.get_work_by_openalex_id(work_id)
        refs = work.get("referenced_works", [])
        results[sid] = refs
        print(f"  [{sid}] {len(refs)} references")
        time.sleep(0.3)

    with open(BRIDGE_REFS_CACHE, "w") as f:
        json.dump(results, f, indent=2)

    return results


def validate_canaries(canary_data: dict, bridge_refs: dict[str, list[str]], bridge_papers: list[dict]) -> dict:
    """Check if any genuinely lost canaries appear in bridge paper references."""
    # Build lookup from bridge paper ID to title
    bridge_titles = {p["id"]: p["title"] for p in bridge_papers}

    validations = []
    reclassified = 0

    for result in canary_data["results"]:
        oa_id = result["openAlexId"]
        # Normalize to full URL form
        if not oa_id.startswith("https://"):
            oa_id_full = f"https://openalex.org/{oa_id}"
        else:
            oa_id_full = oa_id

        # Check which bridge papers cite this canary
        cited_by_bridges = []
        for bridge_id, refs in bridge_refs.items():
            if oa_id_full in refs or oa_id in refs:
                cited_by_bridges.append(bridge_id)

        result["cited_by_bridge_papers"] = cited_by_bridges
        result["bridge_paper_titles"] = [bridge_titles.get(bid, "?") for bid in cited_by_bridges]

        if cited_by_bridges and result["classification"] == "genuinely_lost":
            old = result["classification"]
            result["classification"] = "known_but_ignored"
            result["reclassified_from"] = old
            result["reclassification_reason"] = f"Cited by {len(cited_by_bridges)} modern bridge papers: {', '.join(cited_by_bridges)}"
            reclassified += 1
            print(f"  RECLASSIFIED: {result['title'][:50]} -> known_but_ignored")
            print(f"    Cited by: {', '.join(cited_by_bridges)}")

        validations.append(result)

    canary_data["results"] = validations

    # Update stats
    canary_data["stats"]["genuinely_lost"] = sum(1 for r in validations if r["classification"] == "genuinely_lost")
    canary_data["stats"]["known_but_ignored"] = sum(1 for r in validations if r["classification"] == "known_but_ignored")
    canary_data["stats"]["renamed"] = sum(1 for r in validations if r["classification"] == "renamed")
    canary_data["stats"]["reclassified_by_validation"] = reclassified
    canary_data["metadata"]["validation"] = f"Cross-validated against {len(bridge_refs)} modern bridge papers"

    return canary_data


def main():
    print("=" * 60)
    print("PHASE 3: VALIDATION — Cross-check against Modern Bridge Papers")
    print("=" * 60)

    bridge_papers = load_bridge_papers()
    canary_data = load_lost_canaries()

    print(f"\nCurrent classification:")
    print(f"  Genuinely Lost: {canary_data['stats']['genuinely_lost']}")
    print(f"  Known but Ignored: {canary_data['stats']['known_but_ignored']}")
    print(f"  Renamed: {canary_data['stats']['renamed']}")

    print(f"\nStep 1: Resolve bridge papers to OpenAlex...")
    oa_ids = resolve_bridge_to_openalex(bridge_papers)
    print(f"Resolved {len(oa_ids)}/{len(bridge_papers)} bridge papers")

    print(f"\nStep 2: Fetch bridge paper references...")
    bridge_refs = fetch_bridge_references(bridge_papers, oa_ids)
    total_refs = sum(len(r) for r in bridge_refs.values())
    print(f"Total references across bridge papers: {total_refs}")

    print(f"\nStep 3: Cross-validate canaries...")
    validated = validate_canaries(canary_data, bridge_refs, bridge_papers)

    # Save updated results
    with open(LOST_CANARIES_FILE, "w") as f:
        json.dump(validated, f, indent=2)

    print(f"\n{'=' * 60}")
    print("VALIDATION RESULTS")
    print(f"{'=' * 60}")
    print(f"  Genuinely Lost: {validated['stats']['genuinely_lost']}")
    print(f"  Known but Ignored: {validated['stats']['known_but_ignored']}")
    print(f"  Renamed: {validated['stats']['renamed']}")
    print(f"  Reclassified by validation: {validated['stats'].get('reclassified_by_validation', 0)}")

    # Show which canaries are cited by bridge papers
    print(f"\n{'─' * 60}")
    print("BRIDGE PAPER CITATIONS OF CANARIES")
    print(f"{'─' * 60}")
    for r in validated["results"]:
        bridges = r.get("cited_by_bridge_papers", [])
        if bridges:
            print(f"  {r['title'][:50]} ({r['classification']})")
            for bid in bridges:
                btitle = next((p["title"][:50] for p in bridge_papers if p["id"] == bid), bid)
                print(f"    <- {bid}: {btitle}")
        else:
            print(f"  {r['title'][:50]} ({r['classification']}) — NOT cited by any bridge paper")

    print(f"\nResults saved to {LOST_CANARIES_FILE}")


if __name__ == "__main__":
    main()
