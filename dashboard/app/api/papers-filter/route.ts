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

// Era label → SQL WHERE clause fragment (p. prefix for table alias)
const ERA_FILTERS: Record<string, string> = {
  "< 1990": "p.year < 1990",
  "1990s": "p.year >= 1990 AND p.year < 2000",
  "2000s": "p.year >= 2000 AND p.year < 2010",
  "2010s": "p.year >= 2010 AND p.year < 2020",
  "2020-22": "p.year >= 2020 AND p.year < 2023",
  "2023-24": "p.year >= 2023 AND p.year < 2025",
  "2025+": "p.year >= 2025",
  "unknown": "p.year IS NULL",
};

// Citation label → SQL WHERE clause fragment
const CITE_FILTERS: Record<string, string> = {
  "No data": "(p.citation_count IS NULL OR p.citation_count = 0)",
  "1-10": "p.citation_count >= 1 AND p.citation_count <= 10",
  "11-50": "p.citation_count >= 11 AND p.citation_count <= 50",
  "51-200": "p.citation_count >= 51 AND p.citation_count <= 200",
  "201-1K": "p.citation_count >= 201 AND p.citation_count <= 1000",
  "1K+": "p.citation_count > 1000",
};

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const pattern = searchParams.get("pattern")?.trim();
  const era = searchParams.get("era")?.trim();
  const citations = searchParams.get("citations")?.trim();
  const relevance = searchParams.get("relevance")?.trim();
  const branch = searchParams.get("branch")?.trim();
  const cluster = searchParams.get("cluster")?.trim();
  const q = searchParams.get("q")?.trim();
  const hasCode = searchParams.get("has_code")?.trim();
  const feasibility = searchParams.get("feasibility")?.trim();
  const minRelevance = searchParams.get("min_relevance");
  const limit = Math.min(Number(searchParams.get("limit") || 100), 200);

  if (!pattern && !era && !citations && !relevance && !branch && !cluster && !q && !hasCode && !feasibility) {
    return NextResponse.json(
      { papers: [], error: "Provide at least one filter" },
      { status: 400 },
    );
  }

  try {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let paramIdx = 1;

    // Pattern filter (comma-separated)
    if (pattern) {
      const patterns = pattern.split(",").map((p) => p.trim()).filter(Boolean);
      const placeholders = patterns.map(() => `$${paramIdx++}`).join(", ");
      conditions.push(
        `COALESCE(p.analysis->>'coordination_pattern', 'null') IN (${placeholders})`
      );
      params.push(...patterns);
    }

    // Era filter
    if (era && ERA_FILTERS[era]) {
      conditions.push(ERA_FILTERS[era]);
    }

    // Citation filter
    if (citations && CITE_FILTERS[citations]) {
      conditions.push(CITE_FILTERS[citations]);
    }

    // Relevance score filter (1-5)
    if (relevance) {
      const score = parseInt(relevance);
      if (score >= 1 && score <= 5) {
        conditions.push(`p.relevance_score = $${paramIdx++}`);
        params.push(score);
      }
    }

    // MAS branch filter
    if (branch) {
      conditions.push(`p.mas_branch = $${paramIdx++}`);
      params.push(branch);
    }

    // Cluster filter (requires JOIN with paper_clusters)
    let clusterJoin = "";
    if (cluster) {
      const cid = parseInt(cluster);
      if (!isNaN(cid)) {
        clusterJoin = "JOIN paper_clusters pc ON pc.paper_id = p.id";
        conditions.push(`pc.cluster_id = $${paramIdx++}`);
        params.push(cid);
      }
    }

    // Has code filter
    if (hasCode === "true") {
      conditions.push("p.has_code = TRUE");
    } else if (hasCode === "false") {
      conditions.push("(p.has_code = FALSE OR p.has_code IS NULL)");
    }

    // Feasibility filter (e.g. "4" for >= 4, or "4,5" for exact values)
    if (feasibility) {
      const vals = feasibility.split(",").map(Number).filter((n) => n >= 1 && n <= 5);
      if (vals.length === 1) {
        conditions.push(`p.reproduction_feasibility = $${paramIdx++}`);
        params.push(vals[0]);
      } else if (vals.length > 1) {
        const placeholders = vals.map(() => `$${paramIdx++}`).join(", ");
        conditions.push(`p.reproduction_feasibility IN (${placeholders})`);
        params.push(...vals);
      }
    }

    // Text search (FTS + ILIKE fallback)
    let hasTextSearch = false;
    if (q) {
      hasTextSearch = true;
      conditions.push(`(
        to_tsvector('english',
          COALESCE(p.title,'') || ' ' ||
          COALESCE(p.abstract,'') || ' ' ||
          COALESCE(p.analysis->>'key_contribution_summary','') || ' ' ||
          COALESCE(p.analysis->>'unique_contribution','')
        ) @@ plainto_tsquery('english', $${paramIdx})
        OR p.title ILIKE $${paramIdx + 1}
      )`);
      params.push(q, `%${q}%`);
      paramIdx += 2;
    }

    // Default minimum relevance floor: when browsing by era/citations/pattern/branch
    // (but NOT when explicitly filtering by relevance score), exclude off-topic papers.
    // Override with min_relevance=0 to see everything.
    if (!relevance && !cluster) {
      const floor = minRelevance !== null ? parseInt(minRelevance) : 3;
      if (floor > 0) {
        conditions.push(`p.relevance_score >= $${paramIdx++}`);
        params.push(floor);
      }
    }

    const whereClause = conditions.length > 0
      ? `WHERE ${conditions.join(" AND ")}`
      : "";

    // When text searching, order by relevance rank first, then citations
    const rankExpr = hasTextSearch
      ? `ts_rank_cd(
          to_tsvector('english',
            COALESCE(p.title,'') || ' ' ||
            COALESCE(p.abstract,'') || ' ' ||
            COALESCE(p.analysis->>'key_contribution_summary','') || ' ' ||
            COALESCE(p.analysis->>'unique_contribution','')
          ),
          plainto_tsquery('english', $${paramIdx})
        )`
      : "0";
    const orderClause = hasTextSearch
      ? `ORDER BY search_rank DESC, p.citation_count DESC NULLS LAST`
      : `ORDER BY p.citation_count DESC NULLS LAST`;

    // Add the rank query param if text search is active
    if (hasTextSearch) {
      params.push(q);
      paramIdx++;
    }

    const rows = await query(
      `SELECT p.id, p.title, p.year, p.venue, p.citation_count, p.arxiv_id, p.doi,
              p.semantic_scholar_id, p.is_classical, p.has_code, p.repo_url,
              p.relevance_score, p.mas_branch,
              LEFT(p.abstract, 300) as abstract_snippet,
              p.analysis->>'key_contribution_summary' as key_contribution,
              p.analysis->>'coordination_pattern' as coordination_pattern,
              p.analysis->>'theoretical_grounding' as grounding,
              p.reproduction_feasibility,
              p.analysis->>'classical_concepts_missing' as missing,
              ${rankExpr} as search_rank
       FROM papers p
       ${clusterJoin}
       ${whereClause}
       ${orderClause}
       LIMIT $${paramIdx}`,
      [...params, limit],
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
      relevance: r.relevance_score || null,
      grounding: r.grounding,
      feasibility: r.reproduction_feasibility || null,
      missing: r.missing,
      link: paperLink(r),
    }));

    return NextResponse.json({ papers, total: papers.length });
  } catch (e) {
    return NextResponse.json(
      { papers: [], error: e instanceof Error ? e.message : "Unknown" },
      { status: 500 },
    );
  }
}
