import { NextResponse } from "next/server";
import { query } from "@/lib/db";
import { chatJSON } from "@/lib/llm";

export const dynamic = "force-dynamic";

// --- Pattern normalization ---
const CANONICAL_PATTERNS = [
  "hierarchical", "hybrid", "peer", "supervisor", "blackboard",
  "auction", "contract_net", "stigmergy", "debate", "bdi",
  "generator_critic", "none",
];
const LONG_TAIL_THRESHOLD = 5;

// Known variant → canonical mapping (handles the obvious ones instantly)
const KNOWN_VARIANTS: Record<string, string> = {
  "leader_follower": "hierarchical",
  "leader-follower": "hierarchical",
  "market_based": "auction",
  "market-based": "auction",
  "market": "auction",
  "flat": "peer",
  "decentralized": "peer",
  "consensus": "peer",
  "heterarchical": "peer",
  "negotiation": "contract_net",
  "protocol": "none",
  "null": "none",
};

// LLM-generated cache for truly unknown patterns
let _llmCache: Record<string, string> = {};
let _llmCacheTs = 0;
const CACHE_TTL_MS = 3600_000;

function normalizePattern(raw: string): string | null {
  const lower = raw.toLowerCase().trim();
  // Direct match to canonical
  if (CANONICAL_PATTERNS.includes(lower)) return null; // already canonical
  // Check known variants
  if (KNOWN_VARIANTS[lower]) return KNOWN_VARIANTS[lower];
  // Check if raw string starts with a known variant (handles "market-based (hybrid of...)")
  for (const [prefix, target] of Object.entries(KNOWN_VARIANTS)) {
    if (lower.startsWith(prefix)) return target;
  }
  // Check LLM cache
  if (_llmCache[raw]) return _llmCache[raw];
  return null; // unknown, will go to LLM batch
}

async function normalizeBatchWithLLM(unknowns: string[]): Promise<Record<string, string>> {
  if (unknowns.length === 0) return {};
  const now = Date.now();
  if (now - _llmCacheTs < CACHE_TTL_MS) {
    const stillUnknown = unknowns.filter((u) => !_llmCache[u]);
    if (stillUnknown.length === 0) {
      return Object.fromEntries(unknowns.map((u) => [u, _llmCache[u]]));
    }
  }

  try {
    const map = await chatJSON<Record<string, string>>(
      `You normalize coordination pattern names from a MAS research corpus.
Map each variant to the closest canonical pattern from this list:
${CANONICAL_PATTERNS.join(", ")}

If genuinely novel and doesn't fit any, use "other".
Return JSON object only: {"variant": "canonical", ...}`,
      `Normalize: ${JSON.stringify(unknowns)}`,
      { model: "gpt-5-nano", maxTokens: 256 },
    );
    _llmCache = { ..._llmCache, ...map };
    _llmCacheTs = now;
    return map;
  } catch {
    // Hard fallback
    const fb: Record<string, string> = {};
    for (const u of unknowns) fb[u] = "other";
    return fb;
  }
}

export async function GET() {
  try {
    // Only high-relevance papers (4-5) for dashboard cards
    const REL = "AND relevance_score >= 4";

    // Coordination patterns (raw from DB)
    const rawPatterns = await query(`
      SELECT COALESCE(analysis->>'coordination_pattern', 'null') as pattern, COUNT(*) as cnt
      FROM papers WHERE analysis IS NOT NULL ${REL}
      GROUP BY 1 ORDER BY 2 DESC
    `);

    // Analyzed count
    const analyzedRow = await query(
      `SELECT COUNT(*) as cnt FROM papers WHERE analysis IS NOT NULL ${REL}`
    );
    const analyzedCount = Number(analyzedRow[0]?.cnt ?? 0);

    // Parse raw data
    const parsed = rawPatterns.map((r) => ({
      pattern: String(r.pattern),
      count: Number(r.cnt),
    }));

    // Separate canonical (high-count) from long-tail
    const buckets: Record<string, { count: number; variants: string[] }> = {};
    const unknowns: string[] = [];

    for (const p of parsed) {
      if (p.count >= LONG_TAIL_THRESHOLD) {
        // Already a major pattern — keep as-is
        buckets[p.pattern] = { count: p.count, variants: [] };
      } else {
        // Try to normalize
        const target = normalizePattern(p.pattern);
        if (target) {
          if (!buckets[target]) buckets[target] = { count: 0, variants: [] };
          buckets[target].count += p.count;
          buckets[target].variants.push(p.pattern);
        } else {
          unknowns.push(p.pattern);
        }
      }
    }

    // Batch-normalize unknowns via LLM (if any)
    if (unknowns.length > 0) {
      const llmMap = await normalizeBatchWithLLM(unknowns);
      for (const p of parsed) {
        if (unknowns.includes(p.pattern)) {
          const target = llmMap[p.pattern] || "other";
          if (!buckets[target]) buckets[target] = { count: 0, variants: [] };
          buckets[target].count += p.count;
          buckets[target].variants.push(p.pattern);
        }
      }
    }

    // Build sorted output
    const patterns = Object.entries(buckets)
      .map(([pattern, { count, variants }]) => ({ pattern, count, variants }))
      .sort((a, b) => b.count - a.count);

    // Build mergedMap for the frontend (pattern → [variants that were folded in])
    const mergedMap: Record<string, string[]> = {};
    for (const p of patterns) {
      if (p.variants.length > 0) {
        mergedMap[p.pattern] = p.variants;
      }
    }

    // Missing classical concepts — count by named concept using regex
    const CONCEPTS: [string, string][] = [
      ["BDI", "BDI|belief.desire.intention"],
      ["Blackboard", "blackboard"],
      ["Contract Net", "contract.net"],
      ["FIPA Protocols", "FIPA"],
      ["Joint Intentions", "joint.intention|joint.persistent"],
      ["SharedPlans", "[Ss]hared.?[Pp]lans?"],
      ["Organizational Models", "organizational.*(model|paradigm|structure|framework)"],
      ["MOISE/AGR", "MOISE|AGR"],
      ["HTN Planning", "HTN|hierarchical.task.network"],
      ["Normative MAS", "norm.based|normative"],
      ["Argumentation", "argument\\w*\\s*framework"],
      ["Consensus Protocols", "consensus"],
      ["Trust & Reputation", "trust.{0,10}reputation|reputation.{0,10}trust"],
      ["Auction/Mechanism Design", "auction|mechanism.design"],
      ["KQML", "KQML"],
      ["Mixed-Initiative", "mixed.initiative"],
    ];
    const conceptBase = `analysis IS NOT NULL
      AND analysis->>'classical_concepts_missing' IS NOT NULL
      AND analysis->>'classical_concepts_missing' NOT IN ('none','None','','null')
      ${REL}`;
    const unions = CONCEPTS.map(
      ([name, pattern]) => `
      SELECT '${name}' as concept, COUNT(*) as cnt
      FROM papers
      WHERE ${conceptBase}
        AND analysis->>'classical_concepts_missing' ~* '${pattern}'`
    ).join("\n  UNION ALL");
    const missingClassical = await query(
      `SELECT * FROM (${unions}) sub WHERE cnt > 0 ORDER BY cnt DESC LIMIT 10`
    );

    return NextResponse.json({
      patterns: patterns.map(({ pattern, count }) => ({ pattern, count })),
      analyzedCount,
      mergedMap,
      missingClassical: missingClassical.map((r) => ({
        concept: String(r.concept).substring(0, 80),
        count: Number(r.cnt),
      })),
    });
  } catch (e) {
    return NextResponse.json(
      { patterns: [], analyzedCount: 0, missingClassical: [], error: e instanceof Error ? e.message : "Unknown" },
      { status: 500 }
    );
  }
}
