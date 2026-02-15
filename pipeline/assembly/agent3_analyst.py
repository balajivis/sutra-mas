#!/usr/bin/env python3
"""Agent 3: Deep Analyst — Third station on the assembly line.

Polls papers with pipeline_status='relevant', downloads ArXiv LaTeX source,
sends full text to Opus 4.6 for structured extraction.

Output (analysis JSONB):
  - classical_concepts: which MAS concepts this paper uses/extends
  - modern_mapping: how this maps to LLM agent systems
  - unique_contribution: 1-2 sentences
  - rosetta_entry: classical term → modern equivalent
  - gap_identified: what classical MAS concept would have helped but wasn't mentioned
  - coordination_pattern: supervisor|peer|blackboard|stigmergy|auction|...
  - failure_modes_addressed: which of Cemri's 14 failure modes this paper addresses
  - theoretical_grounding: strong|moderate|weak|none

Usage:
    python3 -m pipeline.assembly.agent3_analyst [--poll-interval 30] [--once]
"""

import argparse
import gzip
import io
import json
import os
import re
import sys
import tarfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, update_paper, count_by_status
from pipeline.apis.llm import chat_json

import psycopg2.extras

SYSTEM_PROMPT = """You are a research analyst bridging classical Multi-Agent Systems (MAS, 1980-2010) with modern LLM agent systems (2023-2026).

Analyze this paper and extract structured metadata. Your analysis should specifically identify:
1. What classical MAS concepts this paper uses, extends, or reinvents
2. How its contributions map to modern LLM agent coordination
3. What classical concepts WOULD have helped but are NOT mentioned

Return a JSON object:
{
  "classical_concepts": ["list of classical MAS concepts used or referenced (e.g., 'contract net', 'BDI', 'blackboard', 'SharedPlans', 'FIPA ACL')"],
  "classical_concepts_missing": "What classical concept would have improved this work but wasn't mentioned? Be specific — name the concept AND explain how it would help. Say 'none' if the paper is well-grounded.",
  "modern_mapping": ["list of modern equivalents or implementations (e.g., 'LangGraph state = blackboard', 'CrewAI roles = organizational paradigms')"],
  "unique_contribution": "1-2 sentences: what is genuinely novel in this paper?",
  "rosetta_entry": {"classical_term": "modern_equivalent"} or null if no clear mapping,
  "coordination_pattern": "The primary coordination pattern: supervisor | peer | blackboard | stigmergy | auction | contract_net | debate | generator_critic | bdi | hierarchical | flat | hybrid | none",
  "failure_modes_addressed": ["Which of Cemri et al.'s failure modes does this address: task_decomposition | agent_selection | result_integration | communication_overhead | context_loss | hallucination_cascade | infinite_loop | role_confusion | goal_drift | partial_failure | coordination_overhead | inconsistent_state | evaluation_difficulty | scalability"],
  "theoretical_grounding": "strong (cites foundational theory) | moderate (some theory) | weak (engineering-only) | none",
  "methodology": "What did they do? 1-2 sentences.",
  "key_results": "Quantitative findings if any, otherwise qualitative summary. 1-2 sentences."
}"""


def download_arxiv_latex(arxiv_id: str) -> str | None:
    """Download and extract LaTeX source from ArXiv.

    Returns cleaned LaTeX text or None if unavailable.
    """
    # Normalize arxiv ID (remove version)
    clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

    url = f"https://arxiv.org/e-print/{clean_id}"
    headers = {"User-Agent": "SutraResearch/1.0 (research@getkapi.com)"}
    req = Request(url, headers=headers)

    try:
        with urlopen(req, timeout=30) as resp:
            content = resp.read()
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception:
        return None

    # ArXiv returns either a .tar.gz or a single .tex/.gz file
    tex_content = []

    try:
        # Try as tar.gz first
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith(".tex") and member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        tex_content.append(f.read().decode("utf-8", errors="replace"))
    except (tarfile.TarError, gzip.BadGzipFile):
        try:
            # Try as gzipped single file
            text = gzip.decompress(content).decode("utf-8", errors="replace")
            tex_content.append(text)
        except Exception:
            try:
                # Try as plain text
                text = content.decode("utf-8", errors="replace")
                if "\\begin{document}" in text or "\\section" in text:
                    tex_content.append(text)
            except Exception:
                return None

    if not tex_content:
        return None

    # Combine and clean
    full_text = "\n\n".join(tex_content)

    # Basic LaTeX cleaning — remove comments, keep structure
    lines = []
    for line in full_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        # Remove inline comments (but keep \%)
        line = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(line)

    cleaned = "\n".join(lines)

    # Truncate to ~15K chars to stay within token limits
    if len(cleaned) > 15000:
        cleaned = cleaned[:15000] + "\n\n[... truncated for analysis ...]"

    return cleaned


def analyze_paper(paper: dict) -> dict | None:
    """Send a paper to Opus 4.6 for structured analysis."""
    arxiv_id = paper.get("arxiv_id")
    latex_source = None

    # Try to get full LaTeX
    if arxiv_id:
        latex_source = download_arxiv_latex(arxiv_id)
        time.sleep(3.1)  # ArXiv rate limit: 1 req/3sec

    # Build the user message
    if latex_source:
        content = f"FULL LATEX SOURCE:\n{latex_source}"
    else:
        abstract = paper.get("abstract") or "No abstract available."
        content = f"ABSTRACT ONLY (no LaTeX available):\n{abstract}"

    title = paper.get("title", "Untitled")
    year = paper.get("year", "?")
    venue = paper.get("venue", "Unknown venue")

    user_msg = f"""Paper: {title}
Year: {year}
Venue: {venue}

{content}"""

    try:
        result = chat_json(
            system=SYSTEM_PROMPT,
            user_message=user_msg,
            model="claude-opus-4-6",
            max_tokens=2048,
            temperature=0.2,
        )
        return result, latex_source
    except Exception as e:
        print(f"  [Analyst] LLM error for '{title[:50]}': {e}")
        return None, latex_source


def poll_and_analyze() -> int:
    """Poll for relevant papers and analyze one. Returns 1 if processed, 0 if idle."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, title, year, abstract, venue, arxiv_id
                   FROM papers
                   WHERE pipeline_status = 'relevant'
                   ORDER BY citation_count DESC
                   LIMIT 1
                   FOR UPDATE SKIP LOCKED""",
                (),
            )
            row = cur.fetchone()
            if not row:
                return 0
            paper = dict(row)

            # Mark as processing
            cur.execute(
                "UPDATE papers SET pipeline_status = 'analyzing' WHERE id = %s",
                (paper["id"],),
            )

    # Process outside transaction (slow: ArXiv download + LLM call)
    result = analyze_paper(paper)

    if result and result[0]:
        analysis, latex = result
        update_paper(
            paper["id"],
            agent_name="agent3_analyst",
            new_status="analyzed",
            analysis=psycopg2.extras.Json(analysis),
            latex_source=latex[:50000] if latex else None,  # Cap storage
        )
        return 1
    else:
        # Failed — put back as relevant for retry
        _, latex = result if result else (None, None)
        update_paper(
            paper["id"],
            agent_name="agent3_analyst",
            new_status="relevant",
        )
        return 0


def main():
    parser = argparse.ArgumentParser(description="Agent 3: Deep Analyst")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls when idle")
    parser.add_argument("--once", action="store_true", help="Process one paper and exit")
    parser.add_argument("--max-papers", type=int, default=0, help="Max papers to process (0=unlimited)")
    args = parser.parse_args()

    print("=" * 60)
    print("  AGENT 3: DEEP ANALYST")
    print("  Assembly Line — Station 3")
    print("=" * 60)
    print(f"  Model: claude-opus-4-6")
    print(f"  ArXiv LaTeX: enabled (3s rate limit)")
    print(f"  Status: {count_by_status()}")

    total_processed = 0

    while True:
        n = poll_and_analyze()
        if n > 0:
            total_processed += n
            print(f"  Analyzed {total_processed} papers. Status: {count_by_status()}")

            if args.once:
                break
            if args.max_papers and total_processed >= args.max_papers:
                break
        else:
            if args.once:
                print("  No papers to analyze.")
                break
            print(f"  Waiting for relevant papers... (polling every {args.poll_interval}s)")
            time.sleep(args.poll_interval)

    print(f"\n  Analyst complete. Processed: {total_processed} papers.")


if __name__ == "__main__":
    main()
