import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

interface PaperInput {
  s2Id: string;
  arxivId?: string | null;
  doi?: string | null;
  title: string;
  year?: number | null;
  cites?: number | null;
  abstractSnippet?: string | null;
}

export async function POST(req: NextRequest) {
  try {
    const { papers }: { papers: PaperInput[] } = await req.json();
    if (!papers?.length) {
      return NextResponse.json({ error: "No papers provided" }, { status: 400 });
    }

    let inserted = 0;
    let skipped = 0;

    const duplicates: string[] = [];

    for (const p of papers) {
      // Skip if already in DB (by semantic_scholar_id, doi, or arxiv_id)
      const existing = await query(
        `SELECT id FROM papers WHERE semantic_scholar_id = $1
         OR ($2::text IS NOT NULL AND doi = $2)
         OR ($3::text IS NOT NULL AND arxiv_id = $3)
         LIMIT 1`,
        [p.s2Id, p.doi || null, p.arxivId || null],
      );
      if (existing.length > 0) {
        skipped++;
        duplicates.push(p.title);
        continue;
      }

      try {
        await query(
          `INSERT INTO papers (
            title, year, semantic_scholar_id, arxiv_id, doi,
            citation_count, abstract, pipeline_status, source, generation, created_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'seed', 'seed-ui', 1, NOW())`,
          [
            p.title,
            p.year || null,
            p.s2Id,
            p.arxivId || null,
            p.doi || null,
            p.cites || 0,
            p.abstractSnippet || null,
          ],
        );
        inserted++;
      } catch (e) {
        // Handle race condition on unique constraints
        if (e instanceof Error && e.message.includes("duplicate key")) {
          skipped++;
          duplicates.push(p.title);
        } else {
          throw e;
        }
      }
    }

    return NextResponse.json({ inserted, skipped, duplicates, total: papers.length });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}
