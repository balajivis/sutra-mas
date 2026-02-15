import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";
import { embed } from "@/lib/llm";

export const dynamic = "force-dynamic";

/** Azure AI Search vector similarity */
async function vectorSearch(
  embedding: number[],
  excludeId: number,
  top: number
): Promise<Record<string, unknown>[] | null> {
  const endpoint = process.env.SUTRA_SEARCH_ENDPOINT;
  const key = process.env.SUTRA_SEARCH_KEY;
  const index = process.env.SUTRA_SEARCH_INDEX || "sutra-papers";
  if (!endpoint || !key) return null;

  const body = {
    search: "*",
    top,
    select:
      "id,title,year,citation_count,coordination_pattern,is_classical," +
      "relevance_score,cluster_id,cluster_label,key_contribution",
    filter: `id ne '${excludeId}'`,
    vectorQueries: [
      {
        kind: "vector",
        vector: embedding,
        fields: "embedding",
        k: top,
      },
    ],
  };

  try {
    const res = await fetch(
      `${endpoint}/indexes/${index}/docs/search?api-version=2024-07-01`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "api-key": key },
        body: JSON.stringify(body),
      }
    );
    if (!res.ok) return null;
    const data = await res.json();
    return data.value || [];
  } catch {
    return null;
  }
}

/** PostgreSQL FTS similarity — use title + key concepts with OR logic */
async function ftsSimilarity(
  paperId: number,
  title: string,
  pattern: string | null,
  concepts: string[] | null,
  top: number
) {
  // Build an OR query from title words + pattern + classical concepts
  const stopwords = new Set([
    "a","an","the","of","in","to","for","and","or","is","are","was","were",
    "with","on","at","by","from","as","it","its","this","that","be","been",
    "has","have","had","not","but","can","do","does","will","would","should",
    "into","than","each","over","also","more","their","between","through",
    "using","based","about","under","after","these","those","such",
  ]);

  const terms: string[] = [];

  // Key terms from title
  const titleTerms = title
    .replace(/[^a-zA-Z0-9\s-]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2 && !stopwords.has(w.toLowerCase()))
    .map((w) => w.toLowerCase());
  terms.push(...titleTerms);

  // Coordination pattern
  if (pattern && pattern !== "none" && pattern !== "null") {
    terms.push(...pattern.split("_"));
  }

  // Classical concepts
  if (concepts && concepts.length > 0) {
    for (const c of concepts.slice(0, 5)) {
      terms.push(
        ...c
          .replace(/[^a-zA-Z0-9\s]/g, " ")
          .split(/\s+/)
          .filter((w) => w.length > 2 && !stopwords.has(w.toLowerCase()))
          .map((w) => w.toLowerCase())
      );
    }
  }

  // Deduplicate and build OR tsquery
  const unique = [...new Set(terms)].slice(0, 20);
  if (unique.length === 0) return [];

  const tsq = unique.join(" | ");

  return query(
    `SELECT p.id, p.title, p.year, p.citation_count as citations,
            p.is_classical, p.relevance_score,
            p.analysis->>'coordination_pattern' as pattern,
            pc.cluster_id, pc.cluster_label,
            LEFT(p.analysis->>'key_contribution_summary', 120) as snippet,
            ts_rank_cd(
              to_tsvector('english',
                COALESCE(p.analysis->>'key_contribution_summary','') || ' ' ||
                COALESCE(p.analysis->>'unique_contribution','') || ' ' ||
                COALESCE(p.title,'')
              ),
              to_tsquery('english', $2)
            ) as rank
     FROM papers p
     LEFT JOIN paper_clusters pc ON pc.paper_id = p.id
     WHERE p.id != $1
       AND p.analysis IS NOT NULL
       AND p.relevance_score >= 3
       AND to_tsvector('english',
             COALESCE(p.analysis->>'key_contribution_summary','') || ' ' ||
             COALESCE(p.analysis->>'unique_contribution','') || ' ' ||
             COALESCE(p.title,'')
           ) @@ to_tsquery('english', $2)
     ORDER BY rank DESC, p.citation_count DESC NULLS LAST
     LIMIT $3`,
    [paperId, tsq, top]
  );
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const paperId = parseInt(id);
  if (isNaN(paperId)) {
    return NextResponse.json({ error: "Invalid paper ID" }, { status: 400 });
  }

  try {
    // Get cluster info + summary in parallel
    const [clusterRows, paperRows] = await Promise.all([
      query(
        `SELECT pc.cluster_id, pc.cluster_label, pc.x, pc.y,
                cm.label as cluster_name, cm.description as cluster_description,
                cm.paper_count
         FROM paper_clusters pc
         LEFT JOIN cluster_meta cm ON cm.cluster_id = pc.cluster_id
         WHERE pc.paper_id = $1`,
        [paperId]
      ),
      query(
        `SELECT title,
                analysis->>'key_contribution_summary' as summary,
                analysis->>'coordination_pattern' as pattern,
                analysis->'classical_concepts' as concepts
         FROM papers WHERE id = $1`,
        [paperId]
      ),
    ]);

    const cluster =
      clusterRows.length > 0
        ? {
            id: clusterRows[0].cluster_id,
            label: clusterRows[0].cluster_name || clusterRows[0].cluster_label,
            description: clusterRows[0].cluster_description,
            paper_count: clusterRows[0].paper_count,
          }
        : null;

    const paperTitle = paperRows[0]?.title as string || "";
    const summary = paperRows[0]?.summary as string | undefined;
    const paperPattern = paperRows[0]?.pattern as string | null;
    const paperConcepts = paperRows[0]?.concepts as string[] | null;

    if (!summary && !paperTitle) {
      return NextResponse.json({
        cluster,
        similar: [],
        method: null,
        message: "Paper has no analysis summary yet",
      });
    }

    // Strategy 1: Azure AI Search vector similarity (best quality)
    try {
      const [vec] = await embed([(summary || paperTitle).slice(0, 2000)]);
      const results = await vectorSearch(vec, paperId, 12);

      if (results && results.length > 0) {
        return NextResponse.json({
          cluster,
          method: "vector",
          similar: results.map((r) => ({
            id: Number(r.id),
            title: r.title,
            year: r.year,
            citations: r.citation_count || 0,
            is_classical: r.is_classical || false,
            relevance: r.relevance_score,
            pattern: r.coordination_pattern,
            cluster_label: r.cluster_label,
            same_cluster: cluster ? r.cluster_id === cluster.id : false,
            score: Number(
              (r as Record<string, unknown>)["@search.score"] || 0
            ),
            snippet: ((r.key_contribution as string) || "").slice(0, 120),
          })),
        });
      }
    } catch {
      // Fall through
    }

    // Strategy 2: PostgreSQL full-text similarity (title + concepts OR query)
    try {
      const ftsRows = await ftsSimilarity(paperId, paperTitle, paperPattern, paperConcepts, 12);
      if (ftsRows.length > 0) {
        return NextResponse.json({
          cluster,
          method: "fts",
          similar: ftsRows.map((r) => ({
            id: r.id,
            title: r.title,
            year: r.year,
            citations: r.citations || 0,
            is_classical: r.is_classical || false,
            relevance: r.relevance_score,
            pattern: r.pattern,
            cluster_label: r.cluster_label,
            same_cluster: cluster ? r.cluster_id === cluster.id : false,
            score: Number(Number(r.rank).toFixed(4)),
            snippet: r.snippet || null,
          })),
        });
      }
    } catch {
      // Fall through
    }

    // Strategy 3: Same-cluster papers by citation count (guaranteed results)
    if (cluster) {
      const sameCluster = await query(
        `SELECT p.id, p.title, p.year, p.citation_count as citations,
                p.is_classical, p.relevance_score,
                p.analysis->>'coordination_pattern' as pattern,
                pc.cluster_label,
                LEFT(p.analysis->>'key_contribution_summary', 120) as snippet
         FROM paper_clusters pc
         JOIN papers p ON p.id = pc.paper_id
         WHERE pc.cluster_id = $1
           AND pc.paper_id != $2
           AND p.relevance_score >= 3
         ORDER BY p.citation_count DESC NULLS LAST
         LIMIT 12`,
        [cluster.id, paperId]
      );

      return NextResponse.json({
        cluster,
        method: "cluster",
        similar: sameCluster.map((r) => ({
          id: r.id,
          title: r.title,
          year: r.year,
          citations: r.citations || 0,
          is_classical: r.is_classical || false,
          relevance: r.relevance_score,
          pattern: r.pattern,
          cluster_label: r.cluster_label,
          same_cluster: true,
          score: 0,
          snippet: r.snippet || null,
        })),
      });
    }

    return NextResponse.json({ cluster: null, similar: [], method: null });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
