-- Sutra corpus database schema
-- PostgreSQL 14+
--
-- To initialize:
--   psql $SUTRA_DB_URL -f schema.sql

-- ─────────────────────────────────────────────
-- Core paper table
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS papers (
    id                      SERIAL PRIMARY KEY,
    title                   TEXT NOT NULL,
    year                    INTEGER,
    abstract                TEXT,
    doi                     VARCHAR UNIQUE,
    arxiv_id                VARCHAR UNIQUE,
    semantic_scholar_id     VARCHAR UNIQUE,
    openalex_id             VARCHAR UNIQUE,
    citation_count          INTEGER DEFAULT 0,
    authors                 JSONB,             -- ["Author One", "Author Two"]
    venue                   TEXT,
    concepts                JSONB,             -- ["concept1", "concept2"]
    source                  TEXT NOT NULL DEFAULT 'collector',
    source_url              TEXT,
    is_classical            BOOLEAN DEFAULT FALSE,

    -- Pipeline state
    pipeline_status         VARCHAR DEFAULT 'collected',
        -- collected -> relevant/marginal/archived -> analyzed -> enriched -> scouted -> done
    processed_by            VARCHAR,
    processed_at            TIMESTAMP,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),
    generation              INTEGER DEFAULT 0,

    -- Agent 2: Filter
    relevance_score         INTEGER,           -- 1-5
    relevance_rationale     TEXT,
    mas_branch              VARCHAR,
        -- communication, organization, coordination, architecture, negotiation, engineering, llm_agents, other
    filter_status           VARCHAR,           -- unfiltered, included, excluded
    filter_reason           TEXT,

    -- Agent 3b: Analyst
    analysis                JSONB,
        -- {
        --   coordination_pattern: "blackboard" | "contract_net" | "supervisor" | "bdi" | ...,
        --   theoretical_grounding: "strong" | "moderate" | "weak" | "none",
        --   classical_concepts: ["concept1", "concept2"],
        --   classical_concepts_missing: "description or 'none'",
        --   modern_mapping: ["mapping1", "mapping2"],
        --   unique_contribution: "1-2 sentences",
        --   rosetta_entry: {"classical_term": "modern_equivalent"} | null,
        --   failure_modes_addressed: ["mode1", "mode2"],
        --   methodology: "1-2 sentences",
        --   key_results: "1-2 sentences",
        --   key_contribution_summary: "3-5 sentences"
        -- }
    latex_source            TEXT,              -- First 50KB of LaTeX from ArXiv

    -- Agent 4: Citation Enricher
    modernity_score         FLOAT,             -- modern_cites / total_cites (2023-2026 weighted)
    refs                    JSONB,             -- [{oa_id, title, year, citations}, ...]
    cited_by                JSONB,

    -- Agent 5: Scout
    has_code                BOOLEAN DEFAULT FALSE,
    repo_url                VARCHAR,
    reproduction_feasibility INTEGER,          -- 1-5
    experiment_notes        TEXT
);

-- ─────────────────────────────────────────────
-- Citation graph (materialized from refs/cited_by)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS citation_edges (
    citing_id   INTEGER NOT NULL REFERENCES papers(id),
    cited_id    INTEGER NOT NULL REFERENCES papers(id),
    PRIMARY KEY (citing_id, cited_id)
);

CREATE INDEX IF NOT EXISTS idx_citation_edges_cited
    ON citation_edges(cited_id);

-- ─────────────────────────────────────────────
-- Cluster assignments + UMAP coordinates
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paper_clusters (
    paper_id        INTEGER PRIMARY KEY REFERENCES papers(id),
    cluster_id      INTEGER NOT NULL,
    cluster_label   TEXT,
    x               FLOAT NOT NULL,    -- UMAP 2D x (normalized 0-100)
    y               FLOAT NOT NULL,    -- UMAP 2D y (normalized 0-100)
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Cluster metadata
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cluster_meta (
    cluster_id      INTEGER PRIMARY KEY,
    label           TEXT,
    description     TEXT,
    paper_count     INTEGER,
    top_concepts    JSONB,
    top_patterns    JSONB,
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Classical-to-modern reinvention pairs
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reinvention_edges (
    modern_id           INTEGER NOT NULL REFERENCES papers(id),
    classical_id        INTEGER NOT NULL REFERENCES papers(id),
    overlap_concepts    JSONB,
    has_citation        BOOLEAN DEFAULT FALSE,
    overlap_score       FLOAT DEFAULT 0,
    PRIMARY KEY (modern_id, classical_id)
);

-- ─────────────────────────────────────────────
-- Clustering run history
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clustering_runs (
    id                  SERIAL PRIMARY KEY,
    started_at          TIMESTAMP DEFAULT NOW(),
    completed_at        TIMESTAMP,
    papers_clustered    INTEGER DEFAULT 0,
    num_clusters        INTEGER DEFAULT 0,
    status              VARCHAR DEFAULT 'running'
        -- running, completed, skipped, failed
);

-- ─────────────────────────────────────────────
-- Source provenance tracking
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paper_sources (
    paper_id    INTEGER NOT NULL REFERENCES papers(id),
    source      VARCHAR NOT NULL,
    raw_entry   JSONB,
    PRIMARY KEY (paper_id, source)
);

-- ─────────────────────────────────────────────
-- Dashboard: research chat history
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS research_chat (
    id          SERIAL PRIMARY KEY,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    sql_used    TEXT,
    sources     JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Dashboard: research insights
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS research_insights (
    id              SERIAL PRIMARY KEY,
    type            TEXT NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    evidence        JSONB,
    paper_count     INTEGER DEFAULT 0,
    status          VARCHAR DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- Dashboard: per-cluster insights
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cluster_insights (
    cluster_id      INTEGER PRIMARY KEY,
    insight         TEXT NOT NULL,
    top_papers      JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);
