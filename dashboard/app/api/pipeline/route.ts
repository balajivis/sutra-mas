import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    // Funnel counts by pipeline_status
    const funnel = await query(
      "SELECT pipeline_status, COUNT(*) as cnt FROM papers GROUP BY pipeline_status"
    );
    const f: Record<string, number> = {};
    for (const r of funnel) {
      f[r.pipeline_status as string] = Number(r.cnt);
    }

    const totalRow = await query("SELECT COUNT(*) as cnt FROM papers");
    const total = Number(totalRow[0]?.cnt ?? 0);

    // Build station data (mirrors dashboard_web.py logic)
    const downstream = (from: string[]) =>
      from.reduce((s, k) => s + (f[k] || 0), 0);

    const agent3bPlus = [
      "analyzed", "enriching", "enriched", "scouting", "scouted",
      "planning_reproduction", "reproduction_planned",
    ];
    const agent4Plus = [
      "enriched", "scouting", "scouted",
      "planning_reproduction", "reproduction_planned",
    ];
    const agent5Plus = [
      "scouted", "planning_reproduction", "reproduction_planned",
    ];

    // Agent 8: Clustering — query paper_clusters table for status
    let clustered = 0;
    let clusterCount = 0;
    let clusteringActive = 0;
    let analyzedTotal = 0;
    try {
      const clusterRows = await query(
        "SELECT COUNT(*) as cnt FROM paper_clusters"
      );
      clustered = Number(clusterRows[0]?.cnt ?? 0);

      const clusterMetaRows = await query(
        "SELECT COUNT(*) as cnt FROM cluster_meta"
      );
      clusterCount = Number(clusterMetaRows[0]?.cnt ?? 0);

      const activeRows = await query(
        "SELECT COUNT(*) as cnt FROM clustering_runs WHERE status = 'running'"
      );
      clusteringActive = Number(activeRows[0]?.cnt ?? 0);

      const analyzedRows = await query(
        "SELECT COUNT(*) as cnt FROM papers WHERE analysis IS NOT NULL AND analysis->>'key_contribution_summary' IS NOT NULL AND pipeline_status NOT IN ('archived')"
      );
      analyzedTotal = Number(analyzedRows[0]?.cnt ?? 0);
    } catch {
      // Tables may not exist yet
    }

    const stations = [
      {
        id: "Agent 1", name: "Collector", color: "#fbbf24",
        desc: "S2 + OpenAlex API expansion",
        input: 0, active: 0,
        done: total - (f.seed || 0),
        total,
      },
      {
        id: "Agent 2", name: "Filter", color: "#34d399",
        desc: "GPT-5-mini relevance scoring (1\u20135)",
        input: f.collected || 0, active: f.filtering || 0,
        done: downstream(["relevant", "marginal", "archived", "analyzing", ...agent3bPlus]),
        total: downstream(["collected", "filtering", "relevant", "marginal", "archived", "analyzing", ...agent3bPlus]),
      },
      {
        id: "Agent 3b", name: "Analyst", color: "#60a5fa",
        desc: "GPT-5.1 deep extraction (LaTeX + JSONB)",
        input: f.relevant || 0, active: f.analyzing || 0,
        done: downstream(agent3bPlus),
        total: downstream(["relevant", "analyzing", ...agent3bPlus]),
      },
      {
        id: "Agent 4", name: "Enricher", color: "#a78bfa",
        desc: "OpenAlex citation expansion + feedback loop",
        input: f.analyzed || 0, active: f.enriching || 0,
        done: downstream(agent4Plus),
        total: downstream(["analyzed", "enriching", ...agent4Plus]),
      },
      {
        id: "Agent 5", name: "Scout", color: "#22d3ee",
        desc: "Papers with Code + GitHub repo search",
        input: f.enriched || 0, active: f.scouting || 0,
        done: downstream(agent5Plus),
        total: downstream(["enriched", "scouting", ...agent5Plus]),
      },
      {
        id: "Agent 6", name: "Reproducer", color: "#f472b6",
        desc: "Auto-run repos + research briefs",
        input: f.scouted || 0, active: f.planning_reproduction || 0,
        done: f.reproduction_planned || 0,
        total: downstream(["scouted", "planning_reproduction", "reproduction_planned"]) || 1,
      },
      {
        id: "Agent 8", name: "Clustering", color: "#fb923c",
        desc: `k-means + UMAP 2D (${clusterCount} clusters)`,
        input: Math.max(0, analyzedTotal - clustered),
        active: clusteringActive,
        done: clustered,
        total: Math.max(analyzedTotal, 1),
      },
    ];

    return NextResponse.json({ stations, funnel: f, total });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
