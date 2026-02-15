"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import Link from "next/link";

interface GraphNode {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  is_classical: boolean;
  pattern: string | null;
  cluster_id: number | null;
  cluster_label: string | null;
  has_code: boolean;
  depth: number;
  // D3 computed
  x?: number;
  y?: number;
}

interface GraphEdge {
  source: number;
  target: number;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  center_id?: number;
  stats: { nodes: number; edges: number; max_depth: number };
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

// Assign swim lanes by coordination pattern
const PATTERN_LANES: Record<string, number> = {
  peer: 0,
  blackboard: 1,
  contract_net: 2,
  auction: 3,
  hierarchical: 4,
  supervisor: 5,
  debate: 6,
  bdi: 7,
  stigmergy: 8,
  generator_critic: 9,
  hybrid: 10,
};

function nodeRadius(citations: number): number {
  return Math.max(4, Math.min(18, Math.log(Math.max(citations, 1) + 1) * 2));
}

function nodeColor(node: GraphNode): string {
  if (node.pattern && PATTERN_COLORS[node.pattern]) {
    return PATTERN_COLORS[node.pattern];
  }
  return node.is_classical ? "#fbbf24" : "#34d399";
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "\u2026" : s;
}

export function LineageGraph({
  paperId,
  clusterId,
  depth = 2,
}: {
  paperId?: number;
  clusterId?: number;
  depth?: number;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Fetch data
  useEffect(() => {
    const params = new URLSearchParams();
    if (paperId) params.set("paper_id", String(paperId));
    if (clusterId) params.set("cluster_id", String(clusterId));
    params.set("depth", String(depth));
    params.set("limit", "300");

    fetch(`/api/citation-graph?${params}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [paperId, clusterId, depth]);

  // Render graph
  const renderGraph = useCallback(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const rect = containerRef.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    svg.attr("width", width).attr("height", height);

    // Compute layout: X = year, Y = pattern swim lane
    const years = data.nodes.map((n) => n.year || 2020).filter(Boolean);
    const minYear = Math.min(...years, 1980);
    const maxYear = Math.max(...years, 2026);

    const xScale = d3
      .scaleLinear()
      .domain([minYear - 2, maxYear + 2])
      .range([80, width - 80]);

    // Collect unique patterns for Y lanes
    const patterns = Array.from(
      new Set(data.nodes.map((n) => n.pattern || "other").filter(Boolean))
    ).sort((a, b) => (PATTERN_LANES[a] ?? 99) - (PATTERN_LANES[b] ?? 99));

    const laneHeight = Math.max(40, (height - 80) / Math.max(patterns.length, 1));

    const yScale = (pattern: string | null): number => {
      const idx = patterns.indexOf(pattern || "other");
      return 50 + (idx >= 0 ? idx : patterns.length) * laneHeight + laneHeight / 2;
    };

    // Position nodes
    // To avoid overlap at same year+lane, jitter Y within the lane
    const laneOccupancy = new Map<string, number>();
    for (const node of data.nodes) {
      const lane = node.pattern || "other";
      const yearKey = `${lane}-${node.year}`;
      const count = laneOccupancy.get(yearKey) || 0;
      laneOccupancy.set(yearKey, count + 1);

      node.x = xScale(node.year || 2020);
      const baseY = yScale(lane);
      // Jitter: spread within ±laneHeight/3
      node.y = baseY + (count % 5 - 2) * (laneHeight / 6);
    }

    // Create zoom group
    const g = svg.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });

    svg.call(zoom);

    // Draw swim lane backgrounds
    patterns.forEach((pattern, i) => {
      const y = 50 + i * laneHeight;
      g.append("rect")
        .attr("x", 0)
        .attr("y", y)
        .attr("width", width * 3)
        .attr("height", laneHeight)
        .attr("fill", i % 2 === 0 ? "rgba(255,255,255,0.01)" : "rgba(255,255,255,0.02)")
        .attr("rx", 2);

      g.append("text")
        .attr("x", 8)
        .attr("y", y + laneHeight / 2)
        .attr("dy", "0.35em")
        .attr("fill", PATTERN_COLORS[pattern] || "#71717a")
        .attr("font-size", "10px")
        .attr("font-family", "var(--font-mono)")
        .attr("opacity", 0.6)
        .text(pattern);
    });

    // Draw year grid lines
    const yearTicks = d3.range(
      Math.ceil(minYear / 5) * 5,
      maxYear + 1,
      5
    );
    for (const yr of yearTicks) {
      const x = xScale(yr);
      g.append("line")
        .attr("x1", x)
        .attr("y1", 30)
        .attr("x2", x)
        .attr("y2", 50 + patterns.length * laneHeight)
        .attr("stroke", "#1e1e2e")
        .attr("stroke-width", 1);

      g.append("text")
        .attr("x", x)
        .attr("y", 24)
        .attr("text-anchor", "middle")
        .attr("fill", "#71717a")
        .attr("font-size", "9px")
        .attr("font-family", "var(--font-mono)")
        .text(String(yr));
    }

    // Build edge lookup for highlighting
    const nodeById = new Map(data.nodes.map((n) => [n.id, n]));

    // Draw edges
    const edgeGroup = g.append("g").attr("class", "edges");

    for (const edge of data.edges) {
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (!source?.x || !target?.x || !source.y || !target.y) continue;

      // Curved arrow from source to target
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dr = Math.sqrt(dx * dx + dy * dy) * 0.6;

      edgeGroup
        .append("path")
        .attr(
          "d",
          `M${source.x},${source.y} A${dr},${dr} 0 0,1 ${target.x},${target.y}`
        )
        .attr("fill", "none")
        .attr("stroke", "#1e1e2e")
        .attr("stroke-width", 0.8)
        .attr("opacity", 0.5)
        .attr("data-source", edge.source)
        .attr("data-target", edge.target)
        .attr("marker-end", "url(#arrowhead)");
    }

    // Arrow marker
    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -3 6 6")
      .attr("refX", 8)
      .attr("refY", 0)
      .attr("markerWidth", 4)
      .attr("markerHeight", 4)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-3L6,0L0,3")
      .attr("fill", "#3a3a4e");

    // Highlighted arrow
    svg
      .select("defs")
      .append("marker")
      .attr("id", "arrowhead-active")
      .attr("viewBox", "0 -3 6 6")
      .attr("refX", 8)
      .attr("refY", 0)
      .attr("markerWidth", 5)
      .attr("markerHeight", 5)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-3L6,0L0,3")
      .attr("fill", "#34d399");

    // Draw nodes
    const nodeGroup = g.append("g").attr("class", "nodes");

    for (const node of data.nodes) {
      if (node.x == null || node.y == null) continue;

      const ng = nodeGroup
        .append("g")
        .attr("transform", `translate(${node.x},${node.y})`)
        .attr("cursor", "pointer")
        .attr("data-id", node.id);

      const r = nodeRadius(node.citations);
      const color = nodeColor(node);
      const isCenter = node.id === data.center_id;

      // Code availability glow
      if (node.has_code) {
        ng.append("circle")
          .attr("r", r + 3)
          .attr("fill", "none")
          .attr("stroke", "#22d3ee")
          .attr("stroke-width", 1.5)
          .attr("opacity", 0.4);
      }

      // Classical ring
      if (node.is_classical) {
        ng.append("circle")
          .attr("r", r + 1.5)
          .attr("fill", "none")
          .attr("stroke", "#fbbf24")
          .attr("stroke-width", 1.5)
          .attr("opacity", 0.5);
      }

      // Center highlight
      if (isCenter) {
        ng.append("circle")
          .attr("r", r + 5)
          .attr("fill", "none")
          .attr("stroke", "#34d399")
          .attr("stroke-width", 2)
          .attr("stroke-dasharray", "3,2");
      }

      // Main circle
      ng.append("circle")
        .attr("r", r)
        .attr("fill", color)
        .attr("opacity", 0.8);

      // Hover handlers
      ng.on("mouseenter", function () {
        setHoveredNode(node);
        // Highlight connected edges
        edgeGroup
          .selectAll("path")
          .attr("opacity", 0.08)
          .attr("stroke-width", 0.5);
        edgeGroup
          .selectAll(
            `path[data-source="${node.id}"], path[data-target="${node.id}"]`
          )
          .attr("stroke", "#34d399")
          .attr("stroke-width", 1.5)
          .attr("opacity", 0.9)
          .attr("marker-end", "url(#arrowhead-active)");
        // Dim other nodes
        nodeGroup.selectAll("g").attr("opacity", 0.2);
        d3.select(this).attr("opacity", 1);
        // Highlight connected nodes
        for (const e of data.edges) {
          if (e.source === node.id || e.target === node.id) {
            const otherId = e.source === node.id ? e.target : e.source;
            nodeGroup.select(`g[data-id="${otherId}"]`).attr("opacity", 1);
          }
        }
      });

      ng.on("mouseleave", function () {
        setHoveredNode(null);
        edgeGroup
          .selectAll("path")
          .attr("stroke", "#1e1e2e")
          .attr("stroke-width", 0.8)
          .attr("opacity", 0.5)
          .attr("marker-end", "url(#arrowhead)");
        nodeGroup.selectAll("g").attr("opacity", 1);
      });

      ng.on("click", function () {
        setSelectedNode(node.id === selectedNode?.id ? null : node);
      });
    }

    // If we have a center, zoom to fit
    if (data.center_id && data.nodes.length > 0) {
      const centerNode = nodeById.get(data.center_id);
      if (centerNode?.x && centerNode.y) {
        const initialTransform = d3.zoomIdentity
          .translate(width / 2 - centerNode.x, height / 2 - centerNode.y);
        svg.call(zoom.transform, initialTransform);
      }
    }
  }, [data, selectedNode]);

  useEffect(() => {
    renderGraph();
    const handleResize = () => renderGraph();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [renderGraph]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-dim text-sm">{error}</p>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-dim text-sm">No citation edges found.</p>
          <p className="text-dim/60 text-xs mt-1">
            Run the materialization script to build the citation graph.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full" ref={containerRef}>
      <svg ref={svgRef} className="w-full h-full" />

      {/* Stats bar */}
      <div className="absolute top-2 right-2 flex items-center gap-3 text-[10px] text-dim bg-card/90 border border-border rounded px-3 py-1.5">
        <span>{data.stats.nodes} papers</span>
        <span>{data.stats.edges} citations</span>
        {data.center_id && <span>depth {data.stats.max_depth}</span>}
      </div>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 flex flex-wrap gap-2 text-[10px] bg-card/90 border border-border rounded px-3 py-2">
        <span className="text-dim mr-1">Pattern:</span>
        {Object.entries(PATTERN_COLORS)
          .slice(0, 6)
          .map(([p, c]) => (
            <span key={p} className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ background: c }}
              />
              <span style={{ color: c }}>{p}</span>
            </span>
          ))}
        <span className="flex items-center gap-1 ml-2">
          <span className="w-2 h-2 rounded-full inline-block border border-amber-400" />
          <span className="text-amber-400">classical</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full inline-block border border-cyan-400" />
          <span className="text-cyan-400">has code</span>
        </span>
      </div>

      {/* Hover tooltip */}
      {hoveredNode && (
        <div className="absolute top-2 left-2 max-w-sm bg-card border border-border rounded-lg p-3 pointer-events-none z-10">
          <p className="text-xs text-text font-medium leading-snug">
            {truncate(hoveredNode.title, 80)}
          </p>
          <div className="flex items-center gap-2 mt-1.5 text-[10px] text-dim">
            <span>{hoveredNode.year || "?"}</span>
            <span>{hoveredNode.citations.toLocaleString()} cites</span>
            {hoveredNode.pattern && (
              <span style={{ color: PATTERN_COLORS[hoveredNode.pattern] || "#71717a" }}>
                {hoveredNode.pattern}
              </span>
            )}
            {hoveredNode.is_classical && (
              <span className="text-amber-400">classical</span>
            )}
            {hoveredNode.cluster_label && (
              <span className="text-dim/60">{hoveredNode.cluster_label}</span>
            )}
          </div>
        </div>
      )}

      {/* Selected node panel */}
      {selectedNode && (
        <div className="absolute top-12 right-2 w-72 bg-card border border-border rounded-lg p-4 z-10">
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="text-xs text-text font-medium leading-snug flex-1">
              {selectedNode.title}
            </p>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-dim hover:text-text text-xs shrink-0"
            >
              &times;
            </button>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-dim mb-3">
            <span>{selectedNode.year || "?"}</span>
            <span>{selectedNode.citations.toLocaleString()} cites</span>
            {selectedNode.pattern && (
              <span style={{ color: PATTERN_COLORS[selectedNode.pattern] }}>
                {selectedNode.pattern}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Link
              href={`/paper/${selectedNode.id}`}
              className="text-[10px] px-2 py-1 rounded border border-accent/30 text-accent hover:text-text transition"
            >
              View paper
            </Link>
            <Link
              href={`/lineage?paper_id=${selectedNode.id}&depth=2`}
              className="text-[10px] px-2 py-1 rounded border border-border text-dim hover:text-text transition"
            >
              Center here
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
