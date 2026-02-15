"""Corpus storage module — shared Neon Postgres backend.

Both the laptop and the sutra-research VM connect to the same database.
Dedup is enforced at the DB level via unique constraints on DOI, arXiv ID,
and Semantic Scholar ID. When a duplicate is found, we merge metadata
(keep the richer version) and track all sources in paper_sources.

Usage:
    from pipeline.utils.storage import db

    # Insert a paper (handles dedup automatically)
    db.upsert_paper({
        "title": "Contract Net Protocol",
        "year": 1980,
        "doi": "10.1109/TCOM.1980.1094802",
        "citation_count": 5000,
        "source": "r1_seeds",
    })

    # Query
    papers = db.query(year_min=2023, venue="ICLR")
    stats = db.corpus_stats()

Environment:
    Set SUTRA_DB_URL or it defaults to the shared Neon instance.
"""

import json
import os
from contextlib import contextmanager
from typing import Optional

import psycopg
from psycopg.rows import dict_row

DEFAULT_DB_URL = ""  # Set SUTRA_DB_URL in your environment


def _get_db_url() -> str:
    return os.environ.get("SUTRA_DB_URL", DEFAULT_DB_URL)


@contextmanager
def get_conn():
    """Get a database connection. Use as context manager."""
    conn = psycopg.connect(_get_db_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class CorpusDB:
    """Interface to the shared Sutra corpus database."""

    def upsert_paper(self, paper: dict, raw_entry: dict = None) -> int:
        """Insert a paper, handling dedup via unique constraints.

        If a paper with the same DOI, arxiv_id, or semantic_scholar_id exists,
        updates the existing record with any new non-null fields and adds
        the source to paper_sources.

        Returns the paper ID.
        """
        with get_conn() as conn:
            cur = conn.cursor()

            # Try to find existing paper by unique identifiers
            existing_id = self._find_existing(cur, paper)

            if existing_id:
                self._merge_paper(cur, existing_id, paper)
                self._add_source(cur, existing_id, paper.get("source", "unknown"), raw_entry)
                return existing_id

            # Insert new paper
            cols = [
                "title", "year", "venue", "doi", "arxiv_id",
                "semantic_scholar_id", "openalex_id", "citation_count",
                "authors", "abstract", "source", "source_url",
                "concepts", "is_classical",
            ]
            values = {}
            for col in cols:
                if col in paper and paper[col] is not None:
                    val = paper[col]
                    if col in ("authors", "concepts") and isinstance(val, (list, dict)):
                        val = json.dumps(val)
                    values[col] = val

            if not values.get("title"):
                raise ValueError("Paper must have a title")
            if "source" not in values:
                values["source"] = "unknown"

            col_names = ", ".join(values.keys())
            placeholders = ", ".join(f"%({k})s" for k in values.keys())

            cur.execute(
                f"INSERT INTO papers ({col_names}) VALUES ({placeholders}) RETURNING id",
                values,
            )
            paper_id = cur.fetchone()["id"]

            self._add_source(cur, paper_id, values.get("source", "unknown"), raw_entry)
            return paper_id

    def upsert_many(self, papers: list[dict], source: str = None) -> dict:
        """Insert multiple papers. Returns stats dict."""
        inserted = 0
        merged = 0
        errors = 0
        for p in papers:
            if source:
                p["source"] = source
            try:
                existing = self._find_existing_quick(p)
                self.upsert_paper(p)
                if existing:
                    merged += 1
                else:
                    inserted += 1
            except Exception as e:
                errors += 1
                print(f"  Error inserting '{p.get('title', '?')[:60]}': {e}")
        return {"inserted": inserted, "merged": merged, "errors": errors, "total": len(papers)}

    def _find_existing_quick(self, paper: dict) -> Optional[int]:
        """Quick check if paper already exists (without opening a transaction)."""
        with get_conn() as conn:
            cur = conn.cursor()
            return self._find_existing(cur, paper)

    def _find_existing(self, cur, paper: dict) -> Optional[int]:
        """Find an existing paper by DOI, arxiv_id, or semantic_scholar_id."""
        for field in ("doi", "arxiv_id", "semantic_scholar_id", "openalex_id"):
            val = paper.get(field)
            if val:
                cur.execute(f"SELECT id FROM papers WHERE {field} = %s", (val,))
                row = cur.fetchone()
                if row:
                    return row["id"]

        # Fuzzy title match as last resort (exact match only — fuzzy is too slow in SQL)
        if paper.get("title") and paper.get("year"):
            cur.execute(
                "SELECT id FROM papers WHERE lower(title) = lower(%s) AND year = %s",
                (paper["title"], paper["year"]),
            )
            row = cur.fetchone()
            if row:
                return row["id"]

        return None

    def _merge_paper(self, cur, paper_id: int, paper: dict):
        """Update existing paper with any new non-null fields."""
        updatable = [
            "venue", "doi", "arxiv_id", "semantic_scholar_id", "openalex_id",
            "citation_count", "authors", "abstract", "source_url", "concepts",
        ]
        sets = []
        values = {}
        for col in updatable:
            val = paper.get(col)
            if val is not None:
                if col in ("authors", "concepts") and isinstance(val, (list, dict)):
                    val = json.dumps(val)
                # For citation_count, take the higher value
                if col == "citation_count":
                    sets.append(f"{col} = GREATEST({col}, %({col})s)")
                else:
                    # Only update if current value is NULL
                    sets.append(f"{col} = COALESCE({col}, %({col})s)")
                values[col] = val

        if sets:
            values["id"] = paper_id
            sets.append("updated_at = NOW()")
            cur.execute(
                f"UPDATE papers SET {', '.join(sets)} WHERE id = %(id)s",
                values,
            )

    def _add_source(self, cur, paper_id: int, source: str, raw_entry: dict = None):
        """Record that this source found this paper."""
        raw_json = json.dumps(raw_entry) if raw_entry else None
        cur.execute(
            """INSERT INTO paper_sources (paper_id, source, raw_entry)
               VALUES (%s, %s, %s)
               ON CONFLICT (paper_id, source) DO NOTHING""",
            (paper_id, source, raw_json),
        )

    # --- Queries ---

    def get_paper(self, paper_id: int) -> Optional[dict]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM papers WHERE id = %s", (paper_id,))
            return cur.fetchone()

    def query(
        self,
        year_min: int = None,
        year_max: int = None,
        venue: str = None,
        source: str = None,
        min_citations: int = None,
        is_classical: bool = None,
        filter_status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Query papers with filters."""
        conditions = []
        params = {}

        if year_min is not None:
            conditions.append("year >= %(year_min)s")
            params["year_min"] = year_min
        if year_max is not None:
            conditions.append("year <= %(year_max)s")
            params["year_max"] = year_max
        if venue:
            conditions.append("venue ILIKE %(venue)s")
            params["venue"] = f"%{venue}%"
        if source:
            conditions.append("source = %(source)s")
            params["source"] = source
        if min_citations is not None:
            conditions.append("citation_count >= %(min_citations)s")
            params["min_citations"] = min_citations
        if is_classical is not None:
            conditions.append("is_classical = %(is_classical)s")
            params["is_classical"] = is_classical
        if filter_status:
            conditions.append("filter_status = %(filter_status)s")
            params["filter_status"] = filter_status

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params["limit"] = limit
        params["offset"] = offset

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM papers {where} ORDER BY citation_count DESC NULLS LAST LIMIT %(limit)s OFFSET %(offset)s",
                params,
            )
            return cur.fetchall()

    def corpus_stats(self) -> dict:
        """Get corpus statistics."""
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) AS total FROM papers")
            total = cur.fetchone()["total"]

            cur.execute(
                """SELECT year, COUNT(*) AS count FROM papers
                   WHERE year IS NOT NULL GROUP BY year ORDER BY year"""
            )
            by_year = {r["year"]: r["count"] for r in cur.fetchall()}

            cur.execute(
                """SELECT source, COUNT(*) AS count FROM papers
                   GROUP BY source ORDER BY count DESC"""
            )
            by_source = {r["source"]: r["count"] for r in cur.fetchall()}

            cur.execute(
                """SELECT venue, COUNT(*) AS count FROM papers
                   WHERE venue IS NOT NULL GROUP BY venue ORDER BY count DESC LIMIT 20"""
            )
            by_venue = {r["venue"]: r["count"] for r in cur.fetchall()}

            cur.execute(
                """SELECT filter_status, COUNT(*) AS count FROM papers
                   GROUP BY filter_status"""
            )
            by_filter = {r["filter_status"]: r["count"] for r in cur.fetchall()}

            cur.execute(
                "SELECT COUNT(*) AS count FROM papers WHERE is_classical = TRUE"
            )
            classical = cur.fetchone()["count"]

            cur.execute(
                """SELECT COUNT(DISTINCT source) AS sources
                   FROM paper_sources"""
            )
            source_count = cur.fetchone()["sources"]

            # Overlap: papers found by multiple sources
            cur.execute(
                """SELECT COUNT(*) AS count FROM (
                       SELECT paper_id FROM paper_sources
                       GROUP BY paper_id HAVING COUNT(*) > 1
                   ) multi"""
            )
            overlap = cur.fetchone()["count"]

            return {
                "total_papers": total,
                "classical_papers": classical,
                "modern_papers": total - classical,
                "unique_sources": source_count,
                "papers_in_multiple_sources": overlap,
                "by_year": by_year,
                "by_source": by_source,
                "by_venue": by_venue,
                "by_filter_status": by_filter,
            }

    def apply_compound_filter(self, top_venues: list[str] = None):
        """Apply the compound filter: citation_count >= 5 OR (year >= 2025 AND venue in TOP_VENUES).

        Updates filter_status to 'included' or 'excluded' with reason.
        """
        if top_venues is None:
            top_venues = [
                "ICLR", "ICML", "NeurIPS", "AAMAS", "AAAI", "IJCAI",
                "ACL", "EMNLP", "NAACL", "COLM",
            ]

        with get_conn() as conn:
            cur = conn.cursor()

            # Mark included: citations >= 5
            cur.execute(
                """UPDATE papers SET filter_status = 'included', filter_reason = 'citation_count >= 5'
                   WHERE citation_count >= 5 AND filter_status = 'unfiltered'"""
            )
            by_citations = cur.rowcount

            # Mark included: recent top venue
            venue_pattern = "|".join(top_venues)
            cur.execute(
                """UPDATE papers SET filter_status = 'included', filter_reason = 'recent_top_venue'
                   WHERE year >= 2025 AND venue ~* %(pattern)s
                   AND filter_status = 'unfiltered'""",
                {"pattern": venue_pattern},
            )
            by_venue = cur.rowcount

            # Mark excluded: everything else still unfiltered
            cur.execute(
                """UPDATE papers SET filter_status = 'excluded',
                   filter_reason = 'low_citations_not_top_venue'
                   WHERE filter_status = 'unfiltered'"""
            )
            excluded = cur.rowcount

            return {
                "included_by_citations": by_citations,
                "included_by_venue": by_venue,
                "excluded": excluded,
            }


# Module-level singleton
db = CorpusDB()
