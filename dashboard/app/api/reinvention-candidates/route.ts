import { NextRequest, NextResponse } from "next/server";
import { query, ensureTables } from "@/lib/db";

/**
 * GET /api/reinvention-candidates
 *
 * Returns reinvention pairs: modern papers that discuss classical concepts
 * but don't cite the originating classical paper.
 *
 * Params:
 *   concept - filter by concept keyword (e.g. "contract_net", "bdi")
 *   pattern - filter by coordination pattern
 *   min_score - minimum overlap score (default 0.3)
 *   show_cited - if "true", include pairs with actual citations too (default false)
 *   limit - max results (default 200)
 */
export async function GET(req: NextRequest) {
  await ensureTables();

  const url = req.nextUrl;
  const concept = url.searchParams.get("concept");
  const pattern = url.searchParams.get("pattern");
  const minScore = parseFloat(url.searchParams.get("min_score") || "0.3");
  const showCited = url.searchParams.get("show_cited") === "true";
  const limit = Math.min(500, parseInt(url.searchParams.get("limit") || "200", 10));

  try {
    const conditions: string[] = ["re.overlap_score >= $1"];
    const params: (string | number | boolean)[] = [minScore];
    let paramIdx = 2;

    if (!showCited) {
      conditions.push("re.has_citation = FALSE");
    }

    if (concept) {
      conditions.push(`re.overlap_concepts::text ILIKE $${paramIdx}`);
      params.push(`%${concept}%`);
      paramIdx++;
    }

    if (pattern) {
      conditions.push(
        `(mp.analysis->>'coordination_pattern' = $${paramIdx} OR cp.analysis->>'coordination_pattern' = $${paramIdx})`
      );
      params.push(pattern);
      paramIdx++;
    }

    params.push(limit);

    const rows = await query(
      `SELECT
         re.modern_id,
         re.classical_id,
         re.overlap_concepts,
         re.has_citation,
         re.overlap_score,
         mp.title as modern_title,
         mp.year as modern_year,
         mp.citation_count as modern_citations,
         mp.analysis->>'coordination_pattern' as modern_pattern,
         cp.title as classical_title,
         cp.year as classical_year,
         cp.citation_count as classical_citations,
         cp.analysis->>'coordination_pattern' as classical_pattern
       FROM reinvention_edges re
       JOIN papers mp ON mp.id = re.modern_id
       JOIN papers cp ON cp.id = re.classical_id
       WHERE ${conditions.join(" AND ")}
       ORDER BY re.overlap_score DESC, cp.citation_count DESC
       LIMIT $${paramIdx}`,
      params
    );

    // Group by classical paper for the bipartite view
    const classicalMap = new Map<number, {
      id: number;
      title: string;
      year: number | null;
      citations: number;
      pattern: string | null;
      connections: {
        modern_id: number;
        modern_title: string;
        modern_year: number | null;
        modern_citations: number;
        modern_pattern: string | null;
        overlap_concepts: string[];
        has_citation: boolean;
        overlap_score: number;
      }[];
    }>();

    const modernSet = new Map<number, {
      id: number;
      title: string;
      year: number | null;
      citations: number;
      pattern: string | null;
    }>();

    for (const r of rows) {
      // Build classical entry
      if (!classicalMap.has(r.classical_id)) {
        classicalMap.set(r.classical_id, {
          id: r.classical_id,
          title: r.classical_title,
          year: r.classical_year,
          citations: r.classical_citations,
          pattern: r.classical_pattern,
          connections: [],
        });
      }
      classicalMap.get(r.classical_id)!.connections.push({
        modern_id: r.modern_id,
        modern_title: r.modern_title,
        modern_year: r.modern_year,
        modern_citations: r.modern_citations,
        modern_pattern: r.modern_pattern,
        overlap_concepts: r.overlap_concepts || [],
        has_citation: r.has_citation,
        overlap_score: r.overlap_score,
      });

      // Track modern papers
      if (!modernSet.has(r.modern_id)) {
        modernSet.set(r.modern_id, {
          id: r.modern_id,
          title: r.modern_title,
          year: r.modern_year,
          citations: r.modern_citations,
          pattern: r.modern_pattern,
        });
      }
    }

    // Get available concepts for the filter UI
    const conceptRows = await query<{ concept: string; count: string }>(
      `SELECT concept, COUNT(*) as count
       FROM (
         SELECT jsonb_array_elements_text(overlap_concepts) as concept
         FROM reinvention_edges
         WHERE has_citation = FALSE AND overlap_score >= 0.3
       ) sub
       GROUP BY concept
       ORDER BY count DESC
       LIMIT 30`
    );

    // Get available patterns
    const patternRows = await query<{ pattern: string; count: string }>(
      `SELECT p.analysis->>'coordination_pattern' as pattern, COUNT(*) as count
       FROM reinvention_edges re
       JOIN papers p ON p.id = re.modern_id
       WHERE re.has_citation = FALSE AND re.overlap_score >= 0.3
         AND p.analysis->>'coordination_pattern' IS NOT NULL
       GROUP BY pattern
       ORDER BY count DESC`
    );

    // Summary stats
    const statsRows = await query<{ total: string; reinventions: string; cited: string }>(
      `SELECT
         COUNT(*) as total,
         COUNT(CASE WHEN has_citation = FALSE THEN 1 END) as reinventions,
         COUNT(CASE WHEN has_citation = TRUE THEN 1 END) as cited
       FROM reinvention_edges
       WHERE overlap_score >= $1`,
      [minScore]
    );
    const stats = statsRows[0] || { total: "0", reinventions: "0", cited: "0" };

    return NextResponse.json({
      classical: Array.from(classicalMap.values())
        .sort((a, b) => b.citations - a.citations),
      modern: Array.from(modernSet.values())
        .sort((a, b) => (b.year || 0) - (a.year || 0)),
      stats: {
        total_pairs: parseInt(stats.total),
        reinventions: parseInt(stats.reinventions),
        cited: parseInt(stats.cited),
        classical_count: classicalMap.size,
        modern_count: modernSet.size,
      },
      filters: {
        concepts: conceptRows.map((r) => ({ concept: r.concept, count: parseInt(r.count) })),
        patterns: patternRows.map((r) => ({ pattern: r.pattern, count: parseInt(r.count) })),
      },
    });
  } catch (err) {
    console.error("[reinvention-candidates]", err);
    return NextResponse.json({ error: "Failed to fetch reinvention candidates" }, { status: 500 });
  }
}
