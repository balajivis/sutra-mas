"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface GraphNode {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  cluster_id: number | null;
  cluster_label: string | null;
  x: number | null;
  y: number | null;
  role: "center" | "reference" | "citedBy" | "externalRef" | "externalCitedBy";
}

interface GraphEdge {
  source: number;
  target: number;
  direction: "refs" | "citedBy";
}

interface CitationData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  totalRefs: number;
  resolvedRefs: number;
  totalCitedBy: number;
  resolvedCitedBy: number;
}

// Simple force-directed layout positions
interface LayoutNode extends GraphNode {
  lx: number;
  ly: number;
  vx: number;
  vy: number;
}

const COLORS: Record<string, string> = {
  center: "#34d399",
  reference: "#60a5fa",
  citedBy: "#fbbf24",
  externalRef: "#3b82f6",
  externalCitedBy: "#d97706",
  edge: "#ffffff",
};

function layoutForce(nodes: LayoutNode[], edges: GraphEdge[], width: number, height: number) {
  // Initialize positions in a circle around center
  const center = nodes.find((n) => n.role === "center");
  if (center) {
    center.lx = width / 2;
    center.ly = height / 2;
  }
  const others = nodes.filter((n) => n.role !== "center");
  others.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / others.length;
    const r = Math.min(width, height) * 0.35;
    n.lx = width / 2 + Math.cos(angle) * r;
    n.ly = height / 2 + Math.sin(angle) * r;
  });

  // Run simple force simulation (50 iterations)
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  for (let iter = 0; iter < 60; iter++) {
    const alpha = 0.3 * (1 - iter / 60);

    // Repulsion between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = b.lx - a.lx, dy = b.ly - a.ly;
        const dist = Math.max(Math.hypot(dx, dy), 1);
        const force = 2000 / (dist * dist);
        dx = (dx / dist) * force * alpha;
        dy = (dy / dist) * force * alpha;
        a.lx -= dx; a.ly -= dy;
        b.lx += dx; b.ly += dy;
      }
    }

    // Attraction along edges
    for (const e of edges) {
      const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
      if (!a || !b) continue;
      let dx = b.lx - a.lx, dy = b.ly - a.ly;
      const dist = Math.max(Math.hypot(dx, dy), 1);
      const idealDist = 120;
      const force = (dist - idealDist) * 0.01 * alpha;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      a.lx += dx; a.ly += dy;
      b.lx -= dx; b.ly -= dy;
    }

    // Center gravity
    for (const n of nodes) {
      n.lx += (width / 2 - n.lx) * 0.01 * alpha;
      n.ly += (height / 2 - n.ly) * 0.01 * alpha;
    }

    // Keep center node fixed
    if (center) {
      center.lx = width / 2;
      center.ly = height / 2;
    }
  }

  // Clamp to bounds
  const margin = 30;
  for (const n of nodes) {
    n.lx = Math.max(margin, Math.min(width - margin, n.lx));
    n.ly = Math.max(margin, Math.min(height - margin, n.ly));
  }
}

export function CitationGraph({ paperId }: { paperId: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<CitationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hovered, setHovered] = useState<GraphNode | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number } | null>(null);
  const layoutRef = useRef<LayoutNode[]>([]);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/paper/${paperId}/citations`)
      .then((r) => r.json())
      .then((d) => {
        if (!d.error) setData(d);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [paperId]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width, h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a0a0f";
    ctx.fillRect(0, 0, w, h);

    const nodes = layoutRef.current;
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    // Draw edges
    for (const e of data.edges) {
      const a = nodeMap.get(e.source), b = nodeMap.get(e.target);
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.lx, a.ly);
      ctx.lineTo(b.lx, b.ly);
      ctx.strokeStyle = e.direction === "refs" ? "rgba(96,165,250,0.15)" : "rgba(251,191,36,0.15)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Arrow
      const angle = Math.atan2(b.ly - a.ly, b.lx - a.lx);
      const r = e.direction === "refs"
        ? Math.max(4, Math.min(10, Math.log(Math.max((b as GraphNode).citations, 1) + 1) * 1.5)) + 4
        : Math.max(4, Math.min(10, Math.log(Math.max((b as GraphNode).citations, 1) + 1) * 1.5)) + 4;
      const ax = b.lx - Math.cos(angle) * r;
      const ay = b.ly - Math.sin(angle) * r;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(ax - Math.cos(angle - 0.4) * 6, ay - Math.sin(angle - 0.4) * 6);
      ctx.lineTo(ax - Math.cos(angle + 0.4) * 6, ay - Math.sin(angle + 0.4) * 6);
      ctx.closePath();
      ctx.fillStyle = e.direction === "refs" ? "rgba(96,165,250,0.3)" : "rgba(251,191,36,0.3)";
      ctx.fill();
    }

    // Draw nodes
    for (const n of nodes) {
      const isExternal = n.role === "externalRef" || n.role === "externalCitedBy";
      const r = n.role === "center"
        ? 12
        : isExternal
          ? Math.max(3, Math.min(7, Math.log(Math.max(n.citations, 1) + 1) * 1.2))
          : Math.max(4, Math.min(10, Math.log(Math.max(n.citations, 1) + 1) * 1.5));
      const color = COLORS[n.role] || "#888";
      const isHovered = hovered?.id === n.id;

      ctx.beginPath();
      ctx.arc(n.lx, n.ly, r, 0, Math.PI * 2);

      if (isExternal) {
        // External nodes: hollow with dashed outline
        ctx.fillStyle = color + (isHovered ? "40" : "20");
        ctx.fill();
        ctx.setLineDash([2, 2]);
        ctx.strokeStyle = color + (isHovered ? "cc" : "66");
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.setLineDash([]);
      } else {
        ctx.fillStyle = color + (isHovered ? "ff" : "cc");
        ctx.fill();
        if (isHovered || n.role === "center") {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = n.role === "center" ? 2 : 1.5;
          ctx.stroke();
        }
      }
    }

    // Tooltip
    if (hovered && tooltip) {
      const text = `${hovered.title?.slice(0, 55) || "?"} (${hovered.year || "?"}) ${hovered.citations} cites`;
      ctx.font = "11px monospace";
      const tw = ctx.measureText(text).width;
      const tx = Math.min(tooltip.x + 12, w - tw - 16);
      const ty = Math.max(tooltip.y - 18, 16);
      ctx.fillStyle = "rgba(18,18,26,0.95)";
      ctx.beginPath();
      ctx.roundRect(tx - 6, ty - 13, tw + 12, 20, 4);
      ctx.fill();
      ctx.strokeStyle = "rgba(60,60,80,1)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#d4d4d8";
      ctx.fillText(text, tx, ty);
    }
  }, [data, hovered, tooltip]);

  // Layout + resize
  useEffect(() => {
    if (!data || data.nodes.length === 0) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;

      const layoutNodes: LayoutNode[] = data.nodes.map((n) => ({
        ...n,
        lx: 0, ly: 0, vx: 0, vy: 0,
      }));
      layoutForce(layoutNodes, data.edges, canvas.width, canvas.height);
      layoutRef.current = layoutNodes;
      render();
    };

    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [data, render]);

  useEffect(() => { render(); }, [render]);

  const findNode = useCallback((mx: number, my: number): GraphNode | null => {
    for (const n of layoutRef.current) {
      const r = n.role === "center" ? 12 : Math.max(4, Math.min(10, Math.log(Math.max(n.citations, 1) + 1) * 1.5));
      if (Math.hypot(mx - n.lx, my - n.ly) < r + 4) return n;
    }
    return null;
  }, []);

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const node = findNode(mx, my);
    setHovered(node);
    setTooltip(node ? { x: mx, y: my } : null);
    if (canvasRef.current) {
      canvasRef.current.style.cursor = node && node.id > 0 && node.role !== "center" ? "pointer" : "default";
    }
  }, [findNode]);

  const [clickedNode, setClickedNode] = useState<number | null>(null);
  const onClick = useCallback((e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const node = findNode(e.clientX - rect.left, e.clientY - rect.top);
    // Only navigate for internal nodes (positive IDs, not center)
    if (node && node.role !== "center" && node.id > 0) {
      setClickedNode(node.id);
    }
  }, [findNode]);

  // Navigate on click
  useEffect(() => {
    if (clickedNode !== null) {
      window.location.href = `/paper/${clickedNode}`;
    }
  }, [clickedNode]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-dim text-xs">
        <span className="animate-pulse">Loading citation network...</span>
      </div>
    );
  }

  if (!data || data.nodes.length <= 1) {
    return (
      <div className="flex items-center justify-center h-full text-dim text-xs">
        No citation data available for this paper.
      </div>
    );
  }

  const internalRefNodes = data.nodes.filter((n) => n.role === "reference");
  const externalRefNodes = data.nodes.filter((n) => n.role === "externalRef");
  const internalCbNodes = data.nodes.filter((n) => n.role === "citedBy");
  const externalCbNodes = data.nodes.filter((n) => n.role === "externalCitedBy");
  const allRefNodes = [...internalRefNodes, ...externalRefNodes];
  const allCbNodes = [...internalCbNodes, ...externalCbNodes];

  return (
    <div className="flex flex-col h-full">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 border-b border-border text-[10px]">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
          <span className="text-zinc-400">This paper</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
          <span className="text-zinc-400">
            References ({internalRefNodes.length} in corpus{externalRefNodes.length > 0 ? `, ${externalRefNodes.length} external` : ""} / {data.totalRefs} total)
          </span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
          <span className="text-zinc-400">
            Cited by ({internalCbNodes.length} in corpus{externalCbNodes.length > 0 ? `, ${externalCbNodes.length} external` : ""} / {data.totalCitedBy} total)
          </span>
        </span>
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="flex-1 relative min-h-0">
        <canvas
          ref={canvasRef}
          onMouseMove={onMouseMove}
          onClick={onClick}
          onMouseLeave={() => { setHovered(null); setTooltip(null); }}
        />
      </div>

      {/* Node list */}
      <div className="max-h-40 overflow-y-auto border-t border-border px-3 py-2 space-y-1">
        {allRefNodes.slice(0, 10).map((n) => {
          const isExternal = n.id < 0;
          const inner = (
            <span className="flex items-center gap-2 w-full">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isExternal ? "bg-blue-400/40 ring-1 ring-blue-400/40" : "bg-blue-400"}`} />
              <span className={`truncate ${isExternal ? "text-zinc-500" : "text-zinc-300"}`}>{n.title}</span>
              <span className="text-zinc-600 shrink-0 tabular-nums">{n.year || "?"}</span>
              <span className="text-zinc-600 shrink-0 tabular-nums">{n.citations} cites</span>
            </span>
          );
          return isExternal ? (
            <div key={n.id} className="flex items-center gap-2 text-[11px]">{inner}</div>
          ) : (
            <Link key={n.id} href={`/paper/${n.id}`} className="flex items-center gap-2 text-[11px] hover:text-accent transition">
              {inner}
            </Link>
          );
        })}
        {allCbNodes.slice(0, 10).map((n) => {
          const isExternal = n.id < 0;
          const inner = (
            <span className="flex items-center gap-2 w-full">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isExternal ? "bg-amber-400/40 ring-1 ring-amber-400/40" : "bg-amber-400"}`} />
              <span className={`truncate ${isExternal ? "text-zinc-500" : "text-zinc-300"}`}>{n.title}</span>
              <span className="text-zinc-600 shrink-0 tabular-nums">{n.year || "?"}</span>
              <span className="text-zinc-600 shrink-0 tabular-nums">{n.citations} cites</span>
            </span>
          );
          return isExternal ? (
            <div key={n.id} className="flex items-center gap-2 text-[11px]">{inner}</div>
          ) : (
            <Link key={n.id} href={`/paper/${n.id}`} className="flex items-center gap-2 text-[11px] hover:text-accent transition">
              {inner}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
