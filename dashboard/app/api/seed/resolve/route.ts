import { NextRequest, NextResponse } from "next/server";
import { chatCompletion } from "@/lib/llm";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/* ---------- URL parsing ---------- */

function extractPaperId(url: string): { type: "arxiv" | "doi" | "s2"; id: string } | null {
  // arXiv: https://arxiv.org/abs/2308.00352 or arxiv.org/pdf/...
  const arxiv = url.match(/arxiv\.org\/(?:abs|pdf)\/(\d{4}\.\d{4,5}(?:v\d+)?)/);
  if (arxiv) return { type: "arxiv", id: arxiv[1] };

  // Semantic Scholar: https://www.semanticscholar.org/paper/.../abc123
  const s2 = url.match(/semanticscholar\.org\/paper\/[^/]*\/([a-f0-9]{40})/i);
  if (s2) return { type: "s2", id: s2[1] };

  // DOI: https://doi.org/10.1234/...
  const doi = url.match(/doi\.org\/(10\.\d{4,}\/[^\s]+)/);
  if (doi) return { type: "doi", id: doi[1] };

  // Bare arXiv ID
  if (/^\d{4}\.\d{4,5}(v\d+)?$/.test(url.trim())) {
    return { type: "arxiv", id: url.trim() };
  }

  // Bare DOI: 10.1145/191246.191322
  if (/^10\.\d{4,}\/\S+$/.test(url.trim())) {
    return { type: "doi", id: url.trim() };
  }

  return null;
}

function s2Query(parsed: { type: string; id: string }): string {
  const base = "https://api.semanticscholar.org/graph/v1/paper";
  const paperFields = "paperId,externalIds,title,abstract,year,venue,citationCount,authors";
  const refDot = "references.paperId,references.externalIds,references.title,references.year,references.citationCount,references.abstract";
  const citeDot = "citations.paperId,citations.externalIds,citations.title,citations.year,citations.citationCount,citations.abstract";
  const fields = `${paperFields},${refDot},${citeDot}`;

  const prefix =
    parsed.type === "arxiv" ? `ARXIV:${parsed.id}` :
    parsed.type === "doi" ? `DOI:${parsed.id}` :
    parsed.id;

  return `${base}/${prefix}?fields=${fields}&citations.limit=500&references.limit=500`;
}

/* ---------- Types ---------- */

interface S2Paper {
  paperId: string;
  externalIds?: { ArXiv?: string; DOI?: string };
  title: string;
  abstract?: string;
  year?: number;
  venue?: string;
  citationCount?: number;
  authors?: { name: string }[];
}

interface S2Ref {
  paperId: string;
  externalIds?: { ArXiv?: string; DOI?: string };
  title: string;
  year?: number;
  citationCount?: number;
  abstract?: string;
}

/* ---------- Handler ---------- */

export async function POST(req: NextRequest) {
  try {
    const { url } = await req.json();
    if (!url?.trim()) {
      return NextResponse.json({ error: "No URL provided" }, { status: 400 });
    }

    // 1. Parse URL
    const parsed = extractPaperId(url.trim());
    if (!parsed) {
      return NextResponse.json(
        { error: "Could not parse paper ID from URL. Supported: arXiv, DOI, Semantic Scholar." },
        { status: 400 },
      );
    }

    // 2. Fetch from Semantic Scholar
    const s2Url = s2Query(parsed);
    const s2Key = process.env.SEMANTIC_SCHOLAR_API_KEY;
    const headers: Record<string, string> = {};
    if (s2Key) headers["x-api-key"] = s2Key;

    const s2Res = await fetch(s2Url, { headers });
    if (!s2Res.ok) {
      const text = await s2Res.text();
      return NextResponse.json(
        { error: `Semantic Scholar API error (${s2Res.status}): ${text.slice(0, 200)}` },
        { status: 502 },
      );
    }

    const paper: S2Paper & { references?: S2Ref[]; citations?: S2Ref[] } =
      await s2Res.json();

    // 3. Check which papers already exist in our DB
    const allS2Ids: string[] = [];
    const refs = (paper.references || [])
      .filter((p) => p?.paperId && p?.title);
    const cites = (paper.citations || [])
      .filter((p) => p?.paperId && p?.title);

    for (const p of [...refs, ...cites]) {
      if (p.paperId) allS2Ids.push(p.paperId);
    }
    if (paper.paperId) allS2Ids.push(paper.paperId);

    let existingIds = new Set<string>();
    if (allS2Ids.length > 0) {
      const rows = await query(
        `SELECT semantic_scholar_id FROM papers WHERE semantic_scholar_id = ANY($1)`,
        [allS2Ids],
      );
      existingIds = new Set(rows.map((r) => r.semantic_scholar_id as string));
    }

    // 4. LLM: extract key contribution
    let keyContribution = "";
    if (paper.abstract) {
      try {
        keyContribution = await chatCompletion(
          "You are a research paper analyst. Given a paper title and abstract, extract the single key unique contribution in 1-2 sentences. Be specific and technical. No preamble.",
          `Title: ${paper.title}\n\nAbstract: ${paper.abstract}`,
          { maxTokens: 256, temperature: 1 },
        );
      } catch {
        keyContribution = "(LLM extraction failed)";
      }
    }

    // 5. Format response
    const formatPaper = (p: S2Ref) => ({
      s2Id: p.paperId,
      arxivId: p.externalIds?.ArXiv || null,
      doi: p.externalIds?.DOI || null,
      title: p.title,
      year: p.year || null,
      cites: p.citationCount || 0,
      abstractSnippet: p.abstract ? p.abstract.slice(0, 200) + (p.abstract.length > 200 ? "..." : "") : null,
      inDb: existingIds.has(p.paperId),
    });

    return NextResponse.json({
      paper: {
        s2Id: paper.paperId,
        arxivId: paper.externalIds?.ArXiv || null,
        doi: paper.externalIds?.DOI || null,
        title: paper.title,
        abstract: paper.abstract || null,
        year: paper.year || null,
        venue: paper.venue || null,
        cites: paper.citationCount || 0,
        authors: (paper.authors || []).map((a) => a.name),
        keyContribution,
        inDb: existingIds.has(paper.paperId),
      },
      references: refs.map(formatPaper).sort((a, b) => b.cites - a.cites),
      citations: cites.map(formatPaper).sort((a, b) => b.cites - a.cites),
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}
