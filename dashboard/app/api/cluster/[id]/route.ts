import { NextRequest, NextResponse } from "next/server";
import { query, queryOne, ensureTables } from "@/lib/db";
import { chatCompletion } from "@/lib/llm";

const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

const INSIGHT_SYSTEM = `You are a research cluster analyst for the Sutra project — a survey bridging classical Multi-Agent Systems (MAS, 1980-2010) with modern LLM agent systems (2023-2026).

Given a cluster label, description, top centroid papers, a landmark paper (most cited), and a survey paper (cites the most), write a 2-paragraph field review:

Paragraph 1 — Field Overview: What is the core research question this cluster addresses? What are the major approaches or schools of thought? How has the field evolved from classical to modern work? Reference specific papers by name.

Paragraph 2 — Significance & Gaps: What are the key open problems? Where are modern LLM agent papers reinventing classical ideas without citation (Lost Canary signals)? What would a researcher entering this area need to know? What bridges exist between eras?

Be specific, cite paper titles and years, and avoid generic statements. Write in an authoritative academic tone.`;

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    await ensureTables();

    const { id } = await params;
    const clusterId = parseInt(id, 10);
    if (isNaN(clusterId)) {
      return NextResponse.json({ error: "Invalid cluster id" }, { status: 400 });
    }

    // Fetch cluster metadata
    const meta = await queryOne(
      "SELECT cluster_id, label, description, paper_count, top_concepts, top_patterns FROM cluster_meta WHERE cluster_id = $1",
      [clusterId],
    );
    if (!meta) {
      return NextResponse.json({ error: "Cluster not found" }, { status: 404 });
    }

    // Top 5 papers by centroid proximity (Euclidean distance on UMAP x/y), citation tie-break
    const topPapers = await query(
      `WITH centroid AS (
        SELECT AVG(x) AS cx, AVG(y) AS cy FROM paper_clusters WHERE cluster_id = $1
      )
      SELECT pc.paper_id AS id,
             p.title,
             p.year,
             COALESCE(p.citation_count, 0) AS citations,
             LEFT(p.abstract, 300) AS abstract,
             p.analysis->>'coordination_pattern' AS pattern,
             p.analysis->>'key_contribution_summary' AS contribution,
             SQRT(POWER(pc.x - c.cx, 2) + POWER(pc.y - c.cy, 2)) AS distance
      FROM paper_clusters pc
      JOIN papers p ON p.id = pc.paper_id
      CROSS JOIN centroid c
      WHERE pc.cluster_id = $1
      ORDER BY distance ASC, p.citation_count DESC NULLS LAST
      LIMIT 5`,
      [clusterId],
    );

    // Landmark paper: highest citation_count in cluster (the paper everyone cites)
    const landmarkPaper = await queryOne(
      `SELECT pc.paper_id AS id, p.title, p.year,
              COALESCE(p.citation_count, 0) AS citations,
              LEFT(p.abstract, 400) AS abstract,
              p.analysis->>'coordination_pattern' AS pattern,
              p.analysis->>'key_contribution_summary' AS contribution,
              COALESCE(jsonb_array_length(p.refs), 0) AS ref_count
       FROM paper_clusters pc
       JOIN papers p ON p.id = pc.paper_id
       WHERE pc.cluster_id = $1
       ORDER BY p.citation_count DESC NULLS LAST
       LIMIT 1`,
      [clusterId],
    );

    // Survey paper: highest reference count in cluster (the paper that cites everyone)
    // Must have 30+ refs to qualify, and must differ from landmark
    const surveyPaper = await queryOne(
      `SELECT pc.paper_id AS id, p.title, p.year,
              COALESCE(p.citation_count, 0) AS citations,
              LEFT(p.abstract, 400) AS abstract,
              p.analysis->>'coordination_pattern' AS pattern,
              p.analysis->>'key_contribution_summary' AS contribution,
              jsonb_array_length(p.refs) AS ref_count
       FROM paper_clusters pc
       JOIN papers p ON p.id = pc.paper_id
       WHERE pc.cluster_id = $1
         AND p.refs IS NOT NULL
         AND jsonb_array_length(p.refs) >= 30
         AND pc.paper_id != $2
       ORDER BY jsonb_array_length(p.refs) DESC, p.citation_count DESC NULLS LAST
       LIMIT 1`,
      [clusterId, landmarkPaper?.id ?? -1],
    );

    // Check cache for LLM insight
    let insight: string | null = null;
    const cached = await queryOne<{ insight: string; created_at: Date }>(
      "SELECT insight, created_at FROM cluster_insights WHERE cluster_id = $1",
      [clusterId],
    );

    if (cached && cached.insight) {
      const age = Date.now() - new Date(cached.created_at).getTime();
      if (age < CACHE_TTL_MS) {
        insight = cached.insight;
      }
    }

    // Generate insight if not cached (or cached was empty)
    if (!insight) {
      try {
        const paperContext = topPapers
          .slice(0, 5)
          .map(
            (p, i) =>
              `${i + 1}. "${p.title}" (${p.year || "?"}, ${p.citations} cites)\n   ${(p.contribution || p.abstract || "").slice(0, 300)}`,
          )
          .join("\n\n");

        const landmarkContext = landmarkPaper
          ? `\n\nLandmark paper (most cited in cluster):\n"${landmarkPaper.title}" (${landmarkPaper.year || "?"}, ${landmarkPaper.citations} cites)\n${(landmarkPaper.contribution || landmarkPaper.abstract || "").slice(0, 400)}`
          : "";

        const surveyContext = surveyPaper
          ? `\n\nSurvey paper (cites the most works, ${surveyPaper.ref_count} references):\n"${surveyPaper.title}" (${surveyPaper.year || "?"}, ${surveyPaper.citations} cites)\n${(surveyPaper.contribution || surveyPaper.abstract || "").slice(0, 400)}`
          : "";

        insight = await chatCompletion(
          INSIGHT_SYSTEM,
          `Cluster: "${meta.label}" (${meta.paper_count} papers)\nDescription: ${meta.description || "N/A"}\n\nTop centroid papers:\n${paperContext}${landmarkContext}${surveyContext}`,
          { model: "gpt-5.1", maxTokens: 2048, temperature: 0 },
        );

        // Upsert cache (only if non-empty)
        if (!insight) throw new Error("Empty LLM response");
        await query(
          `INSERT INTO cluster_insights (cluster_id, insight, top_papers, created_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (cluster_id) DO UPDATE SET insight = $2, top_papers = $3, created_at = NOW()`,
          [clusterId, insight, JSON.stringify(topPapers.map((p) => p.id))],
        ).catch(() => {});
      } catch (err) {
        console.error("Cluster insight generation failed:", err);
        insight = null;
      }
    }

    return NextResponse.json({
      cluster: {
        cluster_id: meta.cluster_id,
        label: meta.label,
        description: meta.description,
        top_concepts: meta.top_concepts,
        top_patterns: meta.top_patterns,
        paper_count: meta.paper_count,
      },
      topPapers: topPapers.map((p) => ({
        id: p.id,
        title: p.title,
        year: p.year,
        citations: p.citations,
        abstract: p.abstract,
        pattern: p.pattern,
        contribution: p.contribution,
        distance: Number(p.distance).toFixed(3),
      })),
      insight,
      landmarkPaper: landmarkPaper
        ? {
            id: landmarkPaper.id,
            title: landmarkPaper.title,
            year: landmarkPaper.year,
            citations: landmarkPaper.citations,
            abstract: landmarkPaper.abstract,
            pattern: landmarkPaper.pattern,
            refCount: Number(landmarkPaper.ref_count),
          }
        : null,
      surveyPaper: surveyPaper
        ? {
            id: surveyPaper.id,
            title: surveyPaper.title,
            year: surveyPaper.year,
            citations: surveyPaper.citations,
            abstract: surveyPaper.abstract,
            pattern: surveyPaper.pattern,
            refCount: Number(surveyPaper.ref_count),
          }
        : null,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}
