"use client";

import { useState, useCallback, useEffect } from "react";

/**
 * Pattern 2: Cognitive Forcing Functions (Bucinca et al., CHI 2021)
 *
 * At judgment checkpoints, the human must commit their assessment
 * BEFORE seeing the AI's recommendation. Prevents overreliance.
 *
 * Flow: Evidence -> Human commits -> AI revealed -> Deliberation
 */

type CheckpointPhase = "evidence" | "commit" | "reveal" | "deliberate";

interface EvidenceItem {
  label: string;
  detail: string;
  paperId?: number;
}

interface CheckpointItem {
  id: string;
  type: "novelty" | "significance" | "cluster_validity" | "thesis_direction";
  question: string;
  evidence: EvidenceItem[];
  aiAssessment: string;
  aiConfidence: number;
  concept?: string;
  alternatives?: { concept: string; count: number }[];
}

const TYPE_COLORS: Record<string, { color: string; label: string }> = {
  novelty: { color: "#fbbf24", label: "Novelty Assessment" },
  significance: { color: "#a78bfa", label: "Significance Judgment" },
  cluster_validity: { color: "#60a5fa", label: "Cluster Validity" },
  thesis_direction: { color: "#34d399", label: "Thesis Direction" },
};

export function JudgmentCheckpoint() {
  const [phase, setPhase] = useState<CheckpointPhase>("evidence");
  const [humanJudgment, setHumanJudgment] = useState("");
  const [humanConfidence, setHumanConfidence] = useState(50);
  const [finalVerdict, setFinalVerdict] = useState<
    "agree" | "disagree" | "partial" | null
  >(null);
  const [item, setItem] = useState<CheckpointItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skippedConcepts, setSkippedConcepts] = useState<string[]>([]);

  const fetchCheckpoint = useCallback(async (skip?: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = skip
        ? `/api/agent0/checkpoint?skip=${encodeURIComponent(skip)}`
        : "/api/agent0/checkpoint";
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.checkpoint) {
        setItem(data.checkpoint);
      } else {
        setError(data.message || "No checkpoint available");
        setItem(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
      setItem(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchCheckpoint();
  }, [fetchCheckpoint]);

  const handleCommit = useCallback(() => {
    if (humanJudgment.trim().length < 10) return;
    setPhase("reveal");
  }, [humanJudgment]);

  const handleDeliberate = useCallback(() => {
    setPhase("deliberate");
  }, []);

  const handleResolve = useCallback((verdict: "agree" | "disagree" | "partial") => {
    setFinalVerdict(verdict);
  }, []);

  const handleNextCheckpoint = useCallback(() => {
    if (item?.concept) {
      setSkippedConcepts((prev) => [...prev, item.concept!]);
    }
    setPhase("evidence");
    setHumanJudgment("");
    setHumanConfidence(50);
    setFinalVerdict(null);
    const allSkips = item?.concept
      ? [...skippedConcepts, item.concept].join(",")
      : skippedConcepts.join(",");
    fetchCheckpoint(allSkips || undefined);
  }, [item, skippedConcepts, fetchCheckpoint]);

  const handleReset = useCallback(() => {
    setPhase("evidence");
    setHumanJudgment("");
    setHumanConfidence(50);
    setFinalVerdict(null);
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-[10px] text-dim animate-pulse mb-1">
            Generating judgment checkpoint...
          </div>
          <div className="text-[9px] text-zinc-600">
            Analyzing Lost Canary candidates from pipeline data
          </div>
        </div>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-[10px] text-red-400 mb-2">
            {error || "No checkpoint data available"}
          </div>
          <button
            onClick={() => fetchCheckpoint()}
            className="px-3 py-1 text-[10px] rounded bg-zinc-800 text-dim hover:text-text border border-border transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const typeStyle = TYPE_COLORS[item.type] || TYPE_COLORS.novelty;

  return (
    <div className="h-full overflow-y-auto px-6 py-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-amber-400">
            Judgment Checkpoint
            <span className="text-dim ml-1">P2</span>
          </span>
          <span
            className="text-[9px] px-1.5 py-0.5 rounded"
            style={{
              background: typeStyle.color + "22",
              color: typeStyle.color,
            }}
          >
            {typeStyle.label}
          </span>
          {/* Phase indicator */}
          <div className="flex items-center gap-1 ml-2">
            {(["evidence", "commit", "reveal", "deliberate"] as const).map(
              (p, i) => (
                <div key={p} className="flex items-center">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      phase === p
                        ? "bg-amber-400"
                        : (["evidence", "commit", "reveal", "deliberate"] as const).indexOf(phase) > i
                          ? "bg-amber-400/40"
                          : "bg-zinc-700"
                    }`}
                  />
                  {i < 3 && (
                    <span className="w-3 h-px bg-zinc-700 mx-0.5" />
                  )}
                </div>
              )
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {finalVerdict && (
            <button
              onClick={handleReset}
              className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
            >
              reset
            </button>
          )}
          <button
            onClick={handleNextCheckpoint}
            className="text-[10px] text-dim hover:text-accent transition cursor-pointer px-2 py-0.5 rounded border border-border/50 hover:border-accent/30"
          >
            next checkpoint
          </button>
        </div>
      </div>

      {/* Question */}
      <div className="text-xs text-zinc-200 font-medium mb-3 leading-relaxed">
        {item.question}
      </div>

      <div className="flex gap-4">
        {/* Left: Evidence (always visible) */}
        <div className="flex-1 space-y-1.5">
          <div className="text-[9px] text-dim uppercase tracking-wider">
            Evidence ({item.evidence.length} sources)
          </div>
          {item.evidence.map((e, i) => (
            <div
              key={i}
              className="px-2 py-1.5 rounded bg-zinc-900/60 border border-border/40"
            >
              <div className="text-[10px] text-amber-400 font-medium">
                {e.label}
              </div>
              <div className="text-[10px] text-zinc-400 mt-0.5 leading-snug">
                {e.detail}
              </div>
            </div>
          ))}

          {/* Alternative concepts */}
          {item.alternatives && item.alternatives.length > 0 && (
            <div className="mt-2 pt-2 border-t border-border/30">
              <div className="text-[9px] text-dim uppercase tracking-wider mb-1">
                Other Lost Canary candidates
              </div>
              <div className="flex flex-wrap gap-1">
                {item.alternatives.map((alt) => (
                  <span
                    key={alt.concept}
                    className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-border/30"
                  >
                    {alt.concept} ({alt.count})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Human commitment + AI reveal */}
        <div className="flex-1 space-y-2">
          {/* Phase 1-2: Human must commit first */}
          {(phase === "evidence" || phase === "commit") && (
            <div>
              <div className="text-[9px] text-dim uppercase tracking-wider mb-1">
                Your assessment{" "}
                <span className="text-amber-400/60">
                  (commit before seeing AI)
                </span>
              </div>
              <textarea
                className="w-full h-20 bg-zinc-900 border border-border rounded px-2.5 py-2 text-[11px] text-zinc-200 placeholder:text-zinc-600 resize-none focus:outline-none focus:border-amber-400/50 transition"
                placeholder="Type your judgment here... What do you think the answer is? (min 10 chars)"
                value={humanJudgment}
                onChange={(e) => {
                  setHumanJudgment(e.target.value);
                  if (e.target.value.trim().length >= 10)
                    setPhase("commit");
                }}
              />
              <div className="flex items-center gap-3 mt-1.5">
                <label className="text-[9px] text-dim">
                  Confidence: {humanConfidence}%
                </label>
                <input
                  type="range"
                  min={10}
                  max={100}
                  step={5}
                  value={humanConfidence}
                  onChange={(e) =>
                    setHumanConfidence(Number(e.target.value))
                  }
                  className="flex-1 h-1 accent-amber-400"
                />
              </div>
              <button
                disabled={humanJudgment.trim().length < 10}
                onClick={handleCommit}
                className={`mt-2 w-full py-1.5 rounded text-[10px] font-bold uppercase tracking-wider transition cursor-pointer ${
                  humanJudgment.trim().length >= 10
                    ? "bg-amber-400/20 text-amber-400 hover:bg-amber-400/30 border border-amber-400/30"
                    : "bg-zinc-800 text-zinc-600 border border-zinc-700 cursor-not-allowed"
                }`}
              >
                Commit Judgment
              </button>
            </div>
          )}

          {/* Phase 3: AI Revealed */}
          {phase === "reveal" && (
            <div>
              <div className="text-[9px] text-dim uppercase tracking-wider mb-1">
                Your assessment{" "}
                <span className="text-accent">(committed)</span>
              </div>
              <div className="px-2.5 py-2 rounded bg-accent/5 border border-accent/20 text-[10px] text-zinc-300 leading-snug">
                {humanJudgment}
                <div className="text-[9px] text-dim mt-1">
                  Confidence: {humanConfidence}%
                </div>
              </div>

              <div className="mt-3">
                <div className="text-[9px] text-dim uppercase tracking-wider mb-1">
                  AI Assessment{" "}
                  <span className="text-purple-400">
                    ({Math.round(item.aiConfidence * 100)}% confidence)
                  </span>
                </div>
                <div className="px-2.5 py-2 rounded bg-purple-400/5 border border-purple-400/20 text-[10px] text-zinc-300 leading-snug">
                  {item.aiAssessment}
                </div>
              </div>

              <button
                onClick={handleDeliberate}
                className="mt-2 w-full py-1.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-400/20 text-purple-400 hover:bg-purple-400/30 border border-purple-400/30 transition cursor-pointer"
              >
                Deliberate
              </button>
            </div>
          )}

          {/* Phase 4: Deliberation */}
          {phase === "deliberate" && (
            <div>
              <div className="text-[9px] text-dim uppercase tracking-wider mb-1">
                Deliberation &mdash; Final judgment on &quot;{item.concept}&quot;
              </div>
              <div className="text-[10px] text-zinc-400 mb-2 leading-snug">
                Compare your assessment with the AI&apos;s. Where do you agree?
                Where do you disagree? Your final judgment shapes the
                research direction.
              </div>

              <div className="flex gap-2">
                {(
                  [
                    {
                      key: "agree" as const,
                      label: "Agree with AI",
                      color: "#34d399",
                    },
                    {
                      key: "partial" as const,
                      label: "Partially agree",
                      color: "#fbbf24",
                    },
                    {
                      key: "disagree" as const,
                      label: "Override AI",
                      color: "#f87171",
                    },
                  ] as const
                ).map((v) => (
                  <button
                    key={v.key}
                    onClick={() => handleResolve(v.key)}
                    className={`flex-1 py-2 rounded text-[10px] font-medium transition cursor-pointer border ${
                      finalVerdict === v.key
                        ? "border-2"
                        : "border-zinc-700 hover:border-zinc-500"
                    }`}
                    style={{
                      borderColor:
                        finalVerdict === v.key ? v.color : undefined,
                      background:
                        finalVerdict === v.key ? v.color + "15" : undefined,
                      color: finalVerdict === v.key ? v.color : "#a1a1aa",
                    }}
                  >
                    {v.label}
                  </button>
                ))}
              </div>

              {finalVerdict && (
                <div className="mt-2 px-2.5 py-2 rounded bg-zinc-900/80 border border-border text-[10px] text-accent leading-snug">
                  Verdict recorded: <strong>{finalVerdict}</strong>.
                  This judgment will be logged to the intervention dataset
                  for the cointelligence paper.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
