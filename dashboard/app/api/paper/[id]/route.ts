import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const paperId = parseInt(id);
  if (isNaN(paperId)) {
    return NextResponse.json({ error: "Invalid paper ID" }, { status: 400 });
  }

  try {
    const rows = await query(
      `SELECT id, title, year, venue, doi, arxiv_id, semantic_scholar_id,
              citation_count, authors, abstract, source,
              is_classical, pipeline_status,
              relevance_score, relevance_rationale, mas_branch,
              analysis, modernity_score,
              has_code, repo_url, reproduction_feasibility, experiment_notes
       FROM papers WHERE id = $1`,
      [paperId]
    );

    if (rows.length === 0) {
      return NextResponse.json({ error: "Paper not found" }, { status: 404 });
    }

    const r = rows[0];

    // Build links
    const links: { label: string; url: string }[] = [];
    if (r.arxiv_id)
      links.push({ label: "ArXiv", url: `https://arxiv.org/abs/${r.arxiv_id}` });
    if (r.doi)
      links.push({ label: "DOI", url: `https://doi.org/${r.doi}` });
    if (r.semantic_scholar_id)
      links.push({
        label: "Semantic Scholar",
        url: `https://www.semanticscholar.org/paper/${r.semantic_scholar_id}`,
      });
    if (r.title)
      links.push({
        label: "Google Scholar",
        url: `https://scholar.google.com/scholar?q=${encodeURIComponent((r.title as string).slice(0, 100))}`,
      });
    if (r.repo_url)
      links.push({ label: "Code", url: r.repo_url as string });

    return NextResponse.json({
      id: r.id,
      title: r.title,
      year: r.year,
      venue: r.venue,
      doi: r.doi,
      arxiv_id: r.arxiv_id,
      citations: r.citation_count || 0,
      authors: r.authors,
      abstract: r.abstract,
      source: r.source,
      is_classical: r.is_classical || false,
      pipeline_status: r.pipeline_status,
      relevance_score: r.relevance_score,
      relevance_rationale: r.relevance_rationale,
      mas_branch: r.mas_branch,
      analysis: r.analysis || null,
      modernity_score: r.modernity_score,
      has_code: r.has_code || false,
      repo_url: r.repo_url,
      reproduction_feasibility: r.reproduction_feasibility,
      experiment_notes: r.experiment_notes,
      links,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
