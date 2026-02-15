import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    // Only high-relevance papers (4-5) for dashboard cards
    const REL = "AND relevance_score >= 4";

    const [eraRows, citeRows, citeSummary, medianRow] = await Promise.all([
      query(`
        SELECT era, cnt FROM (
          SELECT
            CASE
              WHEN year IS NULL THEN 'unknown'
              WHEN year < 1990 THEN '< 1990'
              WHEN year < 2000 THEN '1990s'
              WHEN year < 2010 THEN '2000s'
              WHEN year < 2020 THEN '2010s'
              WHEN year < 2023 THEN '2020-22'
              WHEN year < 2025 THEN '2023-24'
              ELSE '2025+'
            END AS era,
            CASE
              WHEN year IS NULL THEN 8
              WHEN year < 1990 THEN 1
              WHEN year < 2000 THEN 2
              WHEN year < 2010 THEN 3
              WHEN year < 2020 THEN 4
              WHEN year < 2023 THEN 5
              WHEN year < 2025 THEN 6
              ELSE 7
            END AS sort_key,
            COUNT(*) AS cnt
          FROM papers
          WHERE TRUE ${REL}
          GROUP BY 1, 2
        ) sub
        ORDER BY sort_key
      `),
      query(`
        SELECT bucket, cnt FROM (
          SELECT
            CASE
              WHEN citation_count IS NULL OR citation_count = 0 THEN 'No data'
              WHEN citation_count <= 10 THEN '1-10'
              WHEN citation_count <= 50 THEN '11-50'
              WHEN citation_count <= 200 THEN '51-200'
              WHEN citation_count <= 1000 THEN '201-1K'
              ELSE '1K+'
            END AS bucket,
            CASE
              WHEN citation_count IS NULL OR citation_count = 0 THEN 0
              WHEN citation_count <= 10 THEN 1
              WHEN citation_count <= 50 THEN 2
              WHEN citation_count <= 200 THEN 3
              WHEN citation_count <= 1000 THEN 4
              ELSE 5
            END AS sort_key,
            COUNT(*) AS cnt
          FROM papers
          WHERE TRUE ${REL}
          GROUP BY 1, 2
        ) sub
        ORDER BY sort_key
      `),
      query(`
        SELECT
          ROUND(AVG(citation_count))::int AS mean
        FROM papers
        WHERE citation_count IS NOT NULL AND citation_count > 0 ${REL}
      `),
      query(`
        SELECT citation_count AS median
        FROM papers
        WHERE citation_count IS NOT NULL AND citation_count > 0 ${REL}
        ORDER BY citation_count
        LIMIT 1
        OFFSET (SELECT COUNT(*) / 2 FROM papers WHERE citation_count IS NOT NULL AND citation_count > 0 ${REL})
      `),
    ]);

    const total = eraRows.reduce((s, r) => s + Number(r.cnt), 0);

    return NextResponse.json({
      eras: eraRows.map((r) => ({
        label: r.era as string,
        count: Number(r.cnt),
        pct: total > 0 ? Number(((Number(r.cnt) / total) * 100).toFixed(1)) : 0,
      })),
      citations: citeRows.map((r) => ({
        label: r.bucket as string,
        count: Number(r.cnt),
      })),
      citeMean: Number(citeSummary[0]?.mean ?? 0),
      citeMedian: Number(medianRow[0]?.median ?? 0),
      total,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}
