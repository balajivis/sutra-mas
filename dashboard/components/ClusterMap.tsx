"use client";

import { useRef, useEffect, useCallback, useState, useMemo } from "react";
import type { ClusterPoint, ClusterMeta } from "@/lib/types";

// 10 maximally distinct colors for dark backgrounds (high chroma, spread hues)
const COLORS = [
  "#ff3333", // 0 red
  "#3399ff", // 1 blue
  "#ffdd00", // 2 yellow
  "#cc44ff", // 3 purple
  "#00e676", // 4 green
  "#ff8800", // 5 orange
  "#00e5ff", // 6 cyan
  "#ff4da6", // 7 pink
  "#b2ff59", // 8 lime
  "#ffab40", // 9 amber
  "#448aff", // extra
  "#ea80fc", // extra
  "#64ffda", // extra
  "#ff6e40", // extra
  "#8c9eff", // extra
  "#ccff90", // extra
];

function LegendStrip({ clusters, selectedCluster, onSelectCluster }: {
  clusters: ClusterMeta[];
  selectedCluster: number | null;
  onSelectCluster: (id: number | null) => void;
}) {
  return (
    <div className="flex items-center gap-x-3 gap-y-0.5 flex-wrap px-2 py-1 text-[10px] border-b border-border bg-[#0a0a0f]">
      {clusters
        .sort((a, b) => b.paper_count - a.paper_count)
        .map((cl) => (
          <span
            key={cl.cluster_id}
            className="flex items-center gap-1 cursor-pointer hover:opacity-100 whitespace-nowrap"
            style={{
              opacity: selectedCluster !== null && selectedCluster !== cl.cluster_id ? 0.35 : 1,
            }}
            onClick={() =>
              onSelectCluster(selectedCluster === cl.cluster_id ? null : cl.cluster_id)
            }
          >
            <span
              className="inline-block w-2 h-2 rounded-full shrink-0"
              style={{ background: COLORS[cl.cluster_id % COLORS.length] }}
            />
            <span>{cl.label || `C${cl.cluster_id}`}</span>
            <span className="text-dim">{cl.paper_count}</span>
          </span>
        ))}
      {selectedCluster !== null && (
        <span
          className="text-dim hover:text-text cursor-pointer ml-auto"
          onClick={() => onSelectCluster(null)}
        >
          clear
        </span>
      )}
    </div>
  );
}

interface Props {
  points: ClusterPoint[];
  clusters: ClusterMeta[];
  selectedCluster: number | null;
  onSelectCluster: (id: number | null) => void;
}

function YearSlider({
  min,
  max,
  value,
  onChange,
  filteredCount,
  totalCount,
}: {
  min: number;
  max: number;
  value: [number, number];
  onChange: (range: [number, number]) => void;
  filteredCount: number;
  totalCount: number;
}) {
  return (
    <div className="flex items-center gap-3 px-3 py-1.5 border-t border-border bg-[#0a0a0f] text-[10px]">
      <span className="text-zinc-500 shrink-0">Year</span>
      <span className="text-zinc-300 tabular-nums w-8 text-right">{value[0]}</span>
      <div className="flex-1 flex items-center gap-1 relative">
        <input
          type="range"
          min={min}
          max={max}
          value={value[0]}
          onChange={(e) => {
            const v = parseInt(e.target.value);
            onChange([Math.min(v, value[1]), value[1]]);
          }}
          className="absolute inset-0 w-full appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:relative [&::-webkit-slider-thumb]:z-10"
        />
        <input
          type="range"
          min={min}
          max={max}
          value={value[1]}
          onChange={(e) => {
            const v = parseInt(e.target.value);
            onChange([value[0], Math.max(v, value[0])]);
          }}
          className="absolute inset-0 w-full appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:relative [&::-webkit-slider-thumb]:z-10"
        />
        <div className="w-full h-1 bg-zinc-800 rounded-full">
          <div
            className="h-full bg-accent/40 rounded-full"
            style={{
              marginLeft: `${((value[0] - min) / (max - min)) * 100}%`,
              width: `${((value[1] - value[0]) / (max - min)) * 100}%`,
            }}
          />
        </div>
      </div>
      <span className="text-zinc-300 tabular-nums w-8">{value[1]}</span>
      <span className="text-zinc-600 tabular-nums shrink-0">
        {filteredCount === totalCount ? "" : `${filteredCount}/`}{totalCount}
      </span>
    </div>
  );
}

export function ClusterMap({ points, clusters, selectedCluster, onSelectCluster }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  const dragRef = useRef({ dragging: false, lastX: 0, lastY: 0 });
  const [hovered, setHovered] = useState<ClusterPoint | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number } | null>(null);

  // Year range slider
  const yearBounds = useMemo(() => {
    const years = points.map((p) => p.year).filter((y): y is number => y != null && y > 0);
    if (years.length === 0) return { min: 1980, max: 2026 };
    return { min: Math.min(...years), max: Math.max(...years) };
  }, [points]);
  const [yearRange, setYearRange] = useState<[number, number]>([1980, 2026]);

  // Reset range when points change
  useEffect(() => {
    setYearRange([yearBounds.min, yearBounds.max]);
  }, [yearBounds]);

  const filteredPoints = useMemo(
    () => points.filter((p) => {
      if (p.year == null) return true; // show papers without year
      return p.year >= yearRange[0] && p.year <= yearRange[1];
    }),
    [points, yearRange],
  );

  const toScreen = useCallback((px: number, py: number) => {
    const t = transformRef.current;
    return { x: px * t.scale + t.x, y: py * t.scale + t.y };
  }, []);

  const fitToView = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || filteredPoints.length === 0) return;
    const xs = filteredPoints.map((p) => p.x);
    const ys = filteredPoints.map((p) => p.y);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    const xRange = xMax - xMin || 1;
    const yRange = yMax - yMin || 1;
    const w = canvas.width, h = canvas.height;
    const margin = 50;
    const scale = Math.min((w - 2 * margin) / xRange, (h - 2 * margin) / yRange);
    transformRef.current = {
      scale,
      x: margin - xMin * scale + (w - 2 * margin - xRange * scale) / 2,
      y: margin - yMin * scale + (h - 2 * margin - yRange * scale) / 2,
    };
  }, [filteredPoints]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width, h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a0a0f";
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = "rgba(30,30,46,0.5)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i < w; i += 60) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, h); ctx.stroke(); }
    for (let i = 0; i < h; i += 60) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(w, i); ctx.stroke(); }

    // Draw points
    for (const p of filteredPoints) {
      const { x, y } = toScreen(p.x, p.y);
      if (x < -20 || x > w + 20 || y < -20 || y > h + 20) continue;

      const r = Math.max(3, Math.min(14, Math.log(Math.max(p.citations, 1) + 1) * 1.8));
      const color = COLORS[p.cluster_id % COLORS.length];
      const dimmed = selectedCluster !== null && p.cluster_id !== selectedCluster;
      const alpha = dimmed ? 0.12 : p === hovered ? 1 : 0.75;

      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = color + Math.round(alpha * 255).toString(16).padStart(2, "0");
      ctx.fill();

      if (p.is_classical && !dimmed) {
        ctx.strokeStyle = "#fbbf24" + (dimmed ? "20" : "60");
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      if (p === hovered) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // Cluster labels — pill with dark bg + cluster-colored text
    if (clusters.length > 0) {
      ctx.font = "bold 11px monospace";
      ctx.textAlign = "center";
      for (const cl of clusters) {
        const clPoints = filteredPoints.filter((p) => p.cluster_id === cl.cluster_id);
        if (clPoints.length === 0) continue;
        // Position label above the topmost point of the cluster
        const cx = clPoints.reduce((s, p) => s + p.x, 0) / clPoints.length;
        const topY = Math.min(...clPoints.map((p) => p.y));
        const { x, y } = toScreen(cx, topY);
        const labelY = y - 16;
        const dimmed = selectedCluster !== null && cl.cluster_id !== selectedCluster;
        if (dimmed) continue; // hide labels for dimmed clusters
        const label = cl.label || `C${cl.cluster_id}`;
        const tw = ctx.measureText(label).width;
        // Dark background pill
        ctx.fillStyle = "rgba(10,10,15,0.85)";
        ctx.beginPath();
        ctx.roundRect(x - tw / 2 - 6, labelY - 10, tw + 12, 18, 4);
        ctx.fill();
        ctx.strokeStyle = COLORS[cl.cluster_id % COLORS.length] + "60";
        ctx.lineWidth = 1;
        ctx.stroke();
        // Colored text
        ctx.fillStyle = COLORS[cl.cluster_id % COLORS.length];
        ctx.fillText(label, x, labelY + 2);
      }
      ctx.textAlign = "start"; // reset
    }

    // Tooltip
    if (hovered && tooltip) {
      const text = `${hovered.title?.slice(0, 60) || "?"} (${hovered.year || "?"}) — ${hovered.citations} cites`;
      ctx.font = "11px monospace";
      const tw = ctx.measureText(text).width;
      const tx = Math.min(tooltip.x + 12, w - tw - 12);
      const ty = Math.max(tooltip.y - 18, 16);
      ctx.fillStyle = "rgba(18,18,26,0.95)";
      ctx.beginPath();
      ctx.roundRect(tx - 6, ty - 13, tw + 12, 20, 4);
      ctx.fill();
      ctx.strokeStyle = "rgba(30,30,46,1)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#d4d4d8";
      ctx.fillText(text, tx, ty);
    }
  }, [filteredPoints, clusters, selectedCluster, hovered, tooltip, toScreen]);

  // Resize
  useEffect(() => {
    const resize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      fitToView();
      render();
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [fitToView, render]);

  // Render on data/state change
  useEffect(() => { render(); }, [render]);

  // Mouse events
  const findPoint = useCallback(
    (mx: number, my: number): ClusterPoint | null => {
      const t = transformRef.current;
      let closest: ClusterPoint | null = null;
      let closestDist = 20;
      for (const p of filteredPoints) {
        const sx = p.x * t.scale + t.x;
        const sy = p.y * t.scale + t.y;
        const d = Math.hypot(mx - sx, my - sy);
        if (d < closestDist) { closest = p; closestDist = d; }
      }
      return closest;
    },
    [filteredPoints]
  );

  const onMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      if (dragRef.current.dragging) {
        const dx = mx - dragRef.current.lastX;
        const dy = my - dragRef.current.lastY;
        transformRef.current.x += dx;
        transformRef.current.y += dy;
        dragRef.current.lastX = mx;
        dragRef.current.lastY = my;
        render();
        return;
      }

      const pt = findPoint(mx, my);
      setHovered(pt);
      setTooltip(pt ? { x: mx, y: my } : null);
      if (canvasRef.current) {
        canvasRef.current.style.cursor = pt ? "pointer" : "grab";
      }
    },
    [findPoint, render]
  );

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    dragRef.current = { dragging: true, lastX: e.clientX - rect.left, lastY: e.clientY - rect.top };
  }, []);

  const onMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (!dragRef.current.dragging) return;
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const moved = Math.hypot(mx - dragRef.current.lastX, my - dragRef.current.lastY);
      dragRef.current.dragging = false;

      // If barely moved, treat as click
      if (moved < 3) {
        const pt = findPoint(mx, my);
        if (pt) {
          onSelectCluster(selectedCluster === pt.cluster_id ? null : pt.cluster_id);
        } else {
          onSelectCluster(null);
        }
      }
    },
    [findPoint, onSelectCluster, selectedCluster]
  );

  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const t = transformRef.current;
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      const newScale = Math.max(0.1, Math.min(50, t.scale * factor));
      t.x = mx - (mx - t.x) * (newScale / t.scale);
      t.y = my - (my - t.y) * (newScale / t.scale);
      t.scale = newScale;
      render();
    },
    [render]
  );

  if (points.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-dim text-sm border border-border rounded-lg bg-card">
        <div className="text-center">
          <div className="text-2xl mb-2">&#x1F30C;</div>
          <p>No cluster data yet</p>
          <p className="text-xs mt-1 text-zinc-600">
            Run clustering.py to generate the knowledge map
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col rounded-lg overflow-hidden border border-border">
      <LegendStrip
        clusters={clusters}
        selectedCluster={selectedCluster}
        onSelectCluster={onSelectCluster}
      />
      <div ref={containerRef} className="flex-1 relative">
        <canvas
          ref={canvasRef}
          onMouseMove={onMouseMove}
          onMouseDown={onMouseDown}
          onMouseUp={onMouseUp}
          onMouseLeave={() => {
            dragRef.current.dragging = false;
            setHovered(null);
            setTooltip(null);
          }}
          onWheel={onWheel}
        />
      </div>
      <YearSlider
        min={yearBounds.min}
        max={yearBounds.max}
        value={yearRange}
        onChange={setYearRange}
        filteredCount={filteredPoints.length}
        totalCount={points.length}
      />
    </div>
  );
}
