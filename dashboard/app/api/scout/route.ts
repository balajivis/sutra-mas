import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    // Scout summary: with_code vs without_code
    const scoutRows = await query(
      `SELECT
         COUNT(*) FILTER (WHERE has_code = TRUE) as with_code,
         COUNT(*) FILTER (WHERE has_code = FALSE OR has_code IS NULL) as without_code
       FROM papers
       WHERE pipeline_status IN ('scouted','planning_reproduction','reproduction_planned')`
    );
    const with_code = Number(scoutRows[0]?.with_code ?? 0);
    const without_code = Number(scoutRows[0]?.without_code ?? 0);

    // Feasibility breakdown
    const feasRows = await query(
      `SELECT reproduction_feasibility as score, COUNT(*) as cnt
       FROM papers
       WHERE reproduction_feasibility IS NOT NULL
       GROUP BY 1 ORDER BY 1`
    );
    const feasibility = feasRows.map((r) => ({
      score: Number(r.score),
      count: Number(r.cnt),
    }));

    // Feedback generations
    const genRows = await query(
      `SELECT COALESCE(generation, 0) as gen, COUNT(*) as cnt
       FROM papers GROUP BY 1 ORDER BY 1`
    );
    const generations = genRows.map((r) => ({
      gen: Number(r.gen),
      count: Number(r.cnt),
    }));

    return NextResponse.json({ with_code, without_code, feasibility, generations });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
