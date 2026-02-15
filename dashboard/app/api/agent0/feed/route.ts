import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

/**
 * GET /api/agent0/feed
 *
 * Returns recent pipeline activity for the Sensemaking Canvas foraging feed.
 * Three parallel queries: extractions, cluster updates, anomalies.
 */
export async function GET() {
  try {
    const [extractions, clusters, anomalies] = await Promise.all([
      // Recent papers with analysis (Agent 3b output)
      query(
        `SELECT id, title, year,
                analysis->>'coordination_pattern' as pattern,
                analysis->>'key_contribution_summary' as summary,
                analysis->>'classical_concepts_missing' as missing,
                analysis->>'theoretical_grounding' as grounding,
                pipeline_status, processed_at
         FROM papers
         WHERE analysis IS NOT NULL
           AND analysis->>'key_contribution_summary' IS NOT NULL
         ORDER BY processed_at DESC NULLS LAST
         LIMIT 15`
      ),

      // Recent cluster updates (Agent 8 output)
      query(
        `SELECT cluster_id, label, description, paper_count,
                top_concepts, top_patterns, updated_at
         FROM cluster_meta
         ORDER BY updated_at DESC
         LIMIT 5`
      ),

      // Anomalies: high-cite papers with weak/no grounding (Lost Canary signals)
      query(
        `SELECT id, title, year, citation_count,
                analysis->>'coordination_pattern' as pattern,
                analysis->>'theoretical_grounding' as grounding,
                analysis->>'classical_concepts_missing' as missing,
                modernity_score
         FROM papers
         WHERE analysis IS NOT NULL
           AND citation_count > 100
           AND (
             analysis->>'theoretical_grounding' IN ('weak', 'none')
             OR modernity_score < 0.1
           )
         ORDER BY citation_count DESC
         LIMIT 5`
      ),
    ]);

    const items = [];

    // Map extractions to foraging items
    for (const r of extractions) {
      const summary = (r.summary as string) || "";
      const pattern = (r.pattern as string) || "none";
      const missing = (r.missing as string) || "";
      items.push({
        id: `ext-${r.id}`,
        agent: "A3b",
        agentColor: "#a78bfa",
        timestamp: formatAge(r.processed_at as string),
        type: "extraction" as const,
        content: `${r.title} (${r.year}): ${summary.slice(0, 150)}${summary.length > 150 ? "..." : ""}`,
        meta: pattern !== "none" ? `Pattern: ${pattern}` : missing ? `Missing: ${missing.slice(0, 60)}` : undefined,
        paperId: r.id,
      });
    }

    // Map cluster updates
    for (const r of clusters) {
      const concepts = r.top_concepts
        ? (Array.isArray(r.top_concepts) ? r.top_concepts : []).slice(0, 3).join(", ")
        : "";
      items.push({
        id: `clust-${r.cluster_id}`,
        agent: "A8",
        agentColor: "#f472b6",
        timestamp: formatAge(r.updated_at as string),
        type: "cluster_update" as const,
        content: `Cluster ${r.cluster_id}: "${r.label}" - ${r.paper_count} papers. ${r.description ? (r.description as string).slice(0, 100) : ""}`,
        meta: concepts ? `Concepts: ${concepts}` : undefined,
      });
    }

    // Map anomalies
    for (const r of anomalies) {
      const grounding = (r.grounding as string) || "unknown";
      const missing = (r.missing as string) || "";
      const modernity = r.modernity_score != null ? Number(r.modernity_score).toFixed(2) : "?";
      items.push({
        id: `anom-${r.id}`,
        agent: "A4",
        agentColor: "#f87171",
        timestamp: formatAge(null),
        type: "anomaly" as const,
        content: `${r.title} (${r.year}): ${r.citation_count} citations, modernity ${modernity}, grounding: ${grounding}. ${missing ? `Missing: ${missing.slice(0, 80)}` : ""}`,
        meta: "Lost Canary candidate",
        paperId: r.id,
      });
    }

    return NextResponse.json({ items });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error", items: [] },
      { status: 500 }
    );
  }
}

function formatAge(ts: string | null): string {
  if (!ts) return "recently";
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
