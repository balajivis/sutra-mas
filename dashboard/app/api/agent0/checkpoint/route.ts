import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";
import { chatCompletion } from "@/lib/llm";

export const dynamic = "force-dynamic";

/**
 * GET /api/agent0/checkpoint?skip=concept_name
 *
 * Generates a real judgment question from Lost Canary data.
 * 1. Finds the most frequent "classical_concepts_missing" concept
 * 2. Pulls evidence papers mentioning that concept
 * 3. Generates AI assessment via LLM
 * 4. Returns structured checkpoint
 */
export async function GET(req: NextRequest) {
  const skip = req.nextUrl.searchParams.get("skip") || "";

  try {
    // Step 1: Find the top missing classical concept
    // Extract from analysis JSONB, count frequency across papers
    const conceptRows = await query(
      `SELECT concept, COUNT(*) as cnt
       FROM (
         SELECT TRIM(unnest(string_to_array(
           analysis->>'classical_concepts_missing', ','
         ))) as concept
         FROM papers
         WHERE analysis IS NOT NULL
           AND analysis->>'classical_concepts_missing' IS NOT NULL
           AND analysis->>'classical_concepts_missing' != ''
           AND analysis->>'classical_concepts_missing' != 'none'
       ) sub
       WHERE concept != '' AND concept NOT ILIKE $1
       GROUP BY concept
       ORDER BY cnt DESC
       LIMIT 5`,
      [skip ? `%${skip}%` : "____NOMATCH____"]
    );

    if (conceptRows.length === 0) {
      return NextResponse.json({
        checkpoint: null,
        message: "No Lost Canary candidates found in the database.",
      });
    }

    const topConcept = (conceptRows[0].concept as string).trim();
    const conceptCount = Number(conceptRows[0].cnt);

    // Step 2: Pull evidence papers that mention this concept
    const evidencePapers = await query(
      `SELECT id, title, year, citation_count,
              analysis->>'coordination_pattern' as pattern,
              analysis->>'key_contribution_summary' as summary,
              analysis->>'theoretical_grounding' as grounding,
              analysis->>'classical_concepts_missing' as missing,
              modernity_score
       FROM papers
       WHERE analysis IS NOT NULL
         AND analysis->>'classical_concepts_missing' ILIKE $1
       ORDER BY citation_count DESC NULLS LAST
       LIMIT 4`,
      [`%${topConcept}%`]
    );

    // Build evidence array
    const evidence = evidencePapers.map((p) => ({
      label: `${p.title} (${p.year})`,
      detail: `${p.citation_count || 0} citations. Pattern: ${p.pattern || "none"}. Grounding: ${p.grounding || "unknown"}. Summary: ${((p.summary as string) || "").slice(0, 150)}`,
      paperId: p.id,
    }));

    // Also check if there's a classical paper for this concept
    const classicalRow = await query(
      `SELECT id, title, year, citation_count
       FROM papers
       WHERE is_classical = true
         AND (
           title ILIKE $1
           OR abstract ILIKE $1
           OR analysis->>'key_contribution_summary' ILIKE $1
         )
       ORDER BY citation_count DESC NULLS LAST
       LIMIT 1`,
      [`%${topConcept}%`]
    );

    if (classicalRow.length > 0) {
      const c = classicalRow[0];
      evidence.unshift({
        label: `${c.title} (${c.year}) [CLASSICAL]`,
        detail: `${c.citation_count || 0} total citations. This is the classical source for "${topConcept}".`,
        paperId: c.id as number,
      });
    }

    // Step 3: Generate AI assessment
    let aiAssessment = "";
    let aiConfidence = 0.5;

    try {
      const evidenceText = evidence
        .map((e) => `- ${e.label}: ${e.detail}`)
        .join("\n");

      const aiResponse = await chatCompletion(
        `You are a research assessment agent analyzing whether a classical MAS concept is genuinely "lost" in modern LLM agent systems. A "Lost Canary" is a concept with high classical citations but near-zero modern references, indicating the field has forgotten valuable prior work.

Respond with a concise assessment (2-3 sentences max) starting with GENUINELY LOST, PARTIALLY REINVENTED, or NOT LOST. Then give a confidence score 0.0-1.0 on the last line like: CONFIDENCE: 0.85`,
        `Concept: "${topConcept}"
Found in ${conceptCount} modern papers as a missing classical concept.

Evidence:
${evidenceText}

Is "${topConcept}" genuinely lost in modern LLM agent systems?`,
        { model: "gpt-5-mini", maxTokens: 300, temperature: 0.3 }
      );

      // Parse confidence from response
      const confMatch = aiResponse.match(/CONFIDENCE:\s*([\d.]+)/i);
      if (confMatch) {
        aiConfidence = parseFloat(confMatch[1]);
        aiAssessment = aiResponse.replace(/CONFIDENCE:\s*[\d.]+/i, "").trim();
      } else {
        aiAssessment = aiResponse.trim();
        aiConfidence = 0.7;
      }
    } catch {
      aiAssessment = `Analysis pending. "${topConcept}" appears in ${conceptCount} papers as a missing classical concept. Manual review recommended.`;
      aiConfidence = 0.5;
    }

    // Step 4: Build checkpoint
    const checkpoint = {
      id: `ckpt-${topConcept.replace(/\s+/g, "-").toLowerCase()}-${Date.now()}`,
      type: "novelty" as const,
      question: `Is "${topConcept}" a genuinely lost concept in modern LLM agent systems, or has it been reinvented under a different name?`,
      evidence,
      aiAssessment,
      aiConfidence,
      concept: topConcept,
      conceptCount,
      alternatives: conceptRows.slice(1, 4).map((r) => ({
        concept: (r.concept as string).trim(),
        count: Number(r.cnt),
      })),
    };

    return NextResponse.json({ checkpoint });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error", checkpoint: null },
      { status: 500 }
    );
  }
}
