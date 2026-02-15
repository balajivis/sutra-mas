import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

/**
 * Returns the local citation network for a paper:
 * - "references": papers this paper cites (from refs JSONB → join on openalex_id)
 * - "citedBy": papers that cite this paper (from cited_by JSONB → join on semantic_scholar_id)
 * - Unresolved refs/citedBy are included as "external" nodes (not in our corpus)
 * - each node includes id, title, year, citations, cluster_id, cluster_label, x, y (UMAP)
 * - edges: [{source, target, direction}]
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const paperId = parseInt(id, 10);
  if (isNaN(paperId)) {
    return NextResponse.json({ error: "Invalid paper ID" }, { status: 400 });
  }

  try {
    // Get the paper's refs and cited_by arrays + its own cluster position
    const [paperRow] = await query(
      `SELECT p.id, p.title, p.year, COALESCE(p.citation_count, 0) AS citations,
              p.refs, p.cited_by, p.openalex_id,
              pc.cluster_id, pc.cluster_label, pc.x, pc.y
       FROM papers p
       LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
       WHERE p.id = $1`,
      [paperId],
    );

    if (!paperRow) {
      return NextResponse.json({ error: "Paper not found" }, { status: 404 });
    }

    const refs = (paperRow.refs as { oa_id: string; title: string; year: number; citations: number }[]) || [];
    const citedBy = (paperRow.cited_by as { s2_id: string; title: string; year: number; citations?: number }[]) || [];

    // Resolve refs via openalex_id join (our strongest link)
    const refOaIds = refs.map((r) => r.oa_id).filter(Boolean);
    let refNodes: Record<string, unknown>[] = [];
    if (refOaIds.length > 0) {
      refNodes = await query(
        `SELECT p.id, p.title, p.year, COALESCE(p.citation_count, 0) AS citations,
                p.openalex_id,
                pc.cluster_id, pc.cluster_label, pc.x, pc.y
         FROM papers p
         LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
         WHERE p.openalex_id = ANY($1)
         LIMIT 50`,
        [refOaIds],
      );
    }

    // Resolve cited_by via semantic_scholar_id join
    const cbS2Ids = citedBy.map((c) => c.s2_id).filter(Boolean);
    let cbNodes: Record<string, unknown>[] = [];
    if (cbS2Ids.length > 0) {
      cbNodes = await query(
        `SELECT p.id, p.title, p.year, COALESCE(p.citation_count, 0) AS citations,
                p.semantic_scholar_id,
                pc.cluster_id, pc.cluster_label, pc.x, pc.y
         FROM papers p
         LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
         WHERE p.semantic_scholar_id = ANY($1)
         LIMIT 50`,
        [cbS2Ids],
      );
    }

    // Build node list (center paper + resolved refs + resolved cited_by)
    const nodesMap = new Map<number, {
      id: number; title: string; year: number | null; citations: number;
      cluster_id: number | null; cluster_label: string | null;
      x: number | null; y: number | null; role: string;
    }>();

    nodesMap.set(paperId, {
      id: paperId,
      title: paperRow.title as string,
      year: paperRow.year as number | null,
      citations: paperRow.citations as number,
      cluster_id: paperRow.cluster_id as number | null,
      cluster_label: paperRow.cluster_label as string | null,
      x: paperRow.x as number | null,
      y: paperRow.y as number | null,
      role: "center",
    });

    const edges: { source: number; target: number; direction: "refs" | "citedBy" }[] = [];

    // Track which oa_ids were resolved so we can find unresolved ones
    const resolvedOaIds = new Set(refNodes.map((r) => r.openalex_id as string));

    for (const r of refNodes) {
      const rid = r.id as number;
      if (!nodesMap.has(rid)) {
        nodesMap.set(rid, {
          id: rid,
          title: r.title as string,
          year: r.year as number | null,
          citations: r.citations as number,
          cluster_id: r.cluster_id as number | null,
          cluster_label: r.cluster_label as string | null,
          x: r.x as number | null,
          y: r.y as number | null,
          role: "reference",
        });
      }
      edges.push({ source: paperId, target: rid, direction: "refs" });
    }

    // Track which s2_ids were resolved
    const resolvedS2Ids = new Set(cbNodes.map((c) => c.semantic_scholar_id as string));

    for (const c of cbNodes) {
      const cid = c.id as number;
      if (!nodesMap.has(cid)) {
        nodesMap.set(cid, {
          id: cid,
          title: c.title as string,
          year: c.year as number | null,
          citations: c.citations as number,
          cluster_id: c.cluster_id as number | null,
          cluster_label: c.cluster_label as string | null,
          x: c.x as number | null,
          y: c.y as number | null,
          role: "citedBy",
        });
      }
      edges.push({ source: cid, target: paperId, direction: "citedBy" });
    }

    // Add unresolved refs as external nodes (top 25 by citations)
    const unresolvedRefs = refs
      .filter((r) => r.oa_id && !resolvedOaIds.has(r.oa_id))
      .sort((a, b) => (b.citations || 0) - (a.citations || 0))
      .slice(0, 25);

    let extId = -1; // negative IDs for external nodes
    for (const r of unresolvedRefs) {
      nodesMap.set(extId, {
        id: extId,
        title: r.title || "Unknown",
        year: r.year || null,
        citations: r.citations || 0,
        cluster_id: null,
        cluster_label: null,
        x: null,
        y: null,
        role: "externalRef",
      });
      edges.push({ source: paperId, target: extId, direction: "refs" });
      extId--;
    }

    // Add unresolved cited_by as external nodes (top 25)
    const unresolvedCb = citedBy
      .filter((c) => c.s2_id && !resolvedS2Ids.has(c.s2_id))
      .sort((a, b) => (b.citations || 0) - (a.citations || 0))
      .slice(0, 25);

    for (const c of unresolvedCb) {
      nodesMap.set(extId, {
        id: extId,
        title: c.title || "Unknown",
        year: c.year || null,
        citations: c.citations || 0,
        cluster_id: null,
        cluster_label: null,
        x: null,
        y: null,
        role: "externalCitedBy",
      });
      edges.push({ source: extId, target: paperId, direction: "citedBy" });
      extId--;
    }

    return NextResponse.json({
      nodes: Array.from(nodesMap.values()),
      edges,
      totalRefs: refs.length,
      resolvedRefs: refNodes.length,
      totalCitedBy: citedBy.length,
      resolvedCitedBy: cbNodes.length,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}
