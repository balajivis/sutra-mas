"""Shared database module for the assembly line pipeline.

Each agent uses this to poll its input queue and push results downstream.
Uses psycopg2 with FOR UPDATE SKIP LOCKED for safe concurrent access.
"""

import os
import time
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras

# Load .env
for _env_path in [
    os.path.join(os.path.dirname(__file__), "../../experiments/.env"),
    os.path.join(os.path.dirname(__file__), "../.env"),
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

DB_URL = os.environ.get("SUTRA_DB_URL", "")


@contextmanager
def get_conn():
    """Get a database connection. Auto-commits on success, rolls back on error."""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def poll_papers(status: str, limit: int = 10, min_relevance: Optional[int] = None) -> list[dict]:
    """Fetch papers in a given pipeline_status for processing.

    Uses FOR UPDATE SKIP LOCKED so multiple agent instances can run in parallel.
    Returns list of dicts (RealDictRow).
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if min_relevance is not None:
                cur.execute(
                    """SELECT * FROM papers
                       WHERE pipeline_status = %s AND relevance_score >= %s
                       ORDER BY id
                       LIMIT %s
                       FOR UPDATE SKIP LOCKED""",
                    (status, min_relevance, limit),
                )
            else:
                cur.execute(
                    """SELECT * FROM papers
                       WHERE pipeline_status = %s
                       ORDER BY id
                       LIMIT %s
                       FOR UPDATE SKIP LOCKED""",
                    (status, limit),
                )
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def update_paper(paper_id: int, agent_name: str, new_status: str, **kwargs):
    """Update a paper's pipeline_status and any additional columns.

    Handles UniqueViolation gracefully by retrying without the conflicting column.
    """
    set_parts = ["pipeline_status = %s", "processed_by = %s", "processed_at = NOW()", "updated_at = NOW()"]
    values = [new_status, agent_name]

    for col, val in kwargs.items():
        set_parts.append(f"{col} = %s")
        values.append(val)

    values.append(paper_id)

    sql = f"UPDATE papers SET {', '.join(set_parts)} WHERE id = %s"

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
    except psycopg2.errors.UniqueViolation as e:
        # Retry without the conflicting unique column
        conflicting_col = None
        err_msg = str(e)
        for col in kwargs:
            if col in err_msg:
                conflicting_col = col
                break

        if conflicting_col:
            retry_kwargs = {k: v for k, v in kwargs.items() if k != conflicting_col}
            set_parts = ["pipeline_status = %s", "processed_by = %s", "processed_at = NOW()", "updated_at = NOW()"]
            values = [new_status, agent_name]
            for col, val in retry_kwargs.items():
                set_parts.append(f"{col} = %s")
                values.append(val)
            values.append(paper_id)
            sql = f"UPDATE papers SET {', '.join(set_parts)} WHERE id = %s"
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, values)
        else:
            raise


def insert_paper(
    title: str,
    year: Optional[int] = None,
    abstract: Optional[str] = None,
    doi: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    semantic_scholar_id: Optional[str] = None,
    openalex_id: Optional[str] = None,
    citation_count: int = 0,
    authors: Optional[list] = None,
    venue: Optional[str] = None,
    concepts: Optional[list] = None,
    source: str = "collector",
    is_classical: bool = False,
    pipeline_status: str = "collected",
    generation: int = 0,
) -> Optional[int]:
    """Insert a new paper, skipping duplicates.

    Dedup is handled by Postgres UNIQUE constraints on doi, arxiv_id,
    semantic_scholar_id, and openalex_id. Title+year checked via a single
    pre-check query. One round-trip for new papers, one for dupes.

    Returns the paper id if inserted, None if duplicate.
    """
    # Title+year dedup (no unique index for this, so check in Python)
    if title and year:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM papers WHERE lower(title) = lower(%s) AND year = %s",
                    (title, year),
                )
                if cur.fetchone():
                    return None

    # Single INSERT — Postgres UNIQUE constraints handle doi/arxiv/s2/openalex dedup
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO papers
                       (title, year, abstract, doi, arxiv_id, semantic_scholar_id, openalex_id,
                        citation_count, authors, venue, concepts, source, is_classical,
                        pipeline_status, processed_by, generation)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'collector', %s)
                       RETURNING id""",
                    (
                        title, year, abstract, doi, arxiv_id, semantic_scholar_id, openalex_id,
                        citation_count,
                        psycopg2.extras.Json(authors or []),
                        venue,
                        psycopg2.extras.Json(concepts or []),
                        source, is_classical, pipeline_status, generation,
                    ),
                )
                row = cur.fetchone()
                return row[0] if row else None
    except psycopg2.errors.UniqueViolation:
        return None


def count_by_status() -> dict[str, int]:
    """Get paper counts grouped by pipeline_status."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pipeline_status, count(*) FROM papers GROUP BY pipeline_status ORDER BY count DESC"
            )
            return {row[0]: row[1] for row in cur.fetchall()}


def total_papers() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM papers")
            return cur.fetchone()[0]
