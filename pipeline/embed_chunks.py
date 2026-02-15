#!/usr/bin/env python3
"""Embed paper chunks for clustering and knowledge navigation.

Reads analyzed papers from the DB, extracts section chunks identified by
Agent 3b's LLM analysis, and embeds them using text-embedding-3-small.

Two types of chunks per paper:
  1. key_contribution_summary — the LLM-generated standalone summary
  2. sections_to_embed[].summary — LLM summaries of core sections

Stores output in pipeline/data/embeddings.npz (numpy) with metadata in
pipeline/data/embeddings_meta.json.

Usage:
    python3 -m pipeline.embed_chunks [--batch-size 16] [--resume]
"""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.apis.llm import embed
from pipeline.assembly.db import get_conn

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.npz")
META_FILE = os.path.join(DATA_DIR, "embeddings_meta.json")
EMBED_DIM = 1536  # text-embedding-3-small


def fetch_analyzed_papers(already_embedded: set[int]) -> list[dict]:
    """Fetch papers that have analysis with sections_to_embed."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, year, citation_count, arxiv_id,
                          is_classical, analysis, venue
                   FROM papers
                   WHERE analysis IS NOT NULL
                     AND pipeline_status IN ('analyzed', 'enriched', 'scouted',
                                             'reproduction_planned',
                                             'planning_reproduction')
                   ORDER BY citation_count DESC"""
            )
            cols = [d[0] for d in cur.description]
            papers = []
            for row in cur.fetchall():
                p = dict(zip(cols, row))
                if p["id"] not in already_embedded:
                    papers.append(p)
            return papers


def extract_chunks(paper: dict) -> list[dict]:
    """Extract embeddable chunks from a paper's analysis."""
    analysis = paper.get("analysis")
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            return []
    if not analysis:
        return []

    chunks = []

    # Chunk 1: Key contribution summary
    summary = analysis.get("key_contribution_summary")
    if summary and len(summary.strip()) > 20:
        chunks.append({
            "paper_id": paper["id"],
            "chunk_type": "key_contribution",
            "heading": "Key Contribution",
            "text": summary.strip(),
        })

    # Chunks 2-N: Section summaries
    sections = analysis.get("sections_to_embed") or []
    for i, sec in enumerate(sections[:5]):
        text = sec.get("summary", "").strip()
        if not text or len(text) < 20:
            continue
        chunks.append({
            "paper_id": paper["id"],
            "chunk_type": "section",
            "heading": sec.get("heading", f"Section {i+1}"),
            "text": text,
        })

    # Fallback: if no sections, use unique_contribution + methodology + key_results
    if not chunks:
        parts = []
        for field in ["unique_contribution", "methodology", "key_results"]:
            val = analysis.get(field, "")
            if val and val != "none":
                parts.append(val)
        if parts:
            chunks.append({
                "paper_id": paper["id"],
                "chunk_type": "fallback_composite",
                "heading": "Composite Summary",
                "text": " ".join(parts),
            })

    return chunks


def load_existing() -> tuple[np.ndarray | None, list[dict]]:
    """Load existing embeddings and metadata if resuming."""
    if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(META_FILE):
        data = np.load(EMBEDDINGS_FILE)
        with open(META_FILE) as f:
            meta = json.load(f)
        return data["embeddings"], meta
    return None, []


def save_results(embeddings: np.ndarray, meta: list[dict]):
    """Save embeddings and metadata to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    np.savez_compressed(EMBEDDINGS_FILE, embeddings=embeddings)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Embed paper chunks for clustering")
    parser.add_argument("--batch-size", type=int, default=16, help="Texts per embedding API call")
    parser.add_argument("--resume", action="store_true", help="Resume from existing embeddings file")
    parser.add_argument("--dry-run", action="store_true", help="Don't call embedding API, just show chunks")
    args = parser.parse_args()

    print("=" * 60)
    print("  EMBED CHUNKS — Knowledge Navigation Embeddings")
    print("=" * 60)

    # Load existing if resuming
    existing_embeddings, existing_meta = (None, [])
    already_embedded = set()
    if args.resume:
        existing_embeddings, existing_meta = load_existing()
        already_embedded = {m["paper_id"] for m in existing_meta}
        if existing_meta:
            print(f"  Resuming: {len(existing_meta)} chunks from {len(already_embedded)} papers already embedded")

    # Fetch papers
    papers = fetch_analyzed_papers(already_embedded)
    print(f"  Papers to process: {len(papers)}")

    # Extract all chunks
    all_chunks = []
    for paper in papers:
        chunks = extract_chunks(paper)
        for chunk in chunks:
            chunk["title"] = paper["title"]
            chunk["year"] = paper.get("year")
            chunk["citation_count"] = paper.get("citation_count", 0)
            chunk["is_classical"] = paper.get("is_classical", False)
            chunk["venue"] = paper.get("venue")
            analysis = paper.get("analysis")
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except json.JSONDecodeError:
                    analysis = {}
            chunk["coordination_pattern"] = (analysis or {}).get("coordination_pattern", "none")
        all_chunks.extend(chunks)

    print(f"  Total chunks to embed: {len(all_chunks)}")

    if args.dry_run:
        for c in all_chunks[:20]:
            print(f"    [{c['chunk_type']}] Paper {c['paper_id']}: {c['heading'][:40]} — {c['text'][:80]}...")
        print(f"  ... and {max(0, len(all_chunks) - 20)} more")
        return

    if not all_chunks:
        print("  No chunks to embed.")
        return

    # Batch embed
    new_embeddings = []
    texts = [c["text"] for c in all_chunks]

    for i in range(0, len(texts), args.batch_size):
        batch = texts[i:i + args.batch_size]
        try:
            vecs = embed(batch)
            new_embeddings.extend(vecs)
        except Exception as e:
            print(f"  ERROR at batch {i}: {e}")
            # Pad with zeros so indices stay aligned
            new_embeddings.extend([[0.0] * EMBED_DIM] * len(batch))

        done = min(i + args.batch_size, len(texts))
        if done % 100 == 0 or done == len(texts):
            print(f"  Embedded {done}/{len(texts)} chunks")
        time.sleep(0.1)  # Gentle rate limiting

    # Combine with existing
    new_arr = np.array(new_embeddings, dtype=np.float32)
    combined_meta = existing_meta + all_chunks

    if existing_embeddings is not None and len(existing_embeddings) > 0:
        combined_arr = np.vstack([existing_embeddings, new_arr])
    else:
        combined_arr = new_arr

    # Strip text from metadata before saving (save space, text is in DB)
    for m in combined_meta:
        m.pop("text", None)

    save_results(combined_arr, combined_meta)

    print(f"\n  Saved {len(combined_arr)} embeddings to {EMBEDDINGS_FILE}")
    print(f"  Metadata: {META_FILE}")
    print(f"  Papers covered: {len({m['paper_id'] for m in combined_meta})}")


if __name__ == "__main__":
    main()
