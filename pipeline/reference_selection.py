#!/usr/bin/env python3
"""Reference Selection Algorithm for the Sutra survey paper.

Implements the three-tier selection described in Section 3 (Methodology):
  Tier 1 — Surveys:    2 per pillar (1 classic, 1 modern)
  Tier 2 — Landmarks:  5 per pillar (top-cited, span ≥2 decades)
  Tier 3 — Regional:  ~16 per pillar (6 temporal + 10 semantic)

Cross-cutting constraints:
  - Lost Canary: ≥1 per pillar (citations >100, modernity <0.1)
  - Currency:    ≥2 per pillar from 2024-2026
  - Paradigm:    ≥1 per applicable type (theoretical/empirical/system/critique)

Also detects:
  - Bridge papers (high similarity to ≥3 pillar anchors)

Usage:
    python3 -m pipeline.reference_selection
    python3 -m pipeline.reference_selection --output bibliography.json
    python3 -m pipeline.reference_selection --markdown report.md

Dependencies:
    pip install scikit-learn numpy hdbscan azure-search-documents
"""

import argparse
import json
import os
import sys
import re
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.assembly.db import get_conn
from pipeline.assembly.clustering import (
    GUIDED_CLUSTERS,
    pull_embeddings_from_search,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Three eras for temporal spread
ERAS = {
    "Classical":  (0, 2005),      # pre-2005
    "Middle":     (2006, 2022),   # applied MAS + pre-LLM DL
    "LLM":        (2023, 2026),   # current renaissance
}
ERA_MIN_PAPERS = 10   # skip era if <10 papers in cluster for that era
ERA_PICKS = 2         # papers per era

# Targets
SURVEY_PICKS = 2       # 1 classic + 1 modern
LANDMARK_PICKS = 5
REGIONAL_TEMPORAL = 6  # 3 eras × 2
REGIONAL_SEMANTIC = 10
LOST_CANARY_MIN = 1
CURRENCY_MIN = 2       # papers from 2024-2026
CURRENCY_YEAR = 2024

# Citation floor: papers must have ≥ MIN_CITATIONS to be selected,
# unless they're recent (year >= RECENT_YEAR_CUTOFF)
MIN_CITATIONS = 10
RECENT_YEAR_CUTOFF = 2024

# Lost Canary thresholds
CANARY_CITATIONS = 100
CANARY_MODERNITY = 0.1

# K-means sub-clustering within pillars
SUBCLUSTER_TARGET_K = 5  # target sub-regions per pillar

# Papers to exclude from selection (non-MAS, wrong domain, etc.)
EXCLUDE_PAPER_IDS = {
    2210,   # Shannon "A Mathematical Theory of Communication" — information theory, not MAS
    13787,  # Kuhn "The Structure of Scientific Revolutions" — philosophy of science
}


def meets_citation_floor(paper: dict) -> bool:
    """Check if a paper meets the citation floor for bibliography inclusion.

    All selected papers must have ≥ MIN_CITATIONS, unless they're recent
    (year >= RECENT_YEAR_CUTOFF) — recent papers haven't had time to
    accumulate citations.
    """
    cites = paper.get("citation_count") or 0
    year = paper.get("year") or 0
    if year >= RECENT_YEAR_CUTOFF:
        return True  # recent papers exempt
    return cites >= MIN_CITATIONS


def has_verified_provenance(paper: dict) -> bool:
    """Check if a paper has verified provenance.

    For citation-ranked tiers (landmarks, temporal), we require at least
    one external identifier — OpenAlex, DOI, or arXiv — to trust the
    citation count. Papers without any external ID may have unverified
    or fake citation counts.
    """
    return bool(
        paper.get("openalex_id") or
        paper.get("doi") or
        paper.get("arxiv_id")
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_papers() -> list[dict]:
    """Load all clustered papers with full metadata."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.title, p.year, p.citation_count, p.is_classical,
                   p.doi, p.arxiv_id, p.openalex_id, p.venue, p.source,
                   p.modernity_score,
                   p.analysis->>'key_contribution_summary' as summary,
                   p.analysis->>'coordination_pattern' as pattern,
                   p.analysis->>'theoretical_grounding' as grounding,
                   p.analysis->>'methodology' as methodology,
                   p.analysis->'failure_modes_addressed' as failure_modes,
                   p.analysis->'classical_concepts' as classical_concepts,
                   p.analysis->'classical_concepts_missing' as concepts_missing,
                   p.analysis->>'unique_contribution' as unique_contribution,
                   pc.cluster_id, pc.cluster_label
            FROM papers p
            JOIN paper_clusters pc ON p.id = pc.paper_id
            WHERE p.analysis IS NOT NULL
              AND p.analysis->>'key_contribution_summary' IS NOT NULL
            ORDER BY p.id
        """)
        cols = [d[0] for d in cur.description]
        papers = [dict(zip(cols, row)) for row in cur.fetchall()]

    # Filter out explicitly excluded papers
    if EXCLUDE_PAPER_IDS:
        before = len(papers)
        papers = [p for p in papers if p["id"] not in EXCLUDE_PAPER_IDS]
        excluded = before - len(papers)
        if excluded:
            print(f"  Excluded {excluded} papers from EXCLUDE_PAPER_IDS")

    print(f"Loaded {len(papers)} clustered papers with metadata")
    return papers


def load_embeddings_dict() -> dict[int, np.ndarray]:
    """Load embeddings from Azure AI Search, return as {paper_id: vector}."""
    raw = pull_embeddings_from_search()
    return {pid: np.array(vec) for pid, vec in raw.items()}


# ---------------------------------------------------------------------------
# Paradigm classification
# ---------------------------------------------------------------------------

def classify_paradigm(paper: dict) -> set[str]:
    """Classify paper into paradigm types from analysis fields.

    Returns a set of applicable types: theoretical, empirical, system, critique.
    A paper can belong to multiple types.
    """
    types = set()
    meth = (paper.get("methodology") or "").lower()
    grounding = (paper.get("grounding") or "").lower()
    title = (paper.get("title") or "").lower()
    contribution = (paper.get("unique_contribution") or "").lower()
    failure_modes = paper.get("failure_modes") or []

    # Theoretical: formal models, proofs, logical frameworks
    theoretical_kw = [
        "formal", "proof", "theorem", "logic", "specification", "axiom",
        "model checking", "verification", "correctness", "calculus",
        "semantics", "modal logic", "temporal logic",
    ]
    if grounding == "strong" or any(kw in meth for kw in theoretical_kw) or \
       any(kw in title for kw in ["formal", "logic", "theory of", "calculus"]):
        types.add("theoretical")

    # Empirical: experiments, benchmarks, user studies
    empirical_kw = [
        "experiment", "benchmark", "evaluat", "ablation", "user study",
        "empirical", "dataset", "baseline", "comparison", "controlled",
        "quantitative", "measurement", "tested on", "results show",
    ]
    if any(kw in meth for kw in empirical_kw) or \
       any(kw in contribution for kw in empirical_kw):
        types.add("empirical")

    # System: implementations, frameworks, tools
    system_kw = [
        "framework", "implementation", "system", "platform", "tool",
        "architecture", "prototype", "deploy", "middleware", "library",
        "sdk", "runtime", "infrastructure",
    ]
    if any(kw in meth for kw in system_kw) or \
       any(kw in title for kw in ["framework", "platform", "system", "tool"]):
        types.add("system")

    # Critique: failures, limitations, negative results
    critique_kw = [
        "failure", "limitation", "negative", "impossib", "challenge",
        "pitfall", "critique", "problem with", "does not scale",
        "cannot", "when agents fail",
    ]
    if (failure_modes and len(failure_modes) >= 3) or \
       any(kw in meth for kw in critique_kw) or \
       any(kw in title for kw in ["failure", "pitfall", "limitation", "challenge", "cannot"]):
        types.add("critique")

    # Default: if nothing matched, classify based on best guess
    if not types:
        if "survey" in title or "review" in title:
            types.add("empirical")  # surveys are empirical aggregation
        else:
            types.add("system")  # most CS papers describe systems

    return types


# ---------------------------------------------------------------------------
# HDBSCAN sub-clustering within a pillar
# ---------------------------------------------------------------------------

def subcluster_pillar(paper_ids: list[int], embeddings: dict[int, np.ndarray],
                      target_k: int = 5) -> dict[int, int]:
    """K-means sub-clustering within a pillar for semantic diversity.

    Uses k-means rather than HDBSCAN because within-pillar embeddings are
    already dense (all assigned to same anchor by cosine similarity). HDBSCAN
    tends to find 1 cluster in this scenario. K-means with k=5 reliably
    produces the 3-5 sub-regions needed for semantic spread.

    Returns {paper_id: sub_cluster_id}.
    """
    from sklearn.cluster import KMeans

    valid_ids = [pid for pid in paper_ids if pid in embeddings]
    if len(valid_ids) < 20:
        return {pid: 0 for pid in paper_ids}

    X = np.array([embeddings[pid] for pid in valid_ids])

    # L2-normalize for cosine-like k-means
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1
    X_norm = X / norms

    # Adaptive k: min(target_k, n_papers // 15) but at least 3
    k = max(3, min(target_k, len(valid_ids) // 15))

    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_norm)

    result = {}
    for i, pid in enumerate(valid_ids):
        result[pid] = int(labels[i])

    # Papers without embeddings → largest sub-cluster
    from collections import Counter
    counts = Counter(labels)
    largest = counts.most_common(1)[0][0]
    for pid in paper_ids:
        if pid not in result:
            result[pid] = int(largest)

    return result


# ---------------------------------------------------------------------------
# Selection tiers
# ---------------------------------------------------------------------------

def select_surveys(papers: list[dict]) -> list[dict]:
    """Tier 1: Select 2 surveys — 1 classic (<2010), 1 modern (≥2020)."""
    selected = []
    survey_re = re.compile(r'\b(survey|review|overview|state.of.the.art)\b', re.I)

    survey_papers = [p for p in papers
                     if survey_re.search(p.get("title", ""))
                     and meets_citation_floor(p)
                     and has_verified_provenance(p)]

    # Classic survey: published before 2010, highest cited
    classics = sorted(
        [p for p in survey_papers if (p.get("year") or 9999) < 2010],
        key=lambda p: -(p.get("citation_count") or 0)
    )
    if classics:
        classics[0]["_tier"] = "survey"
        classics[0]["_rationale"] = "Classic survey (pre-2010, highest cited)"
        selected.append(classics[0])

    # Modern survey: published 2020+, highest cited
    moderns = sorted(
        [p for p in survey_papers if (p.get("year") or 0) >= 2020],
        key=lambda p: -(p.get("citation_count") or 0)
    )
    if moderns:
        moderns[0]["_tier"] = "survey"
        moderns[0]["_rationale"] = "Modern survey (2020+, highest cited)"
        selected.append(moderns[0])

    return selected


def select_landmarks(papers: list[dict], already: set[int]) -> list[dict]:
    """Tier 2: Top 5 by citation, spanning ≥2 decades.

    Prefers papers with known years for decade-span calculation.
    """
    candidates = sorted(
        [p for p in papers
         if p["id"] not in already
         and meets_citation_floor(p)
         and has_verified_provenance(p)],
        key=lambda p: -(p.get("citation_count") or 0)
    )

    if not candidates:
        return []

    selected = [candidates[0]]
    yr0 = candidates[0].get("year")
    decades = {yr0 // 10} if yr0 else set()

    for p in candidates[1:]:
        if len(selected) >= LANDMARK_PICKS:
            break
        yr = p.get("year")
        if yr:
            decades.add(yr // 10)
        selected.append(p)

    # If all from one decade, swap last with highest-cited from different decade
    if len(decades) <= 1 and len(selected) >= LANDMARK_PICKS:
        the_decade = list(decades)[0] if decades else None
        if the_decade is not None:
            for p in candidates:
                if p["id"] not in {s["id"] for s in selected}:
                    yr = p.get("year")
                    if yr and (yr // 10) != the_decade:
                        selected[-1] = p
                        break

    for p in selected:
        p["_tier"] = "landmark"
        p["_rationale"] = f"Top-cited ({p.get('citation_count', 0)} cites, {p.get('year', '?')})"

    return selected


def select_regional_temporal(papers: list[dict], already: set[int]) -> list[dict]:
    """Regional temporal: 2 per era (3 eras), highest-cited unselected.

    Papers with year=None are excluded from temporal selection entirely —
    they have no temporal signal and would pollute era-based picks.
    """
    selected = []

    for era_name, (lo, hi) in ERAS.items():
        era_papers = sorted(
            [p for p in papers
             if p["id"] not in already
             and p.get("year") is not None
             and lo <= p["year"] <= hi
             and meets_citation_floor(p)
             and has_verified_provenance(p)],
            key=lambda p: -(p.get("citation_count") or 0)
        )

        if len(era_papers) < ERA_MIN_PAPERS:
            continue  # exempt this era

        picked = 0
        for p in era_papers:
            if picked >= ERA_PICKS:
                break
            if p["id"] in already:
                continue
            p["_tier"] = "regional_temporal"
            p["_rationale"] = f"Era {era_name} ({lo}-{hi}), {p.get('citation_count', 0)} cites"
            selected.append(p)
            already.add(p["id"])
            picked += 1

    return selected


def select_regional_semantic(papers: list[dict], sub_clusters: dict[int, int],
                             already: set[int], target: int = REGIONAL_SEMANTIC) -> list[dict]:
    """Regional semantic: pick from distinct HDBSCAN sub-regions, round-robin."""
    # Group unselected papers by sub-cluster, sorted by citation within each
    by_sub = defaultdict(list)
    for p in papers:
        if p["id"] not in already and meets_citation_floor(p):
            sc = sub_clusters.get(p["id"], 0)
            by_sub[sc].append(p)

    for sc in by_sub:
        by_sub[sc].sort(key=lambda p: -(p.get("citation_count") or 0))

    # Round-robin across sub-clusters
    selected = []
    sub_ids = sorted(by_sub.keys(), key=lambda sc: -len(by_sub[sc]))
    pointers = {sc: 0 for sc in sub_ids}

    while len(selected) < target and any(pointers[sc] < len(by_sub[sc]) for sc in sub_ids):
        for sc in sub_ids:
            if len(selected) >= target:
                break
            while pointers[sc] < len(by_sub[sc]):
                p = by_sub[sc][pointers[sc]]
                pointers[sc] += 1
                if p["id"] not in already:
                    p["_tier"] = "regional_semantic"
                    p["_rationale"] = f"Sub-region {sc}, {p.get('citation_count', 0)} cites"
                    selected.append(p)
                    already.add(p["id"])
                    break

    return selected


# ---------------------------------------------------------------------------
# Constraint enforcement
# ---------------------------------------------------------------------------

def enforce_lost_canary(papers: list[dict], selected: list[dict],
                        already: set[int]) -> list[dict]:
    """Ensure ≥1 Lost Canary per pillar. Swap if needed."""
    additions = []

    # Check if any selected paper is a Lost Canary
    has_canary = any(
        (p.get("citation_count") or 0) > CANARY_CITATIONS and
        (p.get("modernity_score") or 1.0) < CANARY_MODERNITY
        for p in selected
    )

    if has_canary:
        return additions

    # Find best Lost Canary candidate not yet selected
    canaries = sorted(
        [p for p in papers
         if p["id"] not in already
         and (p.get("citation_count") or 0) > CANARY_CITATIONS
         and (p.get("modernity_score") is not None)
         and (p.get("modernity_score") or 1.0) < CANARY_MODERNITY],
        key=lambda p: -(p.get("citation_count") or 0)
    )

    # Fallback: papers without modernity score but classical and highly cited
    if not canaries:
        canaries = sorted(
            [p for p in papers
             if p["id"] not in already
             and (p.get("citation_count") or 0) > CANARY_CITATIONS
             and p.get("is_classical")
             and p.get("modernity_score") is None],
            key=lambda p: -(p.get("citation_count") or 0)
        )

    if canaries:
        p = canaries[0]
        p["_tier"] = "lost_canary"
        mod = p.get("modernity_score", "N/A")
        p["_rationale"] = f"Lost Canary: {p.get('citation_count', 0)} cites, modernity={mod}"
        additions.append(p)
        already.add(p["id"])

    return additions


def enforce_currency(papers: list[dict], selected: list[dict],
                     already: set[int]) -> list[dict]:
    """Ensure ≥2 papers from 2024-2026 per pillar."""
    additions = []

    current_count = sum(1 for p in selected if (p.get("year") or 0) >= CURRENCY_YEAR)
    needed = CURRENCY_MIN - current_count

    if needed <= 0:
        return additions

    recent = sorted(
        [p for p in papers
         if p["id"] not in already
         and (p.get("year") or 0) >= CURRENCY_YEAR],
        key=lambda p: -(p.get("citation_count") or 0)
    )

    for p in recent[:needed]:
        p["_tier"] = "currency"
        p["_rationale"] = f"Currency constraint ({p.get('year')}, {p.get('citation_count', 0)} cites)"
        additions.append(p)
        already.add(p["id"])

    return additions


def enforce_paradigm_diversity(papers: list[dict], selected: list[dict],
                               already: set[int]) -> list[dict]:
    """Ensure ≥1 per paradigm type (theoretical/empirical/system/critique)."""
    additions = []

    # What paradigm types are covered?
    covered = set()
    for p in selected:
        covered |= classify_paradigm(p)

    needed_types = {"theoretical", "empirical", "system", "critique"} - covered

    for ptype in needed_types:
        candidates = sorted(
            [p for p in papers
             if p["id"] not in already
             and ptype in classify_paradigm(p)],
            key=lambda p: -(p.get("citation_count") or 0)
        )
        if candidates:
            p = candidates[0]
            p["_tier"] = f"paradigm_{ptype}"
            p["_rationale"] = f"Paradigm diversity ({ptype}), {p.get('citation_count', 0)} cites"
            additions.append(p)
            already.add(p["id"])

    return additions


# ---------------------------------------------------------------------------
# Bridge paper detection
# ---------------------------------------------------------------------------

def detect_bridge_papers(papers: list[dict], embeddings: dict[int, np.ndarray],
                         relative_threshold: float = 0.97, min_pillars: int = 3,
                         min_citations: int = 50) -> list[dict]:
    """Find papers with high cosine similarity to ≥3 pillar anchor descriptions.

    Uses a RELATIVE threshold: a paper bridges to pillar X if its similarity
    to X's anchor is ≥ relative_threshold × its similarity to its own (best)
    anchor. At 0.97, only papers genuinely equidistant between multiple pillars
    qualify — papers like Malone & Crowston (coordination theory) or Wooldridge
    & Jennings (agent definitions) that span the field.

    Also requires min_citations to filter noise — bridge papers are by
    definition foundational works cited across sub-communities.
    """
    from pipeline.apis.llm import embed as embed_fn

    # Embed anchor descriptions
    anchor_texts = [c["description"] for c in GUIDED_CLUSTERS]
    anchor_vecs = np.array(embed_fn(anchor_texts))

    # Normalize anchors
    anchor_norms = np.linalg.norm(anchor_vecs, axis=1, keepdims=True)
    anchor_norms[anchor_norms == 0] = 1
    anchor_vecs = anchor_vecs / anchor_norms

    bridges = []
    for p in papers:
        if (p.get("citation_count") or 0) < min_citations:
            continue

        vec = embeddings.get(p["id"])
        if vec is None:
            continue

        v = vec / (np.linalg.norm(vec) or 1)
        sims = anchor_vecs @ v  # cosine similarities to all 16 anchors

        best_sim = sims.max()
        if best_sim <= 0:
            continue

        cutoff = best_sim * relative_threshold
        pillar_ids = [i for i, s in enumerate(sims) if s >= cutoff]

        if len(pillar_ids) >= min_pillars:
            bridges.append({
                "paper": p,
                "pillar_ids": pillar_ids,
                "pillar_labels": [GUIDED_CLUSTERS[i]["label"] for i in pillar_ids],
                "max_sim": float(best_sim),
                "n_pillars": len(pillar_ids),
            })

    bridges.sort(key=lambda b: (-b["n_pillars"], -(b["paper"].get("citation_count") or 0)))
    return bridges


# ---------------------------------------------------------------------------
# Per-pillar selection
# ---------------------------------------------------------------------------

def select_for_pillar(cluster_id: int, cluster_label: str,
                      papers: list[dict], embeddings: dict[int, np.ndarray]) -> dict:
    """Run full three-tier selection for one pillar."""
    already = set()
    result = {
        "cluster_id": cluster_id,
        "cluster_label": cluster_label,
        "total_papers": len(papers),
        "surveys": [],
        "landmarks": [],
        "regional_temporal": [],
        "regional_semantic": [],
        "constraints": [],  # lost canary, currency, paradigm additions
        "sub_cluster_count": 0,
    }

    # Tier 1: Surveys
    surveys = select_surveys(papers)
    result["surveys"] = surveys
    already.update(p["id"] for p in surveys)

    # Tier 2: Landmarks
    landmarks = select_landmarks(papers, already)
    result["landmarks"] = landmarks
    already.update(p["id"] for p in landmarks)

    # Sub-cluster for regional semantic selection
    paper_ids = [p["id"] for p in papers]
    sub_clusters = subcluster_pillar(paper_ids, embeddings)
    n_sub = len(set(sub_clusters.values()))
    result["sub_cluster_count"] = n_sub

    # Tier 3a: Regional temporal
    temporal = select_regional_temporal(papers, already)
    result["regional_temporal"] = temporal

    # Tier 3b: Regional semantic
    semantic = select_regional_semantic(papers, sub_clusters, already)
    result["regional_semantic"] = semantic

    # All selected so far
    all_selected = surveys + landmarks + temporal + semantic

    # Constraint enforcement
    canary_adds = enforce_lost_canary(papers, all_selected, already)
    currency_adds = enforce_currency(papers, all_selected + canary_adds, already)
    paradigm_adds = enforce_paradigm_diversity(
        papers, all_selected + canary_adds + currency_adds, already
    )
    result["constraints"] = canary_adds + currency_adds + paradigm_adds

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_selection(output_json: str | None = None, output_md: str | None = None):
    """Run the full reference selection algorithm."""
    print("=" * 70)
    print("  SUTRA — Reference Selection Algorithm")
    print("  Three-tier selection across 16 pillars")
    print("=" * 70)

    # Step 1: Load data
    print("\n1. Loading papers...")
    papers = load_papers()

    print("\n2. Loading embeddings from Azure AI Search...")
    embeddings = load_embeddings_dict()
    print(f"   {len(embeddings)} embeddings loaded")

    # Group by cluster
    by_cluster = defaultdict(list)
    for p in papers:
        by_cluster[p["cluster_id"]].append(p)

    # Step 2: Select per pillar
    print("\n3. Running per-pillar selection...")
    all_results = []
    all_selected_ids = set()
    grand_total = 0

    for cluster in GUIDED_CLUSTERS:
        cid = cluster["id"]
        clabel = cluster["label"]
        cpaps = by_cluster.get(cid, [])

        if not cpaps:
            print(f"   [{cid:2d}] {clabel}: NO PAPERS — skipping")
            continue

        result = select_for_pillar(cid, clabel, cpaps, embeddings)
        all_results.append(result)

        n_sel = (len(result["surveys"]) + len(result["landmarks"]) +
                 len(result["regional_temporal"]) + len(result["regional_semantic"]) +
                 len(result["constraints"]))
        grand_total += n_sel

        # Track globally selected IDs
        for tier_key in ["surveys", "landmarks", "regional_temporal", "regional_semantic", "constraints"]:
            for p in result[tier_key]:
                all_selected_ids.add(p["id"])

        print(f"   [{cid:2d}] {clabel}: {n_sel} selected "
              f"(S:{len(result['surveys'])} L:{len(result['landmarks'])} "
              f"T:{len(result['regional_temporal'])} Sem:{len(result['regional_semantic'])} "
              f"C:{len(result['constraints'])}) "
              f"| {result['sub_cluster_count']} sub-clusters "
              f"| {result['total_papers']} papers")

    # Step 3: Bridge papers
    print("\n4. Detecting bridge papers (≥3 pillars)...")
    bridges = detect_bridge_papers(papers, embeddings)
    print(f"   Found {len(bridges)} bridge papers")
    for b in bridges[:10]:
        print(f"     {b['n_pillars']} pillars | {b['paper']['title'][:60]}")

    # Step 4: Summary
    print("\n" + "=" * 70)
    print("  SELECTION SUMMARY")
    print("=" * 70)

    tier_counts = defaultdict(int)
    for r in all_results:
        tier_counts["surveys"] += len(r["surveys"])
        tier_counts["landmarks"] += len(r["landmarks"])
        tier_counts["regional_temporal"] += len(r["regional_temporal"])
        tier_counts["regional_semantic"] += len(r["regional_semantic"])
        tier_counts["constraints"] += len(r["constraints"])

    print(f"\n  Surveys:            {tier_counts['surveys']:4d}")
    print(f"  Landmarks:          {tier_counts['landmarks']:4d}")
    print(f"  Regional temporal:  {tier_counts['regional_temporal']:4d}")
    print(f"  Regional semantic:  {tier_counts['regional_semantic']:4d}")
    print(f"  Constraint adds:    {tier_counts['constraints']:4d}")
    print(f"  ─────────────────────────")
    print(f"  Total (with dupes): {grand_total:4d}")
    print(f"  Unique papers:      {len(all_selected_ids):4d}")
    print(f"  Bridge papers:      {len(bridges):4d}")
    bridge_in_selected = sum(1 for b in bridges if b["paper"]["id"] in all_selected_ids)
    print(f"  Bridges in selection: {bridge_in_selected:4d}")

    # Paradigm coverage across all selected
    all_paradigms = set()
    for r in all_results:
        for tier_key in ["surveys", "landmarks", "regional_temporal", "regional_semantic", "constraints"]:
            for p in r[tier_key]:
                all_paradigms |= classify_paradigm(p)
    print(f"\n  Paradigm types covered: {', '.join(sorted(all_paradigms))}")

    # Era coverage
    era_counts = defaultdict(int)
    for r in all_results:
        for tier_key in ["surveys", "landmarks", "regional_temporal", "regional_semantic", "constraints"]:
            for p in r[tier_key]:
                yr = p.get("year") or 0
                for era_name, (lo, hi) in ERAS.items():
                    if lo <= yr <= hi:
                        era_counts[era_name] += 1
                        break
    print(f"\n  Era distribution:")
    for era_name in ERAS:
        print(f"    {era_name:12s}: {era_counts[era_name]:4d}")

    # Step 5: Output
    if output_json:
        _write_json(all_results, bridges, output_json)
        print(f"\n  JSON written to: {output_json}")

    md_path = output_md or "/tmp/bibliography_selection.md"
    _write_markdown(all_results, bridges, md_path)
    print(f"  Markdown written to: {md_path}")

    return all_results, bridges


def _paper_to_dict(p: dict) -> dict:
    """Serialize a paper for JSON output (strip numpy, internal fields)."""
    return {
        "id": p["id"],
        "title": p.get("title", ""),
        "year": p.get("year"),
        "citation_count": p.get("citation_count", 0),
        "doi": p.get("doi"),
        "arxiv_id": p.get("arxiv_id"),
        "openalex_id": p.get("openalex_id"),
        "venue": p.get("venue", ""),
        "is_classical": p.get("is_classical", False),
        "modernity_score": p.get("modernity_score"),
        "pattern": p.get("pattern", ""),
        "grounding": p.get("grounding", ""),
        "tier": p.get("_tier", ""),
        "rationale": p.get("_rationale", ""),
        "paradigm_types": list(classify_paradigm(p)),
    }


def _write_json(results: list[dict], bridges: list[dict], path: str):
    """Write full selection to JSON."""
    output = {
        "meta": {
            "total_unique": len({p["id"]
                                 for r in results
                                 for k in ["surveys", "landmarks", "regional_temporal",
                                           "regional_semantic", "constraints"]
                                 for p in r[k]}),
            "pillars": len(results),
            "bridge_papers": len(bridges),
        },
        "pillars": [],
        "bridges": [],
    }

    for r in results:
        pillar = {
            "cluster_id": r["cluster_id"],
            "cluster_label": r["cluster_label"],
            "total_papers": r["total_papers"],
            "sub_cluster_count": r["sub_cluster_count"],
            "selections": {},
        }
        for tier_key in ["surveys", "landmarks", "regional_temporal",
                         "regional_semantic", "constraints"]:
            pillar["selections"][tier_key] = [_paper_to_dict(p) for p in r[tier_key]]
        output["pillars"].append(pillar)

    for b in bridges:
        output["bridges"].append({
            "paper": _paper_to_dict(b["paper"]),
            "pillar_ids": b["pillar_ids"],
            "pillar_labels": b["pillar_labels"],
            "n_pillars": b["n_pillars"],
        })

    with open(path, "w") as f:
        json.dump(output, f, indent=2, default=str)


def _write_markdown(results: list[dict], bridges: list[dict], path: str):
    """Write human-readable Markdown report."""
    lines = [
        "# Sutra Survey — Reference Selection Report",
        "",
        f"Generated by `pipeline/reference_selection.py`",
        "",
        "## Summary",
        "",
    ]

    total_unique = len({p["id"]
                        for r in results
                        for k in ["surveys", "landmarks", "regional_temporal",
                                  "regional_semantic", "constraints"]
                        for p in r[k]})
    lines.append(f"- **{total_unique}** unique papers selected across **{len(results)}** pillars")
    lines.append(f"- **{len(bridges)}** bridge papers (≥3 pillars)")
    lines.append("")

    # Per-pillar detail
    for r in results:
        cid = r["cluster_id"]
        lines.append(f"## Pillar {cid}: {r['cluster_label']}")
        lines.append(f"")
        lines.append(f"*{r['total_papers']} papers in cluster, "
                      f"{r['sub_cluster_count']} HDBSCAN sub-regions*")
        lines.append("")

        for tier_name, tier_key in [
            ("Surveys", "surveys"),
            ("Landmarks", "landmarks"),
            ("Regional — Temporal", "regional_temporal"),
            ("Regional — Semantic", "regional_semantic"),
            ("Constraint additions", "constraints"),
        ]:
            paps = r[tier_key]
            if not paps:
                continue
            lines.append(f"### {tier_name} ({len(paps)})")
            lines.append("")
            lines.append("| # | Year | Cites | Title | Rationale |")
            lines.append("|---|------|-------|-------|-----------|")
            for i, p in enumerate(paps, 1):
                yr = p.get("year", "?")
                cites = p.get("citation_count", 0)
                title = (p.get("title") or "")[:65]
                rat = p.get("_rationale", "")
                lines.append(f"| {i} | {yr} | {cites:,} | {title} | {rat} |")
            lines.append("")

    # Bridge papers
    if bridges:
        lines.append("## Bridge Papers")
        lines.append("")
        lines.append("Papers with high semantic similarity to ≥3 pillar anchors.")
        lines.append("")
        lines.append("| Pillars | Year | Cites | Title | Pillars Bridged |")
        lines.append("|---------|------|-------|-------|-----------------|")
        for b in bridges[:50]:
            p = b["paper"]
            yr = p.get("year", "?")
            cites = p.get("citation_count", 0)
            title = (p.get("title") or "")[:55]
            pillars = ", ".join(b["pillar_labels"][:4])
            if len(b["pillar_labels"]) > 4:
                pillars += f" +{len(b['pillar_labels'])-4}"
            lines.append(f"| {b['n_pillars']} | {yr} | {cites:,} | {title} | {pillars} |")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Sutra reference selection algorithm")
    parser.add_argument("--output", "-o", help="JSON output path")
    parser.add_argument("--markdown", "-m", help="Markdown report path")
    args = parser.parse_args()

    run_selection(output_json=args.output, output_md=args.markdown)


if __name__ == "__main__":
    main()
