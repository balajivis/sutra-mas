#!/usr/bin/env python3
"""Push sutra papers + embeddings to Azure AI Search.

Creates a 'sutra-papers' index with hybrid search (keyword + vector) and
semantic ranking. One document per paper with rich filterable metadata.

Requires a dedicated Azure AI Search service for sutra (not shared with Kapi).
Set SUTRA_SEARCH_ENDPOINT and SUTRA_SEARCH_KEY in your .env file.

Usage:
    python3 -m pipeline.search_index                # Create index + push all papers
    python3 -m pipeline.search_index --recreate      # Drop and recreate index
    python3 -m pipeline.search_index --query "contract net"  # Test search
    python3 -m pipeline.search_index --stats         # Show index stats
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.assembly.db import get_conn

# Load .env
for _env_path in [
    os.path.join(os.path.dirname(__file__), "../experiments/.env"),
    os.path.join(os.path.dirname(__file__), ".env"),
    ".env",
    "experiments/.env",
]:
    _env_path = os.path.abspath(_env_path)
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()
        break

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

# --- Config ---

SEARCH_ENDPOINT = os.environ.get("SUTRA_SEARCH_ENDPOINT", "")
SEARCH_KEY = os.environ.get("SUTRA_SEARCH_KEY", "")
INDEX_NAME = os.environ.get("SUTRA_SEARCH_INDEX", "sutra-papers")

EMBED_DIM = 1536


def _get_index_client() -> SearchIndexClient:
    return SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(SEARCH_KEY))


def _get_search_client() -> SearchClient:
    return SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(SEARCH_KEY))


# --- Index Schema ---

def create_index(recreate: bool = False):
    """Create the sutra-papers index with vector + semantic search."""
    client = _get_index_client()

    if recreate:
        try:
            client.delete_index(INDEX_NAME)
            print(f"  Deleted existing index '{INDEX_NAME}'")
        except Exception:
            pass

    fields = [
        # Key
        SimpleField(name="id", type=SearchFieldDataType.String,
                    key=True, filterable=True, sortable=True),

        # Paper metadata
        SearchableField(name="title", type=SearchFieldDataType.String,
                        analyzer_name="en.microsoft"),
        SimpleField(name="year", type=SearchFieldDataType.Int32,
                    filterable=True, sortable=True, facetable=True),
        SearchableField(name="abstract", type=SearchFieldDataType.String,
                        analyzer_name="en.microsoft"),
        SearchableField(name="venue", type=SearchFieldDataType.String,
                        filterable=True, facetable=True),
        SimpleField(name="citation_count", type=SearchFieldDataType.Int32,
                    filterable=True, sortable=True),
        SimpleField(name="arxiv_id", type=SearchFieldDataType.String,
                    filterable=True),
        SimpleField(name="doi", type=SearchFieldDataType.String,
                    filterable=True),
        SimpleField(name="is_classical", type=SearchFieldDataType.Boolean,
                    filterable=True, facetable=True),

        # Analysis fields (from Agent 3b)
        SearchableField(name="key_contribution", type=SearchFieldDataType.String,
                        analyzer_name="en.microsoft"),
        SearchableField(name="unique_contribution", type=SearchFieldDataType.String),
        SearchableField(name="methodology", type=SearchFieldDataType.String),
        SearchableField(name="key_results", type=SearchFieldDataType.String),
        SimpleField(name="coordination_pattern", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),
        SimpleField(name="theoretical_grounding", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),
        SearchableField(name="classical_concepts", type=SearchFieldDataType.String),
        SearchableField(name="modern_mapping", type=SearchFieldDataType.String),
        SearchableField(name="classical_concepts_missing", type=SearchFieldDataType.String),

        # Clustering (from cluster.py)
        SimpleField(name="cluster_id", type=SearchFieldDataType.Int32,
                    filterable=True, facetable=True),
        SimpleField(name="cluster_label", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),
        SimpleField(name="sub_cluster_id", type=SearchFieldDataType.Int32,
                    filterable=True, facetable=True),
        SimpleField(name="sub_cluster_label", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),

        # Reproduction (from Agents 5 + 6)
        SimpleField(name="has_code", type=SearchFieldDataType.Boolean,
                    filterable=True, facetable=True),
        SimpleField(name="repo_url", type=SearchFieldDataType.String,
                    filterable=True),
        SimpleField(name="reproduction_feasibility", type=SearchFieldDataType.Int32,
                    filterable=True, sortable=True),

        # Score fields
        SimpleField(name="relevance_score", type=SearchFieldDataType.Int32,
                    filterable=True, sortable=True),
        SimpleField(name="modernity_score", type=SearchFieldDataType.Double,
                    filterable=True, sortable=True),

        # Vector — hidden=False so clustering can pull embeddings back
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            hidden=False,
            vector_search_dimensions=EMBED_DIM,
            vector_search_profile_name="sutra-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="sutra-hnsw"),
        ],
        profiles=[
            VectorSearchProfile(
                name="sutra-vector-profile",
                algorithm_configuration_name="sutra-hnsw",
            ),
        ],
    )

    semantic_config = SemanticConfiguration(
        name="sutra-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[
                SemanticField(field_name="key_contribution"),
                SemanticField(field_name="abstract"),
                SemanticField(field_name="unique_contribution"),
            ],
            keywords_fields=[
                SemanticField(field_name="coordination_pattern"),
                SemanticField(field_name="classical_concepts"),
            ],
        ),
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
    )

    client.create_or_update_index(index)
    print(f"  Index '{INDEX_NAME}' created/updated at {SEARCH_ENDPOINT}")


# --- Data Loading ---

def _build_embedding_text(analysis: dict, title: str) -> str:
    """Build structured text for embedding — same logic as clustering.py.

    This structured format places papers near others with similar coordination
    patterns, theoretical roots, and classical concepts, producing much better
    clusters than embedding just the summary alone.
    """
    parts = []
    if title:
        parts.append(f"Title: {title}")

    pattern = analysis.get("coordination_pattern") or ""
    if pattern and pattern not in ("none", "null"):
        parts.append(f"Coordination Pattern: {pattern.replace('_', ' ')}")

    grounding = analysis.get("theoretical_grounding") or ""
    if grounding and grounding not in ("none", "null"):
        parts.append(f"Theoretical Grounding: {grounding}")

    concepts = analysis.get("classical_concepts")
    if concepts:
        if isinstance(concepts, str):
            try:
                concepts = json.loads(concepts)
            except (json.JSONDecodeError, TypeError):
                concepts = None
        if isinstance(concepts, list) and concepts:
            parts.append(f"Classical Concepts: {', '.join(str(c) for c in concepts[:8])}")

    missing = analysis.get("classical_concepts_missing")
    if missing:
        if isinstance(missing, str):
            try:
                missing = json.loads(missing)
            except (json.JSONDecodeError, TypeError):
                missing = None
        if isinstance(missing, list) and missing:
            parts.append(f"Missing Classical Concepts: {', '.join(str(m) for m in missing[:5])}")

    summary = analysis.get("key_contribution_summary") or ""
    if summary:
        parts.append(f"Contribution: {summary}")

    return "\n".join(parts)


def generate_embeddings(papers: list[dict], batch_size: int = 16) -> dict[int, list[float]]:
    """Generate embeddings for papers using structured MAS-aware text.

    Uses Azure OpenAI text-embedding-3-small. Embeds a structured document
    (title + pattern + grounding + concepts + summary) instead of just the
    summary. These get pushed to Azure AI Search as the single source of truth
    — Agent 8 pulls them back for clustering/UMAP without re-embedding.
    """
    from pipeline.apis.llm import embed as embed_text
    import time as _time

    to_embed = []
    for p in papers:
        analysis = p.get("analysis")
        if not isinstance(analysis, dict):
            continue
        if not analysis.get("key_contribution_summary"):
            continue
        text = _build_embedding_text(analysis, p.get("title", ""))
        if text:
            to_embed.append((p["id"], text))

    if not to_embed:
        print("  No papers with summaries to embed")
        return {}

    result: dict[int, list[float]] = {}
    texts = [text[:2000] for _, text in to_embed]
    ids = [pid for pid, _ in to_embed]

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]

        # Retry with backoff for rate limits
        for attempt in range(5):
            try:
                vecs = embed_text(batch_texts)
                break
            except Exception as e:
                if "429" in str(e) or "RateLimit" in str(e):
                    wait = 2 ** attempt
                    print(f"\n  Rate limited, waiting {wait}s (attempt {attempt + 1}/5)...", flush=True)
                    _time.sleep(wait)
                else:
                    raise
        else:
            print(f"\n  Failed to embed batch at index {i} after 5 retries, skipping")
            continue

        for pid, vec in zip(batch_ids, vecs):
            result[pid] = vec
        if i + batch_size < len(texts):
            _time.sleep(0.5)
        print(f"\r  Embedded {min(i + batch_size, len(texts))}/{len(texts)} papers", end="", flush=True)
    print()

    return result


def load_cluster_assignments() -> dict[int, dict]:
    """Load cluster assignments from paper_clusters + cluster_meta tables."""
    assignments = {}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pc.paper_id, pc.cluster_id, pc.cluster_label,
                           cm.label as meta_label
                    FROM paper_clusters pc
                    LEFT JOIN cluster_meta cm ON cm.cluster_id = pc.cluster_id
                """)
                for row in cur.fetchall():
                    assignments[row[0]] = {
                        "cluster_id": row[1],
                        "cluster_label": row[3] or row[2] or "",
                        "sub_cluster_id": None,
                        "sub_cluster_label": "",
                    }
        print(f"  Loaded {len(assignments)} cluster assignments from DB")
    except Exception as e:
        print(f"  Warning: Could not load clusters: {e}")
    return assignments


def fetch_papers() -> list[dict]:
    """Fetch all non-archived papers from DB."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, year, abstract, venue, citation_count,
                          arxiv_id, doi, is_classical, analysis,
                          relevance_score, modernity_score,
                          has_code, repo_url, reproduction_feasibility,
                          pipeline_status
                   FROM papers
                   WHERE pipeline_status NOT IN ('archived', 'collected', 'filtering')
                   ORDER BY id"""
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _to_str(val, default: str = "") -> str:
    """Coerce any value to a string — prevents StartArray errors in Azure Search."""
    if val is None:
        return default
    if isinstance(val, (list, tuple)):
        return ", ".join(str(v) for v in val)
    if isinstance(val, dict):
        return json.dumps(val)
    return str(val)


def paper_to_document(paper: dict, embedding: list[float] | None,
                      cluster: dict | None) -> dict:
    """Convert a paper row to an Azure Search document."""
    analysis = paper.get("analysis")
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {}
    analysis = analysis or {}

    doc = {
        "id": str(paper["id"]),
        "title": _to_str(paper.get("title")),
        "year": paper.get("year"),
        "abstract": _to_str(paper.get("abstract"))[:8000],
        "venue": _to_str(paper.get("venue")) or None,
        "citation_count": paper.get("citation_count") or 0,
        "arxiv_id": _to_str(paper.get("arxiv_id")) or None,
        "doi": _to_str(paper.get("doi")) or None,
        "is_classical": bool(paper.get("is_classical", False)),

        # Analysis — all coerced to str to prevent array/object leaking through
        "key_contribution": _to_str(analysis.get("key_contribution_summary")),
        "unique_contribution": _to_str(analysis.get("unique_contribution")),
        "methodology": _to_str(analysis.get("methodology")),
        "key_results": _to_str(analysis.get("key_results")),
        "coordination_pattern": _to_str(analysis.get("coordination_pattern"), "none"),
        "theoretical_grounding": _to_str(analysis.get("theoretical_grounding")),
        "classical_concepts": _to_str(analysis.get("classical_concepts")),
        "modern_mapping": _to_str(analysis.get("modern_mapping")),
        "classical_concepts_missing": _to_str(analysis.get("classical_concepts_missing")),

        # Scores
        "relevance_score": paper.get("relevance_score"),
        "modernity_score": float(paper["modernity_score"]) if paper.get("modernity_score") else None,

        # Reproduction
        "has_code": bool(paper.get("has_code", False)),
        "repo_url": _to_str(paper.get("repo_url")) or None,
        "reproduction_feasibility": paper.get("reproduction_feasibility"),
    }

    # Clustering
    if cluster:
        doc["cluster_id"] = cluster.get("cluster_id")
        doc["cluster_label"] = cluster.get("cluster_label", "")
        doc["sub_cluster_id"] = cluster.get("sub_cluster_id")
        doc["sub_cluster_label"] = cluster.get("sub_cluster_label", "")

    # Vector
    if embedding:
        doc["embedding"] = embedding

    return doc


# --- Push ---

def push_papers(batch_size: int = 100):
    """Push all papers to the search index.

    Generates embeddings on-the-fly via Azure OpenAI, then pushes
    papers + vectors to Azure AI Search (the single source of truth).
    """
    papers = fetch_papers()
    print(f"  Generating embeddings for {len(papers)} papers...")
    embeddings = generate_embeddings(papers)
    clusters = load_cluster_assignments()

    print(f"  Papers to index: {len(papers)}")
    print(f"  Papers with embeddings: {len(embeddings)}")
    print(f"  Papers with clusters: {len(clusters)}")

    client = _get_search_client()
    documents = []

    for paper in papers:
        pid = paper["id"]
        embedding = embeddings.get(pid)
        cluster = clusters.get(pid)
        doc = paper_to_document(paper, embedding, cluster)
        documents.append(doc)

    # Upload in batches
    total_uploaded = 0
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = client.upload_documents(batch)
        succeeded = sum(1 for r in result if r.succeeded)
        failed = sum(1 for r in result if not r.succeeded)
        total_uploaded += succeeded

        if failed > 0:
            errors = [r.error_message for r in result if not r.succeeded][:3]
            print(f"  Batch {i//batch_size + 1}: {succeeded} ok, {failed} failed — {errors}")
        elif (i // batch_size + 1) % 5 == 0 or i + batch_size >= len(documents):
            print(f"  Uploaded {total_uploaded}/{len(documents)} documents")

    print(f"\n  Total indexed: {total_uploaded} papers")


# --- Search ---

def search(query: str, top: int = 10, use_vector: bool = True):
    """Hybrid search: keyword + vector."""
    client = _get_search_client()

    vector_queries = []
    if use_vector:
        # Embed the query
        from pipeline.apis.llm import embed as embed_text
        query_embedding = embed_text([query])[0]
        vector_queries = [
            VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top,
                fields="embedding",
            )
        ]

    results = client.search(
        search_text=query,
        vector_queries=vector_queries if vector_queries else None,
        top=top,
        select="id,title,year,venue,citation_count,coordination_pattern,"
               "key_contribution,is_classical,cluster_label,has_code,repo_url",
    )

    print(f"\n  Search results for: \"{query}\"\n")
    for i, result in enumerate(results):
        classical = " [classical]" if result.get("is_classical") else ""
        code = f" [code: {result['repo_url']}]" if result.get("has_code") else ""
        cluster = f" [{result.get('cluster_label', '')}]" if result.get("cluster_label") else ""
        print(f"  {i+1}. [{result.get('year', '?')}] {result['title'][:70]}")
        print(f"     {result.get('citation_count', 0)} cites | "
              f"{result.get('coordination_pattern', '?')} | "
              f"score: {result.get('@search.score', 0):.3f}"
              f"{classical}{cluster}{code}")
        summary = result.get("key_contribution", "")
        if summary:
            print(f"     {summary[:120]}...")
        print()


def show_stats():
    """Show index statistics."""
    client = _get_index_client()
    try:
        stats = client.get_index_statistics(INDEX_NAME)
        print(f"  Index: {INDEX_NAME}")
        print(f"  Document count: {stats.document_count}")
        print(f"  Storage size:   {stats.storage_size / 1024:.1f} KB")
    except Exception as e:
        print(f"  Error getting stats: {e}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Azure AI Search index for sutra papers")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate index")
    parser.add_argument("--push", action="store_true", help="Push papers to index (default action)")
    parser.add_argument("--query", type=str, help="Test search query")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--batch-size", type=int, default=100, help="Upload batch size")
    parser.add_argument("--no-vector", action="store_true", help="Keyword-only search (skip vector)")
    args = parser.parse_args()

    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        print("  ERROR: Set SUTRA_SEARCH_ENDPOINT and SUTRA_SEARCH_KEY in your .env")
        print("  Example:")
        print("    SUTRA_SEARCH_ENDPOINT=https://your-search-service.search.windows.net")
        print("    SUTRA_SEARCH_KEY=your-admin-key")
        sys.exit(1)

    print("=" * 60)
    print("  SUTRA — Azure AI Search Index")
    print("=" * 60)
    print(f"  Endpoint: {SEARCH_ENDPOINT}")
    print(f"  Index:    {INDEX_NAME}")

    if args.stats:
        show_stats()
        return

    if args.query:
        search(args.query, use_vector=not args.no_vector)
        return

    # Default: create index + push
    create_index(recreate=args.recreate)
    push_papers(batch_size=args.batch_size)


if __name__ == "__main__":
    main()
