#!/usr/bin/env python3
"""Agent 8: Clustering — Periodic batch clustering for the assembly line.

Pulls embeddings from Azure AI Search (the single source of truth), runs
HDBSCAN for natural cluster discovery, projects to 2D with UMAP (fallback
TSNE), generates cluster labels via Claude Opus with MAS taxonomy guidance,
and writes results to paper_clusters + cluster_meta tables.

Azure AI Search stores the 1536-dim text-embedding-3-small vectors pushed
by search_index.py. This agent reuses those embeddings — no re-embedding.
Papers without embeddings in the index are skipped (run search_index.py first).

Pipeline architecture:
    1. Fetch analyzed papers from PostgreSQL (relevance >= 3)
    2. Pull embeddings from Azure AI Search (no API calls to OpenAI)
    3. HDBSCAN for natural cluster count discovery
    4. UMAP 2D projection (fallback TSNE)
    5. Claude Opus cluster labeling with MAS taxonomy guidance
    6. Write to paper_clusters + cluster_meta tables

Usage:
    python3 -m pipeline.assembly.clustering
    python3 -m pipeline.assembly.clustering --once --no-label
    python3 -m pipeline.assembly.clustering --interval 300
    python3 -m pipeline.assembly.clustering --min-cluster 15

Dependencies:
    pip install scikit-learn numpy umap-learn hdbscan azure-search-documents
"""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, count_by_status
from pipeline.apis.llm import embed, chat_json


# ---------------------------------------------------------------------------
# 16 Guided Cluster Anchors — aligned with MAS subfields (informed by AAMAS tracks)
# ---------------------------------------------------------------------------
GUIDED_CLUSTERS = [
    {
        "id": 0,
        "label": "Shared Medium Coordination",
        "description": (
            "Blackboard architecture, shared workspace coordination, knowledge sources, "
            "control shell scheduling, incremental problem solving, Nii 1986, Hearsay-II, "
            "shared memory, shared context management, opportunistic reasoning, "
            "shared state in LLM agents, LangGraph shared state, "
            "Redis shared context, shared scratchpad, collaborative workspace, "
            "centralized knowledge store, shared artifact coordination, "
            "stigmergy, indirect communication, environment-mediated coordination, "
            "Grasse 1959, pheromone, document-driven coordination, "
            "MetaGPT SOPs, artifact-based coordination, shared artifacts, "
            "standard operating procedures, tuple spaces, Linda, "
            "environment as communication medium, trace-based coordination, "
            "shared document editing, collaborative writing, "
            "implicit coordination, emergent coordination through artifacts, "
            "workflow documents, shared logs, asynchronous coordination"
        ),
    },
    {
        "id": 1,
        "label": "Contract Net and Task Allocation",
        "description": (
            "Contract net protocol, task allocation, announce bid award, auction-based allocation, "
            "market-based coordination, Smith 1980, TRACONET, marginal cost bidding, "
            "task routing, agent dispatch, dynamic task assignment, CNET, "
            "combinatorial auctions, winner determination, "
            "LLM task routing, agent selection, capability-based dispatch, "
            "multi-agent task distribution, workload balancing, "
            "which agent handles which task, agent specialization routing"
        ),
    },
    {
        "id": 2,
        "label": "Organizational Design and Team Structures",
        "description": (
            "Organizational paradigms, hierarchies, holarchies, coalitions, teams, "
            "role-based organization, AGR model, MOISE, electronic institutions, "
            "Horling and Lesser 2004, Ferber and Gutknecht Aalaadin, "
            "organizational norms, agent roles, crew-based coordination, "
            "flat vs hierarchical topologies, scaling agent teams, "
            "CrewAI roles, agent team composition, role assignment, "
            "multi-agent team formation, organizational structure for LLM agents, "
            "supervisor worker topology, manager agent, team scaling"
        ),
    },
    {
        "id": 3,
        "label": "Distributed Planning, Problem Solving, and Teamwork",
        "description": (
            "Distributed problem solving, partial global planning, GPGP, "
            "functionally accurate cooperative systems, FA/C, result sharing, "
            "Durfee and Lesser 1983, distributed planning, task decomposition, "
            "distributed constraint satisfaction, DCSP, DPOP, "
            "coordination mechanisms, dependency management, Malone and Crowston, "
            "multi-agent planning, collaborative problem solving, "
            "LLM agent planning, decompose and conquer, sub-task planning, "
            "hierarchical task decomposition, plan synthesis, plan merging, "
            "joint intentions, SharedPlans, mutual belief, commitment, "
            "Cohen and Levesque 1990, Grosz and Kraus 1996, Tambe STEAM, "
            "joint persistent goals, team plans, obligation to inform, "
            "collaborative plans, group plans, teamwork models, "
            "collective intentionality, joint activity, "
            "shared goals, commitment protocols, team coordination, "
            "consensus building, collective action, cooperative task completion"
        ),
    },
    {
        "id": 4,
        "label": "Agent Communication Languages and Protocols",
        "description": (
            "FIPA ACL, KQML, speech acts, performatives, agent communication language, "
            "inform request query propose, message passing, interaction protocols, "
            "communicative acts, semantic content, ontology, "
            "MCP model context protocol, A2A agent-to-agent protocol, "
            "agent interoperability, protocol standards, ANP, "
            "inter-agent communication, message format, message schema, "
            "agent-to-agent messaging, structured messages between agents, "
            "conversation protocols, dialogue protocols, "
            "typed messages, semantic messaging, agent API design, "
            "protocol specification, communication middleware"
        ),
    },
    {
        "id": 5,
        "label": "Argumentation and Structured Debate",
        "description": (
            "Argumentation frameworks, Dung 1995, abstract argumentation, "
            "structured debate, generator critic, attack support relations, "
            "persuasion dialogue, deliberation, multi-agent debate, "
            "argument-based negotiation, formal argumentation, "
            "LLM debate, can agents really debate, multi-agent discussion, "
            "agent disagreement resolution, critique and revision, "
            "self-critique, peer review by agents, adversarial collaboration, "
            "dialectical reasoning, pro and con analysis, "
            "quality improvement through debate, verification through argument"
        ),
    },
    {
        "id": 6,
        "label": "Negotiation, Game Theory, and Economic Paradigms",
        "description": (
            "Automated negotiation, game theory, mechanism design, "
            "Nash equilibrium, social welfare, VCG, bargaining, "
            "Rosenschein and Zlotkin, cooperative games, non-cooperative games, "
            "strategic interaction, utility maximization, Pareto optimality, "
            "agent-mediated negotiation, preference elicitation, social choice, "
            "resource allocation, competitive agents, incentive design, "
            "agent economics, pricing mechanisms, market mechanisms, "
            "strategic agents, rational agents, payoff optimization, "
            "coalition formation, coalition value, Shapley value, "
            "core allocation, stable coalition, coalition structure generation"
        ),
    },
    {
        "id": 7,
        "label": "BDI and Cognitive Agent Architectures",
        "description": (
            "BDI architecture, beliefs desires intentions, Rao and Georgeff 1995, "
            "AgentSpeak, Jason, 2APL, JACK, Jadex, cognitive agents, "
            "deliberative agents, practical reasoning, means-end reasoning, "
            "plan library, goal management, intention reconsideration, "
            "reactive vs deliberative, hybrid architectures, InteRRaP, subsumption, "
            "cognitive architecture for LLM agents, agent reasoning, "
            "agent internal state, mental models, agent beliefs, "
            "goal-directed behavior, autonomous reasoning, "
            "agent decision making, reflection and introspection"
        ),
    },
    {
        "id": 8,
        "label": "Human-Agent Interaction and HITL",
        "description": (
            "Human-agent interaction, human-in-the-loop, mixed initiative, "
            "adjustable autonomy, human-agent teaming, supervisory control, "
            "shared authority, trust calibration, transparency, explainability, "
            "human oversight, approval workflows, escalation, "
            "human as agent peer, co-intelligence, human-AI collaboration, "
            "interactive AI, user feedback, agent alignment, "
            "human preferences, human evaluation of agents, "
            "conversational agents, chatbot interaction, dialogue systems, "
            "user intent, natural language interface, assistant agents"
        ),
    },
    {
        "id": 9,
        "label": "Trust, Reputation, and Norms",
        "description": (
            "Trust models, reputation systems, computational trust, "
            "social norms, normative multi-agent systems, sanctions, "
            "institutional norms, social laws, governance, "
            "witness reputation, direct trust, certified reputation, "
            "norm enforcement, norm emergence, social control, "
            "ethical agents, responsible AI, agent safety, "
            "guardrails, content filtering, alignment, "
            "agent reliability, trustworthy agents"
        ),
    },
    {
        "id": 10,
        "label": "Multi-Agent Engineering: Methodologies, Frameworks, and Platforms",
        "description": (
            "Agent-oriented software engineering, AOSE, Prometheus methodology, "
            "GAIA methodology, Tropos, MaSE, agent platforms, JADE, FIPA compliance, "
            "Jennings 2000 on agent-based SE, agent above object, "
            "formal verification of MAS, model checking, testing agents, "
            "agent development tools, agent programming languages, "
            "software agents, agent middleware, agent infrastructure, "
            "agent deployment, agent lifecycle, agent management, "
            "multi-agent platform, agent runtime, agent SDK, "
            "LLM agent framework, LangGraph, CrewAI, AutoGen, MetaGPT, ChatDev, "
            "agentic AI framework, agent orchestration framework, "
            "multi-agent LLM system design, agent builder platform, "
            "tool use framework, function calling infrastructure, "
            "agent hosting, prompt chaining, agent pipeline, workflow engine for agents"
        ),
    },
    {
        "id": 11,
        "label": "Multi-Agent Robotics and Embodied Teams",
        "description": (
            "Multi-robot systems, robotic teams, robot coordination, "
            "formation control, multi-robot task allocation MRTA, "
            "robot swarms, distributed robotics, RoboCup, "
            "sensor networks, embodied agents, physical coordination, "
            "multi-UAV, multi-UGV, cooperative robotics, "
            "robot communication, spatial coordination, "
            "flocking, consensus in networks, distributed control, "
            "multi-vehicle coordination, autonomous vehicles"
        ),
    },
    {
        "id": 12,
        "label": "Evaluation Benchmarks and Failure Analysis",
        "description": (
            "Agent evaluation, failure analysis, benchmarking, "
            "failure modes of multi-agent systems, Cemri et al 14 failure modes, "
            "scaling agent systems, Kim et al Google DeepMind, "
            "error amplification, agent safety, reliability, "
            "GAIA benchmark, SWE-bench, HumanEval, "
            "multi-agent evaluation metrics, coordination overhead, "
            "token efficiency, cost analysis, agent observability, "
            "agent performance measurement, quality assessment, "
            "error rates, success rates, agent comparison studies"
        ),
    },
    {
        "id": 13,
        "label": "Memory and Context Management",
        "description": (
            "Agent memory, memory architecture, episodic memory, working memory, "
            "long-term memory, short-term memory, memory retrieval, "
            "cross-session context, conversation memory, entity memory, "
            "MemGPT, memory-augmented agents, context window management, "
            "knowledge retention, experience replay, memory consolidation, "
            "retrieval augmented generation, RAG, vector memory, "
            "memory sharing between agents, collective memory, "
            "organizational memory, corporate memory, institutional memory, "
            "context carryover, state persistence, agent state management, "
            "memory-based reasoning, recall and recognition in agents"
        ),
    },
    {
        "id": 14,
        "label": "Learning and Adaptation",
        "description": (
            "Multi-agent reinforcement learning, MARL, cooperative learning, "
            "independent learners, joint action learning, opponent modeling, "
            "self-play, emergent communication, learned coordination, "
            "Markov games, stochastic games, Dec-POMDP, "
            "policy gradient multi-agent, QMIX, MAPPO, MADDPG, "
            "curriculum learning for agents, transfer learning agents, "
            "adaptive agents, online learning, continual learning, "
            "co-evolution, evolutionary multi-agent systems, "
            "learning to communicate, emergent language, "
            "reward shaping, intrinsic motivation, credit assignment in teams, "
            "swarm intelligence, ant colony optimization, particle swarm optimization"
        ),
    },
    {
        "id": 15,
        "label": "Modeling and Simulating Artificial Societies",
        "description": (
            "Agent-based modeling, agent-based simulation, artificial societies, "
            "social simulation, MABS, computational social science, "
            "Epstein and Axtell Sugarscape, Growing Artificial Societies, "
            "Schelling segregation model, opinion dynamics, "
            "generative agents, simulated social behavior, "
            "agent-based computational economics, ACE, "
            "emergent social phenomena, social influence, contagion, "
            "population dynamics, evolutionary dynamics, "
            "ODD protocol, individual-based model, "
            "virtual society, digital twin society, "
            "social dilemma simulation, cooperation evolution, "
            "artificial life, complex adaptive systems"
        ),
    },
]


def build_embedding_text(paper: dict) -> str:
    """Build structured text for embedding that captures MAS-relevant dimensions.

    Instead of just the summary, we embed a structured document that places
    papers near others with similar coordination patterns, theoretical roots,
    and classical concepts. This dramatically improves clustering quality.

    Used by both clustering.py (fallback) and search_index.py (primary).
    """
    parts = []

    # Title anchors the embedding
    title = paper.get("title") or ""
    if title:
        parts.append(f"Title: {title}")

    # Pattern is the strongest clustering signal
    pattern = paper.get("pattern") or ""
    if pattern and pattern not in ("none", "null", ""):
        parts.append(f"Coordination Pattern: {pattern.replace('_', ' ')}")

    # Theoretical grounding separates formal vs empirical work
    grounding = paper.get("grounding") or ""
    if grounding and grounding not in ("none", "null", ""):
        parts.append(f"Theoretical Grounding: {grounding}")

    # Classical concepts are the key discriminator for MAS subdisciplines
    concepts = paper.get("concepts")
    if concepts:
        try:
            cs = json.loads(concepts) if isinstance(concepts, str) else concepts
            if isinstance(cs, list) and cs:
                parts.append(f"Classical Concepts: {', '.join(str(c) for c in cs[:8])}")
        except (json.JSONDecodeError, TypeError):
            pass

    # Missing concepts distinguish papers that SHOULD cite classical work
    missing = paper.get("concepts_missing")
    if missing:
        try:
            ms = json.loads(missing) if isinstance(missing, str) else missing
            if isinstance(ms, list) and ms:
                parts.append(f"Missing Classical Concepts: {', '.join(str(m) for m in ms[:5])}")
        except (json.JSONDecodeError, TypeError):
            pass

    # Summary provides broader context
    summary = paper.get("summary") or ""
    if summary:
        parts.append(f"Contribution: {summary}")

    return "\n".join(parts)


def ensure_tables():
    """Create clustering tables if needed."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS paper_clusters (
                    paper_id INTEGER PRIMARY KEY,
                    cluster_id INTEGER NOT NULL,
                    cluster_label TEXT,
                    x FLOAT NOT NULL,
                    y FLOAT NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS cluster_meta (
                    cluster_id INTEGER PRIMARY KEY,
                    label TEXT,
                    description TEXT,
                    paper_count INTEGER,
                    top_concepts JSONB,
                    top_patterns JSONB,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS clustering_runs (
                    id SERIAL PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    papers_clustered INTEGER DEFAULT 0,
                    num_clusters INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                );
            """)


def fetch_papers(min_relevance: int = 3) -> list[dict]:
    """Fetch analyzed papers with key_contribution_summary.

    Filters to relevance >= min_relevance to exclude noise papers
    (philosophy, tangential CS, etc.) that pollute cluster quality.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, year, citation_count, is_classical,
                       analysis->>'key_contribution_summary' as summary,
                       analysis->>'coordination_pattern' as pattern,
                       analysis->'classical_concepts' as concepts,
                       analysis->>'theoretical_grounding' as grounding,
                       analysis->'classical_concepts_missing' as concepts_missing
                FROM papers
                WHERE analysis IS NOT NULL
                  AND analysis->>'key_contribution_summary' IS NOT NULL
                  AND pipeline_status NOT IN ('archived')
                  AND (relevance_score IS NULL OR relevance_score >= %s)
                ORDER BY id
            """, (min_relevance,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def pull_embeddings_from_search() -> dict[int, list[float]]:
    """Pull embeddings from Azure AI Search — the single source of truth.

    Azure AI Search stores the 1536-dim vectors pushed by search_index.py.
    We page through ALL documents (batch of 1000) requesting only id + embedding.
    """
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    endpoint = os.environ.get("SUTRA_SEARCH_ENDPOINT", "")
    key = os.environ.get("SUTRA_SEARCH_KEY", "")
    index = os.environ.get("SUTRA_SEARCH_INDEX", "sutra-papers")

    if not endpoint or not key:
        print("  Warning: SUTRA_SEARCH_ENDPOINT/KEY not set, falling back to direct embedding")
        return {}

    try:
        client = SearchClient(endpoint, index, AzureKeyCredential(key))
        embeddings: dict[int, list[float]] = {}

        # Iterate ALL documents — SDK auto-pages through results
        # top=50000 ensures we get all documents (max 100K allowed)
        results = client.search(
            search_text="*",
            select=["id", "embedding"],
            top=50000,
        )
        scanned = 0
        for doc in results:
            scanned += 1
            vec = doc.get("embedding")
            if vec and len(vec) > 0:
                embeddings[int(doc["id"])] = vec
            if scanned % 1000 == 0:
                print(f"\r  Scanning... {scanned} docs, {len(embeddings)} with embeddings", end="", flush=True)

        print(f"\r  Pulled {len(embeddings)} embeddings from Azure AI Search ({scanned} docs total)")
        return embeddings
    except Exception as e:
        print(f"  Warning: Could not pull from Azure AI Search: {e}")
        return {}


def embed_papers_fallback(papers: list[dict], batch_size: int = 16) -> np.ndarray:
    """Fallback: embed papers directly via Azure OpenAI API using structured text.

    Used only when Azure AI Search index is not yet built.
    """
    texts = [build_embedding_text(p)[:2000] for p in papers]
    all_vecs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vecs = embed(batch)
        all_vecs.extend(vecs)
        if i + batch_size < len(texts):
            time.sleep(0.5)
        sys.stdout.write(f"\r  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")
        sys.stdout.flush()
    print()
    return np.array(all_vecs)


def load_embeddings(papers: list[dict]) -> np.ndarray:
    """Load embeddings for papers — pulls from Azure AI Search first, falls back to API.

    Returns (N, 1536) array aligned with the papers list. Papers without
    embeddings from either source are excluded (returned array may be shorter).
    """
    search_vecs = pull_embeddings_from_search()

    if search_vecs:
        # Use Azure AI Search embeddings (no API cost)
        all_vecs = []
        included = []
        for p in papers:
            vec = search_vecs.get(p["id"])
            if vec:
                all_vecs.append(vec)
                included.append(p)

        missing = len(papers) - len(included)
        if missing > 0:
            print(f"  {missing} papers not in search index (skipped)")

        # Update papers list in-place to match included
        papers.clear()
        papers.extend(included)
        return np.array(all_vecs)

    # Fallback: embed directly (costly but works without search index)
    print("  Falling back to direct Azure OpenAI embedding...")
    return embed_papers_fallback(papers)


def _assign_noise_to_nearest(X: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Assign HDBSCAN noise points (label -1) to their nearest cluster centroid.

    HDBSCAN may label some points as noise (-1). For our visualization we want
    every paper to belong to a cluster, so we assign noise to nearest centroid.
    """
    from sklearn.metrics.pairwise import cosine_distances

    noise_mask = labels == -1
    n_noise = noise_mask.sum()
    if n_noise == 0:
        return labels

    # Compute cluster centroids (excluding noise)
    unique = sorted(set(labels) - {-1})
    if not unique:
        # Everything is noise — fall back to single cluster
        return np.zeros_like(labels)

    centroids = np.array([X[labels == c].mean(axis=0) for c in unique])
    noise_points = X[noise_mask]

    # Find nearest centroid for each noise point
    dists = cosine_distances(noise_points, centroids)
    nearest = dists.argmin(axis=1)

    result = labels.copy()
    noise_indices = np.where(noise_mask)[0]
    for i, idx in enumerate(noise_indices):
        result[idx] = unique[nearest[i]]

    print(f"  Assigned {n_noise} noise points to nearest clusters")
    return result


def _repel_clusters(coords: np.ndarray, labels: np.ndarray, strength: float = 8.0) -> np.ndarray:
    """Push cluster centroids apart so they don't overlap in the visualization.

    For each cluster, compute centroid. Then apply repulsion between all centroid
    pairs (inverse-square). Translate each point by its cluster's displacement.
    """
    unique_labels = np.unique(labels)
    k = len(unique_labels)
    if k < 2:
        return coords

    # Compute centroids
    centroids = np.zeros((k, 2))
    for i, c in enumerate(unique_labels):
        mask = labels == c
        centroids[i] = coords[mask].mean(axis=0)

    # Repulsion: push centroids apart (inverse-distance, capped)
    displacements = np.zeros_like(centroids)
    for i in range(k):
        for j in range(i + 1, k):
            diff = centroids[i] - centroids[j]
            dist = np.linalg.norm(diff)
            if dist < 1e-6:
                diff = np.random.randn(2) * 0.1
                dist = np.linalg.norm(diff)
            # Repulsion force: stronger when closer
            force = strength / (dist + 0.5)
            direction = diff / dist
            displacements[i] += direction * force
            displacements[j] -= direction * force

    # Apply displacement to all points
    result = coords.copy()
    for i, c in enumerate(unique_labels):
        mask = labels == c
        result[mask] += displacements[i]

    return result


def cluster_and_project(X: np.ndarray, min_cluster_size: int = 15) -> tuple[np.ndarray, np.ndarray, int]:
    """Run HDBSCAN and project to 2D. Returns (labels, coords_2d, k).

    HDBSCAN discovers the natural number of clusters instead of forcing k.
    This handles the varying density of MAS subdisciplines much better than k-means.

    Uses PCA to reduce from 1536 dims to 50 before HDBSCAN — density-based
    methods struggle in very high dimensions (curse of dimensionality).
    """
    import hdbscan
    from sklearn.decomposition import PCA

    # PCA reduction — HDBSCAN needs lower dimensions to find density structure
    n_components = min(50, X.shape[0] - 1, X.shape[1])
    print(f"  PCA: {X.shape[1]} → {n_components} dims...", flush=True)
    X_reduced = PCA(n_components=n_components, random_state=42).fit_transform(X)

    print(f"  HDBSCAN (min_cluster_size={min_cluster_size})...", flush=True)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=5,
        metric="euclidean",
        cluster_selection_method="eom",  # excess of mass — better for varying density
        cluster_selection_epsilon=0.0,
    )
    raw_labels = clusterer.fit_predict(X_reduced)

    n_clusters = len(set(raw_labels) - {-1})
    n_noise = (raw_labels == -1).sum()
    print(f"  HDBSCAN found {n_clusters} clusters, {n_noise} noise points", flush=True)

    # Assign noise points to nearest cluster (using reduced dims)
    labels = _assign_noise_to_nearest(X_reduced, raw_labels)

    # Renumber clusters to be contiguous 0..k-1
    unique_labels = sorted(set(labels))
    label_map = {old: new for new, old in enumerate(unique_labels)}
    labels = np.array([label_map[l] for l in labels])
    k = len(unique_labels)

    # 2D projection — tuned for maximum cluster separation
    print("  Projecting to 2D...", flush=True)
    try:
        import umap
        reducer = umap.UMAP(
            n_components=2,
            random_state=42,
            n_neighbors=10,      # lower = tighter local clusters, more separation
            min_dist=0.8,        # higher = more even spacing within clusters
            spread=4.0,          # higher = more spread between clusters
            metric="cosine",
            repulsion_strength=2.0,  # push dissimilar points further apart
        )
        coords = reducer.fit_transform(X)
        print("  Used UMAP (n_neighbors=10, min_dist=0.8, spread=4.0, repulsion=2.0)", flush=True)
    except ImportError:
        from sklearn.manifold import TSNE
        reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(X) - 1))
        coords = reducer.fit_transform(X)
        print("  Used TSNE (install umap-learn for better projections)", flush=True)

    # Post-UMAP: repel overlapping clusters apart
    print("  Repelling overlapping clusters...", flush=True)
    coords = _repel_clusters(coords, labels, strength=8.0)

    # Normalize to [0, 100] range for consistent frontend rendering
    for dim in range(2):
        col = coords[:, dim]
        mn, mx = col.min(), col.max()
        if mx - mn > 0:
            coords[:, dim] = (col - mn) / (mx - mn) * 100

    return labels, coords, k


def cluster_guided(X: np.ndarray, papers: list[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    """Guided clustering: assign papers to 16 predefined MAS subfield anchors.

    1. Embed anchor descriptions using same embedding model
    2. Compute cosine similarity between each paper and all 16 anchors
    3. Assign to highest-similarity anchor
    4. UMAP for 2D projection
    5. Returns (labels, coords_2d, k=16)
    """
    from sklearn.metrics.pairwise import cosine_similarity

    k = len(GUIDED_CLUSTERS)
    print(f"  Guided clustering: {k} target subfields", flush=True)

    # 1. Embed anchor descriptions
    anchor_texts = [c["description"] for c in GUIDED_CLUSTERS]
    print("  Embedding anchor descriptions...", flush=True)
    anchor_vecs = np.array(embed(anchor_texts))
    print(f"  Anchor embeddings: {anchor_vecs.shape}", flush=True)

    # 2. Cosine similarity: (N_papers, 16)
    print("  Computing paper-anchor similarities...", flush=True)
    sims = cosine_similarity(X, anchor_vecs)

    # 3. Assign each paper to highest-similarity anchor
    labels = sims.argmax(axis=1)

    # Report distribution
    for cid in range(k):
        count = int((labels == cid).sum())
        print(f"    [{cid:2d}] {GUIDED_CLUSTERS[cid]['label']:45s} — {count} papers", flush=True)

    # Check for empty clusters
    empty = [GUIDED_CLUSTERS[i]["label"] for i in range(k) if (labels == i).sum() == 0]
    if empty:
        print(f"  Warning: {len(empty)} empty clusters: {empty}", flush=True)

    # 4. UMAP 2D projection
    print("  Projecting to 2D (UMAP)...", flush=True)
    try:
        import umap
        reducer = umap.UMAP(
            n_components=2,
            random_state=42,
            n_neighbors=15,
            min_dist=0.5,
            spread=3.0,
            metric="cosine",
            repulsion_strength=1.5,
        )
        coords = reducer.fit_transform(X)
        print("  Used UMAP", flush=True)
    except ImportError:
        from sklearn.manifold import TSNE
        reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(X) - 1))
        coords = reducer.fit_transform(X)
        print("  Used TSNE (install umap-learn for better projections)", flush=True)

    # Post-UMAP: repel overlapping clusters
    print("  Repelling overlapping clusters...", flush=True)
    coords = _repel_clusters(coords, labels, strength=8.0)

    # Normalize to [0, 100]
    for dim in range(2):
        col = coords[:, dim]
        mn, mx = col.min(), col.max()
        if mx - mn > 0:
            coords[:, dim] = (col - mn) / (mx - mn) * 100

    return labels, coords, k


def generate_labels_guided(papers: list[dict], labels: np.ndarray, k: int) -> list[dict]:
    """Generate cluster metadata for guided clusters.

    Uses the predefined labels from GUIDED_CLUSTERS, enriched with
    actual paper statistics (top concepts, patterns, year range).
    Optionally refines labels via LLM if paper distribution suggests a better name.
    """
    cluster_info = []
    for cid in range(k):
        mask = labels == cid
        cluster_papers = [p for p, m in zip(papers, mask) if m]
        count = int(mask.sum())

        patterns = {}
        concepts = []
        for p in cluster_papers:
            pat = p.get("pattern") or "none"
            patterns[pat] = patterns.get(pat, 0) + 1
            if p.get("concepts"):
                try:
                    cs = json.loads(p["concepts"]) if isinstance(p["concepts"], str) else p["concepts"]
                    if isinstance(cs, list):
                        concepts.extend(cs[:3])
                except (json.JSONDecodeError, TypeError):
                    pass

        top_patterns = sorted(patterns.items(), key=lambda x: -x[1])[:5]
        top_concepts = list(dict.fromkeys(concepts))[:10]

        years = [p.get("year") for p in cluster_papers if p.get("year")]
        year_range = f"{min(years)}-{max(years)}" if years else "?"

        cluster_info.append({
            "cluster_id": cid,
            "count": count,
            "label": GUIDED_CLUSTERS[cid]["label"],
            "description": GUIDED_CLUSTERS[cid]["description"],
            "top_patterns": top_patterns,
            "top_concepts": top_concepts,
            "year_range": year_range,
        })

    return cluster_info


MAS_TAXONOMY_GUIDANCE = """
You are labeling paper clusters for a Multi-Agent Systems (MAS) survey spanning
1980-2026, from classical AI/distributed systems to modern LLM agent frameworks.

The canonical MAS subdisciplines you should draw labels from include:

COORDINATION & COMMUNICATION:
- Agent Communication Languages (KQML, FIPA-ACL, speech acts, performatives)
- Coordination Mechanisms (partial global planning, GPGP, SharedPlans, teamwork)
- Negotiation & Argumentation (bargaining, persuasion, argumentation frameworks)
- Contract Net & Task Allocation (CNET, auctions, market-based allocation)

AGENT ARCHITECTURES:
- BDI & Cognitive Agents (beliefs-desires-intentions, AgentSpeak, Jason, 2APL)
- Reactive & Hybrid Architectures (subsumption, layered, InteRRaP)
- Agent-Oriented Software Engineering (AOSE, Prometheus, GAIA, Tropos)

ORGANIZATIONAL & SOCIAL:
- Organizational Models (AGR, MOISE, electronic institutions, roles)
- Norms & Governance (normative MAS, social laws, sanctions, trust)
- Social Simulation (opinion dynamics, cultural evolution, ABM)

MULTI-AGENT LEARNING & GAME THEORY:
- Multi-Agent Reinforcement Learning (MARL, cooperative, competitive)
- Mechanism Design & Game Theory (VCG, social welfare, Nash)
- Swarm Intelligence (ant colony, particle swarm, stigmergy)

KNOWLEDGE & REASONING:
- Blackboard Systems (shared knowledge, incremental problem solving)
- Ontologies & Semantic Web (agent-based knowledge management)
- Planning & Scheduling (distributed planning, joint intention)

MODERN LLM AGENTS:
- LLM Agent Frameworks (LangGraph, CrewAI, AutoGen, multi-agent LLM systems)
- Retrieval-Augmented Generation (RAG, knowledge-grounded generation)
- Tool Use & Function Calling (ReAct, tool-augmented LLM agents)
- Evaluation & Benchmarking (agent eval, failure analysis, safety)
- Agent Protocols (MCP, A2A, modern interoperability)

Each label should be a recognized MAS subdiscipline name (3-5 words).
Do NOT use generic labels like "AI Systems" or "Multi-Agent Research".
Each label must be specific enough to distinguish it from the others.
"""


def generate_labels(papers: list[dict], labels: np.ndarray, k: int) -> list[dict]:
    """Generate cluster labels via Claude Opus with MAS taxonomy guidance."""
    cluster_info = []
    for cid in range(k):
        mask = labels == cid
        cluster_papers = [p for p, m in zip(papers, mask) if m]
        patterns = {}
        concepts = []
        groundings = {}
        for p in cluster_papers:
            pat = p.get("pattern") or "none"
            patterns[pat] = patterns.get(pat, 0) + 1
            gr = p.get("grounding") or "none"
            groundings[gr] = groundings.get(gr, 0) + 1
            if p.get("concepts"):
                try:
                    cs = json.loads(p["concepts"]) if isinstance(p["concepts"], str) else p["concepts"]
                    if isinstance(cs, list):
                        concepts.extend(cs[:3])
                except (json.JSONDecodeError, TypeError):
                    pass

        top_patterns = sorted(patterns.items(), key=lambda x: -x[1])[:5]
        top_concepts = list(dict.fromkeys(concepts))[:12]
        top_groundings = sorted(groundings.items(), key=lambda x: -x[1])[:3]

        # Top 5 paper titles for LLM context (mix of classical + modern)
        classical = sorted([p for p in cluster_papers if p.get("is_classical")],
                           key=lambda p: -(p.get("citation_count") or 0))[:3]
        modern = sorted([p for p in cluster_papers if not p.get("is_classical")],
                        key=lambda p: -(p.get("citation_count") or 0))[:3]
        top_papers = classical + modern
        title_list = [
            f"- {p['title']} ({p.get('year', '?')}, {p.get('citation_count', 0)} cites, "
            f"{'classical' if p.get('is_classical') else 'modern'})"
            for p in top_papers
        ]

        # Year range
        years = [p.get("year") for p in cluster_papers if p.get("year")]
        year_range = f"{min(years)}-{max(years)}" if years else "?"

        cluster_info.append({
            "cluster_id": cid,
            "count": int(mask.sum()),
            "top_patterns": top_patterns,
            "top_concepts": top_concepts,
            "top_groundings": top_groundings,
            "top_titles": title_list,
            "year_range": year_range,
        })

    # Build prompt with rich context
    prompt = "Label the following paper clusters from a MAS research corpus.\n\n"
    for ci in cluster_info:
        prompt += f"Cluster {ci['cluster_id']} ({ci['count']} papers, {ci['year_range']}):\n"
        prompt += f"  Coordination patterns: {ci['top_patterns']}\n"
        prompt += f"  Theoretical groundings: {ci['top_groundings']}\n"
        prompt += f"  Classical concepts: {ci['top_concepts'][:8]}\n"
        prompt += f"  Representative papers:\n"
        prompt += "\n".join(f"    {t}" for t in ci["top_titles"]) + "\n\n"

    prompt += (
        "For each cluster, provide:\n"
        "- label: A specific MAS subdiscipline name (3-5 words) from the taxonomy above\n"
        "- description: One sentence explaining what unifies this cluster\n\n"
        'Return JSON array: [{"id": 0, "label": "...", "description": "..."}]'
    )

    try:
        result = chat_json(
            MAS_TAXONOMY_GUIDANCE,
            prompt,
            model="claude-opus-4-6",
            max_tokens=2048,
        )
        if isinstance(result, list):
            for entry in result:
                cid = entry.get("id", -1)
                if 0 <= cid < len(cluster_info):
                    cluster_info[cid]["label"] = entry.get("label", f"Cluster {cid}")
                    cluster_info[cid]["description"] = entry.get("description", "")
            print(f"  Labeled {len(result)} clusters via Claude Opus", flush=True)
    except Exception as e:
        print(f"  Warning: LLM labeling failed: {e}")
        for ci in cluster_info:
            top_pat = ci["top_patterns"][0][0] if ci["top_patterns"] else "mixed"
            ci["label"] = f"{top_pat} ({ci['count']})"
            ci["description"] = ""

    return cluster_info


def write_results(papers: list[dict], labels: np.ndarray, coords: np.ndarray, cluster_info: list[dict]):
    """Write clustering results to DB (full replace)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clear old data
            cur.execute("DELETE FROM paper_clusters")
            cur.execute("DELETE FROM cluster_meta")

            # Insert paper clusters (deduplicate by paper_id — keep first)
            seen_ids = set()
            for i, paper in enumerate(papers):
                pid = paper["id"]
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                ci = cluster_info[int(labels[i])]
                cur.execute(
                    "INSERT INTO paper_clusters (paper_id, cluster_id, cluster_label, x, y) VALUES (%s, %s, %s, %s, %s)",
                    (pid, int(labels[i]), ci.get("label", ""), float(coords[i, 0]), float(coords[i, 1])),
                )

            # Insert cluster metadata
            for ci in cluster_info:
                cur.execute(
                    """INSERT INTO cluster_meta (cluster_id, label, description, paper_count, top_concepts, top_patterns)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        ci["cluster_id"],
                        ci.get("label", f"Cluster {ci['cluster_id']}"),
                        ci.get("description", ""),
                        ci["count"],
                        json.dumps(ci["top_concepts"][:10]),
                        json.dumps([p[0] for p in ci["top_patterns"]]),
                    ),
                )

    print(f"  Wrote {len(papers)} paper assignments + {len(cluster_info)} cluster metadata entries")


def run_clustering(min_cluster_size: int = 15, generate_llm_labels: bool = True, mode: str = "guided"):
    """Full clustering pipeline. mode='guided' (16 subfields) or 'hdbscan' (auto-discover)."""
    print(f"\n  [8] Starting clustering run (mode={mode})...", flush=True)
    ensure_tables()

    # Record run start
    run_id = None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO clustering_runs (status) VALUES ('running') RETURNING id"
            )
            run_id = cur.fetchone()[0]

    try:
        # 1. Fetch papers (relevance >= 3 to filter noise)
        papers = fetch_papers(min_relevance=3)
        print(f"  [8] {len(papers)} analyzed papers with summaries (relevance >= 3)", flush=True)
        if len(papers) < 10:
            print("  [8] Too few papers for meaningful clustering. Skipping.", flush=True)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE clustering_runs SET status='skipped', completed_at=NOW() WHERE id=%s",
                        (run_id,),
                    )
            return

        # 2. Load embeddings (from Azure AI Search, no API cost)
        print("  [8] Loading embeddings...", flush=True)
        X = load_embeddings(papers)
        print(f"  [8] {len(papers)} papers with embeddings", flush=True)

        # 3. Clustering
        if mode == "guided":
            labels, coords, k = cluster_guided(X, papers)
            print(f"  [8] Guided: {k} subfield clusters", flush=True)
            cluster_info = generate_labels_guided(papers, labels, k)
        else:
            labels, coords, k = cluster_and_project(X, min_cluster_size=min_cluster_size)
            print(f"  [8] HDBSCAN found {k} natural clusters", flush=True)
            if generate_llm_labels:
                print("  [8] Generating cluster labels via Claude Opus...", flush=True)
                cluster_info = generate_labels(papers, labels, k)
            else:
                cluster_info = [
                    {"cluster_id": i, "count": int((labels == i).sum()), "label": f"Cluster {i}",
                     "description": "", "top_patterns": [], "top_concepts": []}
                    for i in range(k)
                ]

        # 4. Write to DB
        write_results(papers, labels, coords, cluster_info)

        # Mark run complete
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE clustering_runs SET status='completed', completed_at=NOW(), "
                    "papers_clustered=%s, num_clusters=%s WHERE id=%s",
                    (len(papers), k, run_id),
                )

        # Summary
        print(f"\n  [8] Cluster summary:", flush=True)
        for ci in sorted(cluster_info, key=lambda c: -c["count"]):
            print(f"    [{ci['cluster_id']}] {ci.get('label', '?'):45s} — {ci['count']} papers", flush=True)
        print(f"\n  [8] Done. {len(papers)} papers → {k} clusters.", flush=True)

    except Exception as e:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE clustering_runs SET status='failed', completed_at=NOW() WHERE id=%s",
                    (run_id,),
                )
        raise


def main():
    parser = argparse.ArgumentParser(description="Agent 8: Clustering (batch, periodic)")
    parser.add_argument("--mode", choices=["guided", "hdbscan"], default="guided",
                        help="Clustering mode: 'guided' (16 MAS subfields) or 'hdbscan' (auto-discover)")
    parser.add_argument("--min-cluster", type=int, default=15,
                        help="HDBSCAN min_cluster_size (default: 15, only for hdbscan mode)")
    parser.add_argument("--label", action="store_true", help="Generate LLM cluster labels (hdbscan mode)")
    parser.add_argument("--no-label", action="store_true", help="Skip LLM labeling (hdbscan mode)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=600, help="Seconds between runs (default 600)")
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("  AGENT 8: CLUSTERING", flush=True)
    print("  Assembly Line — Station 8 (batch)", flush=True)
    print("=" * 60, flush=True)
    print(f"  Mode:        {args.mode} ({'16 MAS subfields' if args.mode == 'guided' else 'HDBSCAN auto-discover'})", flush=True)
    print(f"  Embeddings:  text-embedding-3-small (1536 dims)", flush=True)
    if args.mode == "hdbscan":
        print(f"  HDBSCAN:     min_cluster_size={args.min_cluster}", flush=True)
        print(f"  Labels:      {'Claude Opus (MAS taxonomy)' if not args.no_label else 'disabled'}", flush=True)
    print(f"  Interval:    {'once' if args.once else f'every {args.interval}s'}", flush=True)
    print(f"  Status:      {count_by_status()}", flush=True)

    gen_labels = not args.no_label

    if args.once:
        run_clustering(min_cluster_size=args.min_cluster, generate_llm_labels=gen_labels, mode=args.mode)
    else:
        run_num = 0
        while True:
            run_num += 1
            try:
                run_clustering(min_cluster_size=args.min_cluster, generate_llm_labels=gen_labels, mode=args.mode)
            except Exception as e:
                print(f"  [8] Error in run {run_num}: {e}", flush=True)
            print(f"  [8] Sleeping {args.interval}s until next run...", flush=True)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
