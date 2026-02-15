import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

export const dynamic = "force-dynamic";

/**
 * GET /api/agent0/citation-cliff
 *
 * Returns concept-grouped historical citation data for the Citation Cliff
 * visualization. Reads from pipeline/data/citation_cliff_full.json which
 * has full 1980-2026 per-year distributions grouped by concept.
 *
 * Falls back to modernity_scores.json (per-paper, 2012-2026) if the full
 * file is not available.
 */
export async function GET() {
  try {
    const raw = await readDataFile("citation_cliff_full.json");
    const data = JSON.parse(raw);

    return NextResponse.json({
      metadata: data.metadata,
      yearRange: data.yearRange,
      concepts: data.concepts,
      annotations: data.annotations,
    });
  } catch {
    // Fallback: try legacy modernity_scores.json
    try {
      const raw = await readDataFile("modernity_scores.json");
      const data = JSON.parse(raw);
      return NextResponse.json({
        metadata: data.metadata,
        yearRange: [],
        concepts: [],
        annotations: [],
        legacy: true,
        papers: data.results || [],
      });
    } catch (e) {
      return NextResponse.json(
        {
          error: e instanceof Error ? e.message : "Unknown error",
          concepts: [],
          yearRange: [],
          annotations: [],
        },
        { status: 500 }
      );
    }
  }
}

async function readDataFile(filename: string): Promise<string> {
  const candidates = [
    path.resolve(process.cwd(), "..", "pipeline", "data", filename),
    path.resolve(process.cwd(), "..", "..", "pipeline", "data", filename),
    `/home/azureuser/sutra/pipeline/data/${filename}`,
  ];

  for (const p of candidates) {
    try {
      return await readFile(p, "utf-8");
    } catch {
      continue;
    }
  }

  throw new Error(`Data file not found: ${filename}`);
}
