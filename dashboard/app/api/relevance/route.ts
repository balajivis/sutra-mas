import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    // Relevance score distribution (1-5, exclude 0/null)
    const scoreRows = await query(
      "SELECT relevance_score, COUNT(*)::int as cnt FROM papers WHERE relevance_score IS NOT NULL AND relevance_score > 0 GROUP BY relevance_score ORDER BY relevance_score"
    );

    const totalRow = await query(
      "SELECT COUNT(*)::int as cnt FROM papers WHERE relevance_score IS NOT NULL AND relevance_score > 0"
    );
    const scored = Number(totalRow[0]?.cnt ?? 0);

    const labels: Record<number, string> = {
      1: "Off-topic",
      2: "Tangential",
      3: "Marginal",
      4: "Relevant",
      5: "Core MAS",
    };

    const scores = scoreRows.map((r) => ({
      score: Number(r.relevance_score),
      label: labels[Number(r.relevance_score)] || "?",
      count: Number(r.cnt),
      pct: scored > 0 ? Math.round((Number(r.cnt) / scored) * 1000) / 10 : 0,
    }));

    // MAS branch distribution
    const branchRows = await query(
      "SELECT COALESCE(mas_branch, 'unclassified') as branch, COUNT(*)::int as cnt FROM papers WHERE mas_branch IS NOT NULL AND mas_branch != '' GROUP BY mas_branch ORDER BY COUNT(*) DESC LIMIT 10"
    );

    const branches = branchRows.map((r) => ({
      branch: String(r.branch),
      count: Number(r.cnt),
    }));

    return NextResponse.json({ scores, scored, branches });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
