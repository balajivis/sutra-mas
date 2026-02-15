#!/usr/bin/env python3
"""Cluster paper embeddings and export for Three.js visualization.

Two-level clustering:
  1. K-means on paper-level embeddings → high-level trends (10-15 clusters)
  2. K-means within each cluster → sub-trends (3-5 per cluster)

Dimensionality reduction:
  - UMAP to 3D for Three.js visualization

Cluster labeling:
  - LLM generates descriptive labels from top papers in each cluster

Output:
  - pipeline/data/clusters.json — full clustering results
  - pipeline/data/viz_threejs.json — Three.js-ready scene data

Usage:
    python3 -m pipeline.cluster [--k 12] [--sub-k 4] [--label]
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.npz")
META_FILE = os.path.join(DATA_DIR, "embeddings_meta.json")
CLUSTERS_FILE = os.path.join(DATA_DIR, "clusters.json")
VIZ_FILE = os.path.join(DATA_DIR, "viz_threejs.json")


def aggregate_paper_embeddings(embeddings: np.ndarray, meta: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """Average chunk embeddings per paper to get one vector per paper.

    Returns (paper_embeddings, paper_meta) where paper_meta has one entry per paper.
    """
    paper_chunks: dict[int, list[int]] = {}
    paper_info: dict[int, dict] = {}

    for i, m in enumerate(meta):
        pid = m["paper_id"]
        if pid not in paper_chunks:
            paper_chunks[pid] = []
            paper_info[pid] = {
                "paper_id": pid,
                "title": m.get("title", ""),
                "year": m.get("year"),
                "citation_count": m.get("citation_count", 0),
                "is_classical": m.get("is_classical", False),
                "venue": m.get("venue"),
                "coordination_pattern": m.get("coordination_pattern", "none"),
                "chunk_count": 0,
            }
        paper_chunks[pid].append(i)
        paper_info[pid]["chunk_count"] += 1

    paper_ids = sorted(paper_chunks.keys())
    paper_embeddings = np.zeros((len(paper_ids), embeddings.shape[1]), dtype=np.float32)
    paper_meta = []

    for j, pid in enumerate(paper_ids):
        indices = paper_chunks[pid]
        paper_embeddings[j] = embeddings[indices].mean(axis=0)
        paper_meta.append(paper_info[pid])

    return paper_embeddings, paper_meta


def run_kmeans(embeddings: np.ndarray, k: int) -> np.ndarray:
    """K-means clustering. Returns cluster labels."""
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    return km.fit_predict(embeddings)


def run_umap_3d(embeddings: np.ndarray) -> np.ndarray:
    """UMAP reduction to 3D for visualization."""
    try:
        from umap import UMAP
        reducer = UMAP(n_components=3, random_state=42, n_neighbors=15, min_dist=0.1)
        return reducer.fit_transform(embeddings)
    except ImportError:
        # Fallback to PCA if UMAP not installed
        print("  WARNING: umap-learn not installed, falling back to PCA")
        from sklearn.decomposition import PCA
        pca = PCA(n_components=3, random_state=42)
        return pca.fit_transform(embeddings)


def label_clusters_with_llm(paper_meta: list[dict], labels: np.ndarray, k: int) -> dict[int, str]:
    """Use LLM to generate descriptive labels for ALL clusters in one shot.

    Sending all cluster summaries together ensures the LLM produces
    differentiated, non-generic names (e.g., not 5 variants of
    "Multi-Agent Coordination").
    """
    from pipeline.apis.llm import gpt_chat_json

    # Build a summary of each cluster
    cluster_summaries = []
    for c in range(k):
        members = [paper_meta[i] for i in range(len(labels)) if labels[i] == c]
        if not members:
            continue

        members.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
        top = members[:6]
        patterns = {}
        eras = {"classical": 0, "modern": 0}
        for m in members:
            p = m.get("coordination_pattern", "none")
            patterns[p] = patterns.get(p, 0) + 1
            y = m.get("year") or 2020
            if y < 2010:
                eras["classical"] += 1
            else:
                eras["modern"] += 1

        paper_list = "; ".join(
            f"{m['title'][:60]} ({m.get('year', '?')})"
            for m in top
        )
        pattern_dist = ", ".join(f"{p}: {n}" for p, n in sorted(patterns.items(), key=lambda x: -x[1])[:4])

        cluster_summaries.append({
            "cluster_id": c,
            "paper_count": len(members),
            "top_papers": paper_list,
            "patterns": pattern_dist,
            "era_split": f"{eras['classical']} classical, {eras['modern']} modern",
        })

    if not cluster_summaries:
        return {c: f"Cluster {c}" for c in range(k)}

    clusters_text = "\n\n".join(
        f"CLUSTER {cs['cluster_id']} ({cs['paper_count']} papers, {cs['era_split']}):\n"
        f"  Top papers: {cs['top_papers']}\n"
        f"  Patterns: {cs['patterns']}"
        for cs in cluster_summaries
    )

    prompt = f"""You are labeling {len(cluster_summaries)} clusters from a survey of Multi-Agent Systems (MAS) research spanning 1980-2026.

These clusters were produced by embedding and clustering ~1000 papers. Your job: give each cluster a SHORT, SPECIFIC, DIFFERENTIATED label (3-6 words).

Rules:
- Each label must be UNIQUE — no two clusters can have similar names
- Be SPECIFIC to what distinguishes that cluster, not generic ("Multi-Agent Systems" is too vague)
- Prefer concrete concepts: name the coordination pattern, the application domain, or the theoretical contribution
- Classical clusters should reference the era/concepts (e.g., "BDI Architecture & Intentions", "Contract Net Negotiation")
- Modern clusters should reference LLM-specific aspects (e.g., "LLM Agent Tool Use", "Prompt-Based Role Assignment")

{clusters_text}

Return a JSON object mapping cluster_id (as string) to label:
{{"0": "label for cluster 0", "1": "label for cluster 1", ...}}"""

    try:
        result = gpt_chat_json(
            system="You produce concise, differentiated research cluster labels. Return valid JSON only.",
            user_message=prompt,
            model="gpt-5-nano",
            max_tokens=2048,
        )
        cluster_labels = {}
        for cs in cluster_summaries:
            cid = cs["cluster_id"]
            label = result.get(str(cid), result.get(cid, f"Cluster {cid}"))
            cluster_labels[cid] = label
            print(f"    Cluster {cid} ({cs['paper_count']} papers): {label}")
        return cluster_labels
    except Exception as e:
        print(f"    Cluster labeling failed ({e}), using fallback names")
        return {cs["cluster_id"]: f"Cluster {cs['cluster_id']}" for cs in cluster_summaries}


def sub_cluster(embeddings: np.ndarray, paper_meta: list[dict],
                labels: np.ndarray, k: int, sub_k: int,
                use_llm: bool = False) -> dict:
    """Run sub-clustering within each top-level cluster."""
    sub_clusters = {}

    for c in range(k):
        mask = labels == c
        count = mask.sum()
        if count < sub_k * 2:
            # Too few papers for meaningful sub-clustering
            sub_clusters[c] = {"sub_labels": [0] * count, "sub_k": 1, "sub_cluster_labels": {0: "All"}}
            continue

        actual_sub_k = min(sub_k, count // 2)
        cluster_embeddings = embeddings[mask]
        sub_labels = run_kmeans(cluster_embeddings, actual_sub_k)

        sub_cluster_labels = {}
        if use_llm:
            cluster_meta = [paper_meta[i] for i in range(len(labels)) if labels[i] == c]
            sub_cluster_labels = label_clusters_with_llm(cluster_meta, sub_labels, actual_sub_k)
        else:
            for sc in range(actual_sub_k):
                sub_cluster_labels[sc] = f"Sub-{sc}"

        sub_clusters[c] = {
            "sub_labels": sub_labels.tolist(),
            "sub_k": actual_sub_k,
            "sub_cluster_labels": sub_cluster_labels,
        }

    return sub_clusters


def build_viz_json(paper_meta: list[dict], labels: np.ndarray,
                   coords_3d: np.ndarray, cluster_labels: dict,
                   sub_clusters: dict) -> dict:
    """Build Three.js-ready JSON."""
    papers = []
    cluster_idx_within = {}  # Track sub-cluster assignment per paper

    for c_id, sc_data in sub_clusters.items():
        cluster_idx_within[c_id] = iter(sc_data["sub_labels"])

    for i, meta in enumerate(paper_meta):
        c = int(labels[i])
        sc_iter = cluster_idx_within.get(c)
        sc = next(sc_iter, 0) if sc_iter else 0
        sc_label = sub_clusters.get(c, {}).get("sub_cluster_labels", {}).get(sc, "")

        papers.append({
            "id": meta["paper_id"],
            "title": meta["title"],
            "year": meta.get("year"),
            "citations": meta.get("citation_count", 0),
            "is_classical": meta.get("is_classical", False),
            "pattern": meta.get("coordination_pattern", "none"),
            "venue": meta.get("venue"),
            "position": [round(float(coords_3d[i][0]), 4),
                         round(float(coords_3d[i][1]), 4),
                         round(float(coords_3d[i][2]), 4)],
            "cluster": c,
            "cluster_label": cluster_labels.get(c, f"Cluster {c}"),
            "sub_cluster": sc,
            "sub_cluster_label": sc_label,
        })

    # Cluster summaries
    clusters = []
    for c in range(max(labels) + 1):
        mask = labels == c
        if not mask.any():
            continue
        centroid = coords_3d[mask].mean(axis=0)
        member_count = int(mask.sum())
        sc_data = sub_clusters.get(c, {})

        sub_cluster_list = []
        for sc_id, sc_name in sc_data.get("sub_cluster_labels", {}).items():
            sc_member_count = sum(1 for sl in sc_data.get("sub_labels", []) if sl == sc_id)
            sub_cluster_list.append({
                "id": sc_id,
                "label": sc_name,
                "paper_count": sc_member_count,
            })

        clusters.append({
            "id": c,
            "label": cluster_labels.get(c, f"Cluster {c}"),
            "centroid": [round(float(centroid[0]), 4),
                         round(float(centroid[1]), 4),
                         round(float(centroid[2]), 4)],
            "paper_count": member_count,
            "sub_clusters": sub_cluster_list,
        })

    # Era distribution for the visualization
    classical_count = sum(1 for p in papers if p["is_classical"])

    return {
        "metadata": {
            "total_papers": len(papers),
            "total_clusters": len(clusters),
            "classical_papers": classical_count,
            "modern_papers": len(papers) - classical_count,
            "generated_by": "sutra/pipeline/cluster.py",
        },
        "papers": papers,
        "clusters": clusters,
    }


def main():
    parser = argparse.ArgumentParser(description="Cluster paper embeddings for Three.js visualization")
    parser.add_argument("--k", type=int, default=12, help="Number of top-level clusters")
    parser.add_argument("--sub-k", type=int, default=4, help="Number of sub-clusters per cluster")
    parser.add_argument("--label", action="store_true", help="Use LLM to generate cluster labels")
    parser.add_argument("--label-sub", action="store_true", help="Also label sub-clusters with LLM")
    args = parser.parse_args()

    print("=" * 60)
    print("  CLUSTER — Knowledge Map Builder")
    print("=" * 60)

    # Load embeddings
    if not os.path.exists(EMBEDDINGS_FILE):
        print(f"  ERROR: {EMBEDDINGS_FILE} not found. Run embed_chunks.py first.")
        sys.exit(1)

    data = np.load(EMBEDDINGS_FILE)
    embeddings = data["embeddings"]

    with open(META_FILE) as f:
        meta = json.load(f)

    print(f"  Loaded {len(embeddings)} chunk embeddings from {len({m['paper_id'] for m in meta})} papers")

    # Aggregate to paper level
    paper_embeddings, paper_meta = aggregate_paper_embeddings(embeddings, meta)
    print(f"  Aggregated to {len(paper_embeddings)} paper-level embeddings")

    if len(paper_embeddings) < args.k * 2:
        print(f"  WARNING: Only {len(paper_embeddings)} papers, reducing k from {args.k} to {len(paper_embeddings) // 3}")
        args.k = max(2, len(paper_embeddings) // 3)

    # Top-level clustering
    print(f"\n  Running K-means (k={args.k})...")
    labels = run_kmeans(paper_embeddings, args.k)

    for c in range(args.k):
        count = (labels == c).sum()
        if count > 0:
            print(f"    Cluster {c}: {count} papers")

    # Cluster labeling
    cluster_labels = {}
    if args.label:
        print(f"\n  Labeling clusters with LLM...")
        cluster_labels = label_clusters_with_llm(paper_meta, labels, args.k)
    else:
        for c in range(args.k):
            members = [paper_meta[i] for i in range(len(labels)) if labels[i] == c]
            # Simple label from dominant pattern
            patterns = {}
            for m in members:
                p = m.get("coordination_pattern", "none")
                patterns[p] = patterns.get(p, 0) + 1
            dominant = max(patterns, key=patterns.get) if patterns else "mixed"
            cluster_labels[c] = f"{dominant} ({len(members)})"

    # Sub-clustering
    print(f"\n  Running sub-clustering (sub_k={args.sub_k})...")
    sc_data = sub_cluster(paper_embeddings, paper_meta, labels, args.k, args.sub_k,
                          use_llm=args.label_sub)

    # UMAP 3D
    print(f"\n  Running UMAP → 3D...")
    coords_3d = run_umap_3d(paper_embeddings)

    # Build visualization JSON
    viz = build_viz_json(paper_meta, labels, coords_3d, cluster_labels, sc_data)

    # Save
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(VIZ_FILE, "w") as f:
        json.dump(viz, f, indent=2)
    print(f"\n  Three.js data: {VIZ_FILE}")

    # Also save a detailed clusters file with paper lists
    clusters_detail = {}
    for c in range(args.k):
        members = [paper_meta[i] for i in range(len(labels)) if labels[i] == c]
        members.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
        clusters_detail[cluster_labels.get(c, f"Cluster {c}")] = {
            "cluster_id": c,
            "paper_count": len(members),
            "top_papers": [
                {"title": m["title"], "year": m.get("year"), "citations": m.get("citation_count", 0),
                 "pattern": m.get("coordination_pattern")}
                for m in members[:10]
            ],
        }

    with open(CLUSTERS_FILE, "w") as f:
        json.dump(clusters_detail, f, indent=2)
    print(f"  Cluster details: {CLUSTERS_FILE}")

    # Summary
    print(f"\n  Summary:")
    print(f"    Papers:       {viz['metadata']['total_papers']}")
    print(f"    Clusters:     {viz['metadata']['total_clusters']}")
    print(f"    Classical:    {viz['metadata']['classical_papers']}")
    print(f"    Modern:       {viz['metadata']['modern_papers']}")


if __name__ == "__main__":
    main()
