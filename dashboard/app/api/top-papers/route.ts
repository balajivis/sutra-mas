import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [modern, classical] = await Promise.all([
      query(`
        SELECT id, title, year, citation_count as cites, pipeline_status as status
        FROM papers
        WHERE year >= 2023
          AND pipeline_status != 'archived'
          AND relevance_score >= 4
        ORDER BY citation_count DESC NULLS LAST
        LIMIT 15
      `),
      query(`
        SELECT id, title, year, citation_count as cites, pipeline_status as status
        FROM papers
        WHERE (is_classical = true OR year < 2010)
          AND pipeline_status != 'archived'
          AND relevance_score >= 4
        ORDER BY citation_count DESC NULLS LAST
        LIMIT 15
      `),
    ]);

    return NextResponse.json({ modern, classical });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}
