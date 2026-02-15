"use client";

import { useEffect, useState, useCallback, useRef } from "react";

interface Station {
  id: string;
  name: string;
  color: string;
  desc: string;
  input: number;
  active: number;
  done: number;
  total: number;
}

interface PipelineData {
  stations: Station[];
  total: number;
}

function stationStatus(s: Station) {
  if (s.active > 0) return "RUNNING";
  if (s.done > 0 && s.input === 0) return "DONE";
  if (s.input > 0) return "WAITING";
  return "IDLE";
}

export function PipelineStatus() {
  const [data, setData] = useState<PipelineData | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(() => {
    fetch("/api/pipeline")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, 2500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [refresh]);

  if (!data) {
    return (
      <div className="text-dim text-xs py-2 text-center">
        Loading pipeline...
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {data.stations.map((s, i) => {
        const pctDone = s.total > 0 ? (s.done / s.total) * 100 : 0;
        const pctActive = s.total > 0 ? (s.active / s.total) * 100 : 0;
        const status = stationStatus(s);
        const statusColor =
          status === "RUNNING"
            ? s.color
            : status === "DONE"
              ? "#71717a"
              : status === "WAITING"
                ? "#fbbf24"
                : "#27272a";

        return (
          <div key={s.id}>
            <div
              className="grid items-center gap-x-3 py-1"
              style={{ gridTemplateColumns: "80px 1fr auto auto auto" }}
            >
              {/* Agent ID + name */}
              <div>
                <div className="text-sm font-bold" style={{ color: s.color }}>
                  {s.id}
                </div>
                <div className="text-xs text-dim">{s.name}</div>
              </div>

              {/* Progress bar */}
              <div>
                <div className="relative h-6 rounded bg-zinc-900 overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 rounded-l transition-[width] duration-[2s] ease-linear"
                    style={{
                      width: `${pctDone}%`,
                      background: s.color,
                      opacity: 0.7,
                    }}
                  />
                  {s.active > 0 && (
                    <div
                      className="absolute inset-y-0 animate-pulse rounded-r"
                      style={{
                        left: `${pctDone}%`,
                        width: `${Math.max(pctActive, 2)}%`,
                        background: s.color,
                      }}
                    />
                  )}
                  <span className="absolute inset-0 flex items-center px-2 text-xs font-mono text-white drop-shadow-sm">
                    {s.total > 0
                      ? `${s.done.toLocaleString()}/${s.total.toLocaleString()}`
                      : ""}
                  </span>
                </div>
                <div className="text-[10px] text-dim mt-0.5">{s.desc}</div>
              </div>

              {/* Input queue */}
              <div className="text-right text-xs font-mono tabular-nums w-16">
                {s.input > 0 && (
                  <span className="text-amber-400">
                    {s.input.toLocaleString()} in
                  </span>
                )}
              </div>

              {/* Active now */}
              <div className="text-right text-xs font-mono tabular-nums w-16">
                {s.active > 0 && (
                  <span style={{ color: s.color }}>{s.active} now</span>
                )}
              </div>

              {/* Status pill */}
              <div className="w-18 text-right">
                <span
                  className="text-[10px] font-mono px-2 py-0.5 rounded"
                  style={{
                    background: statusColor + "22",
                    color: statusColor,
                  }}
                >
                  {status}
                </span>
              </div>
            </div>
            {i < data.stations.length - 1 && (
              <div className="text-center text-zinc-700 text-[8px] leading-none">
                &#9660;
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
