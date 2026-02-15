"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface InsightData {
  type: string;
  title: string;
  description: string;
  data: Record<string, unknown>[];
  total: number;
  error?: string;
}

const TYPE_STYLES: Record<string, { color: string; icon: string }> = {
  lost_canary: { color: "#fbbf24", icon: "\u{1F426}" },
  pattern_distribution: { color: "#34d399", icon: "\u{1F4CA}" },
  grounding_gaps: { color: "#f87171", icon: "\u26A0\uFE0F" },
  rosetta_entries: { color: "#60a5fa", icon: "\u{1F5FA}" },
  cross_era_bridges: { color: "#a78bfa", icon: "\u{1F309}" },
};

function LostCanaryTable({ data }: { data: Record<string, unknown>[] }) {
  return (
    <div className="space-y-3">
      {data.map((row, i) => {
        const paperIds = (row.paper_ids as number[]) || [];
        const paperTitles = (row.example_papers as string[]) || [];
        return (
          <div key={i} className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-amber-400 font-medium">
                {String(row.concept)}
              </span>
              <span className="text-xs text-dim tabular-nums">
                {Number(row.cnt)} papers
              </span>
            </div>
            {paperTitles.length > 0 && (
              <div className="space-y-1">
                {paperTitles.map((title, j) => (
                  <Link
                    key={j}
                    href={`/paper/${paperIds[j] || ""}`}
                    className="block text-xs text-dim hover:text-accent transition truncate"
                  >
                    &rarr; {title}
                  </Link>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function PatternTable({ data }: { data: Record<string, unknown>[] }) {
  const max = Math.max(...data.map((r) => Number(r.cnt) || 0), 1);
  return (
    <div className="space-y-2">
      {data.map((row, i) => (
        <Link
          key={i}
          href={`/papers?pattern=${encodeURIComponent(String(row.pattern))}`}
          className="grid items-center gap-x-3 hover:bg-white/[0.03] rounded px-2 py-1.5 -mx-2 transition"
          style={{ gridTemplateColumns: "140px 60px 60px 60px 60px 1fr" }}
        >
          <span className="text-sm text-emerald-400 font-medium truncate">
            {String(row.pattern)}
          </span>
          <span className="text-xs text-text text-right tabular-nums">
            {Number(row.cnt)}
          </span>
          <span className="text-xs text-dim text-right tabular-nums">
            {Number(row.classical_cnt)} cl
          </span>
          <span className="text-xs text-dim text-right tabular-nums">
            {Number(row.modern_cnt)} mod
          </span>
          <span className="text-xs text-dim text-right tabular-nums">
            ~{Number(row.avg_cites)} cites
          </span>
          <div className="h-4 bg-zinc-900 rounded overflow-hidden">
            <div
              className="h-full rounded"
              style={{
                width: `${(Number(row.cnt) / max) * 100}%`,
                background: "#34d399",
                opacity: 0.7,
              }}
            />
          </div>
        </Link>
      ))}
    </div>
  );
}

function PaperListTable({ data }: { data: Record<string, unknown>[] }) {
  return (
    <div className="space-y-2">
      {data.map((row, i) => (
        <Link
          key={i}
          href={`/paper/${row.id}`}
          className="block border border-border rounded-lg p-3 hover:border-accent/30 transition"
        >
          <div className="text-sm text-text font-medium leading-snug">
            {String(row.title)}
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-dim">
            <span className="tabular-nums">{String(row.year || "?")}</span>
            <span className="tabular-nums">
              {Number(row.citation_count || 0).toLocaleString()} cites
            </span>
            {row.pattern ? String(row.pattern) !== "none" && (
              <span className="text-accent/70">{String(row.pattern)}</span>
            ) : null}
            {row.grounding ? (
              <span
                className={
                  String(row.grounding) === "strong"
                    ? "text-emerald-400/70"
                    : String(row.grounding) === "weak"
                    ? "text-amber-400/70"
                    : "text-red-400/70"
                }
              >
                {String(row.grounding)} grounding
              </span>
            ) : null}
          </div>
          {row.summary ? (
            <p className="text-xs text-dim/80 mt-1.5 leading-relaxed line-clamp-2">
              {String(row.summary).slice(0, 200)}
            </p>
          ) : null}
          {row.missing &&
            String(row.missing) !== "none" &&
            String(row.missing) !== "None" ? (
              <p className="text-[11px] text-amber-400/60 mt-1 truncate">
                Missing: {String(row.missing).slice(0, 120)}
              </p>
            ) : null}
        </Link>
      ))}
    </div>
  );
}

function RosettaTable({ data }: { data: Record<string, unknown>[] }) {
  return (
    <div className="space-y-3">
      {data.map((row, i) => {
        let entries: Record<string, string> = {};
        try {
          entries =
            typeof row.entry === "string" ? JSON.parse(row.entry) : {};
        } catch {
          /* ignore */
        }
        const paperIds = (row.paper_ids as number[]) || [];
        const paperTitles = (row.example_papers as string[]) || [];
        const keys = Object.keys(entries);
        const cardTitle = keys.length > 0
          ? keys.slice(0, 2).join(" / ")
          : `Entry ${i + 1}`;
        const cnt = Number(row.cnt);

        return (
          <div key={i} className="border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-blue-400 font-medium">
                {cardTitle}
              </span>
              <span className="text-[10px] text-dim tabular-nums px-2 py-0.5 bg-zinc-800 rounded">
                {cnt} {cnt === 1 ? "paper" : "papers"}
              </span>
            </div>
            <div className="space-y-2 bg-zinc-900/50 rounded-md p-3">
              <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-center mb-1">
                <span className="text-[10px] text-dim uppercase tracking-wider">Classical</span>
                <span />
                <span className="text-[10px] text-dim uppercase tracking-wider">Modern</span>
              </div>
              {Object.entries(entries).map(([classical, modern]) => (
                <div
                  key={classical}
                  className="grid grid-cols-[1fr_auto_1fr] gap-3 items-start"
                >
                  <span className="text-xs text-amber-400">{classical}</span>
                  <span className="text-xs text-dim">&rarr;</span>
                  <span className="text-xs text-emerald-400">{modern}</span>
                </div>
              ))}
            </div>
            {paperTitles.length > 0 && (
              <div className="mt-3 pt-2 border-t border-border/50 space-y-1">
                <span className="text-[10px] text-dim uppercase tracking-wider">Evidence</span>
                {paperTitles.map((title, j) => (
                  <Link
                    key={j}
                    href={`/paper/${paperIds[j] || ""}`}
                    className="block text-[11px] text-dim hover:text-accent transition truncate"
                  >
                    &rarr; {title}
                  </Link>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function InsightDetailPage() {
  const params = useParams();
  const type = params.type as string;
  const [data, setData] = useState<InsightData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/insight/${type}`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [type]);

  const style = TYPE_STYLES[type] || { color: "#71717a", icon: "?" };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-dim text-sm">{data?.error || "Not found"}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <header className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-base font-bold tracking-widest uppercase flex items-center gap-2">
            <span>{style.icon}</span>
            <span style={{ color: style.color }}>{data.title}</span>
          </h1>
          <p className="text-xs text-dim mt-1">{data.total} items</p>
        </div>
      </header>

      {data.description && (
        <div className="px-6 py-3 border-b border-border">
          <p className="text-sm text-dim leading-relaxed max-w-3xl">
            {data.description}
          </p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-4xl mx-auto">
          {type === "lost_canary" && <LostCanaryTable data={data.data} />}
          {type === "pattern_distribution" && (
            <PatternTable data={data.data} />
          )}
          {(type === "grounding_gaps" || type === "cross_era_bridges") && (
            <PaperListTable data={data.data} />
          )}
          {type === "rosetta_entries" && <RosettaTable data={data.data} />}
        </div>
      </div>
    </div>
  );
}
