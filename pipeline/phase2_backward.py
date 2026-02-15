"""Phase 2: Backward Pass — Find Root Primitives.

For each of the 22 classical seeds, fetch their reference lists from
OpenAlex (Semantic Scholar has publisher-elided references for most
classical papers). Count how many seeds cite each reference. Apply
branch diversity weighting:

    root_primitive_score = seed_count * unique_branches

Papers with score >= 6 are Root Primitives (the theoretical bedrock
of MAS that multiple branches build upon).

Usage:
    python3 pipeline/phase2_backward.py                    # Full run (fetches from API)
    python3 pipeline/phase2_backward.py --cached           # Use cached refs (skip API)
    python3 pipeline/phase2_backward.py --threshold 4      # Lower threshold
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, ".")
from pipeline.apis import openalex as oa

SEEDS_FILE = "pipeline/data/seeds_resolved.json"
REFS_CACHE = "pipeline/data/refs_cache_oa.json"
OA_IDS_CACHE = "pipeline/data/seeds_openalex_ids.json"
OUTPUT_FILE = "pipeline/data/root_primitives.json"


def load_classical_seeds() -> list[dict]:
    with open(SEEDS_FILE) as f:
        data = json.load(f)
    seeds = [
        s for s in data["classical_seeds"]
        if s.get("resolution_status") == "resolved"
    ]
    print(f"Loaded {len(seeds)} resolved classical seeds (out of {len(data['classical_seeds'])})")
    return seeds


def resolve_seeds_to_openalex(seeds: list[dict]) -> dict[str, str]:
    """Resolve each seed to its OpenAlex work ID. Returns {seed_id: oa_id}."""
    # Check cache
    if os.path.exists(OA_IDS_CACHE):
        with open(OA_IDS_CACHE) as f:
            cache = json.load(f)
        if len(cache) >= len(seeds):
            print(f"Using cached OpenAlex IDs ({len(cache)} entries)")
            return cache

    mapping = {}
    for seed in seeds:
        sid = seed["id"]
        doi = seed.get("doi")
        title = seed.get("title", "")
        year = seed.get("year")

        print(f"  [{sid}] Resolving to OpenAlex: {seed.get('short', title[:30])}...")

        oa_id = oa.resolve_s2_to_openalex(
            s2_id=seed.get("semantic_scholar_id", ""),
            doi=doi,
            title=title,
            year=year,
        )

        if oa_id:
            mapping[sid] = oa_id
            print(f"  [{sid}] -> {oa_id}")
        else:
            print(f"  [{sid}] FAILED to resolve to OpenAlex")

        time.sleep(0.2)

    with open(OA_IDS_CACHE, "w") as f:
        json.dump(mapping, f, indent=2)

    return mapping


def fetch_references_oa(
    seeds: list[dict],
    oa_ids: dict[str, str],
    use_cache: bool = False,
) -> dict[str, list[dict]]:
    """Fetch reference lists via OpenAlex. Returns {seed_id: [refs]}."""
    cache = {}
    if use_cache and os.path.exists(REFS_CACHE):
        with open(REFS_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached reference lists")

    results = {}
    for seed in seeds:
        sid = seed["id"]

        if sid in cache and cache[sid]:
            results[sid] = cache[sid]
            print(f"  [{sid}] {seed.get('short', '?')}: {len(cache[sid])} refs (cached)")
            continue

        oa_id = oa_ids.get(sid)
        if not oa_id:
            print(f"  [{sid}] {seed.get('short', '?')}: No OpenAlex ID, skipping")
            results[sid] = []
            continue

        # Get the work to extract referenced_works
        work_id = oa_id.split("/")[-1] if "/" in oa_id else oa_id
        print(f"  [{sid}] {seed.get('short', '?')}: fetching refs from OpenAlex ({work_id})...")
        work = oa.get_work_by_openalex_id(work_id)
        ref_ids = work.get("referenced_works", [])

        if not ref_ids:
            print(f"  [{sid}] {seed.get('short', '?')}: 0 refs found")
            results[sid] = []
            continue

        # Batch-fetch metadata for all references
        ref_details = oa.get_references_detailed(ref_ids)

        refs = []
        for r in ref_details:
            refs.append({
                "openAlexId": r.get("id", ""),
                "title": r.get("title", ""),
                "year": r.get("publication_year"),
                "citedByCount": r.get("cited_by_count", 0),
                "doi": (r.get("ids", {}) or {}).get("doi", ""),
            })

        # Also keep unresolved ref IDs (some may not have metadata)
        resolved_ids = {r.get("id") for r in ref_details}
        for rid in ref_ids:
            if rid not in resolved_ids:
                refs.append({
                    "openAlexId": rid,
                    "title": "",
                    "year": None,
                    "citedByCount": 0,
                    "doi": "",
                })

        results[sid] = refs
        print(f"  [{sid}] {seed.get('short', '?')}: {len(refs)} refs ({len(ref_details)} with metadata)")
        time.sleep(0.3)

    # Save cache
    all_cached = {**cache, **results}
    with open(REFS_CACHE, "w") as f:
        json.dump(all_cached, f, indent=2)

    return results


def find_root_primitives(
    seeds: list[dict],
    refs_by_seed: dict[str, list[dict]],
    threshold: int = 6,
) -> list[dict]:
    """Identify Root Primitives — papers cited by multiple seeds across branches."""
    paper_map: dict[str, dict] = {}

    for seed in seeds:
        sid = seed["id"]
        branch = seed["branch"]
        refs = refs_by_seed.get(sid, [])

        for ref in refs:
            pid = ref["openAlexId"]
            if not pid:
                continue
            if pid not in paper_map:
                paper_map[pid] = {
                    "openAlexId": pid,
                    "title": ref.get("title", ""),
                    "year": ref.get("year"),
                    "citedByCount": ref.get("citedByCount", 0),
                    "doi": ref.get("doi", ""),
                    "citing_seeds": set(),
                    "citing_branches": set(),
                }
            paper_map[pid]["citing_seeds"].add(sid)
            paper_map[pid]["citing_branches"].add(branch)
            # Update metadata if we have better data
            if ref.get("title") and not paper_map[pid]["title"]:
                paper_map[pid]["title"] = ref["title"]

    primitives = []
    for pid, info in paper_map.items():
        seed_count = len(info["citing_seeds"])
        branch_count = len(info["citing_branches"])
        score = seed_count * branch_count

        if score >= threshold:
            primitives.append({
                "openAlexId": info["openAlexId"],
                "title": info["title"],
                "year": info["year"],
                "citedByCount": info["citedByCount"] or 0,
                "doi": info.get("doi", ""),
                "seed_count": seed_count,
                "branch_count": branch_count,
                "score": score,
                "citing_seeds": sorted(info["citing_seeds"]),
                "citing_branches": sorted(info["citing_branches"]),
            })

    primitives.sort(key=lambda p: (-p["score"], -(p["citedByCount"] or 0)))
    return primitives


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Backward Pass (OpenAlex)")
    parser.add_argument("--cached", action="store_true", help="Use cached data")
    parser.add_argument("--threshold", type=int, default=6, help="Root primitive score threshold (default: 6)")
    args = parser.parse_args()

    print("=" * 60)
    print("PHASE 2: BACKWARD PASS — Finding Root Primitives (OpenAlex)")
    print("=" * 60)

    seeds = load_classical_seeds()

    print("\nStep 1: Resolve seeds to OpenAlex IDs...")
    oa_ids = resolve_seeds_to_openalex(seeds)
    print(f"Resolved {len(oa_ids)}/{len(seeds)} seeds to OpenAlex")

    print("\nStep 2: Fetch reference lists...")
    refs = fetch_references_oa(seeds, oa_ids, use_cache=args.cached)

    total_refs = sum(len(r) for r in refs.values())
    unique_refs = len(set(
        ref["openAlexId"]
        for ref_list in refs.values()
        for ref in ref_list
        if ref.get("openAlexId")
    ))
    print(f"\nTotal references: {total_refs}")
    print(f"Unique papers referenced: {unique_refs}")

    print(f"\nStep 3: Find Root Primitives (threshold: {args.threshold})...")
    primitives = find_root_primitives(seeds, refs, threshold=args.threshold)

    output = {
        "metadata": {
            "description": "Root Primitives — papers cited by multiple classical seeds across branches",
            "source": "OpenAlex referenced_works",
            "threshold": args.threshold,
            "scoring": "seed_count * branch_diversity",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "stats": {
            "seeds_processed": len(oa_ids),
            "seeds_with_refs": sum(1 for r in refs.values() if r),
            "total_references": total_refs,
            "unique_references": unique_refs,
            "root_primitives_found": len(primitives),
        },
        "root_primitives": primitives,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"ROOT PRIMITIVES FOUND: {len(primitives)}")
    print(f"{'=' * 60}")
    for i, p in enumerate(primitives[:40], 1):
        branches = ", ".join(p["citing_branches"])
        print(f"  {i:2d}. [score={p['score']:2d}] {p['title'][:55]}")
        print(f"      {p['year'] or '?'} | {p['citedByCount']} cites | {p['seed_count']} seeds x {p['branch_count']} branches ({branches})")

    if len(primitives) > 40:
        print(f"  ... and {len(primitives) - 40} more")

    score_dist = defaultdict(int)
    for p in primitives:
        score_dist[p["score"]] += 1
    print(f"\nScore distribution:")
    for score in sorted(score_dist.keys(), reverse=True):
        print(f"  score={score}: {score_dist[score]} papers")

    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
