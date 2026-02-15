import { NextRequest, NextResponse } from "next/server";
import { query, ensureTables } from "@/lib/db";

/**
 * GET /api/citation-graph
 *
 * Returns nodes + edges for the citation lineage graph.
 *
 * Params:
 *   paper_id - center on a specific paper, BFS outward
 *   cluster_id - show all edges within a cluster
 *   depth - BFS depth (default 2, max 3)
 *   direction - "both" | "outgoing" | "incoming" (default "both")
 *   limit - max nodes (default 200)
 */
export async function GET(req: NextRequest) {
  await ensureTables();

  const url = req.nextUrl;
  const paperId = url.searchParams.get("paper_id");
  const clusterId = url.searchParams.get("cluster_id");
  const depth = Math.min(3, parseInt(url.searchParams.get("depth") || "2", 10));
  const direction = url.searchParams.get("direction") || "both";
  const limit = Math.min(500, parseInt(url.searchParams.get("limit") || "200", 10));

  try {
    if (paperId) {
      return NextResponse.json(
        await paperCenteredGraph(parseInt(paperId, 10), depth, direction, limit)
      );
    } else if (clusterId) {
      return NextResponse.json(
        await clusterGraph(parseInt(clusterId, 10), limit)
      );
    } else {
      return NextResponse.json(
        await topCitedGraph(limit)
      );
    }
  } catch (err) {
    console.error("[citation-graph]", err);
    return NextResponse.json({ error: "Failed to build citation graph" }, { status: 500 });
  }
}

interface GraphNode {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  is_classical: boolean;
  pattern: string | null;
  cluster_id: number | null;
  cluster_label: string | null;
  has_code: boolean;
  depth: number;
}

interface GraphEdge {
  source: number;
  target: number;
}

interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  center_id?: number;
  stats: { nodes: number; edges: number; max_depth: number };
}

async function fetchNodeData(ids: number[]): Promise<GraphNode[]> {
  if (ids.length === 0) return [];
  const placeholders = ids.map((_, i) => `$${i + 1}`).join(",");
  return query<GraphNode>(
    `SELECT p.id, p.title, p.year, p.citation_count as citations, p.is_classical,
            p.analysis->>'coordination_pattern' as pattern,
            pc.cluster_id, pc.cluster_label,
            COALESCE(p.has_code, false) as has_code,
            0 as depth
     FROM papers p
     LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
     WHERE p.id IN (${placeholders})`,
    ids
  );
}

async function paperCenteredGraph(
  paperId: number,
  maxDepth: number,
  direction: string,
  limit: number
): Promise<GraphResponse> {
  const visited = new Set<number>([paperId]);
  const allEdges: GraphEdge[] = [];
  const depthMap = new Map<number, number>([[paperId, 0]]);

  let frontier = [paperId];

  for (let d = 1; d <= maxDepth && frontier.length > 0; d++) {
    const placeholders = frontier.map((_, i) => `$${i + 1}`).join(",");
    const newFrontier: number[] = [];

    // Outgoing: papers this frontier cites
    if (direction === "both" || direction === "outgoing") {
      const outgoing = await query<{ citing_id: number; cited_id: number }>(
        `SELECT citing_id, cited_id FROM citation_edges
         WHERE citing_id IN (${placeholders})`,
        frontier
      );
      for (const e of outgoing) {
        allEdges.push({ source: e.citing_id, target: e.cited_id });
        if (!visited.has(e.cited_id) && visited.size < limit) {
          visited.add(e.cited_id);
          depthMap.set(e.cited_id, d);
          newFrontier.push(e.cited_id);
        }
      }
    }

    // Incoming: papers that cite this frontier
    if (direction === "both" || direction === "incoming") {
      const incoming = await query<{ citing_id: number; cited_id: number }>(
        `SELECT citing_id, cited_id FROM citation_edges
         WHERE cited_id IN (${placeholders})`,
        frontier
      );
      for (const e of incoming) {
        allEdges.push({ source: e.citing_id, target: e.cited_id });
        if (!visited.has(e.citing_id) && visited.size < limit) {
          visited.add(e.citing_id);
          depthMap.set(e.citing_id, d);
          newFrontier.push(e.citing_id);
        }
      }
    }

    frontier = newFrontier;
  }

  const nodeIds = Array.from(visited);
  const nodes = await fetchNodeData(nodeIds);

  // Set depth on nodes
  for (const n of nodes) {
    n.depth = depthMap.get(n.id) ?? 0;
  }

  // Deduplicate edges
  const edgeSet = new Set<string>();
  const uniqueEdges = allEdges.filter((e) => {
    const key = `${e.source}-${e.target}`;
    if (edgeSet.has(key)) return false;
    edgeSet.add(key);
    // Only keep edges where both endpoints are in our node set
    return visited.has(e.source) && visited.has(e.target);
  });

  return {
    nodes,
    edges: uniqueEdges,
    center_id: paperId,
    stats: { nodes: nodes.length, edges: uniqueEdges.length, max_depth: maxDepth },
  };
}

async function clusterGraph(clusterId: number, limit: number): Promise<GraphResponse> {
  // Get paper IDs in this cluster
  const clusterPapers = await query<{ paper_id: number }>(
    `SELECT paper_id FROM paper_clusters WHERE cluster_id = $1 LIMIT $2`,
    [clusterId, limit]
  );
  const ids = clusterPapers.map((p) => p.paper_id);
  if (ids.length === 0) {
    return { nodes: [], edges: [], stats: { nodes: 0, edges: 0, max_depth: 0 } };
  }

  const placeholders = ids.map((_, i) => `$${i + 1}`).join(",");

  // Get all edges between papers in this cluster
  const edges = await query<{ citing_id: number; cited_id: number }>(
    `SELECT citing_id, cited_id FROM citation_edges
     WHERE citing_id IN (${placeholders}) AND cited_id IN (${placeholders})`,
    ids
  );

  const nodes = await fetchNodeData(ids);
  for (const n of nodes) n.depth = 0;

  return {
    nodes,
    edges: edges.map((e) => ({ source: e.citing_id, target: e.cited_id })),
    stats: { nodes: nodes.length, edges: edges.length, max_depth: 0 },
  };
}

async function topCitedGraph(limit: number): Promise<GraphResponse> {
  // Get top papers by citation count that have edges
  const topPapers = await query<{ id: number }>(
    `SELECT DISTINCT p.id FROM papers p
     JOIN citation_edges ce ON (ce.citing_id = p.id OR ce.cited_id = p.id)
     WHERE p.relevance_score >= 3
     ORDER BY p.id
     LIMIT $1`,
    [limit]
  );

  const ids = topPapers.map((p) => p.id);
  if (ids.length === 0) {
    return { nodes: [], edges: [], stats: { nodes: 0, edges: 0, max_depth: 0 } };
  }

  // Get top papers by citation count
  const topByCount = await query<{ id: number }>(
    `SELECT id FROM papers
     WHERE relevance_score >= 3
     ORDER BY citation_count DESC
     LIMIT $1`,
    [limit]
  );
  const topIds = new Set(topByCount.map((p) => p.id));
  const allIds = Array.from(new Set([...ids.filter((id) => topIds.has(id)), ...Array.from(topIds).slice(0, limit)])).slice(0, limit);

  const placeholders = allIds.map((_, i) => `$${i + 1}`).join(",");
  const edges = await query<{ citing_id: number; cited_id: number }>(
    `SELECT citing_id, cited_id FROM citation_edges
     WHERE citing_id IN (${placeholders}) AND cited_id IN (${placeholders})`,
    allIds
  );

  const nodes = await fetchNodeData(allIds);
  for (const n of nodes) n.depth = 0;

  return {
    nodes,
    edges: edges.map((e) => ({ source: e.citing_id, target: e.cited_id })),
    stats: { nodes: nodes.length, edges: edges.length, max_depth: 0 },
  };
}
