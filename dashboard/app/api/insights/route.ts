import { NextResponse } from "next/server";
import { query, ensureTables } from "@/lib/db";
import { chatJSON } from "@/lib/llm";

interface InsightSpec {
  title: string;
  sql: string;
}

// Named classical MAS concepts to extract from free-text classical_concepts_missing field
const LOST_CANARY_CONCEPTS: [string, string][] = [
  ["BDI", "BDI|belief.desire.intention"],
  ["Blackboard", "blackboard"],
  ["Contract Net", "contract.net"],
  ["FIPA Protocols", "FIPA"],
  ["Joint Intentions", "joint.intention|joint.persistent"],
  ["SharedPlans", "[Ss]hared.?[Pp]lans?"],
  ["Organizational Models", "organizational.*(model|paradigm|structure|framework)"],
  ["MOISE/AGR", "MOISE|AGR"],
  ["HTN Planning", "HTN|hierarchical.task.network"],
  ["Normative MAS", "norm.based|normative"],
  ["Argumentation", "argument\\w*\\s*framework"],
  ["Consensus Protocols", "consensus"],
  ["Trust & Reputation", "trust.{0,10}reputation|reputation.{0,10}trust"],
  ["Auction/Mechanism Design", "auction|mechanism.design"],
  ["KQML", "KQML"],
  ["Mixed-Initiative", "mixed.initiative"],
];

const ANALYZED_BASE = `analysis IS NOT NULL
    AND analysis->>'classical_concepts_missing' IS NOT NULL
    AND analysis->>'classical_concepts_missing' NOT IN ('none','None','','null')`;

function buildLostCanarySQL(): string {
  const unions = LOST_CANARY_CONCEPTS.map(
    ([name, pattern]) => `
    SELECT '${name}' as concept, COUNT(*) as cnt,
           (array_agg(title ORDER BY citation_count DESC NULLS LAST))[1:3] as example_papers,
           (array_agg(id ORDER BY citation_count DESC NULLS LAST))[1:3] as paper_ids
    FROM papers
    WHERE ${ANALYZED_BASE}
      AND analysis->>'classical_concepts_missing' ~* '${pattern}'`
  ).join("\n  UNION ALL");

  return `SELECT * FROM (${unions}\n  ) sub WHERE cnt > 0 ORDER BY cnt DESC`;
}

const INSIGHT_QUERIES: Record<string, InsightSpec> = {
  lost_canary: {
    title: "Lost Canary Signals",
    sql: buildLostCanarySQL(),
  },
  pattern_distribution: {
    title: "Coordination Patterns",
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
    sql: `
      SELECT id, title, year, citation_count,
             analysis->>'coordination_pattern' as pattern,
             analysis->>'theoretical_grounding' as grounding,
             analysis->>'classical_concepts_missing' as missing
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->>'theoretical_grounding' IN ('none','weak')
        AND citation_count > 50
      ORDER BY citation_count DESC
      LIMIT 15`,
  },
  rosetta_entries: {
    title: "Rosetta Stone Entries",
    sql: `
      SELECT analysis->>'rosetta_entry' as entry, COUNT(*) as cnt
      FROM papers
      WHERE analysis IS NOT NULL
        AND analysis->'rosetta_entry' IS NOT NULL
        AND analysis->>'rosetta_entry' NOT IN ('null','','{}')
      GROUP BY 1 ORDER BY cnt DESC LIMIT 15`,
  },
  cross_era_bridges: {
    title: "Modern Papers with Strong Classical Grounding",
    sql: `
      SELECT id, title, year, citation_count,
             analysis->>'coordination_pattern' as pattern,
             analysis->>'theoretical_grounding' as grounding,
             analysis->'classical_concepts' as concepts
      FROM papers
      WHERE analysis IS NOT NULL
        AND year >= 2023
        AND analysis->>'theoretical_grounding' = 'strong'
      ORDER BY citation_count DESC
      LIMIT 15`,
  },
};

const SYNTH_SYSTEM = `You are a synthesis agent for the Sutra research project bridging classical MAS with modern LLM agents.

Given aggregated data about a specific aspect of the paper corpus, generate a research insight.

Return JSON:
{
  "title": "Short insight title (5-10 words)",
  "content": "2-4 sentence insight explaining the finding, its significance, and what action it suggests",
  "significance": "high|medium|low",
  "questions": ["1-2 follow-up questions this raises"]
}

Focus on: Lost Canaries (missed classical concepts), Rosetta Stone (confirmed mappings), Gaps, and Anomalies.`;

export async function GET() {
  try {
    await ensureTables();

    // Check cache (30 min)
    const cached = await query(
      `SELECT * FROM research_insights WHERE status = 'active' AND created_at > NOW() - INTERVAL '30 minutes' ORDER BY created_at DESC`
    );
    if (cached.length > 0) {
      return NextResponse.json(
        cached.map((r) => ({
          type: r.type,
          title: r.title,
          content: r.content,
          evidence: r.evidence,
          count: r.paper_count,
        }))
      );
    }

    // Generate fresh insights
    const insights: Array<{
      type: string;
      title: string;
      content: string;
      data: Record<string, unknown>[];
      count: number;
      synthesis?: Record<string, unknown>;
    }> = [];
    for (const [key, spec] of Object.entries(INSIGHT_QUERIES)) {
      try {
        const rows = await query(spec.sql);
        if (rows.length > 0) {
          interface SynthResult { title?: string; content?: string; significance?: string; questions?: string[] }
          let synthesis: SynthResult | null = null;
          try {
            synthesis = await chatJSON<SynthResult>(
              SYNTH_SYSTEM,
              `Aspect: ${spec.title}\nData:\n${JSON.stringify(rows.slice(0, 10), null, 2)}`
            );
          } catch {
            // LLM not available — that's OK, raw data still useful
          }

          insights.push({
            type: key,
            title: synthesis?.title || spec.title,
            content: synthesis?.content || JSON.stringify(rows.slice(0, 5)),
            data: rows.slice(0, 10) as Record<string, unknown>[],
            count: rows.length,
            synthesis: synthesis ? (synthesis as unknown as Record<string, unknown>) : undefined,
          });
        }
      } catch (e) {
        insights.push({
          type: key,
          title: spec.title,
          content: `Error: ${e instanceof Error ? e.message : e}`,
          data: [],
          count: 0,
        });
      }
    }

    // Cache (fire and forget)
    query("DELETE FROM research_insights WHERE status = 'active'")
      .then(() =>
        Promise.all(
          insights.map((i) =>
            query(
              "INSERT INTO research_insights (type, title, content, evidence, paper_count) VALUES ($1, $2, $3, $4, $5)",
              [
                i.type,
                i.title,
                i.content,
                JSON.stringify(i.data),
                i.count,
              ]
            )
          )
        )
      )
      .catch(() => {});

    return NextResponse.json(insights);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
