#!/usr/bin/env python3
"""Agent 6: Reproduction Planner — Sixth station on the assembly line.

Polls papers with pipeline_status='scouted' and plans reproduction in two tracks:

Track A (auto, ~25 papers): Modern papers with repo_url.
  - Shallow-clone the repo
  - Attempt pip install in a throwaway venv
  - Find entry points (main.py, run.py, examples/, tests/)
  - Attempt to run with a timeout
  - Record install/run results

Track B (research, ~25 papers): Classical papers without repos.
  - Search GitHub for reimplementations
  - Search Papers with Code more broadly
  - Check if pattern maps to existing test harness (experiments/patterns/)
  - Produce a research brief for Claude Code deep-dive sessions

Pipeline: ... → Agent 5 (scouted) → Agent 6 (reproduction_planned)

Updates:
  - experiment_notes: JSON with track, brief, results, recommendation
  - pipeline_status → 'reproduction_planned'

Usage:
    python3 -m pipeline.assembly.agent6_reproducer \
        [--max-papers 50] [--auto-limit 25] [--research-limit 25] \
        [--poll-interval 60] [--once] [--skip-auto] [--skip-research]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from pipeline.assembly.db import get_conn, update_paper, count_by_status

import psycopg2.extras

# --- Config ---

GITHUB_SEARCH = "https://api.github.com/search/repositories"
PWC_BASE = "https://paperswithcode.com/api/v1"

INSTALL_TIMEOUT = 300   # 5 minutes
RUN_TIMEOUT = 180       # 3 minutes
CLONE_TIMEOUT = 60      # 1 minute

# Patterns with implementations in experiments/patterns/
HARNESS_PATTERNS = {
    "blackboard", "contract_net", "bdi", "debate",
    "generator_critic", "joint_persistent_goals", "stigmergy",
    "supervisor",
}

# Coordination patterns that are software-engineering reproducible (not ML-heavy)
SE_PATTERNS = {
    "blackboard", "contract_net", "contract net", "bdi", "belief-desire-intention",
    "pub_sub", "publish-subscribe", "broker", "mediator", "voting", "auction",
    "negotiation", "stigmergy", "shared_plans", "joint_intentions",
    "supervisor", "hierarchy", "pipeline", "debate", "generator_critic",
    "generator-critic", "facilitator", "matchmaker", "federation",
    "tuple_space", "tuple space", "linda", "actor", "actor_model",
}

# Patterns that are ML-heavy — skip for auto-reproduction
ML_PATTERNS = {
    "reinforcement_learning", "marl", "multi-agent rl", "training",
    "gradient", "neural", "deep_learning", "reward_shaping",
}


def _http_get(url: str, headers: dict | None = None, timeout: int = 15) -> dict | None:
    """Simple HTTP GET returning parsed JSON or None."""
    hdrs = {"Accept": "application/json", "User-Agent": "SutraResearch/1.0"}
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token and "github.com" in url:
        hdrs["Authorization"] = f"token {gh_token}"
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (HTTPError, URLError, TimeoutError):
        return None


def _run(cmd: list[str], timeout: int, cwd: str | None = None) -> tuple[int, str]:
    """Run a command with timeout. Returns (returncode, combined output)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode, output[-2000:]  # Truncate long output
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {timeout}s"
    except Exception as e:
        return -2, str(e)


# --- Track Classification ---

def classify_paper(paper: dict) -> str:
    """Classify a scouted paper into a reproduction track.

    Returns: 'auto', 'research', or 'skip'.
    """
    analysis = paper.get("analysis") or {}
    pattern = (analysis.get("coordination_pattern") or "").lower().replace(" ", "_")
    has_repo = bool(paper.get("repo_url"))
    is_classical = paper.get("is_classical", False)
    year = paper.get("year") or 0
    feasibility = paper.get("reproduction_feasibility") or 0

    # Skip ML-heavy patterns
    if any(ml in pattern for ml in ML_PATTERNS):
        if not has_repo:
            return "skip"

    # Track A: has a repo and is a coordination/SE pattern
    if has_repo and feasibility >= 3:
        return "auto"

    # Track B: classical or old paper, worth researching
    if is_classical or year < 2015:
        return "research"

    # Track B: modern but no repo, if it's a known SE pattern
    if any(se in pattern for se in SE_PATTERNS):
        return "research"

    # Low feasibility, no code, not a core pattern
    if feasibility <= 1:
        return "skip"

    return "research"


# --- Track A: Auto Reproduction ---

def find_entry_points(repo_dir: str) -> list[str]:
    """Find likely entry points in a cloned repo."""
    candidates = []
    priority_names = [
        "main.py", "run.py", "demo.py", "example.py", "app.py",
        "simulate.py", "experiment.py", "test.py",
    ]

    for name in priority_names:
        path = os.path.join(repo_dir, name)
        if os.path.isfile(path):
            candidates.append(path)

    # Check examples/ and demo/ directories
    for subdir in ["examples", "demo", "demos", "scripts"]:
        d = os.path.join(repo_dir, subdir)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".py") and not f.startswith("_"):
                    candidates.append(os.path.join(d, f))
                    if len(candidates) >= 5:
                        break

    return candidates[:5]


def detect_project_type(repo_dir: str) -> dict:
    """Detect what kind of Python project this is."""
    info = {"has_requirements": False, "has_setup": False, "has_pyproject": False,
            "has_dockerfile": False, "has_tests": False, "has_makefile": False,
            "python_files": 0}

    for name, key in [
        ("requirements.txt", "has_requirements"), ("setup.py", "has_setup"),
        ("pyproject.toml", "has_pyproject"), ("Dockerfile", "has_dockerfile"),
        ("Makefile", "has_makefile"),
    ]:
        if os.path.isfile(os.path.join(repo_dir, name)):
            info[key] = True

    if os.path.isdir(os.path.join(repo_dir, "tests")) or os.path.isdir(os.path.join(repo_dir, "test")):
        info["has_tests"] = True

    for root, _dirs, files in os.walk(repo_dir):
        if ".git" in root or "venv" in root or "__pycache__" in root:
            continue
        info["python_files"] += sum(1 for f in files if f.endswith(".py"))

    return info


def auto_reproduce(paper: dict, work_dir: str) -> dict:
    """Track A: Clone, install, run. Returns a result dict."""
    repo_url = paper["repo_url"]
    paper_id = paper["id"]
    result = {
        "track": "auto",
        "repo_url": repo_url,
        "clone": None, "project_type": None,
        "install": None, "run": None,
        "entry_points": [],
        "recommendation": "unknown",
    }

    # 1. Clone
    repo_dir = os.path.join(work_dir, f"repo_{paper_id}")
    rc, out = _run(["git", "clone", "--depth", "1", repo_url, repo_dir], CLONE_TIMEOUT)
    if rc != 0:
        result["clone"] = {"status": "fail", "output": out}
        result["recommendation"] = "clone_failed"
        return result
    result["clone"] = {"status": "success"}

    # 2. Detect project type
    proj = detect_project_type(repo_dir)
    result["project_type"] = proj

    if proj["python_files"] == 0:
        result["recommendation"] = "not_python"
        result["clone"]["note"] = f"No Python files found in repo"
        return result

    # 3. Install in throwaway venv
    venv_dir = os.path.join(work_dir, f"venv_{paper_id}")
    rc, out = _run([sys.executable, "-m", "venv", venv_dir], 30)
    if rc != 0:
        result["install"] = {"status": "venv_fail", "output": out}
        result["recommendation"] = "install_failed"
        return result

    pip = os.path.join(venv_dir, "bin", "pip")

    if proj["has_requirements"]:
        rc, out = _run([pip, "install", "-r", os.path.join(repo_dir, "requirements.txt")], INSTALL_TIMEOUT)
        result["install"] = {"status": "success" if rc == 0 else "fail", "method": "requirements.txt", "output": out}
    elif proj["has_setup"]:
        rc, out = _run([pip, "install", "-e", repo_dir], INSTALL_TIMEOUT)
        result["install"] = {"status": "success" if rc == 0 else "fail", "method": "setup.py", "output": out}
    elif proj["has_pyproject"]:
        rc, out = _run([pip, "install", "-e", repo_dir], INSTALL_TIMEOUT)
        result["install"] = {"status": "success" if rc == 0 else "fail", "method": "pyproject.toml", "output": out}
    else:
        result["install"] = {"status": "skipped", "note": "No requirements.txt, setup.py, or pyproject.toml"}

    # 4. Find and try entry points
    entries = find_entry_points(repo_dir)
    result["entry_points"] = [os.path.relpath(e, repo_dir) for e in entries]
    python = os.path.join(venv_dir, "bin", "python")

    if entries and result["install"] and result["install"]["status"] in ("success", "skipped"):
        entry = entries[0]
        rc, out = _run([python, entry], RUN_TIMEOUT, cwd=repo_dir)
        result["run"] = {
            "status": "success" if rc == 0 else ("timeout" if rc == -1 else "fail"),
            "entry": os.path.relpath(entry, repo_dir),
            "returncode": rc,
            "output": out,
        }

    # 5. Determine recommendation
    install_ok = result["install"] and result["install"]["status"] == "success"
    run_ok = result["run"] and result["run"]["status"] == "success"

    if run_ok:
        result["recommendation"] = "reproduce_ready"
    elif install_ok:
        result["recommendation"] = "install_ok_run_needs_work"
    elif result["install"] and result["install"]["status"] == "skipped" and entries:
        result["recommendation"] = "needs_manual_setup"
    else:
        result["recommendation"] = "install_failed"

    return result


# --- Track B: Research Triage ---

def search_github_reimplementations(pattern: str, title: str) -> list[dict]:
    """Search GitHub for reimplementations of a classical pattern."""
    repos = []
    queries = []

    if pattern and pattern != "none":
        clean = pattern.replace("_", " ")
        queries.append(f"{clean} agent python")
        queries.append(f"{clean} multi-agent implementation")

    # Also search by paper title keywords
    stop = {"a", "an", "the", "of", "in", "for", "and", "or", "with", "on", "to", "from", "by", "multi", "agent"}
    terms = [w for w in title.split() if w.lower() not in stop][:5]
    if terms:
        queries.append(" ".join(terms) + " python")

    seen_urls = set()
    for query in queries[:3]:  # Max 3 searches to stay under GitHub rate limit
        params = urlencode({"q": query, "sort": "stars", "per_page": 5})
        data = _http_get(f"{GITHUB_SEARCH}?{params}")
        time.sleep(2)  # GitHub rate limit

        if data and data.get("items"):
            for item in data["items"][:3]:
                url = item.get("html_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                repos.append({
                    "url": url,
                    "stars": item.get("stargazers_count", 0),
                    "description": (item.get("description") or "")[:200],
                    "language": item.get("language", ""),
                    "updated": item.get("updated_at", "")[:10],
                })

    return repos


def search_pwc_broader(title: str) -> list[dict]:
    """Search Papers with Code more broadly for related implementations."""
    stop = {"a", "an", "the", "of", "in", "for", "and", "or", "with", "on", "to", "from", "by"}
    terms = [w for w in title.split() if w.lower() not in stop][:6]
    query = " ".join(terms)
    params = urlencode({"q": query[:100]})
    data = _http_get(f"{PWC_BASE}/papers/?{params}")
    results = []
    if data and data.get("results"):
        for paper in data["results"][:5]:
            pid = paper.get("id")
            if pid:
                repo_data = _http_get(f"{PWC_BASE}/papers/{pid}/repositories/")
                if repo_data and repo_data.get("results"):
                    for r in repo_data["results"][:2]:
                        results.append({
                            "pwc_paper": paper.get("title", "")[:100],
                            "url": r.get("url", ""),
                            "stars": r.get("stars", 0),
                            "framework": r.get("framework", ""),
                        })
            time.sleep(0.5)
    return results


def research_triage(paper: dict) -> dict:
    """Track B: Research triage for classical papers."""
    analysis = paper.get("analysis") or {}
    pattern = (analysis.get("coordination_pattern") or "").lower().replace(" ", "_")
    title = paper.get("title", "")

    result = {
        "track": "research",
        "pattern": pattern,
        "github_repos": [],
        "pwc_repos": [],
        "harness_match": None,
        "recommendation": "needs_research",
        "brief": "",
    }

    # 1. Check if pattern matches existing harness
    pattern_normalized = pattern.replace("-", "_").replace(" ", "_")
    for hp in HARNESS_PATTERNS:
        if hp in pattern_normalized or pattern_normalized in hp:
            result["harness_match"] = hp
            break

    # 2. Search GitHub for reimplementations
    result["github_repos"] = search_github_reimplementations(pattern, title)

    # 3. Search Papers with Code
    result["pwc_repos"] = search_pwc_broader(title)

    # 4. Build brief and recommendation
    total_repos = len(result["github_repos"]) + len(result["pwc_repos"])
    starred_repos = [r for r in result["github_repos"] if r.get("stars", 0) >= 10]

    lines = []
    lines.append(f"Paper: {title}")
    lines.append(f"Pattern: {pattern or 'unknown'}")
    lines.append(f"Year: {paper.get('year', '?')}")

    if result["harness_match"]:
        lines.append(f"Harness match: experiments/patterns/{result['harness_match']}.py")
        result["recommendation"] = "reproduce_ready"

    if starred_repos:
        best = max(starred_repos, key=lambda r: r["stars"])
        lines.append(f"Best reimplementation: {best['url']} ({best['stars']} stars)")
        result["recommendation"] = "reproduce_ready"
    elif result["github_repos"]:
        lines.append(f"Found {len(result['github_repos'])} GitHub repos (low stars)")

    if result["pwc_repos"]:
        lines.append(f"Papers with Code: {len(result['pwc_repos'])} related implementations")

    if total_repos == 0 and not result["harness_match"]:
        lines.append("No implementations found. Needs Claude Code deep-dive.")
        result["recommendation"] = "needs_research"

    result["brief"] = "\n".join(lines)
    return result


# --- Main Agent Loop ---

def fetch_scouted_papers(track: str, limit: int) -> list[dict]:
    """Fetch scouted papers for a given track."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if track == "auto":
                cur.execute(
                    """SELECT id, title, year, arxiv_id, repo_url, has_code,
                              reproduction_feasibility, analysis, is_classical,
                              experiment_notes
                       FROM papers
                       WHERE pipeline_status = 'scouted'
                         AND has_code = true
                         AND repo_url IS NOT NULL
                       ORDER BY citation_count DESC
                       LIMIT %s
                       FOR UPDATE SKIP LOCKED""",
                    (limit,),
                )
            else:
                cur.execute(
                    """SELECT id, title, year, arxiv_id, repo_url, has_code,
                              reproduction_feasibility, analysis, is_classical,
                              experiment_notes
                       FROM papers
                       WHERE pipeline_status = 'scouted'
                         AND (has_code = false OR repo_url IS NULL)
                       ORDER BY citation_count DESC
                       LIMIT %s
                       FOR UPDATE SKIP LOCKED""",
                    (limit,),
                )
            rows = cur.fetchall()

            # Mark as in-progress
            for row in rows:
                cur.execute(
                    "UPDATE papers SET pipeline_status = 'planning_reproduction' WHERE id = %s",
                    (row["id"],),
                )

            return [dict(r) for r in rows]


def process_paper(paper: dict, work_dir: str) -> dict:
    """Process a single paper through the appropriate track."""
    track = classify_paper(paper)

    if track == "auto":
        return auto_reproduce(paper, work_dir)
    elif track == "research":
        return research_triage(paper)
    else:
        return {"track": "skip", "recommendation": "skip",
                "brief": "Low feasibility, ML-heavy, or not a core SE pattern."}


def main():
    parser = argparse.ArgumentParser(description="Agent 6: Reproduction Planner")
    parser.add_argument("--max-papers", type=int, default=50, help="Total papers to process")
    parser.add_argument("--auto-limit", type=int, default=25, help="Max Track A (auto) papers")
    parser.add_argument("--research-limit", type=int, default=25, help="Max Track B (research) papers")
    parser.add_argument("--poll-interval", type=int, default=60, help="Seconds between polls when idle")
    parser.add_argument("--once", action="store_true", help="Run one batch and exit")
    parser.add_argument("--skip-auto", action="store_true", help="Skip Track A (auto reproduction)")
    parser.add_argument("--skip-research", action="store_true", help="Skip Track B (research triage)")
    args = parser.parse_args()

    print("=" * 60)
    print("  AGENT 6: REPRODUCTION PLANNER")
    print("  Assembly Line — Station 6")
    print("=" * 60)
    print(f"  Track A (auto):     up to {args.auto_limit} papers")
    print(f"  Track B (research): up to {args.research_limit} papers")
    print(f"  Status: {count_by_status()}")

    auto_processed = 0
    research_processed = 0
    skipped = 0

    work_dir = tempfile.mkdtemp(prefix="sutra-reproduce-")
    print(f"  Work dir: {work_dir}")

    try:
        while True:
            did_work = False

            # Track A: Auto reproduction
            if not args.skip_auto and auto_processed < args.auto_limit:
                papers = fetch_scouted_papers("auto", min(5, args.auto_limit - auto_processed))
                for paper in papers:
                    did_work = True
                    print(f"\n  [A] Processing: {paper['title'][:60]}...")
                    print(f"      Repo: {paper['repo_url']}")

                    result = process_paper(paper, work_dir)
                    notes_json = json.dumps(result, default=str)

                    update_paper(
                        paper["id"],
                        agent_name="agent6_reproducer",
                        new_status="reproduction_planned",
                        experiment_notes=notes_json,
                    )

                    auto_processed += 1
                    print(f"      Result: {result['recommendation']}")

                    # Clean up repo + venv for this paper
                    for prefix in [f"repo_{paper['id']}", f"venv_{paper['id']}"]:
                        path = os.path.join(work_dir, prefix)
                        if os.path.exists(path):
                            shutil.rmtree(path, ignore_errors=True)

            # Track B: Research triage
            if not args.skip_research and research_processed < args.research_limit:
                papers = fetch_scouted_papers("research", min(5, args.research_limit - research_processed))
                for paper in papers:
                    did_work = True
                    print(f"\n  [B] Researching: {paper['title'][:60]}...")

                    result = process_paper(paper, work_dir)
                    notes_json = json.dumps(result, default=str)

                    update_paper(
                        paper["id"],
                        agent_name="agent6_reproducer",
                        new_status="reproduction_planned",
                        experiment_notes=notes_json,
                    )

                    research_processed += 1
                    print(f"      Recommendation: {result['recommendation']}")
                    if result.get("brief"):
                        for line in result["brief"].split("\n"):
                            print(f"      {line}")

            # Check if we've hit limits
            total = auto_processed + research_processed
            if total >= args.max_papers:
                break
            if auto_processed >= args.auto_limit and research_processed >= args.research_limit:
                break

            if not did_work:
                if args.once:
                    print("\n  No scouted papers available.")
                    break
                print(f"\n  Waiting for scouted papers... (polling every {args.poll_interval}s)")
                time.sleep(args.poll_interval)
            elif args.once:
                break

            if total % 10 == 0 and total > 0:
                print(f"\n  Progress: {auto_processed} auto + {research_processed} research = {total} total")
                print(f"  Status: {count_by_status()}")

    finally:
        # Clean up work directory
        shutil.rmtree(work_dir, ignore_errors=True)

    # Summary
    print("\n" + "=" * 60)
    print("  REPRODUCTION PLANNING COMPLETE")
    print(f"  Track A (auto):     {auto_processed} papers")
    print(f"  Track B (research): {research_processed} papers")
    print(f"  Skipped:            {skipped}")
    print(f"  Status: {count_by_status()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
