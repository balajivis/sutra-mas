import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

const PATTERN_COLORS: Record<string, string> = {
  hierarchical: "#fbbf24",
  supervisor: "#f97316",
  peer: "#34d399",
  blackboard: "#60a5fa",
  auction: "#a78bfa",
  contract_net: "#f472b6",
  stigmergy: "#22d3ee",
  debate: "#e879f9",
  bdi: "#fb923c",
  hybrid: "#94a3b8",
  generator_critic: "#4ade80",
};

export async function GET() {
  try {
    // Stats
    const [statsRows, candidateRows] = await Promise.all([
      query(`
        SELECT
          COUNT(*) FILTER (WHERE has_code = TRUE AND reproduction_feasibility >= 4) as ready,
          COUNT(*) FILTER (WHERE has_code = TRUE AND (reproduction_feasibility IS NULL OR reproduction_feasibility < 4)) as needs_work,
          COUNT(*) FILTER (WHERE (has_code = FALSE OR has_code IS NULL)
                          AND analysis->>'coordination_pattern' IS NOT NULL
                          AND analysis->>'coordination_pattern' NOT IN ('none','null'))
            as pattern_no_code
        FROM papers
        WHERE analysis IS NOT NULL AND relevance_score >= 4
      `),
      // Top candidates: code + feasible, ordered by citations
      query(`
        SELECT p.id, p.title, p.year, p.citation_count,
               p.has_code, p.reproduction_feasibility,
               p.analysis->>'coordination_pattern' as pattern
        FROM papers p
        WHERE p.has_code = TRUE
          AND p.reproduction_feasibility >= 4
          AND p.relevance_score >= 4
          AND p.analysis IS NOT NULL
          AND p.analysis->>'coordination_pattern' IS NOT NULL
          AND p.analysis->>'coordination_pattern' NOT IN ('none','null')
        ORDER BY p.citation_count DESC NULLS LAST
        LIMIT 20
      `),
    ]);

    const stats = {
      ready: Number(statsRows[0]?.ready ?? 0),
      needs_work: Number(statsRows[0]?.needs_work ?? 0),
      pattern_no_code: Number(statsRows[0]?.pattern_no_code ?? 0),
    };

    const candidates = candidateRows.map((r) => ({
      id: r.id,
      title: r.title,
      year: r.year,
      citations: r.citation_count || 0,
      pattern: r.pattern || "none",
      pattern_color: PATTERN_COLORS[r.pattern] || "#71717a",
      has_code: r.has_code || false,
      feasibility: r.reproduction_feasibility,
    }));

    return NextResponse.json({ stats, candidates });
  } catch (e) {
    return NextResponse.json(
      { stats: { ready: 0, needs_work: 0, pattern_no_code: 0 }, candidates: [], error: e instanceof Error ? e.message : "Unknown" },
      { status: 500 },
    );
  }
}
