"use client";

import Link from "next/link";

export interface PaperCardData {
  id: number | string;
  title: string;
  year: number | null;
  venue?: string | null;
  citations: number;
  pattern?: string | null;
  summary?: string;
  classical?: boolean;
  cluster?: string | null;
  has_code?: boolean;
  repo_url?: string | null;
  relevance?: number | null;
  grounding?: string | null;
  missing?: string | null;
  score?: number;
}

const PATTERN_COLORS: Record<string, string> = {
  hierarchical: "#fbbf24",
  supervisor: "#f97316",
  peer: "#34d399",
  blackboard: "#60a5fa",
  auction: "#a78bfa",
  contract_net: "#f472b6",
  stigmergy: "#22d3ee",
  debate: "#e879f9",
  bdi: "#fb923c",
  hybrid: "#94a3b8",
  generator_critic: "#4ade80",
};

function Tag({ color, label }: { color: string; label: string }) {
  return (
    <span
      className="inline-block text-[10px] px-1.5 py-0.5 rounded"
      style={{ background: `${color}15`, color }}
    >
      {label}
    </span>
  );
}

interface Props {
  paper: PaperCardData;
  index?: number;
  defaultExpanded?: boolean;
}

export function PaperCard({ paper: r, index, defaultExpanded }: Props) {
  return (
    <Link
      href={`/paper/${r.id}`}
      className="block border border-border rounded-lg p-4 hover:border-accent/30 transition group"
      style={{ background: "var(--card)" }}
    >
      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 mb-1">
            {index != null && (
              <span className="text-xs text-dim tabular-nums w-5 shrink-0 pt-0.5">
                {index}.
              </span>
            )}
            <span className="text-sm text-text group-hover:text-accent transition leading-snug">
              {r.title}
            </span>
          </div>

          {/* Meta row */}
          <div
            className="flex items-center gap-2.5 flex-wrap"
            style={{ marginLeft: index != null ? "1.75rem" : 0 }}
          >
            <span className="text-xs text-dim tabular-nums">
              {r.year || "?"}
            </span>
            <span className="text-xs text-dim tabular-nums">
              {r.citations.toLocaleString()} cites
            </span>
            {r.venue && (
              <span className="text-xs text-dim truncate max-w-[180px]">
                {r.venue}
              </span>
            )}
            {r.relevance != null && r.relevance > 0 && (
              <span className="text-xs text-dim">R{r.relevance}/5</span>
            )}
            {r.classical && <Tag color="#fbbf24" label="classical" />}
            {r.pattern &&
              r.pattern !== "none" &&
              r.pattern !== "null" && (
                <Tag
                  color={PATTERN_COLORS[r.pattern] || "#71717a"}
                  label={r.pattern}
                />
              )}
            {r.cluster && <Tag color="#34d399" label={r.cluster} />}
            {r.has_code && <Tag color="#22d3ee" label="has code" />}
            {r.grounding &&
              r.grounding !== "none" &&
              r.grounding !== "null" && (
                <Tag color="#a78bfa" label={r.grounding} />
              )}
          </div>
        </div>

        {/* Score / citation badge */}
        <div className="text-right shrink-0">
          {r.score != null && r.score > 0 ? (
            <div className="text-[10px] text-dim tabular-nums">{r.score}</div>
          ) : (
            <div className="text-lg font-bold tabular-nums text-zinc-600">
              {r.citations.toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {/* Summary */}
      {r.summary && (
        <div style={{ marginLeft: index != null ? "1.75rem" : 0 }}>
          <p
            className={`text-xs text-dim leading-relaxed mt-2 ${defaultExpanded ? "" : "line-clamp-2"}`}
          >
            {r.summary}
          </p>
        </div>
      )}

      {/* Missing classical concepts */}
      {r.missing &&
        r.missing !== "none" &&
        r.missing !== "None" && (
          <div
            className="mt-2 text-[10px] text-amber-400/70"
            style={{ marginLeft: index != null ? "1.75rem" : 0 }}
          >
            Missing: {r.missing.slice(0, 150)}
          </div>
        )}
    </Link>
  );
}
