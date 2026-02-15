#!/usr/bin/env python3
"""Assembly Line Status Dashboard — Comprehensive Pipeline Monitor.

Shows current state of the 6-agent pipeline with detailed breakdowns:
  - Pipeline funnel (status counts with visual bars)
  - Era distribution (classical vs modern)
  - Source breakdown (CSV, API, feedback loop)
  - Citation buckets
  - Relevance score distribution
  - MAS branch classification
  - Coordination patterns (from Agent 3 analysis)
  - Feedback loop generation depth
  - Agent activity log
  - Missing classical concepts (Lost Canary signal)
  - Reproduction scout stats
  - Top papers per stage

Usage:
    python3 -m pipeline.assembly.status
    python3 -m pipeline.assembly.status --watch          # Auto-refresh every 30s
    python3 -m pipeline.assembly.status --watch --interval 10
    python3 -m pipeline.assembly.status --section funnel  # Show only one section
    python3 -m pipeline.assembly.status --compact         # Minimal output
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn

W = 72  # Dashboard width


def _bar(count, total, width=30):
    """Render a proportional bar."""
    if total == 0:
        return ""
    filled = int(count / total * width)
    return "█" * filled + "░" * (width - filled)


def _header(title):
    print()
    print(f"  ┌{'─' * (W - 4)}┐")
    print(f"  │ {title:<{W - 5}}│")
    print(f"  └{'─' * (W - 4)}┘")


def section_funnel(cur):
    """Pipeline funnel — papers at each stage."""
    _header("PIPELINE FUNNEL")

    cur.execute(
        "SELECT pipeline_status, COUNT(*) FROM papers GROUP BY pipeline_status ORDER BY COUNT(*) DESC"
    )
    status_counts = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute("SELECT COUNT(*) FROM papers")
    total = cur.fetchone()[0]

    # Ordered stages with descriptions
    stages = [
        ("seed",                    "Seeds (r1)",             "Anchor papers"),
        ("collected",               "Station 1 → 2",         "Awaiting filter"),
        ("filtering",               "Station 2 (active)",     "Being filtered"),
        ("relevant",                "Station 2 → 3",         "Score 4-5, awaiting analysis"),
        ("marginal",                "Station 2 (parked)",     "Score 3, deferred"),
        ("archived",                "Station 2 (out)",        "Score 1-2, filtered out"),
        ("analyzing",               "Station 3 (active)",     "Being analyzed"),
        ("analyzed",                "Station 3 → 4",         "Awaiting enrichment"),
        ("enriching",               "Station 4 (active)",     "Being enriched"),
        ("enriched",                "Station 4 → 5",         "Awaiting scout"),
        ("scouting",                "Station 5 (active)",     "Being scouted"),
        ("scouted",                 "Station 5 → 6",         "Awaiting repro plan"),
        ("planning_reproduction",   "Station 6 (active)",     "Being triaged"),
        ("reproduction_planned",    "COMPLETE",               "All stations done"),
    ]

    print(f"\n  Total papers in DB: {total}")
    print(f"  {'─' * (W - 4)}")
    print(f"  {'Status':<14}  {'Stage':<24}  {'Count':>6}  Bar")
    print(f"  {'─' * (W - 4)}")

    max_count = max(status_counts.values()) if status_counts else 1

    for key, label, desc in stages:
        count = status_counts.pop(key, 0)
        if count > 0:
            bar_len = int(count / max_count * 25)
            bar = "█" * max(bar_len, 1)
            print(f"  {key:<14}  {label:<24}  {count:>6}  {bar}")

    # Show any unexpected statuses
    for key, count in status_counts.items():
        if count > 0:
            print(f"  {key:<14}  {'(unknown)':<24}  {count:>6}")

    print(f"  {'─' * (W - 4)}")

    # Summary buckets (re-query since status_counts was consumed by pop())
    cur.execute("SELECT pipeline_status, COUNT(*) FROM papers GROUP BY pipeline_status")
    all_s = {row[0]: row[1] for row in cur.fetchall()}

    awaiting = all_s.get("collected", 0)
    active = sum(all_s.get(s, 0) for s in ["filtering", "analyzing", "enriching", "scouting", "planning_reproduction"])
    done_relevant = sum(all_s.get(s, 0) for s in ["relevant", "analyzed", "enriched", "scouted", "reproduction_planned"])
    marginal = all_s.get("marginal", 0)
    archived = all_s.get("archived", 0)
    complete = all_s.get("reproduction_planned", 0)

    print(f"\n  Awaiting processing:   {awaiting:>6}")
    print(f"  Active (in agents):    {active:>6}")
    print(f"  Progressing (2→done):  {done_relevant:>6}")
    print(f"  Marginal (score 3):    {marginal:>6}")
    print(f"  Archived (score 1-2):  {archived:>6}")
    print(f"  Pipeline complete:     {complete:>6}")


def section_era(cur):
    """Era distribution — classical vs modern."""
    _header("ERA DISTRIBUTION")

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
    rows = cur.fetchall()
    total = sum(r[1] for r in rows)

    for era, cnt in rows:
        pct = cnt / total * 100 if total else 0
        bar = _bar(cnt, total, 25)
        print(f"  {era:<10}  {cnt:>6}  ({pct:5.1f}%)  {bar}")

    # Classical vs modern split
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE year < 2010) as classical,
            COUNT(*) FILTER (WHERE year >= 2010 AND year < 2023) as transitional,
            COUNT(*) FILTER (WHERE year >= 2023) as modern,
            COUNT(*) FILTER (WHERE year IS NULL) as unknown
        FROM papers
    """)
    row = cur.fetchone()
    print(f"\n  Classical (<2010): {row[0]:>6}    Transitional (2010-22): {row[1]:>6}")
    print(f"  Modern (2023+):    {row[2]:>6}    Unknown year:           {row[3]:>6}")

    cur.execute("SELECT COUNT(*) FROM papers WHERE is_classical = TRUE")
    flagged = cur.fetchone()[0]
    print(f"  Flagged is_classical: {flagged}")


def section_sources(cur):
    """Source breakdown."""
    _header("SOURCES")

    cur.execute("""
        SELECT source, COUNT(*) as cnt
        FROM papers
        GROUP BY source
        ORDER BY cnt DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    total = sum(r[1] for r in rows)

    for source, cnt in rows:
        pct = cnt / total * 100 if total else 0
        print(f"  {(source or 'null'):<30}  {cnt:>6}  ({pct:5.1f}%)")


def section_citations(cur):
    """Citation count distribution."""
    _header("CITATION DISTRIBUTION")

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE citation_count IS NULL OR citation_count = 0) as no_data,
            COUNT(*) FILTER (WHERE citation_count BETWEEN 1 AND 10) as low,
            COUNT(*) FILTER (WHERE citation_count BETWEEN 11 AND 50) as moderate,
            COUNT(*) FILTER (WHERE citation_count BETWEEN 51 AND 200) as good,
            COUNT(*) FILTER (WHERE citation_count BETWEEN 201 AND 1000) as high,
            COUNT(*) FILTER (WHERE citation_count > 1000) as landmark
        FROM papers
    """)
    row = cur.fetchone()
    buckets = [
        ("No data (0)",    row[0]),
        ("1-10 cites",     row[1]),
        ("11-50 cites",    row[2]),
        ("51-200 cites",   row[3]),
        ("201-1000 cites", row[4]),
        ("1000+ cites",    row[5]),
    ]
    total = sum(b[1] for b in buckets)
    for label, cnt in buckets:
        pct = cnt / total * 100 if total else 0
        bar = _bar(cnt, total, 20)
        print(f"  {label:<18}  {cnt:>6}  ({pct:5.1f}%)  {bar}")

    cur.execute("SELECT AVG(citation_count), PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY citation_count) FROM papers WHERE citation_count > 0")
    row = cur.fetchone()
    if row[0]:
        print(f"\n  Mean citations: {row[0]:.0f}   Median: {row[1]:.0f}")


def section_relevance(cur):
    """Relevance score distribution (Agent 2 output)."""
    _header("RELEVANCE SCORES (Agent 2)")

    cur.execute("""
        SELECT relevance_score, COUNT(*) as cnt
        FROM papers
        WHERE relevance_score IS NOT NULL
        GROUP BY relevance_score
        ORDER BY relevance_score
    """)
    rows = cur.fetchall()
    if not rows:
        print("  No papers scored yet.")
        return

    total = sum(r[1] for r in rows)
    for score, cnt in rows:
        pct = cnt / total * 100 if total else 0
        bar = _bar(cnt, total, 25)
        label = {1: "Off-topic", 2: "Tangential", 3: "Marginal", 4: "Relevant", 5: "Core MAS"}.get(score, "?")
        print(f"  Score {score}: {label:<12}  {cnt:>6}  ({pct:5.1f}%)  {bar}")

    # MAS branch breakdown
    cur.execute("""
        SELECT mas_branch, COUNT(*) as cnt
        FROM papers
        WHERE mas_branch IS NOT NULL AND mas_branch != ''
        GROUP BY mas_branch
        ORDER BY cnt DESC
    """)
    branches = cur.fetchall()
    if branches:
        print(f"\n  MAS Branch Classification:")
        for branch, cnt in branches:
            print(f"    {(branch or 'unclassified'):<30}  {cnt:>6}")


def section_analysis(cur):
    """Agent 3/3b analysis stats — coordination patterns, classical concepts."""
    _header("DEEP ANALYSIS (Agent 3/3b)")

    cur.execute("SELECT COUNT(*) FROM papers WHERE analysis IS NOT NULL")
    analyzed = cur.fetchone()[0]
    print(f"  Papers with analysis: {analyzed}")

    if analyzed == 0:
        return

    # Coordination patterns
    cur.execute("""
        SELECT analysis->>'coordination_pattern' as pattern, COUNT(*) as cnt
        FROM papers
        WHERE analysis IS NOT NULL AND analysis->>'coordination_pattern' IS NOT NULL
        GROUP BY pattern
        ORDER BY cnt DESC
    """)
    patterns = cur.fetchall()
    if patterns:
        print(f"\n  Coordination Patterns:")
        for pattern, cnt in patterns:
            pct = cnt / analyzed * 100
            print(f"    {(pattern or 'null'):<22}  {cnt:>5}  ({pct:4.1f}%)")

    # Theoretical grounding
    cur.execute("""
        SELECT analysis->>'theoretical_grounding' as grounding, COUNT(*) as cnt
        FROM papers
        WHERE analysis IS NOT NULL AND analysis->>'theoretical_grounding' IS NOT NULL
        GROUP BY grounding
        ORDER BY cnt DESC
    """)
    grounding = cur.fetchall()
    if grounding:
        print(f"\n  Theoretical Grounding:")
        for level, cnt in grounding:
            print(f"    {(level or 'null'):<22}  {cnt:>5}")

    # Top missing classical concepts (Lost Canary signal!)
    cur.execute("""
        SELECT analysis->>'classical_concepts_missing' as missing, COUNT(*) as cnt
        FROM papers
        WHERE analysis IS NOT NULL
          AND analysis->>'classical_concepts_missing' IS NOT NULL
          AND analysis->>'classical_concepts_missing' != 'none'
          AND analysis->>'classical_concepts_missing' != ''
        GROUP BY missing
        ORDER BY cnt DESC
        LIMIT 10
    """)
    missing = cur.fetchall()
    if missing:
        print(f"\n  Top Missing Classical Concepts (Lost Canary signal):")
        for concept, cnt in missing:
            text = (concept or "")[:65]
            print(f"    [{cnt:>3}x]  {text}")


def section_generations(cur):
    """Feedback loop generation depth (Agent 4 safety)."""
    _header("FEEDBACK LOOP GENERATIONS (Agent 4)")

    cur.execute("""
        SELECT generation, COUNT(*) as cnt
        FROM papers
        WHERE generation IS NOT NULL
        GROUP BY generation
        ORDER BY generation
    """)
    rows = cur.fetchall()
    if not rows:
        print("  No generation data yet.")
        return

    total = sum(r[1] for r in rows)
    for gen, cnt in rows:
        pct = cnt / total * 100 if total else 0
        bar = _bar(cnt, total, 25)
        label = "Original" if gen == 0 else f"Gen {gen} (feedback)"
        print(f"  {label:<25}  {cnt:>6}  ({pct:5.1f}%)  {bar}")


def section_scout(cur):
    """Reproduction scout stats (Agent 5)."""
    _header("REPRODUCTION SCOUT (Agent 5)")

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE has_code = TRUE) as with_code,
            COUNT(*) FILTER (WHERE has_code = FALSE OR has_code IS NULL) as without_code
        FROM papers
        WHERE pipeline_status IN ('scouted', 'planning_reproduction', 'reproduction_planned')
    """)
    row = cur.fetchone()
    print(f"  With code:    {row[0]:>6}")
    print(f"  Without code: {row[1]:>6}")

    cur.execute("""
        SELECT reproduction_feasibility, COUNT(*) as cnt
        FROM papers
        WHERE reproduction_feasibility IS NOT NULL
        GROUP BY reproduction_feasibility
        ORDER BY reproduction_feasibility
    """)
    rows = cur.fetchall()
    if rows:
        print(f"\n  Reproduction Feasibility:")
        labels = {1: "Very hard", 2: "Hard", 3: "Moderate", 4: "Feasible", 5: "Easy (popular repo)"}
        for feas, cnt in rows:
            print(f"    {feas}/5 {labels.get(feas, '?'):<22}  {cnt:>5}")


def section_agents(cur):
    """Recent agent activity."""
    _header("AGENT ACTIVITY (last 50 actions)")

    cur.execute("""
        SELECT processed_by, pipeline_status, COUNT(*) as cnt,
               MAX(processed_at) as last_active
        FROM papers
        WHERE processed_by IS NOT NULL
        GROUP BY processed_by, pipeline_status
        ORDER BY last_active DESC NULLS LAST
        LIMIT 20
    """)
    rows = cur.fetchall()
    if not rows:
        print("  No agent activity recorded yet.")
        return

    print(f"  {'Agent':<28}  {'→ Status':<22}  {'Count':>6}  Last Active")
    print(f"  {'─' * (W - 4)}")
    for agent, status, cnt, last in rows:
        ts = last.strftime("%m-%d %H:%M") if last else "—"
        print(f"  {(agent or '?'):<28}  {(status or '?'):<22}  {cnt:>6}  {ts}")


def section_top_papers(cur):
    """Top papers by citation count, grouped by stage."""
    _header("TOP PAPERS BY STAGE")

    stages_to_show = [
        ("relevant", "Relevant (awaiting analysis)"),
        ("analyzed", "Analyzed (awaiting enrichment)"),
        ("enriched", "Enriched (awaiting scout)"),
        ("scouted", "Scouted (awaiting repro plan)"),
        ("reproduction_planned", "Pipeline Complete"),
    ]

    for status_key, label in stages_to_show:
        cur.execute(
            """SELECT title, year, citation_count, relevance_score
               FROM papers
               WHERE pipeline_status = %s
               ORDER BY citation_count DESC NULLS LAST
               LIMIT 5""",
            (status_key,),
        )
        rows = cur.fetchall()
        if rows:
            print(f"\n  {label}:")
            for title, year, cites, rscore in rows:
                score_str = f"R{rscore}" if rscore else "---"
                print(f"    {year or '?':4} | {cites or 0:>6} cites | {score_str:>3} | {(title or '?')[:50]}")


def run_dashboard(sections=None, compact=False):
    """Run the full dashboard."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Banner
            print()
            print(f"  {'═' * (W - 4)}")
            print(f"  ║{'SUTRA ASSEMBLY LINE — STATUS DASHBOARD':^{W - 6}}║")
            print(f"  {'═' * (W - 4)}")

            now = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {now:>{W - 4}}")

            available = {
                "funnel": section_funnel,
                "era": section_era,
                "sources": section_sources,
                "citations": section_citations,
                "relevance": section_relevance,
                "analysis": section_analysis,
                "generations": section_generations,
                "scout": section_scout,
                "agents": section_agents,
                "top": section_top_papers,
            }

            if compact:
                # Compact mode: just funnel + agents
                section_funnel(cur)
                section_agents(cur)
            elif sections:
                for s in sections:
                    if s in available:
                        available[s](cur)
                    else:
                        print(f"\n  Unknown section: {s}")
                        print(f"  Available: {', '.join(available.keys())}")
            else:
                for fn in available.values():
                    fn(cur)

            print(f"\n  {'═' * (W - 4)}")


def main():
    parser = argparse.ArgumentParser(description="Sutra Assembly Line — Status Dashboard")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=30, help="Refresh interval in seconds (default: 30)")
    parser.add_argument("--section", type=str, nargs="*", help="Show specific sections (funnel, era, sources, citations, relevance, analysis, generations, scout, agents, top)")
    parser.add_argument("--compact", action="store_true", help="Minimal output (funnel + agents only)")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                os.system("clear" if os.name != "nt" else "cls")
                run_dashboard(sections=args.section, compact=args.compact)
                print(f"\n  Refreshing in {args.interval}s... (Ctrl+C to exit)")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  Dashboard stopped.")
    else:
        run_dashboard(sections=args.section, compact=args.compact)


if __name__ == "__main__":
    main()
