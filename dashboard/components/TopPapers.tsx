"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface PaperRow {
  id: number;
  title: string;
  year: number | null;
  cites: number | null;
  status: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  analyzed: "#34d399",
  enriched: "#34d399",
  seed: "#60a5fa",
  scouted: "#60a5fa",
  collected: "#60a5fa",
  relevant: "#a78bfa",
  reproduction_planned: "#a78bfa",
  planning_repro: "#a78bfa",
  marginal: "#fbbf24",
  archived: "#f87171",
};

function statusColor(status: string | null): string {
  if (!status) return "#71717a";
  return STATUS_COLORS[status] || "#71717a";
}

export function TopPapers() {
  const [modern, setModern] = useState<PaperRow[]>([]);
  const [classical, setClassical] = useState<PaperRow[]>([]);

  const refresh = useCallback(() => {
    fetch("/api/top-papers")
      .then((r) => r.json())
      .then((d) => {
        setModern(d.modern || []);
        setClassical(d.classical || []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 30_000);
    return () => clearInterval(iv);
  }, [refresh]);

  return (
    <div className="grid grid-cols-2 gap-4">
      <PaperTable title="Top Modern Papers (2023+)" rows={modern} />
      <PaperTable title="Top Classical Papers" rows={classical} />
    </div>
  );
}

function PaperTable({ title, rows }: { title: string; rows: PaperRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="border border-border rounded-lg p-4 h-64 flex items-center justify-center text-dim text-xs">
        Loading...
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg p-4">
      <h3 className="text-xs font-bold uppercase tracking-widest text-accent mb-3 pb-2 border-b border-border">
        {title}
      </h3>
      <div className="overflow-y-auto max-h-[400px]">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] text-dim uppercase tracking-wider">
              <th className="text-left pb-2 font-medium">Title</th>
              <th className="text-right pb-2 font-medium w-14">Year</th>
              <th className="text-right pb-2 font-medium w-16">Cites</th>
              <th className="text-right pb-2 font-medium w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                className="border-t border-border/50 hover:bg-zinc-900/50 transition"
              >
                <td className="py-1.5 pr-3 text-text truncate max-w-0">
                  <Link
                    href={`/paper/${row.id}`}
                    className="block truncate hover:text-accent transition"
                  >
                    {row.title}
                  </Link>
                </td>
                <td className="py-1.5 text-right text-dim tabular-nums">
                  {row.year || "?"}
                </td>
                <td className="py-1.5 text-right text-text tabular-nums font-medium">
                  {(row.cites || 0).toLocaleString()}
                </td>
                <td className="py-1.5 text-right">
                  <span
                    className="inline-block text-[10px] px-2 py-0.5 rounded-full font-medium"
                    style={{
                      color: statusColor(row.status),
                      backgroundColor: `${statusColor(row.status)}15`,
                      border: `1px solid ${statusColor(row.status)}30`,
                    }}
                  >
                    {row.status || "unknown"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
