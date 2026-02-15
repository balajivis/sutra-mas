"""Phase 3: Forward Pass — Compute Modernity Scores, detect Lost Canaries.

For each Root Primitive from Phase 2, compute:

    Modernity Score = citations_2023_2026 / total_citations

Papers with total citations >= 500 AND Modernity Score < 0.05 are
Lost Canary candidates — foundational work that modern LLM agent
research has forgotten.

Uses OpenAlex counts_by_year for the citation time-series, with
the cites filter as a cross-check for the modern window.

Usage:
    python3 pipeline/phase3_forward.py                    # Full run
    python3 pipeline/phase3_forward.py --cached           # Use cached data
    python3 pipeline/phase3_forward.py --min-citations 300  # Lower threshold
    python3 pipeline/phase3_forward.py --modernity-cutoff 0.08  # Higher cutoff
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, ".")
from pipeline.apis import openalex as oa

ROOT_PRIMITIVES_FILE = "pipeline/data/root_primitives.json"
FORWARD_CACHE = "pipeline/data/forward_cache_oa.json"
OUTPUT_FILE = "pipeline/data/modernity_scores.json"

MODERN_YEAR_START = 2023
MODERN_YEAR_END = 2026
DEFAULT_MIN_CITATIONS = 500
DEFAULT_MODERNITY_CUTOFF = 0.05


def load_root_primitives() -> list[dict]:
    """Load root primitives from Phase 2 output."""
    with open(ROOT_PRIMITIVES_FILE) as f:
        data = json.load(f)
    primitives = data["root_primitives"]
    print(f"Loaded {len(primitives)} root primitives")
    return primitives


def clean_and_deduplicate(primitives: list[dict]) -> list[dict]:
    """Remove phantom entries and deduplicate by title.

    Phantom entries are OpenAlex IDs that return 404 or have no metadata.
    Duplicates happen when the same paper has multiple OpenAlex IDs.
    """
    # Step 1: Remove entries with no title (phantom IDs)
    valid = []
    removed_phantom = 0
    for p in primitives:
        if not p.get("title"):
            print(f"  Removing phantom entry: {p['openAlexId']} (no title, score={p['score']})")
            removed_phantom += 1
        else:
            valid.append(p)

    # Step 2: Deduplicate by normalized title
    seen_titles: dict[str, int] = {}
    deduped = []
    removed_dupes = 0
    for p in valid:
        # Normalize: lowercase, strip punctuation artifacts
        norm = p["title"].lower().strip().rstrip(".")
        if norm in seen_titles:
            existing_idx = seen_titles[norm]
            existing = deduped[existing_idx]
            # Keep the one with more citations
            if (p.get("citedByCount") or 0) > (existing.get("citedByCount") or 0):
                # Merge seed info
                merged_seeds = sorted(set(existing["citing_seeds"] + p["citing_seeds"]))
                merged_branches = sorted(set(existing["citing_branches"] + p["citing_branches"]))
                p["citing_seeds"] = merged_seeds
                p["citing_branches"] = merged_branches
                p["seed_count"] = len(merged_seeds)
                p["branch_count"] = len(merged_branches)
                p["score"] = p["seed_count"] * p["branch_count"]
                deduped[existing_idx] = p
                print(f"  Dedup: kept {p['openAlexId']} over {existing['openAlexId']} for '{norm[:50]}'")
            else:
                # Keep existing, merge seed info into it
                existing["citing_seeds"] = sorted(set(existing["citing_seeds"] + p["citing_seeds"]))
                existing["citing_branches"] = sorted(set(existing["citing_branches"] + p["citing_branches"]))
                existing["seed_count"] = len(existing["citing_seeds"])
                existing["branch_count"] = len(existing["citing_branches"])
                existing["score"] = existing["seed_count"] * existing["branch_count"]
                print(f"  Dedup: kept {existing['openAlexId']} over {p['openAlexId']} for '{norm[:50]}'")
            removed_dupes += 1
        else:
            seen_titles[norm] = len(deduped)
            deduped.append(p)

    print(f"\nCleaning: {removed_phantom} phantom + {removed_dupes} duplicate = {removed_phantom + removed_dupes} removed")
    print(f"Remaining: {len(deduped)} root primitives")
    return deduped


def fetch_citation_data(
    primitives: list[dict],
    use_cache: bool = False,
) -> dict[str, dict]:
    """Fetch citation time-series data from OpenAlex.

    For each primitive, get:
    - counts_by_year (from work object)
    - total cited_by_count
    - Cross-check: exact modern citation count via cites filter

    Returns {openAlexId: {cited_by_count, counts_by_year, modern_count_exact}}.
    """
    cache = {}
    if use_cache and os.path.exists(FORWARD_CACHE):
        with open(FORWARD_CACHE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached entries")

    results = {}
    for i, p in enumerate(primitives):
        oa_id = p["openAlexId"]

        if oa_id in cache:
            results[oa_id] = cache[oa_id]
            print(f"  [{i+1}/{len(primitives)}] {p['title'][:45]}... (cached)")
            continue

        print(f"  [{i+1}/{len(primitives)}] {p['title'][:45]}...")

        # 1. Fetch work with counts_by_year
        work = oa.get_work_with_counts(oa_id)
        if not work or not work.get("id"):
            print(f"    -> NOT FOUND in OpenAlex (may be merged/deleted)")
            results[oa_id] = {
                "cited_by_count": p.get("citedByCount", 0),
                "counts_by_year": [],
                "modern_count_exact": 0,
                "status": "not_found",
            }
            continue

        total = work.get("cited_by_count", 0)
        counts_by_year = work.get("counts_by_year", [])

        # Extract modern citations from counts_by_year
        modern_from_cby = sum(
            entry.get("cited_by_count", 0)
            for entry in counts_by_year
            if MODERN_YEAR_START <= entry.get("year", 0) <= MODERN_YEAR_END
        )

        # 2. Cross-check with exact cites filter count
        time.sleep(0.2)
        modern_exact = oa.count_citing_works(oa_id, year_from=MODERN_YEAR_START, year_to=MODERN_YEAR_END)

        entry = {
            "cited_by_count": total,
            "counts_by_year": counts_by_year,
            "modern_from_counts_by_year": modern_from_cby,
            "modern_count_exact": modern_exact,
            "status": "ok",
        }
        results[oa_id] = entry

        print(f"    -> total={total}, modern(cby)={modern_from_cby}, modern(exact)={modern_exact}")
        time.sleep(0.3)

    # Save cache
    all_cached = {**cache, **results}
    with open(FORWARD_CACHE, "w") as f:
        json.dump(all_cached, f, indent=2)
    print(f"\nCached {len(all_cached)} entries to {FORWARD_CACHE}")

    return results


def compute_modernity_scores(
    primitives: list[dict],
    citation_data: dict[str, dict],
    min_citations: int = DEFAULT_MIN_CITATIONS,
    modernity_cutoff: float = DEFAULT_MODERNITY_CUTOFF,
) -> list[dict]:
    """Compute Modernity Scores and classify candidates.

    For each root primitive:
    - Use the exact modern count (from cites filter) as numerator
    - Use cited_by_count as denominator
    - Classify: lost_canary_candidate, active, below_threshold
    """
    scored = []
    for p in primitives:
        oa_id = p["openAlexId"]
        cdata = citation_data.get(oa_id, {})

        total = cdata.get("cited_by_count", p.get("citedByCount", 0))
        modern = cdata.get("modern_count_exact", 0)
        status = cdata.get("status", "unknown")

        if total > 0:
            modernity = modern / total
        else:
            modernity = 0.0

        # Classification
        if total < min_citations:
            classification = "below_citation_threshold"
        elif modernity < modernity_cutoff:
            classification = "lost_canary_candidate"
        else:
            classification = "active"

        # Build year distribution from counts_by_year
        year_dist = {}
        for entry in cdata.get("counts_by_year", []):
            yr = entry.get("year")
            cnt = entry.get("cited_by_count", 0)
            if yr:
                year_dist[str(yr)] = cnt

        scored.append({
            "openAlexId": oa_id,
            "title": p["title"],
            "year": p.get("year"),
            "doi": p.get("doi", ""),
            "total_citations": total,
            "modern_citations_2023_2026": modern,
            "modernity_score": round(modernity, 6),
            "classification": classification,
            "root_primitive_score": p["score"],
            "seed_count": p["seed_count"],
            "branch_count": p["branch_count"],
            "citing_seeds": p["citing_seeds"],
            "citing_branches": p["citing_branches"],
            "year_distribution": year_dist,
        })

    # Sort by modernity score ascending (most "lost" first)
    scored.sort(key=lambda x: (
        0 if x["classification"] == "lost_canary_candidate" else 1,
        x["modernity_score"],
        -x["total_citations"],
    ))

    return scored


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Forward Pass — Modernity Scores")
    parser.add_argument("--cached", action="store_true", help="Use cached citation data")
    parser.add_argument("--min-citations", type=int, default=DEFAULT_MIN_CITATIONS,
                        help=f"Minimum total citations for Lost Canary eligibility (default: {DEFAULT_MIN_CITATIONS})")
    parser.add_argument("--modernity-cutoff", type=float, default=DEFAULT_MODERNITY_CUTOFF,
                        help=f"Modernity Score threshold (default: {DEFAULT_MODERNITY_CUTOFF})")
    args = parser.parse_args()

    print("=" * 60)
    print("PHASE 3: FORWARD PASS — Computing Modernity Scores (OpenAlex)")
    print("=" * 60)

    # Step 1: Load and clean
    print("\nStep 1: Load and clean root primitives...")
    primitives = load_root_primitives()
    primitives = clean_and_deduplicate(primitives)

    # Step 2: Fetch citation data
    print(f"\nStep 2: Fetch citation time-series from OpenAlex...")
    citation_data = fetch_citation_data(primitives, use_cache=args.cached)

    # Step 3: Compute scores
    print(f"\nStep 3: Compute Modernity Scores (min_citations={args.min_citations}, cutoff={args.modernity_cutoff})...")
    scored = compute_modernity_scores(
        primitives, citation_data,
        min_citations=args.min_citations,
        modernity_cutoff=args.modernity_cutoff,
    )

    # Classify results
    lost_canaries = [s for s in scored if s["classification"] == "lost_canary_candidate"]
    active = [s for s in scored if s["classification"] == "active"]
    below_threshold = [s for s in scored if s["classification"] == "below_citation_threshold"]

    # Save output
    output = {
        "metadata": {
            "description": "Modernity Scores for Root Primitives — Phase 3 Forward Pass",
            "source": "OpenAlex counts_by_year + cites filter",
            "modern_window": f"{MODERN_YEAR_START}-{MODERN_YEAR_END}",
            "min_citations": args.min_citations,
            "modernity_cutoff": args.modernity_cutoff,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "stats": {
            "root_primitives_analyzed": len(scored),
            "lost_canary_candidates": len(lost_canaries),
            "active_papers": len(active),
            "below_citation_threshold": len(below_threshold),
        },
        "results": scored,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Print results
    print(f"\n{'=' * 60}")
    print(f"MODERNITY SCORE RESULTS")
    print(f"{'=' * 60}")

    print(f"\n  Analyzed: {len(scored)} root primitives")
    print(f"  Lost Canary candidates: {len(lost_canaries)}")
    print(f"  Active (above cutoff): {len(active)}")
    print(f"  Below citation threshold: {len(below_threshold)}")

    if lost_canaries:
        print(f"\n{'─' * 60}")
        print(f"LOST CANARY CANDIDATES (Modernity < {args.modernity_cutoff}, Citations >= {args.min_citations})")
        print(f"{'─' * 60}")
        for i, lc in enumerate(lost_canaries, 1):
            print(f"  {i}. {lc['title'][:55]}")
            print(f"     {lc['year'] or '?'} | {lc['total_citations']} total | {lc['modern_citations_2023_2026']} modern | MS={lc['modernity_score']:.4f}")
            print(f"     Seeds: {lc['seed_count']} | Branches: {', '.join(lc['citing_branches'])}")

    if active:
        print(f"\n{'─' * 60}")
        print(f"ACTIVE PAPERS (Modernity >= {args.modernity_cutoff}, Citations >= {args.min_citations})")
        print(f"{'─' * 60}")
        for i, a in enumerate(active, 1):
            print(f"  {i}. {a['title'][:55]}")
            print(f"     {a['year'] or '?'} | {a['total_citations']} total | {a['modern_citations_2023_2026']} modern | MS={a['modernity_score']:.4f}")

    if below_threshold:
        print(f"\n{'─' * 60}")
        print(f"BELOW CITATION THRESHOLD (< {args.min_citations} total citations)")
        print(f"{'─' * 60}")
        for i, bt in enumerate(below_threshold, 1):
            print(f"  {i}. {bt['title'][:55]} ({bt['total_citations']} cites, MS={bt['modernity_score']:.4f})")

    # Score distribution
    print(f"\n{'─' * 60}")
    print("MODERNITY SCORE DISTRIBUTION")
    print(f"{'─' * 60}")
    bins = defaultdict(int)
    for s in scored:
        if s["total_citations"] >= args.min_citations:
            bucket = int(s["modernity_score"] * 100) // 5 * 5  # 5% buckets
            bins[bucket] += 1
    for bucket in sorted(bins.keys()):
        bar = "█" * bins[bucket]
        print(f"  {bucket:3d}-{bucket+4:3d}%: {bar} ({bins[bucket]})")

    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
