import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

interface InsightSpec {
  title: string;
  description: string;
  sql: string;
}

const INSIGHT_QUERIES: Record<string, InsightSpec> = {
  lost_canary: {
    title: "Lost Canary Signals",
    description:
      "Classical MAS concepts that modern LLM agent papers fail to reference or reinvent. High-frequency missing concepts suggest systematic knowledge gaps.",
    sql: `
      SELECT analysis->>'classical_concepts_missing' as concept, COUNT(*) as cnt,
             (array_agg(title ORDER BY citation_count DESC NULLS LAST))[1:5] as example_papers,
             (array_agg(id ORDER BY citation_count DESC NULLS LAST))[1:5] as paper_ids
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->>'classical_concepts_missing' IS NOT NULL
        AND analysis->>'classical_concepts_missing' NOT IN ('none','None','','null')
      GROUP BY 1 ORDER BY cnt DESC LIMIT 30`,
  },
  pattern_distribution: {
    title: "Coordination Patterns",
    description:
      "Distribution of coordination patterns across the corpus, split by classical vs modern era. Shows which patterns dominate and which are underexplored.",
    sql: `
      SELECT analysis->>'coordination_pattern' as pattern, COUNT(*) as cnt,
             COUNT(*) FILTER (WHERE is_classical) as classical_cnt,
             COUNT(*) FILTER (WHERE NOT is_classical AND year >= 2023) as modern_cnt,
             ROUND(AVG(citation_count))::int as avg_cites
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->>'coordination_pattern' IS NOT NULL
        AND analysis->>'coordination_pattern' NOT IN ('none','null','')
      GROUP BY 1 ORDER BY cnt DESC`,
  },
  grounding_gaps: {
    title: "High-Impact Papers with Weak Grounding",
    description:
      "Highly-cited papers that lack strong theoretical grounding in classical MAS. These represent opportunities for improvement through classical coordination patterns.",
    sql: `
      SELECT id, title, year, citation_count,
             analysis->>'coordination_pattern' as pattern,
             analysis->>'theoretical_grounding' as grounding,
             analysis->>'classical_concepts_missing' as missing,
             analysis->>'key_contribution_summary' as summary
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->>'theoretical_grounding' IN ('none','weak')
        AND citation_count > 50
      ORDER BY citation_count DESC
      LIMIT 50`,
  },
  rosetta_entries: {
    title: "Rosetta Stone Entries",
    description:
      "Mappings between classical MAS concepts and their modern LLM agent equivalents. Each entry bridges terminology across eras.",
    sql: `
      SELECT analysis->>'rosetta_entry' as entry, COUNT(*) as cnt,
             (array_agg(title ORDER BY citation_count DESC NULLS LAST))[1:3] as example_papers,
             (array_agg(id ORDER BY citation_count DESC NULLS LAST))[1:3] as paper_ids
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->'rosetta_entry' IS NOT NULL
        AND analysis->>'rosetta_entry' NOT IN ('null','','{}')
      GROUP BY 1 ORDER BY cnt DESC LIMIT 30`,
  },
  cross_era_bridges: {
    title: "Modern Papers with Strong Classical Grounding",
    description:
      "Recent papers (2023+) that successfully build on classical MAS foundations. These represent best practices for bridging the eras.",
    sql: `
      SELECT id, title, year, citation_count,
             analysis->>'coordination_pattern' as pattern,
             analysis->>'theoretical_grounding' as grounding,
             analysis->'classical_concepts' as concepts,
             analysis->>'key_contribution_summary' as summary
      FROM papers
      WHERE analysis IS NOT NULL
        AND year >= 2023
        AND analysis->>'theoretical_grounding' = 'strong'
      ORDER BY citation_count DESC
      LIMIT 50`,
  },
};

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ type: string }> }
) {
  const { type } = await params;
  const spec = INSIGHT_QUERIES[type];
  if (!spec) {
    return NextResponse.json(
      { error: `Unknown insight type: ${type}` },
      { status: 404 }
    );
  }

  try {
    const rows = await query(spec.sql);
    return NextResponse.json({
      type,
      title: spec.title,
      description: spec.description,
      data: rows,
      total: rows.length,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
