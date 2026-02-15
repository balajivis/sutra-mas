import { NextResponse } from "next/server";
import { query, ensureTables } from "@/lib/db";

export async function GET() {
  try {
    await ensureTables();

    const points = await query(`
      SELECT pc.paper_id, pc.cluster_id, pc.cluster_label, pc.x, pc.y,
             p.title, p.year, COALESCE(p.citation_count, 0) as citations,
             p.is_classical,
             p.analysis->>'coordination_pattern' as pattern,
             p.analysis->>'theoretical_grounding' as grounding
      FROM paper_clusters pc
      JOIN papers p ON p.id = pc.paper_id
      ORDER BY pc.cluster_id, p.citation_count DESC NULLS LAST
    `);

    const clusters = await query(
      "SELECT * FROM cluster_meta ORDER BY cluster_id"
    );

    return NextResponse.json({
      points,
      clusters,
      count: points.length,
    });
  } catch (e) {
    return NextResponse.json({
      points: [],
      clusters: [],
      count: 0,
      error: e instanceof Error ? e.message : "Unknown error",
    });
  }
}
