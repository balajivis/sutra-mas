"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface EraRow {
  label: string;
  count: number;
  pct: number;
}

interface CiteRow {
  label: string;
  count: number;
}

interface CorpusData {
  eras: EraRow[];
  citations: CiteRow[];
  citeMean: number;
  citeMedian: number;
  total: number;
}

export function CorpusCards() {
  const [data, setData] = useState<CorpusData | null>(null);

  const refresh = useCallback(() => {
    fetch("/api/corpus-stats")
      .then((r) => r.json())
      .then((d) => {
        if (d.eras && d.citations) setData(d);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 10_000);
    return () => clearInterval(iv);
  }, [refresh]);

  if (!data) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-border rounded-lg p-4 h-64 flex items-center justify-center text-dim text-xs">
          Loading...
        </div>
        <div className="border border-border rounded-lg p-4 h-64 flex items-center justify-center text-dim text-xs">
          Loading...
        </div>
      </div>
    );
  }

  const eraMax = Math.max(...data.eras.map((e) => e.count));
  const citeMax = Math.max(...data.citations.map((c) => c.count));

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Era Breakdown */}
      <div className="border border-border rounded-lg p-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-accent mb-3 pb-2 border-b border-border">
          Era Breakdown (Decades)
        </h3>
        <div className="space-y-2">
          {data.eras.map((row) => (
            <Link
              key={row.label}
              href={`/papers?era=${encodeURIComponent(row.label)}`}
              className="grid items-center gap-x-3 hover:bg-white/[0.03] rounded px-1 -mx-1 transition"
              style={{ gridTemplateColumns: "80px 60px 50px 1fr" }}
            >
              <span className="text-sm text-text">{row.label}</span>
              <span className="text-sm text-text text-right tabular-nums">
                {row.count.toLocaleString()}
              </span>
              <span className="text-sm text-dim text-right tabular-nums">
                {row.pct}%
              </span>
              <div className="h-4 bg-zinc-900 rounded overflow-hidden">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${(row.count / eraMax) * 100}%`,
                    background: "#a78bfa",
                    opacity: 0.8,
                  }}
                />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Citation Distribution */}
      <div className="border border-border rounded-lg p-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-accent mb-3 pb-2 border-b border-border">
          Citation Distribution
        </h3>
        <div className="space-y-2">
          {data.citations.map((row) => (
            <Link
              key={row.label}
              href={`/papers?citations=${encodeURIComponent(row.label)}`}
              className="grid items-center gap-x-3 hover:bg-white/[0.03] rounded px-1 -mx-1 transition"
              style={{ gridTemplateColumns: "80px 60px 1fr" }}
            >
              <span className="text-sm text-text">{row.label}</span>
              <span className="text-sm text-text text-right tabular-nums">
                {row.count.toLocaleString()}
              </span>
              <div className="h-4 bg-zinc-900 rounded overflow-hidden">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${(row.count / citeMax) * 100}%`,
                    background: "#fbbf24",
                    opacity: 0.8,
                  }}
                />
              </div>
            </Link>
          ))}
        </div>
        <p className="text-xs text-dim mt-3">
          Mean: {data.citeMean.toLocaleString()} &nbsp;&nbsp; Median:{" "}
          {data.citeMedian.toLocaleString()}
        </p>
      </div>
    </div>
  );
}
