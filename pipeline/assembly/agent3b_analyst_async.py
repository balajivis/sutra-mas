#!/usr/bin/env python3
"""Agent 3b: Async Pipelined Analyst — Station 3 on the assembly line.

Polls papers with pipeline_status='relevant', downloads ArXiv LaTeX source
sequentially (3.1s rate limit), but fires GPT-5.1 extraction calls concurrently
via a thread pool. Results are written to DB as they arrive (out of order).

Pipeline architecture:
    Main thread (every 3.1s):
      1. Check thread pool for completed LLM results → write to DB
      2. Poll DB for next 'relevant' paper → mark 'analyzing'
      3. Download ArXiv LaTeX (blocking, 3.1s)
      4. Submit LLM extraction to thread pool (non-blocking)
      5. Repeat

    Thread pool (--concurrent workers, default 10):
      - Each worker runs one GPT-5.1 call (~20-30s)
      - With 3.1s between submissions, naturally maintains ~10 in-flight
      - Papers without arxiv_id skip the download and submit instantly

Uses GPT-5.1 (Azure OpenAI).

Usage:
    python3 -m pipeline.assembly.agent3b_analyst_async --concurrent 10 --max-papers 5000
    python3 -m pipeline.assembly.agent3b_analyst_async --once
"""

import argparse
import concurrent.futures
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
from pipeline.apis.llm import gpt_chat_json

import psycopg2.extras

SYSTEM_PROMPT = """You are a research analyst bridging classical Multi-Agent Systems (MAS, 1980-2010) with modern LLM agent systems (2023-2026).

Analyze this paper and extract structured metadata. Your analysis should specifically identify:
1. What classical MAS concepts this paper uses, extends, or reinvents
2. How its contributions map to modern LLM agent coordination
3. What classical concepts WOULD have helped but are NOT mentioned
4. The core sections worth embedding for clustering and knowledge navigation

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
  "key_results": "Quantitative findings if any, otherwise qualitative summary. 1-2 sentences.",
  "key_contribution_summary": "A 3-5 sentence standalone summary of this paper's core contribution, written for a researcher navigating a knowledge map. Should be self-contained — readable without the original paper. Include the problem, approach, and main finding.",
  "sections_to_embed": [
    {
      "heading": "Exact LaTeX section heading or identifier (e.g., '\\\\section{Coordination Protocol}' or 'Section 3: Architecture')",
      "reason": "Why this section matters for the survey (1 sentence)",
      "summary": "A 2-4 sentence summary of this section's content, capturing the key ideas in plain language"
    }
  ]
}

For sections_to_embed: Identify the 3-5 most important sections from the paper for embedding and clustering. Focus on sections that describe the CORE CONTRIBUTION — methodology, architecture, algorithm, protocol design, or key results. Skip boilerplate (intro fluff, related work, acknowledgements). If working from an abstract only, return a single entry with heading "Abstract" and a good summary."""


def download_arxiv_latex(arxiv_id: str) -> str | None:
    """Download and extract LaTeX source from ArXiv."""
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

    tex_content = []

    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith(".tex") and member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        tex_content.append(f.read().decode("utf-8", errors="replace"))
    except (tarfile.TarError, gzip.BadGzipFile):
        try:
            text = gzip.decompress(content).decode("utf-8", errors="replace")
            tex_content.append(text)
        except Exception:
            try:
                text = content.decode("utf-8", errors="replace")
                if "\\begin{document}" in text or "\\section" in text:
                    tex_content.append(text)
            except Exception:
                return None

    if not tex_content:
        return None

    full_text = "\n\n".join(tex_content)

    lines = []
    for line in full_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        line = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(line)

    cleaned = "\n".join(lines)

    if len(cleaned) > 15000:
        cleaned = cleaned[:15000] + "\n\n[... truncated for analysis ...]"

    return cleaned


def _run_llm_extraction(paper: dict, latex_source: str | None) -> tuple[dict, dict | None, str | None]:
    """Run GPT-5.1 extraction in a worker thread.

    Returns (paper, analysis_dict_or_None, latex_source).
    """
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
        result = gpt_chat_json(
            system=SYSTEM_PROMPT,
            user_message=user_msg,
            max_tokens=8192,
        )
        return (paper, result, latex_source)
    except Exception as e:
        print(f"  [3b] LLM error for '{title[:50]}': {e}", flush=True)
        return (paper, None, latex_source)


def poll_next_paper() -> dict | None:
    """Poll for the next relevant paper and mark it as analyzing."""
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
                return None
            paper = dict(row)

            cur.execute(
                "UPDATE papers SET pipeline_status = 'analyzing' WHERE id = %s",
                (paper["id"],),
            )
            return paper


def write_result(paper: dict, analysis: dict | None, latex_source: str | None) -> bool:
    """Write LLM result to DB. Returns True if successful."""
    if analysis:
        update_paper(
            paper["id"],
            agent_name="agent3b_analyst_async",
            new_status="analyzed",
            analysis=psycopg2.extras.Json(analysis),
            latex_source=latex_source[:50000] if latex_source else None,
        )
        return True
    else:
        update_paper(
            paper["id"],
            agent_name="agent3b_analyst_async",
            new_status="relevant",
        )
        return False


def drain_completed(futures_map: dict, done_set: set | None = None) -> tuple[int, int]:
    """Check for completed futures and write results."""
    successes = 0
    failures = 0

    if done_set is None:
        done_set = set()
        for f in list(futures_map.keys()):
            if f.done():
                done_set.add(f)

    for future in done_set:
        paper, analysis, latex = future.result()
        ok = write_result(paper, analysis, latex)
        if ok:
            successes += 1
            print(f"  [3b] Analyzed: {paper['title'][:60]}", flush=True)
        else:
            failures += 1
            print(f"  [3b] Failed:   {paper['title'][:60]}", flush=True)
        del futures_map[future]

    return successes, failures


def main():
    parser = argparse.ArgumentParser(description="Agent 3b: Pipelined Analyst (GPT-5.1)")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls when idle")
    parser.add_argument("--once", action="store_true", help="Process one paper and exit")
    parser.add_argument("--max-papers", type=int, default=5000, help="Max papers to process (default: 5000)")
    parser.add_argument("--concurrent", type=int, default=10, help="Max in-flight LLM calls (default: 10)")
    # Backward compat alias
    parser.add_argument("--max-concurrent", type=int, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    concurrent_count = args.max_concurrent or args.concurrent

    print("=" * 60, flush=True)
    print("  AGENT 3b: PIPELINED ANALYST", flush=True)
    print("  Assembly Line — Station 3", flush=True)
    print("=" * 60, flush=True)
    print(f"  Model:       GPT-5.1 (Azure OpenAI)", flush=True)
    print(f"  LLM workers: {concurrent_count} parallel", flush=True)
    print(f"  ArXiv:       single-threaded (3.1s rate limit)", flush=True)
    print(f"  Max papers:  {args.max_papers}", flush=True)
    print(f"  Status:      {count_by_status()}", flush=True)

    total_polled = 0
    total_analyzed = 0
    total_failed = 0
    idle_streak = 0

    futures_map = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
        while total_polled < args.max_papers:
            # 1. Drain completed futures
            s, f = drain_completed(futures_map)
            total_analyzed += s
            total_failed += f

            # 2. If at max concurrent, wait for one to finish
            if len(futures_map) >= concurrent_count:
                done, _ = concurrent.futures.wait(
                    futures_map.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                s, f = drain_completed(futures_map, done)
                total_analyzed += s
                total_failed += f

            # 3. Poll for next paper
            paper = poll_next_paper()
            if not paper:
                if args.once:
                    break
                idle_streak += 1
                if idle_streak > 1 and not futures_map:
                    print(f"  [3b] No relevant papers. Waiting {args.poll_interval}s...", flush=True)
                    time.sleep(args.poll_interval)
                else:
                    time.sleep(1)
                continue

            idle_streak = 0
            total_polled += 1

            # 4. Download LaTeX (blocking, single-threaded, respects ArXiv rate limit)
            arxiv_id = paper.get("arxiv_id")
            latex_source = None
            if arxiv_id:
                latex_source = download_arxiv_latex(arxiv_id)
                time.sleep(3.1)  # ArXiv rate limit

            # 5. Submit LLM call to thread pool (non-blocking)
            future = executor.submit(_run_llm_extraction, paper, latex_source)
            futures_map[future] = paper

            if total_polled % 10 == 0:
                print(f"  [3b] Polled: {total_polled}, Analyzed: {total_analyzed}, "
                      f"Failed: {total_failed}, In-flight: {len(futures_map)}",
                      flush=True)
                print(f"       Status: {count_by_status()}", flush=True)

            if args.once:
                break

        # Drain remaining in-flight calls
        if futures_map:
            print(f"  [3b] Draining {len(futures_map)} in-flight LLM calls...", flush=True)
            done, _ = concurrent.futures.wait(futures_map.keys())
            s, f = drain_completed(futures_map, done)
            total_analyzed += s
            total_failed += f

    print(f"\n  Agent 3b complete.", flush=True)
    print(f"  Polled: {total_polled}, Analyzed: {total_analyzed}, Failed: {total_failed}", flush=True)


if __name__ == "__main__":
    main()
