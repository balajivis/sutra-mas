#!/usr/bin/env bash
#
# export-corpus.sh — Export Sutra corpus data from Postgres for open-source release
#
# Usage:
#   ./scripts/export-corpus.sh              # Export to data/ directory
#   ./scripts/export-corpus.sh /tmp/export  # Export to custom directory
#
# Prerequisites:
#   - SUTRA_DB_URL env var set (or .env file in experiments/)
#   - psql installed locally
#   - Network access to Neon Postgres
#
# Outputs:
#   data/corpus.jsonl           — Full corpus (one JSON object per paper)
#   data/corpus-lite.csv        — Lightweight CSV (id, title, year, cluster, pattern, citations)
#   data/citation-edges.csv     — Directed citation graph
#   data/clusters.csv           — Cluster assignments + UMAP coordinates
#   data/cluster-meta.json      — 16 cluster labels, descriptions, paper counts
#   data/reinvention-map.csv    — Classical-to-modern paper mappings
#   data/lost-canaries.json     — High-citation, low-modernity papers (the forgotten knowledge)
#   data/reading-triples.json   — 3 entry-point papers per cluster (landmark, central, survey)
#   data/corpus-stats.json      — Summary statistics for the paper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUT_DIR="${1:-$PROJECT_DIR/data}"

# Load DB URL from .env if not in environment
if [[ -z "${SUTRA_DB_URL:-}" ]]; then
    ENV_FILE="$PROJECT_DIR/experiments/.env"
    if [[ -f "$ENV_FILE" ]]; then
        SUTRA_DB_URL=$(grep '^SUTRA_DB_URL=' "$ENV_FILE" | cut -d'=' -f2-)
        export SUTRA_DB_URL
    else
        echo "ERROR: SUTRA_DB_URL not set and no .env found at $ENV_FILE"
        exit 1
    fi
fi

mkdir -p "$OUT_DIR"

echo "=== Sutra Corpus Export ==="
echo "Target: $OUT_DIR"
echo ""

# ─────────────────────────────────────────────
# 1. Full corpus as JSONL
# ─────────────────────────────────────────────
echo "[1/9] Exporting full corpus (JSONL)..."
psql "$SUTRA_DB_URL" -t -A -c "
  SELECT json_build_object(
    'id', p.id,
    'title', p.title,
    'year', p.year,
    'authors', p.authors,
    'abstract', LEFT(p.abstract, 2000),
    'doi', p.doi,
    'arxiv_id', p.arxiv_id,
    'openalex_id', p.openalex_id,
    'citation_count', p.citation_count,
    'venue', p.venue,
    'source', p.source,
    'is_classical', p.is_classical,
    'pipeline_status', p.pipeline_status,
    'relevance_score', p.relevance_score,
    'mas_branch', p.mas_branch,
    'modernity_score', ROUND(p.modernity_score::numeric, 4),
    'has_code', p.has_code,
    'repo_url', p.repo_url,
    'coordination_pattern', p.analysis->>'coordination_pattern',
    'theoretical_grounding', p.analysis->>'theoretical_grounding',
    'classical_concepts', p.analysis->'classical_concepts',
    'classical_concepts_missing', p.analysis->>'classical_concepts_missing',
    'key_contribution', p.analysis->>'key_contribution_summary',
    'rosetta_entry', p.analysis->'rosetta_entry',
    'cluster_id', pc.cluster_id,
    'cluster_label', pc.cluster_label,
    'umap_x', ROUND(pc.x::numeric, 4),
    'umap_y', ROUND(pc.y::numeric, 4)
  )
  FROM papers p
  LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
  WHERE p.pipeline_status NOT IN ('collected', 'archived')
  ORDER BY p.id
" > "$OUT_DIR/corpus.jsonl"

CORPUS_COUNT=$(wc -l < "$OUT_DIR/corpus.jsonl" | tr -d ' ')
echo "    -> $CORPUS_COUNT papers exported"

# ─────────────────────────────────────────────
# 2. Lightweight CSV
# ─────────────────────────────────────────────
echo "[2/9] Exporting lightweight CSV..."
psql "$SUTRA_DB_URL" -c "
  COPY (
    SELECT
      p.id,
      p.title,
      p.year,
      p.citation_count,
      p.venue,
      p.is_classical,
      p.mas_branch,
      ROUND(p.modernity_score::numeric, 4) AS modernity_score,
      p.analysis->>'coordination_pattern' AS coordination_pattern,
      p.analysis->>'theoretical_grounding' AS theoretical_grounding,
      p.has_code,
      pc.cluster_id,
      pc.cluster_label,
      ROUND(pc.x::numeric, 4) AS umap_x,
      ROUND(pc.y::numeric, 4) AS umap_y
    FROM papers p
    LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
    WHERE p.pipeline_status NOT IN ('collected', 'archived')
    ORDER BY p.id
  ) TO STDOUT WITH CSV HEADER
" > "$OUT_DIR/corpus-lite.csv"
echo "    -> done"

# ─────────────────────────────────────────────
# 3. Citation edges
# ─────────────────────────────────────────────
echo "[3/9] Exporting citation graph..."
psql "$SUTRA_DB_URL" -c "
  COPY (
    SELECT citing_id, cited_id
    FROM citation_edges
    ORDER BY citing_id, cited_id
  ) TO STDOUT WITH CSV HEADER
" > "$OUT_DIR/citation-edges.csv"

EDGE_COUNT=$(tail -n +2 "$OUT_DIR/citation-edges.csv" | wc -l | tr -d ' ')
echo "    -> $EDGE_COUNT edges exported"

# ─────────────────────────────────────────────
# 4. Cluster assignments + UMAP coordinates
# ─────────────────────────────────────────────
echo "[4/9] Exporting cluster assignments..."
psql "$SUTRA_DB_URL" -c "
  COPY (
    SELECT
      paper_id,
      cluster_id,
      cluster_label,
      ROUND(x::numeric, 4) AS umap_x,
      ROUND(y::numeric, 4) AS umap_y
    FROM paper_clusters
    ORDER BY cluster_id, paper_id
  ) TO STDOUT WITH CSV HEADER
" > "$OUT_DIR/clusters.csv"

CLUSTER_COUNT=$(tail -n +2 "$OUT_DIR/clusters.csv" | wc -l | tr -d ' ')
echo "    -> $CLUSTER_COUNT papers with cluster assignments"

# ─────────────────────────────────────────────
# 5. Cluster metadata
# ─────────────────────────────────────────────
echo "[5/9] Exporting cluster metadata..."
psql "$SUTRA_DB_URL" -t -A -c "
  SELECT json_agg(
    json_build_object(
      'cluster_id', cm.cluster_id,
      'label', cm.label,
      'description', cm.description,
      'paper_count', cm.paper_count,
      'top_concepts', cm.top_concepts,
      'top_patterns', cm.top_patterns
    ) ORDER BY cm.cluster_id
  )
  FROM cluster_meta cm
" | python3 -m json.tool > "$OUT_DIR/cluster-meta.json" 2>/dev/null || \
  psql "$SUTRA_DB_URL" -t -A -c "
    SELECT json_agg(
      json_build_object(
        'cluster_id', cm.cluster_id,
        'label', cm.label,
        'description', cm.description,
        'paper_count', cm.paper_count
      ) ORDER BY cm.cluster_id
    )
    FROM cluster_meta cm
  " > "$OUT_DIR/cluster-meta.json"
echo "    -> done"

# ─────────────────────────────────────────────
# 6. Reinvention map
# ─────────────────────────────────────────────
echo "[6/9] Exporting reinvention map..."
psql "$SUTRA_DB_URL" -c "
  COPY (
    SELECT
      re.classical_id,
      cp.title AS classical_title,
      cp.year AS classical_year,
      re.modern_id,
      mp.title AS modern_title,
      mp.year AS modern_year,
      re.has_citation,
      ROUND(re.overlap_score::numeric, 4) AS overlap_score,
      re.overlap_concepts
    FROM reinvention_edges re
    JOIN papers cp ON cp.id = re.classical_id
    JOIN papers mp ON mp.id = re.modern_id
    ORDER BY re.overlap_score DESC
  ) TO STDOUT WITH CSV HEADER
" > "$OUT_DIR/reinvention-map.csv"

REINV_COUNT=$(tail -n +2 "$OUT_DIR/reinvention-map.csv" | wc -l | tr -d ' ')
echo "    -> $REINV_COUNT reinvention edges"

# ─────────────────────────────────────────────
# 7. Lost Canaries
# ─────────────────────────────────────────────
echo "[7/9] Identifying Lost Canaries..."
psql "$SUTRA_DB_URL" -t -A -c "
  SELECT json_agg(canary ORDER BY canary->>'citation_count' DESC)
  FROM (
    SELECT json_build_object(
      'id', p.id,
      'title', p.title,
      'year', p.year,
      'citation_count', p.citation_count,
      'modernity_score', ROUND(p.modernity_score::numeric, 4),
      'coordination_pattern', p.analysis->>'coordination_pattern',
      'classical_concepts', p.analysis->'classical_concepts',
      'venue', p.venue,
      'cluster_id', pc.cluster_id,
      'cluster_label', pc.cluster_label
    ) AS canary
    FROM papers p
    LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
    WHERE p.citation_count >= 500
      AND p.modernity_score IS NOT NULL
      AND p.modernity_score < 0.05
      AND p.is_classical = true
    ORDER BY p.citation_count DESC
  ) sub
" | python3 -m json.tool > "$OUT_DIR/lost-canaries.json" 2>/dev/null || \
  echo "[]" > "$OUT_DIR/lost-canaries.json"

CANARY_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUT_DIR/lost-canaries.json'))))" 2>/dev/null || echo "0")
echo "    -> $CANARY_COUNT Lost Canaries identified"

# ─────────────────────────────────────────────
# 8. Reading Triples (landmark, central, survey per cluster)
# ─────────────────────────────────────────────
echo "[8/9] Computing reading triples..."
psql "$SUTRA_DB_URL" -t -A -c "
  WITH ranked AS (
    SELECT
      pc.cluster_id,
      pc.cluster_label,
      p.id,
      p.title,
      p.year,
      p.citation_count,
      ROW_NUMBER() OVER (
        PARTITION BY pc.cluster_id
        ORDER BY p.citation_count DESC NULLS LAST
      ) AS citation_rank
    FROM paper_clusters pc
    JOIN papers p ON p.id = pc.paper_id
    WHERE p.pipeline_status NOT IN ('collected', 'archived')
  ),
  in_cluster_degree AS (
    SELECT
      pc.cluster_id,
      ce.cited_id AS paper_id,
      COUNT(*) AS in_degree
    FROM citation_edges ce
    JOIN paper_clusters pc ON pc.paper_id = ce.cited_id
    JOIN paper_clusters pc2 ON pc2.paper_id = ce.citing_id
      AND pc2.cluster_id = pc.cluster_id
    GROUP BY pc.cluster_id, ce.cited_id
  ),
  central_ranked AS (
    SELECT
      icd.cluster_id,
      icd.paper_id,
      p.title,
      p.year,
      icd.in_degree,
      ROW_NUMBER() OVER (
        PARTITION BY icd.cluster_id
        ORDER BY icd.in_degree DESC
      ) AS degree_rank
    FROM in_cluster_degree icd
    JOIN papers p ON p.id = icd.paper_id
  )
  SELECT json_agg(
    json_build_object(
      'cluster_id', r.cluster_id,
      'cluster_label', r.cluster_label,
      'landmark', json_build_object(
        'id', r.id, 'title', r.title, 'year', r.year,
        'citation_count', r.citation_count
      ),
      'central', (
        SELECT json_build_object(
          'id', cr.paper_id, 'title', cr.title, 'year', cr.year,
          'in_cluster_degree', cr.in_degree
        )
        FROM central_ranked cr
        WHERE cr.cluster_id = r.cluster_id AND cr.degree_rank = 1
      )
    ) ORDER BY r.cluster_id
  )
  FROM ranked r
  WHERE r.citation_rank = 1
" | python3 -m json.tool > "$OUT_DIR/reading-triples.json" 2>/dev/null || \
  echo "[]" > "$OUT_DIR/reading-triples.json"
echo "    -> done"

# ─────────────────────────────────────────────
# 9. Corpus statistics
# ─────────────────────────────────────────────
echo "[9/9] Computing corpus statistics..."
psql "$SUTRA_DB_URL" -t -A -c "
  SELECT json_build_object(
    'total_papers', (SELECT COUNT(*) FROM papers),
    'by_status', (
      SELECT json_object_agg(pipeline_status, cnt)
      FROM (SELECT pipeline_status, COUNT(*) AS cnt FROM papers GROUP BY pipeline_status) s
    ),
    'by_era', json_build_object(
      'classical_pre_2010', (SELECT COUNT(*) FROM papers WHERE year < 2010 AND pipeline_status NOT IN ('collected','archived')),
      'middle_2010_2022', (SELECT COUNT(*) FROM papers WHERE year BETWEEN 2010 AND 2022 AND pipeline_status NOT IN ('collected','archived')),
      'modern_2023_plus', (SELECT COUNT(*) FROM papers WHERE year >= 2023 AND pipeline_status NOT IN ('collected','archived'))
    ),
    'by_cluster', (
      SELECT json_agg(json_build_object('cluster_id', cluster_id, 'label', cluster_label, 'count', cnt) ORDER BY cluster_id)
      FROM (SELECT cluster_id, cluster_label, COUNT(*) AS cnt FROM paper_clusters GROUP BY cluster_id, cluster_label) c
    ),
    'citation_edges', (SELECT COUNT(*) FROM citation_edges),
    'reinvention_edges', (SELECT COUNT(*) FROM reinvention_edges),
    'papers_with_code', (SELECT COUNT(*) FROM papers WHERE has_code = true),
    'papers_with_analysis', (SELECT COUNT(*) FROM papers WHERE analysis IS NOT NULL),
    'top_coordination_patterns', (
      SELECT json_agg(json_build_object('pattern', pattern, 'count', cnt) ORDER BY cnt DESC)
      FROM (
        SELECT analysis->>'coordination_pattern' AS pattern, COUNT(*) AS cnt
        FROM papers
        WHERE analysis->>'coordination_pattern' IS NOT NULL
        GROUP BY analysis->>'coordination_pattern'
      ) p
    ),
    'exported_at', NOW()
  )
" | python3 -m json.tool > "$OUT_DIR/corpus-stats.json"
echo "    -> done"

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
echo ""
echo "=== Export Complete ==="
echo ""
ls -lh "$OUT_DIR"/ | tail -n +2
echo ""
echo "Total size: $(du -sh "$OUT_DIR" | cut -f1)"
