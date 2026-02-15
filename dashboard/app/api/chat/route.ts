import { NextRequest, NextResponse } from "next/server";
import { query, ensureTables } from "@/lib/db";
import { chatCompletion } from "@/lib/llm";

const SYNTH_SYSTEM = `You are a research analyst for the Sutra project — a survey bridging classical MAS (1980-2010) with modern LLM agent systems (2023-2026).

Given a question and relevant papers retrieved from the corpus, synthesize a clear, insightful answer.

Guidelines:
- Be specific: cite paper titles and years
- Connect findings to the Sutra thesis (classical MAS concepts are being reinvented without citation)
- Highlight Lost Canary signals (classical concepts that modern papers miss)
- Highlight Rosetta Stone mappings (classical concept → modern equivalent)
- Note coordination patterns: supervisor, peer, blackboard, contract_net, debate, etc.
- Keep answers concise (3-8 sentences) but substantive
- If no relevant results were found, say so and suggest a rephrased query
- End with one follow-up question the researcher might want to ask next`;

/** Postgres full-text search with ts_rank — same logic as dashboard_web.py _db_search */
async function searchPapers(q: string, top = 15) {
  return query(
    `SELECT id, title, year, venue, citation_count, arxiv_id, doi,
            semantic_scholar_id, is_classical, has_code, repo_url,
            relevance_score, pipeline_status,
            LEFT(abstract, 300) as abstract_snippet,
            analysis->>'key_contribution_summary' as key_contribution,
            analysis->>'coordination_pattern' as coordination_pattern,
            analysis->>'theoretical_grounding' as grounding,
            analysis->>'classical_concepts_missing' as missing,
            analysis->>'unique_contribution' as unique_contribution,
            ts_rank_cd(
              to_tsvector('english',
                COALESCE(title,'') || ' ' ||
                COALESCE(abstract,'') || ' ' ||
                COALESCE(analysis->>'key_contribution_summary','') || ' ' ||
                COALESCE(analysis->>'unique_contribution','')
              ),
              plainto_tsquery('english', $1)
            ) as rank
     FROM papers
     WHERE pipeline_status NOT IN ('archived')
       AND (
         to_tsvector('english',
           COALESCE(title,'') || ' ' ||
           COALESCE(abstract,'') || ' ' ||
           COALESCE(analysis->>'key_contribution_summary','') || ' ' ||
           COALESCE(analysis->>'unique_contribution','')
         ) @@ plainto_tsquery('english', $1)
         OR title ILIKE $2
       )
     ORDER BY rank DESC, citation_count DESC NULLS LAST
     LIMIT $3`,
    [q, `%${q}%`, top],
  );
}

function paperLink(r: Record<string, unknown>): string {
  if (r.arxiv_id) return `https://arxiv.org/abs/${r.arxiv_id}`;
  if (r.doi) return `https://doi.org/${r.doi}`;
  if (r.semantic_scholar_id)
    return `https://www.semanticscholar.org/paper/${r.semantic_scholar_id}`;
  return `https://scholar.google.com/scholar?q=${encodeURIComponent(String(r.title || "").slice(0, 100))}`;
}

export async function POST(req: NextRequest) {
  try {
    await ensureTables();

    const { question } = await req.json();
    if (!question?.trim()) {
      return NextResponse.json({ error: "Empty question" }, { status: 400 });
    }

    // Step 1: Retrieve via Postgres full-text search
    const rows = await searchPapers(question.trim());

    // Format results for display and LLM context
    const sources = rows.map((r) => ({
      id: r.id,
      title: r.title,
      year: r.year,
      citations: r.citation_count || 0,
      pattern: r.coordination_pattern || "none",
      summary: (r.key_contribution || r.abstract_snippet || "").slice(0, 200),
      classical: r.is_classical || false,
      grounding: r.grounding,
      missing: r.missing,
      link: paperLink(r),
      score: Number(r.rank || 0),
    }));

    // Step 2: Synthesize answer with LLM (temperature: 1 for gpt-5-mini compat)
    let answer: string;
    try {
      const context = sources
        .slice(0, 12)
        .map(
          (s, i) =>
            `${i + 1}. "${s.title}" (${s.year || "?"}, ${s.citations} cites, pattern: ${s.pattern})${s.classical ? " [CLASSICAL]" : ""}\n   ${s.summary}${s.missing ? `\n   Missing concept: ${s.missing}` : ""}`,
        )
        .join("\n\n");

      answer = await chatCompletion(
        SYNTH_SYSTEM,
        `Question: ${question}\n\nRetrieved papers (${sources.length} results, showing top 12):\n\n${context}`,
        { temperature: 1 },
      );
    } catch {
      answer =
        sources.length > 0
          ? `Found ${sources.length} relevant papers but synthesis failed. Top result: "${sources[0].title}" (${sources[0].year}).`
          : "No relevant papers found. Try rephrasing your question.";
    }

    // Save to history (fire and forget)
    query(
      "INSERT INTO research_chat (question, answer, sql_used, sources) VALUES ($1, $2, $3, $4)",
      [
        question,
        answer,
        "full-text-search",
        JSON.stringify(sources.slice(0, 12).map((s) => s.id)),
      ],
    ).catch(() => {});

    return NextResponse.json({
      answer,
      sources: sources.slice(0, 12),
      total: sources.length,
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 },
    );
  }
}

export async function GET() {
  try {
    await ensureTables();
    const rows = await query(
      "SELECT id, question, answer, sql_used, sources, created_at FROM research_chat ORDER BY created_at DESC LIMIT 20",
    );
    rows.reverse();
    return NextResponse.json(rows);
  } catch {
    return NextResponse.json([]);
  }
}
