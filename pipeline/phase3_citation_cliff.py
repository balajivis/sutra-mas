"""Phase 3b: Citation Cliff — Full Historical Citation Data for Visualization.

Fetches full per-year citation distributions (1980-2026) for all classical
seeds + root primitives using OpenAlex's group_by=publication_year on
cites:{oa_id} filter. Groups papers into ~15 named concepts for the
Citation Cliff visualization.

This overcomes the limitation of counts_by_year (which only returns ~10-14
recent years) by using the group_by API which returns the FULL distribution.

Usage:
    python3 -m pipeline.phase3_citation_cliff           # Full run
    python3 -m pipeline.phase3_citation_cliff --cached   # Use cached API responses
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlencode

sys.path.insert(0, ".")
from pipeline.apis.openalex import _request, BASE_URL

# ── Input / Output files ──────────────────────────────────────────────────

SEEDS_FILE = "pipeline/data/seeds.json"
SEEDS_OA_FILE = "pipeline/data/seeds_openalex_ids.json"
MODERNITY_FILE = "pipeline/data/modernity_scores.json"
LOST_CANARIES_FILE = "pipeline/data/lost_canaries.json"
API_CACHE_FILE = "pipeline/data/citation_cliff_cache.json"
OUTPUT_FILE = "pipeline/data/citation_cliff_full.json"

# ── Concept groupings ─────────────────────────────────────────────────────
# Maps concept name -> list of OpenAlex IDs that belong to it.
# Built from seeds.json + root primitives, manually curated.

CONCEPT_GROUPS = {
    "Contract Net": {
        "description": "Task allocation via announce/bid/award (Smith 1980)",
        "seed_ids": ["C05"],
        "extra_oa_ids": ["https://openalex.org/W2068394020"],  # Negotiation as metaphor (1983)
    },
    "SharedPlans": {
        "description": "Collaborative plans for complex group action (Grosz & Kraus 1996)",
        "seed_ids": ["C09"],
        "extra_oa_ids": ["https://openalex.org/W332028463"],  # Plans for Discourse (1990)
    },
    "Joint Intentions": {
        "description": "Intention as committed choice, obligation to inform (Cohen & Levesque 1990)",
        "seed_ids": ["C10"],
        "extra_oa_ids": [
            "https://openalex.org/W2117272332",  # On acting together (1990)
            "https://openalex.org/W2119471769",  # Commitments and conventions (1993)
            "https://openalex.org/W2076064414",  # Controlling cooperative problem solving (1995)
        ],
    },
    "BDI": {
        "description": "Belief-Desire-Intention architecture (Rao & Georgeff 1995)",
        "seed_ids": ["C14"],
        "extra_oa_ids": [
            "https://openalex.org/W2004550196",  # Plans and resource-bounded practical reasoning (Bratman 1988)
            "https://openalex.org/W1877676982",  # A representationalist theory of intention (1993)
        ],
    },
    "Blackboard": {
        "description": "Shared state + control shell (Nii 1986)",
        "seed_ids": ["C15"],
        "extra_oa_ids": [],
    },
    "FA/C & Result Sharing": {
        "description": "Functionally accurate cooperative systems (Lesser & Corkill 1983)",
        "seed_ids": [],  # C08 OA ID is wrong (resolves to QUANTUM ESPRESSO)
        "extra_oa_ids": [
            "https://openalex.org/W2085568149",  # Functionally Accurate, Cooperative Distributed Systems (1981)
            "https://openalex.org/W2028817969",   # Frameworks for Cooperation (1981)
            "https://openalex.org/W1546574211",   # Distributed rational decision making (Durfee 1999)
        ],
    },
    "KQML / ACL": {
        "description": "Agent communication languages and performatives (Finin 1994)",
        "seed_ids": ["C01"],
        "extra_oa_ids": [],
    },
    "Organizational Models": {
        "description": "Hierarchies, holarchies, role-based organization (Horling & Lesser 2004)",
        "seed_ids": ["C03", "C04"],
        "extra_oa_ids": [
            "https://openalex.org/W2028628502",  # Organizational View (1981)
        ],
    },
    "STEAM / Teamwork": {
        "description": "Flexible teamwork via joint intentions in practice (Tambe 1997)",
        "seed_ids": ["C12"],
        "extra_oa_ids": [
            "https://openalex.org/W1484321175",  # Planned team activity (1994)
        ],
    },
    "TAEMS": {
        "description": "Task environment modeling for coordination design (Decker 1996)",
        "seed_ids": [],  # C11 OA ID is wrong (resolves to Hybrid Intelligence 2020)
        "extra_oa_ids": [
            "https://openalex.org/W1739646785",  # Introduction to planning in multiagent systems (Decker 2009)
        ],
    },
    "Discourse Structure": {
        "description": "Plans for discourse, intentions in communication (Grosz & Sidner)",
        "seed_ids": [],
        "extra_oa_ids": [
            "https://openalex.org/W3212193146",  # Intentions in Communication (1991)
            "https://openalex.org/W332028463",    # Plans for Discourse (1990) — also in SharedPlans
        ],
    },
    "Intelligent Agents": {
        "description": "Weak vs strong agency, agent theory (Wooldridge & Jennings 1995)",
        "seed_ids": ["C13"],
        "extra_oa_ids": [],
    },
    "STRIPS / Planning": {
        "description": "Classical AI planning as theorem proving (Fikes & Nilsson 1971)",
        "seed_ids": [],
        "extra_oa_ids": [
            "https://openalex.org/W2337392266",  # STRIPS (1971)
        ],
    },
    "Social Knowledge": {
        "description": "Social conceptions of knowledge and open systems semantics (Singh 1991)",
        "seed_ids": [],
        "extra_oa_ids": [
            "https://openalex.org/W2055143352",  # Social conceptions (1991)
        ],
    },
    "Subsumption": {
        "description": "Reactive layered control architecture (Brooks 1986)",
        "seed_ids": ["C16"],
        "extra_oa_ids": [],
    },
    "Coordination Theory": {
        "description": "Dependencies determine coordination mechanisms (Malone & Crowston 1994)",
        "seed_ids": ["C06"],
        "extra_oa_ids": [],
    },
    "Distributed AI Foundations": {
        "description": "Foundational DAI frameworks and anthologies",
        "seed_ids": [],
        "extra_oa_ids": [
            "https://openalex.org/W1506018624",  # Distributed AI (Bond & Gasser 1987)
            "https://openalex.org/W2124241059",  # Readings in Distributed AI (1988)
        ],
    },
}

# ── Survival classification ───────────────────────────────────────────────
# Override from lost_canaries.json; also manual overrides for seeds.

SURVIVAL_OVERRIDES = {
    # Genuinely lost (from lost_canaries analysis)
    "https://openalex.org/W332028463": "genuinely_lost",      # Plans for Discourse
    "https://openalex.org/W384331506": "genuinely_lost",      # On Being Responsible
    "https://openalex.org/W2117272332": "genuinely_lost",     # On acting together
    "https://openalex.org/W2055143352": "genuinely_lost",     # Social conceptions
    # Known but ignored
    "https://openalex.org/W2431139695": "known_but_ignored",  # Intention is choice with commitment
}


# ── Cemri / Kim overlay annotations ──────────────────────────────────────

ANNOTATIONS = [
    {
        "type": "failure_band",
        "label": "75% failure rate (ChatDev, Cemri 2025)",
        "year_start": 2023,
        "year_end": 2026,
        "position": "top",
    },
    {
        "type": "callout",
        "concept": "Joint Intentions",
        "label": "When forgotten \u2192 FC2 inter-agent misalignment (36.9% of failures)",
        "year": 2020,
    },
    {
        "type": "callout",
        "concept": "FA/C & Result Sharing",
        "label": "When forgotten \u2192 3x token waste, no shared artifacts",
        "year": 2018,
    },
    {
        "type": "callout",
        "concept": "Contract Net",
        "label": "When forgotten \u2192 static routing, no adaptive task allocation",
        "year": 2016,
    },
    {
        "type": "stat",
        "label": "17.2x error amplification without coordination (Kim 2025)",
        "year": 2024,
        "position": "right",
    },
    {
        "type": "stat",
        "label": "4.4x error amplification even with centralized control (Kim 2025)",
        "year": 2023,
        "position": "right",
    },
    {
        "type": "era_label",
        "label": "Classical MAS Era",
        "year_start": 1980,
        "year_end": 2010,
    },
    {
        "type": "era_label",
        "label": "Deep Learning Era",
        "year_start": 2011,
        "year_end": 2022,
    },
    {
        "type": "era_label",
        "label": "LLM Agent Era",
        "year_start": 2023,
        "year_end": 2026,
    },
]


def load_seeds_oa_ids() -> dict[str, str]:
    """Load seed ID -> OpenAlex ID mapping."""
    with open(SEEDS_OA_FILE) as f:
        return json.load(f)


def load_lost_canaries() -> dict[str, str]:
    """Load lost canary classifications by OA ID."""
    try:
        with open(LOST_CANARIES_FILE) as f:
            data = json.load(f)
        return {
            r["openAlexId"]: r["classification"]
            for r in data.get("results", [])
        }
    except FileNotFoundError:
        print("[WARN] lost_canaries.json not found, using defaults")
        return {}


def load_modernity_scores() -> dict[str, dict]:
    """Load modernity scores by OA ID for classification fallback."""
    try:
        with open(MODERNITY_FILE) as f:
            data = json.load(f)
        return {r["openAlexId"]: r for r in data.get("results", [])}
    except FileNotFoundError:
        return {}


def fetch_citing_year_distribution(oa_id: str) -> dict[int, int]:
    """Fetch full per-year citation distribution using group_by.

    Uses: GET /works?filter=cites:{id}&group_by=publication_year&per_page=200
    Returns dict of {year: count} spanning the full history.
    per_page controls the number of group_by buckets (max 200, enough for ~50 years).
    """
    short_id = oa_id.split("/")[-1] if "/" in oa_id else oa_id
    params = urlencode({
        "filter": f"cites:{short_id}",
        "group_by": "publication_year",
        "per_page": "200",
    })
    url = f"{BASE_URL}/works?{params}"
    data = _request(url)

    year_dist = {}
    for bucket in data.get("group_by", []):
        year = int(bucket["key"])
        count = bucket["count"]
        if 1970 <= year <= 2026:  # Filter out weird years
            year_dist[year] = count

    return year_dist


def fetch_work_metadata(oa_id: str) -> dict:
    """Fetch basic metadata for a work."""
    short_id = oa_id.split("/")[-1] if "/" in oa_id else oa_id
    params = urlencode({
        "select": "id,title,publication_year,cited_by_count",
    })
    url = f"{BASE_URL}/works/{short_id}?{params}"
    return _request(url)


def resolve_concept_oa_ids(seeds_oa: dict[str, str]) -> dict[str, list[str]]:
    """Resolve each concept group to a deduplicated list of OA IDs."""
    concept_ids = {}
    for name, group in CONCEPT_GROUPS.items():
        ids = set()
        for sid in group["seed_ids"]:
            if sid in seeds_oa:
                ids.add(seeds_oa[sid])
            else:
                print(f"  [WARN] Seed {sid} has no OA ID, skipping")
        for oa_id in group["extra_oa_ids"]:
            ids.add(oa_id)
        concept_ids[name] = sorted(ids)
    return concept_ids


def classify_survival(oa_id: str, canary_map: dict, modernity_map: dict) -> str:
    """Determine survival classification for a paper."""
    # Check explicit overrides first
    if oa_id in SURVIVAL_OVERRIDES:
        return SURVIVAL_OVERRIDES[oa_id]

    # Check lost canaries data
    if oa_id in canary_map:
        cl = canary_map[oa_id]
        if cl == "genuinely_lost":
            return "genuinely_lost"
        elif cl in ("renamed", "known_but_ignored"):
            return cl
        elif cl == "lost_canary_candidate":
            return "renamed"  # Default canary candidates to renamed

    # Check modernity scores
    if oa_id in modernity_map:
        ms = modernity_map[oa_id]
        score = ms.get("modernity_score", 0)
        if score >= 0.05:
            return "active"
        elif ms.get("classification") == "lost_canary_candidate":
            return "renamed"  # Most lost canary candidates are renamed

    return "below_threshold"


def concept_survival(paper_survivals: list[str]) -> str:
    """Determine overall survival for a concept based on its papers.

    Worst case wins: if any paper is genuinely_lost, concept is genuinely_lost.
    """
    priority = {"genuinely_lost": 0, "known_but_ignored": 1, "below_threshold": 2, "renamed": 3, "active": 4}
    if not paper_survivals:
        return "below_threshold"
    return min(paper_survivals, key=lambda s: priority.get(s, 2))


def main():
    parser = argparse.ArgumentParser(description="Phase 3b: Citation Cliff data generation")
    parser.add_argument("--cached", action="store_true", help="Use cached API responses")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 3b: Citation Cliff — Full Historical Data")
    print("=" * 60)

    # Load input data
    seeds_oa = load_seeds_oa_ids()
    canary_map = load_lost_canaries()
    modernity_map = load_modernity_scores()

    print(f"\nLoaded {len(seeds_oa)} seed OA IDs")
    print(f"Loaded {len(canary_map)} lost canary classifications")
    print(f"Loaded {len(modernity_map)} modernity scores")

    # Resolve concept groups to OA IDs
    concept_ids = resolve_concept_oa_ids(seeds_oa)
    all_oa_ids = set()
    for ids in concept_ids.values():
        all_oa_ids.update(ids)
    print(f"\n{len(CONCEPT_GROUPS)} concepts, {len(all_oa_ids)} unique papers")

    # Load or fetch API cache
    cache = {}
    if args.cached and os.path.exists(API_CACHE_FILE):
        with open(API_CACHE_FILE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached API responses")

    # Fetch per-paper data
    paper_data = {}
    for i, oa_id in enumerate(sorted(all_oa_ids)):
        short_id = oa_id.split("/")[-1]
        print(f"\n[{i+1}/{len(all_oa_ids)}] {short_id}...")

        if oa_id in cache:
            paper_data[oa_id] = cache[oa_id]
            print(f"  (cached) {paper_data[oa_id].get('title', '?')[:50]}")
            continue

        # Fetch metadata
        meta = fetch_work_metadata(oa_id)
        if not meta or not meta.get("title"):
            print(f"  [SKIP] No metadata for {oa_id}")
            continue

        # Fetch full year distribution
        year_dist = fetch_citing_year_distribution(oa_id)

        entry = {
            "oa_id": oa_id,
            "title": meta.get("title", "Unknown"),
            "year": meta.get("publication_year"),
            "total_citations": meta.get("cited_by_count", 0),
            "year_distribution": year_dist,
        }
        paper_data[oa_id] = entry
        cache[oa_id] = entry

        print(f"  {entry['title'][:50]} ({entry['year']})")
        print(f"  Total cites: {entry['total_citations']}, year range: {min(year_dist.keys()) if year_dist else '?'}-{max(year_dist.keys()) if year_dist else '?'}")

        time.sleep(0.3)  # Polite rate limiting

    # Save cache
    with open(API_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"\nSaved API cache ({len(cache)} entries)")

    # Build concept records
    concepts = []
    global_years = set()

    for name, oa_ids in concept_ids.items():
        group_def = CONCEPT_GROUPS[name]
        papers_in_concept = []
        summed_years = defaultdict(int)
        total_cites = 0
        modern_cites = 0
        paper_survivals = []

        for oa_id in oa_ids:
            if oa_id not in paper_data:
                continue
            pd = paper_data[oa_id]
            papers_in_concept.append(f"{pd['title'][:60]} ({pd['year']})")
            total_cites += pd["total_citations"]

            # Sum year distributions
            for yr_str, count in pd["year_distribution"].items():
                yr = int(yr_str)
                summed_years[yr] += count
                global_years.add(yr)
                if 2023 <= yr <= 2026:
                    modern_cites += count

            # Classify survival
            survival = classify_survival(oa_id, canary_map, modernity_map)
            paper_survivals.append(survival)

        # Sort year data
        year_data = [{"year": y, "citations": summed_years.get(y, 0)}
                     for y in sorted(summed_years.keys())]

        # Overall concept survival
        overall_survival = concept_survival(paper_survivals)

        concepts.append({
            "name": name,
            "description": group_def["description"],
            "papers": papers_in_concept,
            "paperCount": len(papers_in_concept),
            "survival": overall_survival,
            "totalCitations": total_cites,
            "modernCitations": modern_cites,
            "modernityScore": round(modern_cites / total_cites, 6) if total_cites > 0 else 0,
            "yearData": year_data,
            "peakYear": max(summed_years, key=summed_years.get) if summed_years else None,
            "peakCitations": max(summed_years.values()) if summed_years else 0,
        })

    # Fill in zero-years for all concepts to match the global range
    year_range = sorted(global_years) if global_years else list(range(1980, 2027))
    for concept in concepts:
        existing_years = {d["year"] for d in concept["yearData"]}
        for yr in year_range:
            if yr not in existing_years:
                concept["yearData"].append({"year": yr, "citations": 0})
        concept["yearData"].sort(key=lambda d: d["year"])

    # Sort concepts: genuinely lost first, then by modernityScore ascending
    survival_order = {"genuinely_lost": 0, "known_but_ignored": 1, "below_threshold": 2, "renamed": 3, "active": 4}
    concepts.sort(key=lambda c: (survival_order.get(c["survival"], 2), c["modernityScore"]))

    # Build output
    output = {
        "metadata": {
            "description": "Citation Cliff: Full historical per-year citation data grouped by concept",
            "source": "OpenAlex group_by=publication_year on cites:{id} filter",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "conceptCount": len(concepts),
            "paperCount": len(all_oa_ids),
            "yearRange": [min(year_range), max(year_range)] if year_range else [1980, 2026],
        },
        "yearRange": year_range,
        "concepts": concepts,
        "annotations": ANNOTATIONS,
    }

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Concepts: {len(concepts)}")
    print(f"Year range: {year_range[0]}-{year_range[-1]}")
    print()

    # Summary table
    print(f"{'Concept':<30} {'Survival':<20} {'Total':>8} {'Modern':>8} {'Peak':>6} {'Peak Yr':>8}")
    print("-" * 90)
    for c in concepts:
        print(f"{c['name']:<30} {c['survival']:<20} {c['totalCitations']:>8} {c['modernCitations']:>8} {c['peakCitations']:>6} {c['peakYear'] or '-':>8}")

    print(f"\n{'=' * 60}")
    print("Done.")


if __name__ == "__main__":
    main()
