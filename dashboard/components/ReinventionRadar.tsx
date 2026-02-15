"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import Link from "next/link";

interface ClassicalPaper {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  pattern: string | null;
  connections: Connection[];
}

interface Connection {
  modern_id: number;
  modern_title: string;
  modern_year: number | null;
  modern_citations: number;
  modern_pattern: string | null;
  overlap_concepts: string[];
  has_citation: boolean;
  overlap_score: number;
}

interface ModernPaper {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  pattern: string | null;
}

interface FilterOption {
  concept?: string;
  pattern?: string;
  count: number;
}

interface RadarData {
  classical: ClassicalPaper[];
  modern: ModernPaper[];
  stats: {
    total_pairs: number;
    reinventions: number;
    cited: number;
    classical_count: number;
    modern_count: number;
  };
  filters: {
    concepts: FilterOption[];
    patterns: FilterOption[];
  };
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

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "\u2026" : s;
}

export function ReinventionRadar({
  concept,
  pattern,
}: {
  concept?: string;
  pattern?: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<RadarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<{
    classical: ClassicalPaper;
    connection: Connection;
  } | null>(null);
  const [showCited, setShowCited] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState(concept || "");
  const [selectedPattern, setSelectedPattern] = useState(pattern || "");

  // Fetch data
  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (selectedConcept) params.set("concept", selectedConcept);
    if (selectedPattern) params.set("pattern", selectedPattern);
    if (showCited) params.set("show_cited", "true");
    params.set("limit", "300");

    fetch(`/api/reinvention-candidates?${params}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedConcept, selectedPattern, showCited]);

  // Render
  const renderRadar = useCallback(() => {
    if (!data || !svgRef.current || !containerRef.current) return;
    if (data.classical.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const rect = containerRef.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    svg.attr("width", width).attr("height", height);

    // Layout: classical on left (x=20%), modern on right (x=80%)
    const leftX = width * 0.18;
    const rightX = width * 0.82;
    const topPad = 50;
    const bottomPad = 20;
    const usableHeight = height - topPad - bottomPad;

    // Sort classical by year (oldest first), limit to top 40
    const classicalPapers = data.classical.slice(0, 40);
    const classicalSpacing = Math.max(20, usableHeight / Math.max(classicalPapers.length, 1));

    // Collect all unique modern paper IDs referenced
    const modernIds = new Set<number>();
    for (const cp of classicalPapers) {
      for (const conn of cp.connections) {
        modernIds.add(conn.modern_id);
      }
    }

    // Modern papers: sort by year
    const modernPapers = data.modern
      .filter((m) => modernIds.has(m.id))
      .sort((a, b) => (a.year || 2025) - (b.year || 2025))
      .slice(0, 60);

    const modernSpacing = Math.max(16, usableHeight / Math.max(modernPapers.length, 1));

    // Position maps
    const classicalY = new Map<number, number>();
    classicalPapers.forEach((cp, i) => {
      classicalY.set(cp.id, topPad + i * classicalSpacing + classicalSpacing / 2);
    });

    const modernY = new Map<number, number>();
    modernPapers.forEach((mp, i) => {
      modernY.set(mp.id, topPad + i * modernSpacing + modernSpacing / 2);
    });

    const g = svg.append("g");

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });
    svg.call(zoom);

    // Column headers
    g.append("text")
      .attr("x", leftX)
      .attr("y", 20)
      .attr("text-anchor", "middle")
      .attr("fill", "#fbbf24")
      .attr("font-size", "11px")
      .attr("font-weight", "bold")
      .attr("font-family", "var(--font-mono)")
      .text("CLASSICAL (pre-2010)");

    g.append("text")
      .attr("x", rightX)
      .attr("y", 20)
      .attr("text-anchor", "middle")
      .attr("fill", "#34d399")
      .attr("font-size", "11px")
      .attr("font-weight", "bold")
      .attr("font-family", "var(--font-mono)")
      .text("MODERN (2020+)");

    // Draw connecting lines FIRST (behind nodes)
    const edgeGroup = g.append("g").attr("class", "edges");

    for (const cp of classicalPapers) {
      const cy = classicalY.get(cp.id);
      if (cy == null) continue;

      for (const conn of cp.connections) {
        const my = modernY.get(conn.modern_id);
        if (my == null) continue;

        const isCited = conn.has_citation;
        const color = isCited ? "#34d399" : "#f87171";
        const opacity = isCited ? 0.3 : 0.5;

        // Bezier curve from left to right
        const midX = (leftX + rightX) / 2;

        edgeGroup
          .append("path")
          .attr(
            "d",
            `M${leftX + 8},${cy} C${midX},${cy} ${midX},${my} ${rightX - 8},${my}`
          )
          .attr("fill", "none")
          .attr("stroke", color)
          .attr("stroke-width", Math.max(0.5, conn.overlap_score * 2))
          .attr("opacity", opacity)
          .attr("stroke-dasharray", isCited ? "none" : "4,3")
          .attr("data-classical", cp.id)
          .attr("data-modern", conn.modern_id)
          .attr("cursor", "pointer")
          .on("mouseenter", function () {
            setHoveredEdge({ classical: cp, connection: conn });
            d3.select(this)
              .attr("stroke-width", 2.5)
              .attr("opacity", 1);
            // Dim other edges
            edgeGroup
              .selectAll("path")
              .filter(function () {
                return this !== d3.select(this).node();
              })
              .attr("opacity", 0.05);
            d3.select(this).attr("opacity", 1);
          })
          .on("mouseleave", function () {
            setHoveredEdge(null);
            edgeGroup
              .selectAll("path")
              .attr("opacity", function () {
                return d3.select(this).attr("stroke-dasharray") === "none"
                  ? 0.3
                  : 0.5;
              })
              .attr("stroke-width", function () {
                const score = parseFloat(
                  d3.select(this).attr("data-score") || "0.5"
                );
                return Math.max(0.5, score * 2);
              });
          });
      }
    }

    // Draw classical paper nodes (left side)
    const classicalGroup = g.append("g").attr("class", "classical");

    for (const cp of classicalPapers) {
      const cy = classicalY.get(cp.id);
      if (cy == null) continue;

      const r = Math.max(4, Math.min(12, Math.log(Math.max(cp.citations, 1) + 1) * 1.5));
      const color = cp.pattern
        ? PATTERN_COLORS[cp.pattern] || "#fbbf24"
        : "#fbbf24";

      const ng = classicalGroup
        .append("g")
        .attr("transform", `translate(${leftX},${cy})`)
        .attr("cursor", "pointer");

      ng.append("circle")
        .attr("r", r)
        .attr("fill", color)
        .attr("opacity", 0.85);

      // Label (right-aligned, to the left of the dot)
      ng.append("text")
        .attr("x", -r - 6)
        .attr("y", 0)
        .attr("dy", "0.35em")
        .attr("text-anchor", "end")
        .attr("fill", "#d4d4d8")
        .attr("font-size", "9px")
        .attr("font-family", "var(--font-mono)")
        .text(truncate(cp.title, 35));

      ng.append("text")
        .attr("x", -r - 6)
        .attr("y", 11)
        .attr("text-anchor", "end")
        .attr("fill", "#71717a")
        .attr("font-size", "8px")
        .attr("font-family", "var(--font-mono)")
        .text(`${cp.year || "?"} \u00b7 ${cp.citations.toLocaleString()} cites`);

      ng.on("mouseenter", function () {
        // Highlight all edges from this classical paper
        edgeGroup.selectAll("path").attr("opacity", 0.05);
        edgeGroup
          .selectAll(`path[data-classical="${cp.id}"]`)
          .attr("opacity", 1)
          .attr("stroke-width", 2);
      });

      ng.on("mouseleave", function () {
        edgeGroup
          .selectAll("path")
          .attr("opacity", function () {
            return d3.select(this).attr("stroke-dasharray") === "none"
              ? 0.3
              : 0.5;
          })
          .attr("stroke-width", 0.8);
      });

      ng.on("click", function () {
        window.location.href = `/paper/${cp.id}`;
      });
    }

    // Draw modern paper nodes (right side)
    const modernGroup = g.append("g").attr("class", "modern");

    for (const mp of modernPapers) {
      const my = modernY.get(mp.id);
      if (my == null) continue;

      const r = Math.max(3, Math.min(10, Math.log(Math.max(mp.citations, 1) + 1) * 1.2));
      const color = mp.pattern
        ? PATTERN_COLORS[mp.pattern] || "#34d399"
        : "#34d399";

      const ng = modernGroup
        .append("g")
        .attr("transform", `translate(${rightX},${my})`)
        .attr("cursor", "pointer");

      ng.append("circle")
        .attr("r", r)
        .attr("fill", color)
        .attr("opacity", 0.85);

      // Label (left-aligned, to the right of the dot)
      ng.append("text")
        .attr("x", r + 6)
        .attr("y", 0)
        .attr("dy", "0.35em")
        .attr("text-anchor", "start")
        .attr("fill", "#d4d4d8")
        .attr("font-size", "9px")
        .attr("font-family", "var(--font-mono)")
        .text(truncate(mp.title, 35));

      ng.append("text")
        .attr("x", r + 6)
        .attr("y", 11)
        .attr("text-anchor", "start")
        .attr("fill", "#71717a")
        .attr("font-size", "8px")
        .attr("font-family", "var(--font-mono)")
        .text(`${mp.year || "?"} \u00b7 ${mp.citations.toLocaleString()} cites`);

      ng.on("mouseenter", function () {
        edgeGroup.selectAll("path").attr("opacity", 0.05);
        edgeGroup
          .selectAll(`path[data-modern="${mp.id}"]`)
          .attr("opacity", 1)
          .attr("stroke-width", 2);
      });

      ng.on("mouseleave", function () {
        edgeGroup
          .selectAll("path")
          .attr("opacity", function () {
            return d3.select(this).attr("stroke-dasharray") === "none"
              ? 0.3
              : 0.5;
          })
          .attr("stroke-width", 0.8);
      });

      ng.on("click", function () {
        window.location.href = `/paper/${mp.id}`;
      });
    }
  }, [data]);

  useEffect(() => {
    renderRadar();
    const handleResize = () => renderRadar();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [renderRadar]);

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

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="px-4 py-2 border-b border-border flex items-center gap-3 shrink-0 flex-wrap">
        {/* Concept filter */}
        <select
          value={selectedConcept}
          onChange={(e) => setSelectedConcept(e.target.value)}
          className="text-[10px] bg-card border border-border rounded px-2 py-1 text-text"
        >
          <option value="">All concepts</option>
          {data?.filters.concepts.map((c) => (
            <option key={c.concept} value={c.concept}>
              {c.concept} ({c.count})
            </option>
          ))}
        </select>

        {/* Pattern filter */}
        <select
          value={selectedPattern}
          onChange={(e) => setSelectedPattern(e.target.value)}
          className="text-[10px] bg-card border border-border rounded px-2 py-1 text-text"
        >
          <option value="">All patterns</option>
          {data?.filters.patterns.map((p) => (
            <option key={p.pattern} value={p.pattern}>
              {p.pattern} ({p.count})
            </option>
          ))}
        </select>

        {/* Show cited toggle */}
        <label className="flex items-center gap-1.5 text-[10px] text-dim cursor-pointer">
          <input
            type="checkbox"
            checked={showCited}
            onChange={(e) => setShowCited(e.target.checked)}
            className="rounded border-border"
          />
          Show cited pairs
        </label>

        {/* Stats */}
        {data?.stats && (
          <div className="flex items-center gap-3 text-[10px] text-dim ml-auto">
            <span className="text-red-400">
              {data.stats.reinventions} reinventions
            </span>
            <span className="text-dim/60">
              {data.stats.cited} cited
            </span>
            <span>
              {data.stats.classical_count} classical &harr; {data.stats.modern_count}{" "}
              modern
            </span>
          </div>
        )}
      </div>

      {/* Graph area */}
      <div className="flex-1 min-h-0 relative" ref={containerRef}>
        <svg ref={svgRef} className="w-full h-full" />

        {/* Legend */}
        <div className="absolute bottom-2 left-2 flex items-center gap-4 text-[10px] bg-card/90 border border-border rounded px-3 py-2">
          <span className="flex items-center gap-1.5">
            <span className="w-6 h-0 border-t border-dashed border-red-400 inline-block" />
            <span className="text-red-400">Reinvention (no citation)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-6 h-0 border-t border-emerald-400 inline-block" />
            <span className="text-emerald-400">Cited (acknowledged)</span>
          </span>
        </div>

        {/* Hovered edge detail */}
        {hoveredEdge && (
          <div className="absolute top-2 left-1/2 -translate-x-1/2 max-w-md bg-card border border-border rounded-lg p-3 pointer-events-none z-10">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <p className="text-[10px] text-amber-400 uppercase tracking-wider mb-0.5">
                  Classical
                </p>
                <p className="text-xs text-text leading-snug">
                  {truncate(hoveredEdge.classical.title, 60)}
                </p>
                <p className="text-[10px] text-dim">
                  {hoveredEdge.classical.year} &middot;{" "}
                  {hoveredEdge.classical.citations.toLocaleString()} cites
                </p>
              </div>
              <div className="text-lg text-dim self-center px-2">
                {hoveredEdge.connection.has_citation ? (
                  <span className="text-emerald-400">&rarr;</span>
                ) : (
                  <span className="text-red-400">&rarr;&#x0338;</span>
                )}
              </div>
              <div className="flex-1">
                <p className="text-[10px] text-emerald-400 uppercase tracking-wider mb-0.5">
                  Modern
                </p>
                <p className="text-xs text-text leading-snug">
                  {truncate(hoveredEdge.connection.modern_title, 60)}
                </p>
                <p className="text-[10px] text-dim">
                  {hoveredEdge.connection.modern_year} &middot;{" "}
                  {hoveredEdge.connection.modern_citations.toLocaleString()}{" "}
                  cites
                </p>
              </div>
            </div>
            {hoveredEdge.connection.overlap_concepts.length > 0 && (
              <div className="mt-2 pt-2 border-t border-border">
                <p className="text-[10px] text-dim mb-1">Shared concepts:</p>
                <div className="flex flex-wrap gap-1">
                  {hoveredEdge.connection.overlap_concepts.map((c, i) => (
                    <span
                      key={i}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.04] text-text"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {!hoveredEdge.connection.has_citation && (
              <p className="text-[10px] text-red-400/80 mt-2">
                Reinvention: Modern paper discusses these concepts but does not
                cite the classical work.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
