import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export async function GET() {
  try {
    // Only count high-relevance papers (4-5) for dashboard stats
    const REL_FILTER = "AND relevance_score >= 4";

    const patterns = await query(`
      SELECT
        analysis->>'coordination_pattern' as pattern,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE year < 2010) as classical,
        COUNT(*) FILTER (WHERE year >= 2023) as modern,
        ROUND(AVG(citation_count))::int as avg_cites,
        array_agg(DISTINCT analysis->>'theoretical_grounding') as grounding_types
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->>'coordination_pattern' IS NOT NULL
        AND analysis->>'coordination_pattern' NOT IN ('none','null','')
        ${REL_FILTER}
      GROUP BY 1
      ORDER BY total DESC
    `);

    // Also get some quick stats
    const stats = await query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE analysis IS NOT NULL) as analyzed,
        COUNT(*) FILTER (WHERE year < 2010) as classical,
        COUNT(*) FILTER (WHERE year >= 2023) as modern,
        COUNT(*) FILTER (WHERE pipeline_status = 'archived') as archived,
        COUNT(DISTINCT analysis->>'coordination_pattern')
          FILTER (WHERE analysis->>'coordination_pattern' NOT IN ('none','null','')) as pattern_count
      FROM papers
      WHERE relevance_score >= 4
    `);

    return NextResponse.json({ patterns, stats: stats[0] || {} });
  } catch (e) {
    return NextResponse.json(
      { patterns: [], stats: {}, error: e instanceof Error ? e.message : "Unknown" },
      { status: 500 }
    );
  }
}
