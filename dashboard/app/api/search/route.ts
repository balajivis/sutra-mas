import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";
import { embed } from "@/lib/llm";

export const dynamic = "force-dynamic";

/**
 * Hybrid search: Azure AI Search (when available) with Postgres FTS fallback.
 * Mirrors dashboard_web.py /api/search behavior.
 */

function paperLink(r: Record<string, unknown>): string {
  if (r.arxiv_id) return `https://arxiv.org/abs/${r.arxiv_id}`;
  if (r.doi) return `https://doi.org/${r.doi}`;
  if (r.semantic_scholar_id)
    return `https://www.semanticscholar.org/paper/${r.semantic_scholar_id}`;
  return `https://scholar.google.com/scholar?q=${encodeURIComponent(String(r.title || "").slice(0, 100))}`;
}

/** Postgres full-text search with ts_rank */
async function dbSearch(q: string, top: number) {
  return query(
    `SELECT id, title, year, venue, citation_count, arxiv_id, doi,
            semantic_scholar_id, is_classical, has_code, repo_url,
            relevance_score, pipeline_status,
            LEFT(abstract, 300) as abstract_snippet,
            analysis->>'key_contribution_summary' as key_contribution,
            analysis->>'coordination_pattern' as coordination_pattern,
            analysis->>'theoretical_grounding' as grounding,
            analysis->>'classical_concepts_missing' as missing,
            ts_rank_cd(
              to_tsvector('english',
                COALESCE(title,'') || ' ' ||
                COALESCE(abstract,'') || ' ' ||
                COALESCE(analysis->>'key_contribution_summary','') || ' ' ||
                COALESCE(analysis->>'unique_contribution','')
              ),
              plainto_tsquery('english', $1)
            ) as rank
     FROM papers
     WHERE pipeline_status NOT IN ('archived')
       AND (
         to_tsvector('english',
           COALESCE(title,'') || ' ' ||
           COALESCE(abstract,'') || ' ' ||
           COALESCE(analysis->>'key_contribution_summary','') || ' ' ||
           COALESCE(analysis->>'unique_contribution','')
         ) @@ plainto_tsquery('english', $1)
         OR title ILIKE $2
       )
     ORDER BY rank DESC, citation_count DESC NULLS LAST
     LIMIT $3`,
    [q, `%${q}%`, top],
  );
}

/** Azure AI Search (when sutra-papers index is available) */
async function aiSearch(q: string, top: number, useVector: boolean) {
  const endpoint = process.env.SUTRA_SEARCH_ENDPOINT;
  const key = process.env.SUTRA_SEARCH_KEY;
  const index = process.env.SUTRA_SEARCH_INDEX || "sutra-papers";
  if (!endpoint || !key) return null;

  const select =
    "id,title,year,venue,citation_count,coordination_pattern," +
    "key_contribution,is_classical,cluster_label,has_code,repo_url," +
    "relevance_score,theoretical_grounding,classical_concepts_missing,arxiv_id,doi";

  const body: Record<string, unknown> = {
    search: q,
    top,
    select,
  };

  if (useVector) {
    try {
      const [qvec] = await embed([q]);
      body.vectorQueries = [
        {
          kind: "vector",
          vector: qvec,
          fields: "embedding",
          k: top,
        },
      ];
    } catch {
      // Fall back to keyword-only
    }
  }

  const res = await fetch(
    `${endpoint}/indexes/${index}/docs/search?api-version=2024-07-01`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": key,
      },
      body: JSON.stringify(body),
    },
  );

  if (!res.ok) return null;

  const data = await res.json();
  return (data.value || []).map(
    (r: Record<string, unknown>) => ({
      id: r.id,
      title: r.title || "",
      year: r.year,
      venue: r.venue,
      citations: r.citation_count || 0,
      pattern: r.coordination_pattern || "none",
      summary: (String(r.key_contribution || "")).slice(0, 200),
      classical: r.is_classical || false,
      cluster: r.cluster_label,
      has_code: r.has_code || false,
      repo_url: r.repo_url,
      grounding: r.theoretical_grounding,
      missing: r.classical_concepts_missing,
      score: Number((r as Record<string, unknown>)["@search.score"] || 0),
      link: r.arxiv_id
        ? `https://arxiv.org/abs/${r.arxiv_id}`
        : r.doi
          ? `https://doi.org/${r.doi}`
          : null,
    }),
  );
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q")?.trim() || "";
  const vector = searchParams.get("vector") === "true";
  const top = Math.min(Number(searchParams.get("top") || 15), 50);

  if (!q) {
    return NextResponse.json({ results: [], source: "none" });
  }

  // Try Azure AI Search first
  try {
    const aiResults = await aiSearch(q, top, vector);
    if (aiResults) {
      return NextResponse.json({
        results: aiResults,
        source: "azure-ai-search",
      });
    }
  } catch {
    // Fall through to Postgres
  }

  // Fallback: Postgres full-text search
  try {
    const rows = await dbSearch(q, top);
    const results = rows.map((r) => ({
      id: r.id,
      title: r.title,
      year: r.year,
      venue: r.venue,
      citations: r.citation_count || 0,
      pattern: r.coordination_pattern || "none",
      summary: (r.key_contribution || r.abstract_snippet || "").slice(0, 200),
      classical: r.is_classical || false,
      has_code: r.has_code || false,
      repo_url: r.repo_url,
      grounding: r.grounding,
      missing: r.missing,
      score: Number(r.rank || 0),
      link: paperLink(r),
    }));

    return NextResponse.json({ results, source: "postgres" });
  } catch (e) {
    return NextResponse.json(
      { results: [], source: "error", error: e instanceof Error ? e.message : "Unknown" },
      { status: 500 },
    );
  }
}
