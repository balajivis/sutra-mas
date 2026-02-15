import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

function paperLink(r: Record<string, unknown>): string {
  if (r.arxiv_id) return `https://arxiv.org/abs/${r.arxiv_id}`;
  if (r.doi) return `https://doi.org/${r.doi}`;
  if (r.semantic_scholar_id)
    return `https://www.semanticscholar.org/paper/${r.semantic_scholar_id}`;
  return `https://scholar.google.com/scholar?q=${encodeURIComponent(String(r.title || "").slice(0, 100))}`;
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const pattern = searchParams.get("pattern")?.trim();
  const limit = Math.min(Number(searchParams.get("limit") || 100), 200);

  if (!pattern) {
    return NextResponse.json({ papers: [], error: "Missing pattern parameter" }, { status: 400 });
  }

  try {
    // Support comma-separated patterns (for merged groups)
    const patterns = pattern.split(",").map((p) => p.trim()).filter(Boolean);

    const placeholders = patterns.map((_, i) => `$${i + 1}`).join(", ");

    const rows = await query(
      `SELECT id, title, year, venue, citation_count, arxiv_id, doi,
              semantic_scholar_id, is_classical, has_code, repo_url,
              relevance_score,
              LEFT(abstract, 300) as abstract_snippet,
              analysis->>'key_contribution_summary' as key_contribution,
              analysis->>'coordination_pattern' as coordination_pattern,
              analysis->>'theoretical_grounding' as grounding,
              analysis->>'classical_concepts_missing' as missing
       FROM papers
       WHERE analysis IS NOT NULL
         AND COALESCE(analysis->>'coordination_pattern', 'null') IN (${placeholders})
       ORDER BY citation_count DESC NULLS LAST
       LIMIT $${patterns.length + 1}`,
      [...patterns, limit],
    );

    const papers = rows.map((r) => ({
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
      link: paperLink(r),
    }));

    return NextResponse.json({ papers, total: papers.length, pattern: patterns });
  } catch (e) {
    return NextResponse.json(
      { papers: [], error: e instanceof Error ? e.message : "Unknown" },
      { status: 500 },
    );
  }
}
