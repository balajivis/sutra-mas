#!/usr/bin/env python3
"""Sutra Assembly Line — Live Web Dashboard (v2).

Research-focused dashboard: Classical vs Modern bridge, experimentation
readiness, pipeline funnel, and analysis depth.

Usage:
    python3 -m pipeline.assembly.dashboard_web
    python3 -m pipeline.assembly.dashboard_web --port 8050
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from pipeline.assembly.db import get_conn

app = FastAPI(title="Sutra Dashboard")

# --- Experiment results reader ---
EXPERIMENTS_DIR = os.path.join(os.path.dirname(__file__), "../../experiments/results")


def _fetch_experiments() -> list[dict]:
    """Read all experiment JSON files from experiments/results/."""
    import json as _json
    results = []
    if not os.path.isdir(EXPERIMENTS_DIR):
        return results
    for fname in sorted(os.listdir(EXPERIMENTS_DIR)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(EXPERIMENTS_DIR, fname)) as f:
                d = _json.load(f)
            results.append({
                "pattern": d.get("pattern", "?"),
                "benchmark": d.get("benchmark", "?"),
                "quality": d.get("quality_score", 0),
                "tokens": d.get("total_tokens", 0),
                "efficiency": round(d.get("quality_score", 0) / max(d.get("total_tokens", 1), 1) * 1000, 2),
                "agents": d.get("num_agents", 0),
                "rounds": d.get("num_rounds", 0),
                "time": round(d.get("wall_time_seconds", 0), 1),
                "model": d.get("model", "?"),
                "file": fname,
            })
        except Exception:
            continue
    return results

# --- Azure AI Search (optional, for /api/search) ---
_search_client = None
_search_available = False

def _init_search():
    global _search_client, _search_available
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        endpoint = os.environ.get("SUTRA_SEARCH_ENDPOINT", "")
        key = os.environ.get("SUTRA_SEARCH_KEY", "")
        index = os.environ.get("SUTRA_SEARCH_INDEX", "sutra-papers")
        if endpoint and key:
            _search_client = SearchClient(endpoint, index, AzureKeyCredential(key))
            _search_available = True
    except Exception:
        pass

_init_search()


def _fetch_all():
    data = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Funnel
            cur.execute("SELECT pipeline_status, COUNT(*) FROM papers GROUP BY pipeline_status")
            data["funnel"] = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute("SELECT COUNT(*) FROM papers")
            data["total"] = cur.fetchone()[0]

            # 2. Classical vs Modern — the core research lens
            cur.execute("""
                SELECT
                    CASE
                        WHEN year IS NULL THEN 'unknown'
                        WHEN year < 2010 THEN 'classical'
                        WHEN year < 2023 THEN 'transitional'
                        ELSE 'modern'
                    END AS era,
                    pipeline_status,
                    COUNT(*) as cnt
                FROM papers
                GROUP BY era, pipeline_status
            """)
            era_status = {}
            for era, status, cnt in cur.fetchall():
                if era not in era_status:
                    era_status[era] = {}
                era_status[era][status] = cnt
            data["era_status"] = era_status

            # Era totals
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE year < 2010) as classical,
                    COUNT(*) FILTER (WHERE year >= 2010 AND year < 2023) as transitional,
                    COUNT(*) FILTER (WHERE year >= 2023) as modern,
                    COUNT(*) FILTER (WHERE year IS NULL) as unknown
                FROM papers
            """)
            r = cur.fetchone()
            data["era_totals"] = {
                "classical": r[0], "transitional": r[1],
                "modern": r[2], "unknown": r[3],
            }

            # Era decade breakdown
            cur.execute("""
                SELECT
                    CASE
                        WHEN year IS NULL THEN 'unknown'
                        WHEN year < 1990 THEN '< 1990'
                        WHEN year < 2000 THEN '1990s'
                        WHEN year < 2010 THEN '2000s'
                        WHEN year < 2020 THEN '2010s'
                        WHEN year < 2023 THEN '2020-22'
                        WHEN year < 2025 THEN '2023-24'
                        ELSE '2025+'
                    END AS era,
                    COUNT(*) as cnt
                FROM papers
                GROUP BY era
                ORDER BY MIN(COALESCE(year, 9999))
            """)
            data["era_decades"] = [(r[0], r[1]) for r in cur.fetchall()]

            # 3. Top classical papers (the ones that matter for the survey)
            cur.execute("""
                SELECT COALESCE(title, '?'), year, COALESCE(citation_count, 0),
                       pipeline_status, relevance_score
                FROM papers
                WHERE year < 2010
                ORDER BY citation_count DESC NULLS LAST
                LIMIT 15
            """)
            data["top_classical"] = [
                (r[0][:60], r[1], r[2], r[3], r[4]) for r in cur.fetchall()
            ]

            # 4. Top modern papers
            cur.execute("""
                SELECT COALESCE(title, '?'), year, COALESCE(citation_count, 0),
                       pipeline_status, relevance_score
                FROM papers
                WHERE year >= 2023
                ORDER BY citation_count DESC NULLS LAST
                LIMIT 15
            """)
            data["top_modern"] = [
                (r[0][:60], r[1], r[2], r[3], r[4]) for r in cur.fetchall()
            ]

            # 5. Citations
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE citation_count IS NULL OR citation_count = 0),
                    COUNT(*) FILTER (WHERE citation_count BETWEEN 1 AND 10),
                    COUNT(*) FILTER (WHERE citation_count BETWEEN 11 AND 50),
                    COUNT(*) FILTER (WHERE citation_count BETWEEN 51 AND 200),
                    COUNT(*) FILTER (WHERE citation_count BETWEEN 201 AND 1000),
                    COUNT(*) FILTER (WHERE citation_count > 1000)
                FROM papers
            """)
            r = cur.fetchone()
            data["citations"] = [
                ("No data", r[0]), ("1-10", r[1]), ("11-50", r[2]),
                ("51-200", r[3]), ("201-1K", r[4]), ("1K+", r[5]),
            ]

            cur.execute("""
                SELECT COALESCE(AVG(citation_count)::int, 0),
                       COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY citation_count)::int, 0)
                FROM papers WHERE citation_count > 0
            """)
            r = cur.fetchone()
            data["cite_stats"] = {"mean": r[0], "median": r[1]}

            # 6. Relevance scores (exclude score=0 which is just the archived default)
            cur.execute("""
                SELECT relevance_score, COUNT(*) FROM papers
                WHERE relevance_score IS NOT NULL AND relevance_score > 0
                GROUP BY relevance_score ORDER BY relevance_score
            """)
            data["relevance"] = [(r[0], r[1]) for r in cur.fetchall()]

            # Total scored
            cur.execute("SELECT COUNT(*) FROM papers WHERE relevance_score IS NOT NULL AND relevance_score > 0")
            data["scored_count"] = cur.fetchone()[0]

            # MAS branches
            cur.execute("""
                SELECT COALESCE(mas_branch, 'unclassified'), COUNT(*) FROM papers
                WHERE mas_branch IS NOT NULL AND mas_branch != ''
                GROUP BY mas_branch ORDER BY COUNT(*) DESC LIMIT 10
            """)
            data["branches"] = [(r[0], r[1]) for r in cur.fetchall()]

            # 7. Analysis — coordination patterns
            cur.execute("SELECT COUNT(*) FROM papers WHERE analysis IS NOT NULL")
            data["analyzed_count"] = cur.fetchone()[0]

            cur.execute("""
                SELECT COALESCE(analysis->>'coordination_pattern', 'null'), COUNT(*)
                FROM papers WHERE analysis IS NOT NULL
                GROUP BY 1 ORDER BY 2 DESC
            """)
            data["patterns"] = [(r[0], r[1]) for r in cur.fetchall()]

            cur.execute("""
                SELECT COALESCE(analysis->>'theoretical_grounding', 'null'), COUNT(*)
                FROM papers WHERE analysis IS NOT NULL
                GROUP BY 1 ORDER BY 2 DESC
            """)
            data["grounding"] = [(r[0], r[1]) for r in cur.fetchall()]

            # Missing classical concepts — extract named concepts via SQL regex
            _concept_patterns = [
                ("BDI", r"BDI|belief.desire.intention"),
                ("Blackboard", r"blackboard"),
                ("Contract Net", r"contract.net"),
                ("FIPA Protocols", r"FIPA"),
                ("Joint Intentions", r"joint.intention"),
                ("SharedPlans", r"[Ss]hared.?[Pp]lans?"),
                ("Organizational Models", r"organizational.*(model|paradigm|structure|framework)"),
                ("MOISE/AGR", r"MOISE|AGR"),
                ("HTN Planning", r"HTN|hierarchical.task.network"),
                ("Normative MAS", r"norm.based|normative"),
                ("Argumentation", r"argument\w*\s*framework"),
                ("Consensus Protocols", r"consensus"),
                ("Trust & Reputation", r"trust.{0,10}reputation|reputation.{0,10}trust"),
                ("Auction/Mechanism Design", r"auction|mechanism.design"),
                ("KQML", r"KQML"),
                ("Mixed-Initiative", r"mixed.initiative"),
            ]
            missing_counts = []
            for label, pattern in _concept_patterns:
                cur.execute("""
                    SELECT COUNT(*) FROM papers
                    WHERE analysis IS NOT NULL
                      AND analysis->>'classical_concepts_missing' ~* %s
                """, (pattern,))
                cnt = cur.fetchone()[0]
                if cnt > 0:
                    missing_counts.append((label, cnt))
            missing_counts.sort(key=lambda x: -x[1])
            data["missing_classical"] = missing_counts[:12]

            # 8. Experimentation candidates
            # Papers that have been analyzed, have a coordination pattern, and ideally code
            cur.execute("""
                SELECT COALESCE(title, '?'), year, COALESCE(citation_count, 0),
                       analysis->>'coordination_pattern' as pattern,
                       COALESCE(has_code, FALSE) as has_code,
                       COALESCE(repo_url, '') as repo_url,
                       COALESCE(reproduction_feasibility, 0) as feasibility
                FROM papers
                WHERE analysis IS NOT NULL
                  AND analysis->>'coordination_pattern' IS NOT NULL
                  AND analysis->>'coordination_pattern' NOT IN ('none', 'null', '')
                ORDER BY
                    CASE WHEN has_code = TRUE THEN 0 ELSE 1 END,
                    reproduction_feasibility DESC NULLS LAST,
                    citation_count DESC NULLS LAST
                LIMIT 20
            """)
            data["experiment_candidates"] = [
                (r[0][:55], r[1], r[2], r[3], r[4], r[5][:50] if r[5] else "", r[6])
                for r in cur.fetchall()
            ]

            # Experiment readiness summary
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE has_code = TRUE AND reproduction_feasibility >= 4) as ready,
                    COUNT(*) FILTER (WHERE has_code = TRUE AND reproduction_feasibility < 4) as has_code_needs_work,
                    COUNT(*) FILTER (WHERE (has_code = FALSE OR has_code IS NULL) AND analysis IS NOT NULL) as no_code_analyzed,
                    COUNT(*) FILTER (WHERE analysis IS NOT NULL AND analysis->>'coordination_pattern' IS NOT NULL
                                     AND analysis->>'coordination_pattern' NOT IN ('none', 'null', '')) as has_pattern
                FROM papers
            """)
            r = cur.fetchone()
            data["experiment_readiness"] = {
                "ready": r[0], "has_code_needs_work": r[1],
                "no_code_analyzed": r[2], "has_pattern": r[3],
            }

            # 9. Scout summary
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE has_code = TRUE),
                    COUNT(*) FILTER (WHERE has_code = FALSE OR has_code IS NULL)
                FROM papers
                WHERE pipeline_status IN ('scouted','planning_reproduction','reproduction_planned')
            """)
            r = cur.fetchone()
            data["scout"] = {"with_code": r[0], "without_code": r[1]}

            cur.execute("""
                SELECT reproduction_feasibility, COUNT(*) FROM papers
                WHERE reproduction_feasibility IS NOT NULL
                GROUP BY 1 ORDER BY 1
            """)
            data["feasibility"] = [(r[0], r[1]) for r in cur.fetchall()]

            # 10. Clustering status (Agent 8)
            try:
                cur.execute("SELECT COUNT(*) FROM paper_clusters")
                data["clustered_count"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM cluster_meta")
                data["cluster_count"] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM clustering_runs WHERE status = 'running'")
                data["clustering_active"] = cur.fetchone()[0]
                cur.execute("""
                    SELECT COUNT(*) FROM papers
                    WHERE analysis IS NOT NULL
                      AND analysis->>'key_contribution_summary' IS NOT NULL
                      AND pipeline_status NOT IN ('archived')
                """)
                data["clusterable_count"] = cur.fetchone()[0]
                cur.execute("""
                    SELECT status, papers_clustered, num_clusters,
                           to_char(completed_at, 'MM-DD HH24:MI') as completed
                    FROM clustering_runs ORDER BY id DESC LIMIT 1
                """)
                last_run = cur.fetchone()
                if last_run:
                    data["last_clustering_run"] = {
                        "status": last_run[0], "papers": last_run[1],
                        "clusters": last_run[2], "completed": last_run[3] or "-",
                    }
                else:
                    data["last_clustering_run"] = None
            except Exception:
                data["clustered_count"] = 0
                data["cluster_count"] = 0
                data["clustering_active"] = 0
                data["clusterable_count"] = 0
                data["last_clustering_run"] = None

            # 11. Agent activity
            cur.execute("""
                SELECT COALESCE(processed_by, '?'), pipeline_status, COUNT(*),
                       to_char(MAX(processed_at), 'MM-DD HH24:MI')
                FROM papers WHERE processed_by IS NOT NULL
                GROUP BY 1, 2 ORDER BY MAX(processed_at) DESC NULLS LAST LIMIT 15
            """)
            data["agents"] = [(r[0], r[1], r[2], r[3] or "-") for r in cur.fetchall()]

            # 11. Generations
            cur.execute("""
                SELECT COALESCE(generation, 0), COUNT(*) FROM papers
                GROUP BY 1 ORDER BY 1
            """)
            data["generations"] = [(r[0], r[1]) for r in cur.fetchall()]

            data["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Experiment results (from JSON files, not DB)
    data["experiments"] = _fetch_experiments()

    return data


@app.get("/api/status")
def api_status():
    return JSONResponse(_fetch_all())


@app.get("/api/experiments")
def api_experiments():
    return JSONResponse(_fetch_experiments())


def _db_search(q: str, top: int = 15) -> list[dict]:
    """Fallback: search Neon Postgres via ILIKE + ts_rank when Azure AI Search isn't available."""
    results = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Use Postgres full-text search if available, otherwise ILIKE
            cur.execute("""
                SELECT id, title, year, venue, citation_count, arxiv_id, doi,
                       semantic_scholar_id,
                       is_classical, has_code, repo_url, relevance_score,
                       pipeline_status, abstract,
                       analysis->>'key_contribution_summary' as key_contribution,
                       analysis->>'coordination_pattern' as coordination_pattern,
                       analysis->>'theoretical_grounding' as grounding,
                       analysis->>'classical_concepts_missing' as missing,
                       ts_rank_cd(
                           to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'') || ' ' ||
                                       COALESCE(analysis->>'key_contribution_summary','') || ' ' ||
                                       COALESCE(analysis->>'unique_contribution','')),
                           plainto_tsquery('english', %s)
                       ) as rank
                FROM papers
                WHERE pipeline_status NOT IN ('archived')
                  AND (
                    to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'') || ' ' ||
                                COALESCE(analysis->>'key_contribution_summary','') || ' ' ||
                                COALESCE(analysis->>'unique_contribution',''))
                    @@ plainto_tsquery('english', %s)
                    OR title ILIKE %s
                  )
                ORDER BY rank DESC, citation_count DESC NULLS LAST
                LIMIT %s
            """, (q, q, f"%{q}%", top))
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                r = dict(zip(cols, row))
                pat = r.get("coordination_pattern") or "none"
                # Build link: prefer arxiv > doi > semantic scholar > google scholar
                import urllib.parse as _up
                arxiv = r.get("arxiv_id")
                doi = r.get("doi")
                s2id = r.get("semantic_scholar_id")
                link = None
                if arxiv:
                    link = f"https://arxiv.org/abs/{arxiv}"
                elif doi:
                    link = f"https://doi.org/{doi}"
                elif s2id:
                    link = f"https://www.semanticscholar.org/paper/{s2id}"
                else:
                    link = f"https://scholar.google.com/scholar?q={_up.quote(r.get('title','')[:100])}"

                results.append({
                    "id": str(r["id"]),
                    "title": r.get("title", ""),
                    "year": r.get("year"),
                    "venue": r.get("venue"),
                    "citations": r.get("citation_count") or 0,
                    "pattern": pat,
                    "summary": (r.get("key_contribution") or (r.get("abstract") or "")[:200])[:200],
                    "classical": r.get("is_classical", False),
                    "cluster": None,
                    "has_code": r.get("has_code", False),
                    "repo_url": r.get("repo_url"),
                    "relevance": r.get("relevance_score"),
                    "grounding": r.get("grounding"),
                    "missing": r.get("missing"),
                    "score": round(float(r.get("rank") or 0), 3),
                    "link": link,
                })
    return results


@app.get("/api/search")
def api_search(q: str = Query(""), vector: bool = Query(False), top: int = Query(15)):
    """Hybrid search via Azure AI Search, with Postgres fallback."""
    if not q.strip():
        return JSONResponse({"results": [], "available": _search_available})
    if not _search_available:
        # Fallback to Postgres
        try:
            results = _db_search(q.strip(), top)
            return JSONResponse({"results": results, "available": True, "source": "postgres"})
        except Exception as e:
            return JSONResponse({"results": [], "available": False, "error": str(e)})

    try:
        vector_queries = None
        if vector:
            try:
                from azure.search.documents.models import VectorizedQuery
                from pipeline.apis.llm import embed as embed_text
                qvec = embed_text([q])[0]
                vector_queries = [VectorizedQuery(
                    vector=qvec, k_nearest_neighbors=top, fields="embedding",
                )]
            except Exception:
                pass  # Fall back to keyword-only

        raw = _search_client.search(
            search_text=q,
            vector_queries=vector_queries,
            top=top,
            select="id,title,year,venue,citation_count,coordination_pattern,"
                   "key_contribution,is_classical,cluster_label,has_code,repo_url,"
                   "relevance_score,theoretical_grounding,classical_concepts_missing,"
                   "arxiv_id,doi",
        )
        results = []
        for r in raw:
            arxiv = r.get("arxiv_id")
            doi = r.get("doi")
            link = None
            if arxiv:
                link = f"https://arxiv.org/abs/{arxiv}"
            elif doi:
                link = f"https://doi.org/{doi}"

            results.append({
                "id": r.get("id"),
                "title": r.get("title", ""),
                "year": r.get("year"),
                "venue": r.get("venue"),
                "citations": r.get("citation_count", 0),
                "pattern": r.get("coordination_pattern"),
                "summary": (r.get("key_contribution") or "")[:200],
                "classical": r.get("is_classical", False),
                "cluster": r.get("cluster_label"),
                "has_code": r.get("has_code", False),
                "repo_url": r.get("repo_url"),
                "relevance": r.get("relevance_score"),
                "grounding": r.get("theoretical_grounding"),
                "missing": r.get("classical_concepts_missing"),
                "score": round(r.get("@search.score", 0), 3),
                "link": link,
            })
        return JSONResponse({"results": results, "available": True})
    except Exception as e:
        return JSONResponse({"results": [], "available": True, "error": str(e)})


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Sutra Assembly Line</title>
<style>
  :root {
    --bg: #0a0a0f; --card: #12121a; --border: #1e1e2e;
    --text: #d4d4d8; --dim: #71717a; --accent: #34d399;
    --amber: #fbbf24; --red: #f87171; --blue: #60a5fa;
    --purple: #a78bfa; --cyan: #22d3ee; --pink: #f472b6;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'SF Mono','Fira Code','JetBrains Mono', monospace;
    font-size: 13px; line-height: 1.5; padding: 20px 24px;
  }
  h1 { font-size: 18px; color: var(--accent); letter-spacing: 2px; }
  .subtitle { color: var(--dim); font-size: 11px; margin-bottom: 16px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  @media (max-width: 1200px) { .grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px;
    overflow: hidden;
  }
  .card h2 {
    font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--accent); margin-bottom: 10px; border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
  }
  .card h2.classical { color: var(--amber); }
  .card h2.modern { color: var(--blue); }
  .card h2.experiment { color: var(--pink); }
  .card h2.canary { color: var(--amber); }
  .card.span2 { grid-column: span 2; }
  .card.span3 { grid-column: 1 / -1; }
  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left; color: var(--dim); font-size: 10px; text-transform: uppercase;
    letter-spacing: 1px; padding: 3px 6px; border-bottom: 1px solid var(--border);
  }
  td { padding: 3px 6px; font-size: 12px; }
  tr:hover td { background: rgba(52,211,153,0.04); }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .bar-w { width:100%; height:12px; background:var(--border); border-radius:3px; overflow:hidden; display:inline-block; vertical-align:middle; }
  .bar-f { height:100%; border-radius:3px; transition:width 0.4s ease; }
  .bg { background: linear-gradient(90deg,#059669,#34d399); }
  .ba { background: linear-gradient(90deg,#d97706,#fbbf24); }
  .bb { background: linear-gradient(90deg,#2563eb,#60a5fa); }
  .bp { background: linear-gradient(90deg,#7c3aed,#a78bfa); }
  .br { background: linear-gradient(90deg,#dc2626,#f87171); }
  .bc { background: linear-gradient(90deg,#0891b2,#22d3ee); }
  .bk { background: linear-gradient(90deg,#db2777,#f472b6); }
  .bd { background: linear-gradient(90deg,#3f3f46,#71717a); }
  .pill {
    display:inline-block; padding:1px 8px; border-radius:10px;
    font-size:10px; font-weight:600; white-space:nowrap;
  }
  .p-active { background:rgba(52,211,153,0.15); color:var(--accent); }
  .p-queue  { background:rgba(251,191,36,0.15); color:var(--amber); }
  .p-done   { background:rgba(96,165,250,0.15); color:var(--blue); }
  .p-out    { background:rgba(248,113,113,0.1); color:var(--red); }
  .p-exp    { background:rgba(244,114,182,0.15); color:var(--pink); }
  .big-num { font-size: 26px; font-weight: 700; }
  .stat-row { display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.03); }
  .stat-label { color: var(--dim); font-size: 12px; }
  .stat-val { font-weight: 600; font-size: 13px; }
  .top-bar { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
  .summary-strip { display:flex; gap:24px; flex-wrap:wrap; margin-bottom:16px; }
  .summary-item { text-align:center; min-width:80px; }
  .summary-item .big-num { font-size:22px; }
  .summary-item .label { font-size:10px; color:var(--dim); text-transform:uppercase; letter-spacing:0.5px; }
  .refresh-dot {
    display:inline-block; width:8px; height:8px; border-radius:50%;
    background:var(--accent); margin-right:6px;
    animation:pulse 2.5s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .era-split { display:flex; gap:8px; margin-top:8px; }
  .era-block {
    flex:1; text-align:center; padding:8px 4px; border-radius:6px;
    border:1px solid var(--border);
  }
  .era-block .num { font-size:18px; font-weight:700; display:block; }
  .era-block .label { font-size:9px; color:var(--dim); text-transform:uppercase; }
  .code-yes { color: var(--accent); }
  .code-no { color: var(--dim); }
  .trunc { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:250px; display:inline-block; vertical-align:bottom; }
  .ts { color:var(--dim); font-size:10px; }

  /* Search */
  .search-wrap {
    margin-bottom:16px; display:flex; gap:8px; align-items:center;
  }
  .search-input {
    flex:1; background:var(--card); border:1px solid var(--border);
    border-radius:6px; padding:10px 14px; color:var(--text);
    font-family:inherit; font-size:13px; outline:none;
    transition:border-color 0.2s;
  }
  .search-input:focus { border-color:var(--accent); }
  .search-input::placeholder { color:var(--dim); }
  .search-toggle {
    background:var(--card); border:1px solid var(--border); border-radius:6px;
    padding:8px 12px; color:var(--dim); font-family:inherit; font-size:11px;
    cursor:pointer; transition:all 0.2s; white-space:nowrap;
  }
  .search-toggle.active { border-color:var(--accent); color:var(--accent); }
  .search-toggle:hover { border-color:var(--accent); }
  .search-results {
    margin-bottom:16px; display:none;
  }
  .search-results.visible { display:block; }
  .sr-card {
    background:var(--card); border:1px solid var(--border); border-radius:8px;
    padding:12px 16px; margin-bottom:8px;
    display:grid; grid-template-columns:1fr auto; gap:8px;
  }
  .sr-card:hover { border-color:rgba(52,211,153,0.3); }
  .sr-title { font-size:13px; font-weight:600; color:var(--text); margin-bottom:4px; }
  .sr-meta { font-size:11px; color:var(--dim); display:flex; gap:10px; flex-wrap:wrap; }
  .sr-summary { font-size:11px; color:var(--dim); margin-top:6px; line-height:1.4;
                 font-style:italic; }
  .sr-missing { font-size:10px; color:var(--amber); margin-top:4px; }
  .sr-score { font-size:18px; font-weight:700; color:var(--accent);
              display:flex; align-items:center; }
  .sr-count { font-size:11px; color:var(--dim); margin-bottom:8px; }
  .sr-empty { color:var(--dim); padding:16px; text-align:center; }

  /* Assembly line */
  .aline { display:flex; flex-direction:column; gap:0; }
  .station {
    display:grid; grid-template-columns: 90px 1fr 80px 70px 70px;
    align-items:center; gap:8px; padding:8px 10px;
    border-bottom:1px solid var(--border);
    position: relative;
  }
  .station:last-child { border-bottom:none; }
  .station-id {
    font-weight:700; font-size:13px;
  }
  .station-bar-wrap {
    height:22px; background:var(--border); border-radius:4px; overflow:hidden;
    position:relative;
  }
  .station-bar-done {
    position:absolute; left:0; top:0; height:100%; border-radius:4px 0 0 4px;
    transition:width 0.5s ease;
  }
  .station-bar-active {
    position:absolute; top:0; height:100%;
    transition:width 0.5s ease, left 0.5s ease;
    border-radius:0;
    animation: barPulse 1.5s infinite;
  }
  @keyframes barPulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
  .station-bar-label {
    position:absolute; left:8px; top:0; height:100%;
    display:flex; align-items:center;
    font-size:10px; color:rgba(255,255,255,0.8); font-weight:600;
    z-index:1; text-shadow: 0 0 4px rgba(0,0,0,0.5);
  }
  .station-count { text-align:right; font-variant-numeric:tabular-nums; font-size:12px; }
  .station-desc { font-size:10px; color:var(--dim); line-height:1.2; }
  .station-arrow {
    display:flex; justify-content:center; color:var(--border); font-size:10px; padding:0;
    margin:-4px 0 -4px 45px;
  }
</style>
</head>
<body>
<div class="top-bar">
  <div>
    <h1>SUTRA ASSEMBLY LINE</h1>
    <div class="subtitle"><span class="refresh-dot"></span>Live dashboard &mdash; <span id="ts">--</span></div>
  </div>
  <a href="http://localhost:8051" target="_blank"
     style="font-size:11px;color:var(--accent);border:1px solid var(--border);border-radius:6px;padding:6px 12px;text-decoration:none;transition:border-color 0.2s"
     onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--border)'">
    Research Desk &rarr;
  </a>
</div>

<div class="summary-strip" id="summary"></div>

<div class="search-wrap">
  <input class="search-input" id="searchBox" type="text"
         placeholder="Search papers... (e.g. contract net, blackboard, LLM agent coordination)">
  <button class="search-toggle" id="vectorToggle" title="Enable vector search (slower, more semantic)">Vector</button>
</div>
<div class="search-results" id="searchResults"></div>

<div class="grid" id="grid"></div>

<script>
const STAGES = [
  ["seed","Seeds (r1)","p-done"],
  ["collected","Collected","p-queue"],
  ["filtering","Filtering","p-active"],
  ["relevant","Relevant","p-done"],
  ["marginal","Marginal","p-out"],
  ["archived","Archived","p-out"],
  ["analyzing","Analyzing","p-active"],
  ["analyzed","Analyzed","p-done"],
  ["enriching","Enriching","p-active"],
  ["enriched","Enriched","p-done"],
  ["scouting","Scouting","p-active"],
  ["scouted","Scouted","p-done"],
  ["planning_reproduction","Planning","p-active"],
  ["reproduction_planned","Complete","p-done"],
];
const REL = {1:"Off-topic",2:"Tangential",3:"Marginal",4:"Relevant",5:"Core MAS"};
const FEAS = {1:"Very hard",2:"Hard",3:"Moderate",4:"Feasible",5:"Easy"};

function B(v,mx,cls="bg"){const p=mx>0?(v/mx*100).toFixed(1):0;return `<div class="bar-w"><div class="bar-f ${cls}" style="width:${p}%"></div></div>`;}
function P(n,t){return t>0?(n/t*100).toFixed(1):"0.0";}

function render(d) {
  document.getElementById("ts").textContent = d.ts;

  const f = d.funnel;
  const queued = f.collected||0;
  const active = (f.filtering||0)+(f.analyzing||0)+(f.enriching||0)+(f.scouting||0)+(f.planning_reproduction||0);
  const progressing = (f.relevant||0)+(f.analyzed||0)+(f.enriched||0)+(f.scouted||0)+(f.reproduction_planned||0);
  const complete = f.reproduction_planned||0;
  const et = d.era_totals;
  const er = d.experiment_readiness;

  document.getElementById("summary").innerHTML = `
    <div class="summary-item"><div class="big-num" style="color:var(--text)">${d.total.toLocaleString()}</div><div class="label">Total</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--amber)">${et.classical.toLocaleString()}</div><div class="label">Classical</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--blue)">${et.modern.toLocaleString()}</div><div class="label">Modern</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--purple)">${active.toLocaleString()}</div><div class="label">Active</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--red)">${(f.archived||0).toLocaleString()}</div><div class="label">Archived</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--accent)">${d.analyzed_count.toLocaleString()}</div><div class="label">Analyzed</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--pink)">${er.ready.toLocaleString()}</div><div class="label">Exp. Ready</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--cyan)">${er.has_pattern.toLocaleString()}</div><div class="label">Has Pattern</div></div>
    <div class="summary-item"><div class="big-num" style="color:var(--text)">${(d.experiments||[]).length}</div><div class="label">Exp. Runs</div></div>
  `;

  let h = "";

  // ── ASSEMBLY LINE (the main visual) ──
  const stations = [
    {
      id:"Agent 1", name:"Collector", color:"var(--amber)",
      desc:"S2 + OpenAlex API expansion",
      input:0, active:0,
      done: d.total - (f.seed||0),
      total: d.total,
    },
    {
      id:"Agent 2", name:"Filter", color:"var(--accent)",
      desc:"GPT-5-mini relevance scoring (1-5)",
      input: f.collected||0, active: f.filtering||0,
      done: (f.relevant||0)+(f.marginal||0)+(f.archived||0)+(f.analyzing||0)+(f.analyzed||0)+(f.enriching||0)+(f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
      total: (f.collected||0)+(f.filtering||0)+(f.relevant||0)+(f.marginal||0)+(f.archived||0)+(f.analyzing||0)+(f.analyzed||0)+(f.enriching||0)+(f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
    },
    {
      id:"Agent 3b", name:"Analyst", color:"var(--blue)",
      desc:"GPT-5.1 deep extraction (LaTeX + JSONB)",
      input: f.relevant||0, active: f.analyzing||0,
      done: (f.analyzed||0)+(f.enriching||0)+(f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
      total: (f.relevant||0)+(f.analyzing||0)+(f.analyzed||0)+(f.enriching||0)+(f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
    },
    {
      id:"Agent 4", name:"Enricher", color:"var(--purple)",
      desc:"S2 citation expansion + feedback loop",
      input: f.analyzed||0, active: f.enriching||0,
      done: (f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
      total: (f.analyzed||0)+(f.enriching||0)+(f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
    },
    {
      id:"Agent 5", name:"Scout", color:"var(--cyan)",
      desc:"Papers with Code + GitHub repo search",
      input: f.enriched||0, active: f.scouting||0,
      done: (f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
      total: (f.enriched||0)+(f.scouting||0)+(f.scouted||0)+(f.planning_reproduction||0)+(f.reproduction_planned||0),
    },
    (() => {
      // Agent 6 combines DB pipeline status + experiment harness results
      const dbInput = f.scouted||0;
      const dbActive = f.planning_reproduction||0;
      const dbDone = f.reproduction_planned||0;
      const exps = d.experiments||[];
      const uniquePatterns = new Set(exps.map(e=>e.pattern)).size;
      const expRuns = exps.length;
      return {
        id:"Agent 6", name:"Reproducer", color:"var(--pink)",
        desc: expRuns>0
          ? `${uniquePatterns} patterns tested, ${expRuns} experiment runs`
          : "Auto-run repos + research briefs",
        input: dbInput, active: dbActive,
        done: dbDone + expRuns,
        total: (dbInput)+(dbActive)+(dbDone)+Math.max(expRuns,1),
      };
    })(),
    {
      id:"Agent 8", name:"Clustering", color:"#fb923c",
      desc: `k-means + UMAP 2D (${d.cluster_count||0} clusters)`,
      input: Math.max(0, (d.clusterable_count||0) - (d.clustered_count||0)),
      active: d.clustering_active||0,
      done: d.clustered_count||0,
      total: Math.max(d.clusterable_count||0, 1),
    },
  ];

  let alH = "";
  for(let i=0; i<stations.length; i++){
    const s = stations[i];
    const pctDone = s.total>0 ? (s.done/s.total*100) : 0;
    const pctActive = s.total>0 ? (s.active/s.total*100) : 0;
    const status = s.active>0 ? "RUNNING" : s.done>0&&s.input===0 ? "DONE" : s.input>0 ? "WAITING" : "IDLE";
    const statusColor = s.active>0 ? s.color : status==="DONE" ? "var(--dim)" : status==="WAITING" ? "var(--amber)" : "var(--border)";
    const barLabel = s.total>0 ? `${s.done}/${s.total}` : "";

    alH += `<div class="station">
      <div>
        <div class="station-id" style="color:${s.color}">${s.id}</div>
        <div class="station-desc">${s.name}</div>
      </div>
      <div>
        <div class="station-bar-wrap">
          <div class="station-bar-done" style="width:${pctDone.toFixed(1)}%;background:${s.color};opacity:0.7"></div>
          ${s.active>0 ? `<div class="station-bar-active" style="left:${pctDone.toFixed(1)}%;width:${Math.max(pctActive,2).toFixed(1)}%;background:${s.color}"></div>` : ""}
          <div class="station-bar-label">${barLabel}</div>
        </div>
        <div class="station-desc" style="margin-top:2px">${s.desc}</div>
      </div>
      <div class="station-count">${s.input>0 ? `<span style="color:var(--amber)">${s.input.toLocaleString()} in</span>` : ""}</div>
      <div class="station-count">${s.active>0 ? `<span style="color:${s.color}">${s.active} now</span>` : ""}</div>
      <div><span class="pill" style="background:${statusColor}22;color:${statusColor};font-size:9px">${status}</span></div>
    </div>`;
    if(i < stations.length-1) alH += `<div class="station-arrow">&#9660;</div>`;
  }
  h+=`<div class="card span3"><h2>Assembly Line &mdash; 7 Stations</h2><div class="aline">${alH}</div></div>`;

  // ── EXPERIMENTS ──
  if(d.experiments && d.experiments.length>0){
    // Group by benchmark, deduplicate (keep best per pattern+benchmark)
    const best = {};
    for(const e of d.experiments){
      const key = e.pattern+"|"+e.benchmark;
      if(!best[key] || e.quality > best[key].quality) best[key] = e;
    }
    const exps = Object.values(best).sort((a,b)=>b.quality-a.quality||a.tokens-b.tokens);

    // Get unique benchmarks
    const benchmarks = [...new Set(exps.map(e=>e.benchmark))].sort();
    const patterns = [...new Set(exps.map(e=>e.pattern))].sort((a,b)=>{
      // Sort by max quality across benchmarks
      const maxA = Math.max(...exps.filter(e=>e.pattern===a).map(e=>e.quality));
      const maxB = Math.max(...exps.filter(e=>e.pattern===b).map(e=>e.quality));
      return maxB-maxA;
    });

    // Pivot table: patterns (rows) x benchmarks (cols)
    let expH = `<tr><th>Pattern</th>`;
    for(const bm of benchmarks) expH += `<th colspan="2" style="text-align:center">${bm.replace(/_/g," ")}</th>`;
    expH += `</tr><tr><th></th>`;
    for(const bm of benchmarks) expH += `<th class="num">Quality</th><th class="num">Tokens</th>`;
    expH += `</tr>`;

    const maxQ = Math.max(...exps.map(e=>e.quality),1);
    for(const pat of patterns){
      expH += `<tr><td style="white-space:nowrap">${pat.replace(/_/g," ")}</td>`;
      for(const bm of benchmarks){
        const e = best[pat+"|"+bm];
        if(e){
          const qColor = e.quality>=90?"var(--accent)":e.quality>=80?"var(--blue)":e.quality>=70?"var(--amber)":"var(--red)";
          expH += `<td class="num" style="color:${qColor};font-weight:600">${e.quality}</td>`;
          expH += `<td class="num" style="color:var(--dim)">${(e.tokens/1000).toFixed(1)}K</td>`;
        } else {
          expH += `<td class="num" style="color:var(--border)">&mdash;</td><td></td>`;
        }
      }
      expH += `</tr>`;
    }

    // Summary stats
    const totalExps = d.experiments.length;
    const uniquePatterns = new Set(d.experiments.map(e=>e.pattern)).size;
    const uniqueBenchmarks = benchmarks.length;
    const bestExp = exps[0];

    h+=`<div class="card span3"><h2 class="experiment">Experiment Harness &mdash; ${totalExps} runs, ${uniquePatterns} patterns, ${uniqueBenchmarks} benchmarks</h2>`;
    h+=`<div style="display:flex;gap:20px;margin-bottom:10px">
      <div><span class="stat-label">Best: </span><span class="stat-val" style="color:var(--accent)">${bestExp.pattern.replace(/_/g," ")} (${bestExp.quality}) on ${bestExp.benchmark.replace(/_/g," ")}</span></div>
      <div><span class="stat-label">Model: </span><span class="stat-val">${bestExp.model||"?"}</span></div>
    </div>`;
    h+=`<table>${expH}</table></div>`;
  }

  // ── FUNNEL ──
  const maxF = Math.max(...STAGES.map(s=>f[s[0]]||0),1);
  let fR = "";
  for(const[k,l,p]of STAGES){const c=f[k]||0;if(!c)continue;
    fR+=`<tr><td><span class="pill ${p}">${l}</span></td><td class="num">${c.toLocaleString()}</td><td style="width:50%">${B(c,maxF,c===maxF?"bg":"bb")}</td></tr>`;}
  h+=`<div class="card"><h2>Pipeline Funnel</h2><table>${fR}</table></div>`;

  // ── CLASSICAL vs MODERN SPLIT ──
  const eras = ["classical","transitional","modern","unknown"];
  const eColors = {classical:"ba",transitional:"bp",modern:"bb",unknown:"bd"};
  const ePill = {classical:"p-queue",transitional:"p-done",modern:"p-done",unknown:"p-out"};
  const pipeline_groups = {
    "queued":["collected"],
    "filtered":["relevant","marginal","archived"],
    "analyzed":["analyzing","analyzed"],
    "enriched+":["enriching","enriched","scouting","scouted","planning_reproduction","reproduction_planned"],
  };
  let csRows = `<tr><th>Era</th><th>Total</th><th>Queued</th><th>Filtered</th><th>Analyzed</th><th>Enriched+</th></tr>`;
  for(const era of eras){
    const es = d.era_status[era]||{};
    const tot = Object.values(es).reduce((a,b)=>a+b,0);
    if(!tot) continue;
    const q = (pipeline_groups.queued||[]).reduce((a,s)=>a+(es[s]||0),0);
    const fl = pipeline_groups.filtered.reduce((a,s)=>a+(es[s]||0),0);
    const an = pipeline_groups.analyzed.reduce((a,s)=>a+(es[s]||0),0);
    const en = (pipeline_groups["enriched+"]||[]).reduce((a,s)=>a+(es[s]||0),0);
    csRows+=`<tr><td><span class="pill ${ePill[era]}">${era}</span></td>
      <td class="num">${tot.toLocaleString()}</td>
      <td class="num">${q||""}</td><td class="num">${fl||""}</td>
      <td class="num">${an||""}</td><td class="num">${en||""}</td></tr>`;
  }
  h+=`<div class="card"><h2>Classical vs Modern &mdash; Pipeline Progress</h2><table>${csRows}</table>
    <div class="era-split">
      <div class="era-block" style="border-color:var(--amber)"><span class="num" style="color:var(--amber)">${et.classical}</span><span class="label">Classical (&lt;2010)</span></div>
      <div class="era-block" style="border-color:var(--purple)"><span class="num" style="color:var(--purple)">${et.transitional}</span><span class="label">Transitional</span></div>
      <div class="era-block" style="border-color:var(--blue)"><span class="num" style="color:var(--blue)">${et.modern}</span><span class="label">Modern (2023+)</span></div>
    </div></div>`;

  // ── ERA DECADES ──
  const maxEd = Math.max(...d.era_decades.map(e=>e[1]),1);
  let edR = d.era_decades.map(([e,c])=>
    `<tr><td>${e}</td><td class="num">${c.toLocaleString()}</td><td class="num">${P(c,d.total)}%</td><td style="width:40%">${B(c,maxEd,"bp")}</td></tr>`
  ).join("");
  h+=`<div class="card"><h2>Era Breakdown (Decades)</h2><table>${edR}</table></div>`;

  // ── EXPERIMENTATION CANDIDATES ──
  h+=`<div class="card span2"><h2 class="experiment">Experimentation Candidates</h2>`;
  h+=`<div style="display:flex;gap:16px;margin-bottom:10px">
    <div class="stat-row" style="flex:1"><span class="stat-label">Ready (code + feasible)</span><span class="stat-val" style="color:var(--accent)">${er.ready}</span></div>
    <div class="stat-row" style="flex:1"><span class="stat-label">Has code, needs work</span><span class="stat-val" style="color:var(--amber)">${er.has_code_needs_work}</span></div>
    <div class="stat-row" style="flex:1"><span class="stat-label">Has pattern (no code)</span><span class="stat-val" style="color:var(--cyan)">${er.has_pattern}</span></div>
  </div>`;
  if(d.experiment_candidates.length>0){
    let ecR = `<tr><th>Title</th><th>Year</th><th>Cites</th><th>Pattern</th><th>Code</th><th>Feas.</th></tr>`;
    for(const[t,y,c,pat,code,repo,feas]of d.experiment_candidates){
      const codeIcon = code ? `<span class="code-yes">&#10003;</span>` : `<span class="code-no">&mdash;</span>`;
      const feasPill = feas>=4?'p-active':feas>=2?'p-queue':'p-out';
      ecR+=`<tr><td><span class="trunc">${t}</span></td><td class="num">${y||"?"}</td><td class="num">${c.toLocaleString()}</td>
        <td><span class="pill p-exp">${pat}</span></td><td>${codeIcon}</td>
        <td><span class="pill ${feasPill}">${feas?feas+"/5":"?"}</span></td></tr>`;
    }
    h+=`<table>${ecR}</table>`;
  } else { h+=`<div style="color:var(--dim);padding:8px">No analyzed papers with coordination patterns yet. Run Agent 3/3b.</div>`; }
  h+=`</div>`;

  // ── CITATIONS ──
  const maxC=Math.max(...d.citations.map(c=>c[1]),1);
  let cR=d.citations.map(([l,c])=>`<tr><td>${l}</td><td class="num">${c.toLocaleString()}</td><td style="width:45%">${B(c,maxC,"ba")}</td></tr>`).join("");
  cR+=`<tr><td colspan="3" style="padding-top:6px;color:var(--dim);font-size:11px">Mean: ${d.cite_stats.mean} &nbsp; Median: ${d.cite_stats.median}</td></tr>`;
  h+=`<div class="card"><h2>Citation Distribution</h2><table>${cR}</table></div>`;

  // ── RELEVANCE (only if data) ──
  if(d.relevance.length>0){
    const totR=d.relevance.reduce((a,r)=>a+r[1],0);
    const maxR=Math.max(...d.relevance.map(r=>r[1]),1);
    let rR=d.relevance.map(([s,c])=>{
      const cls=s>=4?"bg":s===3?"ba":"br";
      return `<tr><td>${s}/5 ${REL[s]||"?"}</td><td class="num">${c.toLocaleString()}</td><td class="num">${P(c,totR)}%</td><td style="width:30%">${B(c,maxR,cls)}</td></tr>`;
    }).join("");
    if(d.branches.length>0){
      rR+=`<tr><td colspan="4" style="padding-top:10px"><strong style="color:var(--dim);font-size:10px">MAS BRANCHES</strong></td></tr>`;
      rR+=d.branches.map(([b,c])=>`<tr><td colspan="2">${b}</td><td class="num" colspan="2">${c}</td></tr>`).join("");
    }
    h+=`<div class="card"><h2>Relevance Scores (Agent 2) &mdash; ${d.scored_count} scored</h2><table>${rR}</table></div>`;
  }

  // ── TOP CLASSICAL ──
  if(d.top_classical.length>0){
    let tcR=`<tr><th>Title</th><th>Year</th><th>Cites</th><th>Status</th></tr>`;
    for(const[t,y,c,st,rs]of d.top_classical){
      const sPill = st==="archived"?"p-out":st==="collected"?"p-queue":"p-done";
      tcR+=`<tr><td><span class="trunc">${t}</span></td><td class="num">${y||"?"}</td><td class="num">${c.toLocaleString()}</td>
        <td><span class="pill ${sPill}">${st}</span></td></tr>`;
    }
    h+=`<div class="card span2"><h2 class="classical">Top Classical Papers (&lt;2010)</h2><table>${tcR}</table></div>`;
  }

  // ── TOP MODERN ──
  if(d.top_modern.length>0){
    let tmR=`<tr><th>Title</th><th>Year</th><th>Cites</th><th>Status</th></tr>`;
    for(const[t,y,c,st,rs]of d.top_modern){
      const sPill = st==="archived"?"p-out":st==="collected"?"p-queue":"p-done";
      tmR+=`<tr><td><span class="trunc">${t}</span></td><td class="num">${y||"?"}</td><td class="num">${c.toLocaleString()}</td>
        <td><span class="pill ${sPill}">${st}</span></td></tr>`;
    }
    h+=`<div class="card"><h2 class="modern">Top Modern Papers (2023+)</h2><table>${tmR}</table></div>`;
  }

  // ── ANALYSIS ──
  if(d.analyzed_count>0){
    let aR="";
    if(d.patterns.length>0){
      aR+=`<tr><td colspan="3"><strong style="color:var(--dim);font-size:10px">COORDINATION PATTERNS</strong></td></tr>`;
      const maxP=Math.max(...d.patterns.map(p=>p[1]),1);
      aR+=d.patterns.map(([p,c])=>`<tr><td>${p}</td><td class="num">${c}</td><td style="width:35%">${B(c,maxP,"bg")}</td></tr>`).join("");
    }
    if(d.grounding.length>0){
      aR+=`<tr><td colspan="3" style="padding-top:10px"><strong style="color:var(--dim);font-size:10px">THEORETICAL GROUNDING</strong></td></tr>`;
      aR+=d.grounding.map(([g,c])=>`<tr><td>${g}</td><td class="num" colspan="2">${c}</td></tr>`).join("");
    }
    h+=`<div class="card"><h2>Deep Analysis (Agent 3/3b) &mdash; ${d.analyzed_count} papers</h2><table>${aR}</table></div>`;
  }

  // ── MISSING CLASSICAL (LOST CANARY) ──
  if(d.missing_classical.length>0){
    const maxMC = Math.max(...d.missing_classical.map(c=>c[1]),1);
    let mcR=d.missing_classical.map(([c,n])=>{
      const pct = d.analyzed_count>0 ? (n/d.analyzed_count*100).toFixed(0) : 0;
      return `<tr><td style="color:var(--amber);font-weight:600;font-size:12px;white-space:nowrap">${c}</td><td class="num">${n.toLocaleString()}</td><td class="num" style="color:var(--dim)">${pct}%</td><td style="width:35%">${B(n,maxMC,"ba")}</td></tr>`;
    }).join("");
    h+=`<div class="card"><h2 class="canary">Lost Canary Signal &mdash; Missing Classical Concepts (${d.analyzed_count} analyzed)</h2><table>${mcR}</table></div>`;
  }

  // ── SCOUT + GENERATIONS (combined) ──
  let sgH = `<div style="display:flex;gap:20px;margin-bottom:8px">
    <div><span class="stat-label">With code: </span><span class="stat-val code-yes">${d.scout.with_code}</span></div>
    <div><span class="stat-label">No code: </span><span class="stat-val code-no">${d.scout.without_code}</span></div>
  </div>`;
  if(d.feasibility.length>0){
    sgH+=`<table>`;
    sgH+=d.feasibility.map(([f,c])=>`<tr><td>${f}/5 ${FEAS[f]||"?"}</td><td class="num">${c}</td></tr>`).join("");
    sgH+=`</table>`;
  }
  if(d.generations.length>1||d.generations.some(g=>g[0]>0)){
    sgH+=`<div style="margin-top:10px;border-top:1px solid var(--border);padding-top:8px"><strong style="color:var(--dim);font-size:10px">FEEDBACK GENERATIONS</strong></div>`;
    const maxG=Math.max(...d.generations.map(g=>g[1]),1);
    sgH+=`<table>`;
    sgH+=d.generations.map(([g,c])=>`<tr><td>${g===0?"Original":"Gen "+g}</td><td class="num">${c.toLocaleString()}</td><td style="width:40%">${B(c,maxG,"bc")}</td></tr>`).join("");
    sgH+=`</table>`;
  }
  h+=`<div class="card"><h2>Scout + Feedback (Agents 4-5)</h2>${sgH}</div>`;

  // ── AGENTS ──
  if(d.agents.length>0){
    let agR=d.agents.map(([a,s,c,t])=>
      `<tr><td>${a}</td><td><span class="pill p-done">${s}</span></td><td class="num">${c}</td><td class="ts">${t}</td></tr>`
    ).join("");
    h+=`<div class="card span3"><h2>Agent Activity</h2><table><tr><th>Agent</th><th>Output Status</th><th>Count</th><th>Last Active</th></tr>${agR}</table></div>`;
  }

  document.getElementById("grid").innerHTML = h;
}

async function poll(){try{const r=await fetch("/api/status");render(await r.json());}catch(e){console.error("Poll:",e);}}
poll(); setInterval(poll, 2500);

// ── SEARCH ──
let searchTimeout = null;
let useVector = false;
const searchBox = document.getElementById("searchBox");
const vectorToggle = document.getElementById("vectorToggle");
const searchResults = document.getElementById("searchResults");

vectorToggle.addEventListener("click", () => {
  useVector = !useVector;
  vectorToggle.classList.toggle("active", useVector);
  if(searchBox.value.trim()) doSearch(searchBox.value.trim());
});

searchBox.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);
  const q = e.target.value.trim();
  if(!q) { searchResults.classList.remove("visible"); searchResults.innerHTML=""; return; }
  searchTimeout = setTimeout(() => doSearch(q), 400);
});

searchBox.addEventListener("keydown", (e) => {
  if(e.key==="Escape") { searchBox.value=""; searchResults.classList.remove("visible"); searchResults.innerHTML=""; }
  if(e.key==="Enter") { clearTimeout(searchTimeout); const q=searchBox.value.trim(); if(q) doSearch(q); }
});

async function doSearch(q) {
  try {
    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&vector=${useVector}&top=15`);
    const d = await r.json();
    if(!d.available) {
      searchResults.innerHTML = `<div class="sr-empty">Azure AI Search not configured. Push papers with: python3 -m pipeline.search_index</div>`;
      searchResults.classList.add("visible");
      return;
    }
    if(d.error) {
      searchResults.innerHTML = `<div class="sr-empty">Search error: ${d.error}</div>`;
      searchResults.classList.add("visible");
      return;
    }
    if(!d.results.length) {
      searchResults.innerHTML = `<div class="sr-empty">No results for "${q}"</div>`;
      searchResults.classList.add("visible");
      return;
    }
    let html = `<div class="sr-count">${d.results.length} results for "<strong>${q}</strong>"${useVector?" (hybrid vector+keyword)":" (keyword)"}</div>`;
    for(const r of d.results) {
      const tags = [];
      if(r.classical) tags.push(`<span class="pill p-queue">classical</span>`);
      if(r.pattern && r.pattern!=="none") tags.push(`<span class="pill p-exp">${r.pattern}</span>`);
      if(r.cluster) tags.push(`<span class="pill p-done">${r.cluster}</span>`);
      if(r.has_code) tags.push(`<span class="pill p-active">has code</span>`);
      if(r.grounding && r.grounding!=="none") tags.push(`<span class="pill" style="background:rgba(167,139,250,0.15);color:var(--purple)">${r.grounding}</span>`);
      if(r.link && r.link.includes("arxiv")) tags.push(`<span class="pill" style="background:rgba(239,68,68,0.15);color:#f87171">arxiv</span>`);
      else if(r.link && r.link.includes("doi.org")) tags.push(`<span class="pill" style="background:rgba(96,165,250,0.15);color:#60a5fa">doi</span>`);
      else if(r.link && r.link.includes("semanticscholar")) tags.push(`<span class="pill" style="background:rgba(251,191,36,0.15);color:#fbbf24">S2</span>`);
      else if(r.link && r.link.includes("scholar.google")) tags.push(`<span class="pill" style="background:rgba(52,211,153,0.15);color:#34d399">scholar</span>`);

      html += `<div class="sr-card">
        <div>
          <div class="sr-title">${r.link?`<a href="${r.link}" target="_blank" style="color:inherit;text-decoration:none;border-bottom:1px dashed var(--dim)">${r.title}</a>`:r.title}</div>
          <div class="sr-meta">
            <span>${r.year||"?"}</span>
            <span>${(r.citations||0).toLocaleString()} cites</span>
            ${r.venue?`<span>${r.venue}</span>`:""}
            ${r.relevance?`<span>R${r.relevance}/5</span>`:""}
            ${tags.join(" ")}
          </div>
          ${r.summary?`<div class="sr-summary">${r.summary}</div>`:""}
          ${r.missing&&r.missing!=="none"?`<div class="sr-missing">Missing: ${r.missing.substring(0,120)}</div>`:""}
          ${r.repo_url?`<div style="font-size:10px;margin-top:3px"><a href="${r.repo_url}" target="_blank" style="color:var(--accent)">${r.repo_url}</a></div>`:""}
        </div>
        <div class="sr-score">${r.score}</div>
      </div>`;
    }
    searchResults.innerHTML = html;
    searchResults.classList.add("visible");
  } catch(e) {
    searchResults.innerHTML = `<div class="sr-empty">Search failed: ${e.message}</div>`;
    searchResults.classList.add("visible");
  }
}
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Sutra Assembly Line — Web Dashboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8050)
    args = parser.parse_args()
    print(f"\n  SUTRA DASHBOARD: http://localhost:{args.port}\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
