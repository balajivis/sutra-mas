"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Citation Cliff Visualization
 *
 * Multi-line chart showing per-year citation distributions for classical MAS
 * concepts (not individual papers). Each line is a concept group (Contract Net,
 * BDI, SharedPlans, etc.) with citations summed across constituent papers.
 *
 * The "cliff" is the dramatic drop-off where modern LLM agent papers stop citing
 * classical foundations — the visual signature of the Lost Canary phenomenon.
 *
 * Features:
 * - Full 1980-2026 year range (via OpenAlex group_by API)
 * - Lines colored by survival: red=genuinely lost, amber=renamed/below, green=active
 * - Cemri failure band overlay (2023+)
 * - Kim stat annotations (17.2x, 4.4x)
 * - SVG export for paper figures
 *
 * Data: pipeline/data/citation_cliff_full.json via /api/agent0/citation-cliff
 */

interface YearDataPoint {
  year: number;
  citations: number;
}

interface ConceptSeries {
  name: string;
  description: string;
  papers: string[];
  paperCount: number;
  survival: "genuinely_lost" | "known_but_ignored" | "below_threshold" | "renamed" | "active";
  totalCitations: number;
  modernCitations: number;
  modernityScore: number;
  yearData: YearDataPoint[];
  peakYear: number | null;
  peakCitations: number;
}

interface Annotation {
  type: "failure_band" | "callout" | "stat" | "era_label";
  label: string;
  year?: number;
  year_start?: number;
  year_end?: number;
  concept?: string;
  position?: string;
}

interface CliffData {
  metadata: {
    description: string;
    conceptCount: number;
    paperCount: number;
    yearRange: [number, number];
  };
  yearRange: number[];
  concepts: ConceptSeries[];
  annotations: Annotation[];
}

const SURVIVAL_COLORS: Record<string, { stroke: string; label: string; bg: string }> = {
  genuinely_lost: { stroke: "#ef4444", label: "Genuinely Lost", bg: "#ef444420" },
  known_but_ignored: { stroke: "#f59e0b", label: "Known but Ignored", bg: "#f59e0b20" },
  below_threshold: { stroke: "#f59e0b", label: "Below Threshold", bg: "#f59e0b20" },
  renamed: { stroke: "#f59e0b", label: "Renamed", bg: "#f59e0b20" },
  active: { stroke: "#22c55e", label: "Active", bg: "#22c55e20" },
};

// Distinct line colors — one per concept
const CONCEPT_LINE_COLORS = [
  "#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e",
  "#14b8a6", "#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6",
  "#a855f7", "#d946ef", "#ec4899", "#f43f5e", "#fb923c",
  "#a3e635", "#2dd4bf",
];

export function CitationCliff() {
  const [data, setData] = useState<CliffData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredConcept, setHoveredConcept] = useState<number | null>(null);
  const [selectedConcepts, setSelectedConcepts] = useState<Set<number>>(new Set());
  const [showNormalized, setShowNormalized] = useState(false);
  const [showAnnotations, setShowAnnotations] = useState(true);
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    year: number;
    concepts: { name: string; citations: number; color: string; survival: string }[];
  } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/agent0/citation-cliff");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setData(d);
      // Select all by default
      setSelectedConcepts(new Set((d.concepts as ConceptSeries[]).map((_, i) => i)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleConcept = useCallback((idx: number) => {
    setSelectedConcepts((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    if (!data) return;
    setSelectedConcepts(new Set(data.concepts.map((_, i) => i)));
  }, [data]);

  const selectNone = useCallback(() => {
    setSelectedConcepts(new Set());
  }, []);

  const selectBySurvival = useCallback(
    (survival: string) => {
      if (!data) return;
      const next = new Set<number>();
      data.concepts.forEach((c, i) => {
        if (survival === "amber") {
          if (["known_but_ignored", "below_threshold", "renamed"].includes(c.survival)) next.add(i);
        } else if (c.survival === survival) {
          next.add(i);
        }
      });
      setSelectedConcepts(next);
    },
    [data]
  );

  const downloadSVG = useCallback(() => {
    if (!svgRef.current) return;
    const svg = svgRef.current;
    const serializer = new XMLSerializer();
    let source = serializer.serializeToString(svg);
    // Add XML declaration and namespace
    if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    source = '<?xml version="1.0" standalone="no"?>\r\n' + source;
    const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "citation-cliff.svg";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-[10px] text-dim animate-pulse">Loading citation data...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-[10px] text-red-400 mb-2">{error || "No data"}</div>
          <button
            onClick={fetchData}
            className="px-3 py-1 text-[10px] rounded bg-zinc-800 text-dim hover:text-text border border-border transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { yearRange, concepts, annotations } = data;
  const activeConcepts = concepts.filter((_, i) => selectedConcepts.has(i));

  // Chart dimensions
  const margin = { top: 24, right: 24, bottom: 36, left: 50 };
  const chartW = 960;
  const chartH = 360;
  const innerW = chartW - margin.left - margin.right;
  const innerH = chartH - margin.top - margin.bottom;

  // Scales
  const minYear = yearRange[0] || 1980;
  const maxYear = yearRange[yearRange.length - 1] || 2026;
  const xScale = (year: number) =>
    margin.left + ((year - minYear) / (maxYear - minYear)) * innerW;

  // Y scale
  let yMax = 10;
  for (const c of activeConcepts) {
    for (const d of c.yearData) {
      const val = showNormalized && c.totalCitations > 0
        ? (d.citations / c.totalCitations) * 1000
        : d.citations;
      if (val > yMax) yMax = val;
    }
  }
  yMax = Math.ceil(yMax * 1.15);
  const yScale = (val: number) =>
    margin.top + innerH - (val / yMax) * innerH;

  // Build SVG paths
  const paths = activeConcepts.map((c) => {
    const idx = concepts.indexOf(c);
    const survivalColor = SURVIVAL_COLORS[c.survival]?.stroke || "#f59e0b";
    const lineColor = CONCEPT_LINE_COLORS[idx % CONCEPT_LINE_COLORS.length];
    const points = c.yearData
      .filter((d) => d.year >= minYear && d.year <= maxYear)
      .map((d) => {
        const val = showNormalized && c.totalCitations > 0
          ? (d.citations / c.totalCitations) * 1000
          : d.citations;
        return `${xScale(d.year)},${yScale(val)}`;
      })
      .join(" ");
    return { idx, lineColor, survivalColor, points, concept: c };
  });

  // Annotation helpers
  const failureBand = annotations.find((a) => a.type === "failure_band");
  const eraLabels = annotations.filter((a) => a.type === "era_label");
  const callouts = annotations.filter((a) => a.type === "callout");
  const stats = annotations.filter((a) => a.type === "stat");

  // Y-axis ticks
  const yTicks: number[] = [];
  const yStep = yMax > 500 ? Math.ceil(yMax / 5 / 100) * 100
    : yMax > 100 ? Math.ceil(yMax / 5 / 10) * 10
    : Math.ceil(yMax / 5);
  for (let v = 0; v <= yMax; v += yStep) yTicks.push(v);

  // X-axis ticks — every 5 years
  const xTicks: number[] = [];
  for (let y = Math.ceil(minYear / 5) * 5; y <= maxYear; y += 5) xTicks.push(y);
  if (!xTicks.includes(minYear)) xTicks.unshift(minYear);
  if (!xTicks.includes(maxYear)) xTicks.push(maxYear);

  // Summary stats
  const lostCount = concepts.filter((c) => c.survival === "genuinely_lost").length;
  const activeCount = concepts.filter((c) => c.survival === "active").length;
  const renamedCount = concepts.filter((c) =>
    ["renamed", "known_but_ignored", "below_threshold"].includes(c.survival)
  ).length;

  const handleSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * chartW;
    const my = ((e.clientY - rect.top) / rect.height) * chartH;

    const yearFloat = minYear + ((mx - margin.left) / innerW) * (maxYear - minYear);
    const year = Math.round(yearFloat);
    if (year < minYear || year > maxYear) {
      setTooltip(null);
      return;
    }

    const tConcepts = activeConcepts
      .map((c) => {
        const d = c.yearData.find((d) => d.year === year);
        return {
          name: c.name,
          citations: d?.citations || 0,
          color: CONCEPT_LINE_COLORS[concepts.indexOf(c) % CONCEPT_LINE_COLORS.length],
          survival: c.survival,
        };
      })
      .filter((c) => c.citations > 0)
      .sort((a, b) => b.citations - a.citations);

    if (tConcepts.length > 0) {
      setTooltip({
        x: (mx / chartW) * 100,
        y: (my / chartH) * 100,
        year,
        concepts: tConcepts,
      });
    } else {
      setTooltip(null);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-2 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <span className="text-[10px] text-dim uppercase tracking-wider">
            Citation Cliff
            <span className="text-red-400 ml-1">The Forgetting Curve of MAS</span>
          </span>
          <div className="flex items-center gap-3 mt-0.5 text-[9px]">
            <span className="text-red-400">{lostCount} genuinely lost</span>
            <span className="text-amber-400">{renamedCount} renamed/fading</span>
            <span className="text-green-400">{activeCount} active</span>
            <span className="text-dim">{concepts.length} concepts, {data.metadata.paperCount} papers</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={downloadSVG}
            className="px-2 py-0.5 text-[9px] rounded border border-border text-dim hover:text-text transition cursor-pointer"
            title="Download SVG for paper figures"
          >
            SVG
          </button>
          <button
            onClick={() => setShowAnnotations(!showAnnotations)}
            className={`px-2 py-0.5 text-[9px] rounded border transition cursor-pointer ${
              showAnnotations
                ? "border-blue-400/40 text-blue-400 bg-blue-400/10"
                : "border-border text-dim hover:text-text"
            }`}
          >
            Annotations
          </button>
          <button
            onClick={() => setShowNormalized(!showNormalized)}
            className={`px-2 py-0.5 text-[9px] rounded border transition cursor-pointer ${
              showNormalized
                ? "border-accent/40 text-accent bg-accent/10"
                : "border-border text-dim hover:text-text"
            }`}
          >
            {showNormalized ? "Normalized" : "Raw counts"}
          </button>
          <div className="flex items-center gap-1 text-[9px]">
            <button
              onClick={() => selectBySurvival("genuinely_lost")}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-white/[0.04] transition cursor-pointer"
            >
              <span className="w-2 h-0.5 rounded bg-red-500" />
              <span className="text-dim">Lost</span>
            </button>
            <button
              onClick={() => selectBySurvival("amber")}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-white/[0.04] transition cursor-pointer"
            >
              <span className="w-2 h-0.5 rounded bg-amber-500" />
              <span className="text-dim">Fading</span>
            </button>
            <button
              onClick={() => selectBySurvival("active")}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-white/[0.04] transition cursor-pointer"
            >
              <span className="w-2 h-0.5 rounded bg-green-500" />
              <span className="text-dim">Active</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex min-h-0">
        {/* Chart */}
        <div className="flex-1 overflow-auto px-4 py-2 relative">
          <svg
            ref={svgRef}
            viewBox={`0 0 ${chartW} ${chartH}`}
            className="w-full"
            style={{ minWidth: 800, height: "auto", background: "#09090b" }}
            onMouseMove={handleSvgMouseMove}
            onMouseLeave={() => setTooltip(null)}
          >
            {/* Era background bands */}
            {showAnnotations && eraLabels.map((era, i) => {
              const x1 = xScale(Math.max(era.year_start!, minYear));
              const x2 = xScale(Math.min(era.year_end!, maxYear));
              return (
                <g key={`era-${i}`}>
                  <rect
                    x={x1}
                    y={margin.top}
                    width={x2 - x1}
                    height={innerH}
                    fill={i === 2 ? "#ef444406" : i === 1 ? "#3b82f604" : "#22c55e04"}
                  />
                  <text
                    x={(x1 + x2) / 2}
                    y={chartH - 22}
                    textAnchor="middle"
                    fill={i === 2 ? "#ef4444" : i === 1 ? "#3b82f6" : "#22c55e"}
                    opacity={0.3}
                    fontSize={9}
                    fontWeight="bold"
                  >
                    {era.label}
                  </text>
                </g>
              );
            })}

            {/* Failure band overlay (Cemri) */}
            {showAnnotations && failureBand && (
              <g>
                <rect
                  x={xScale(failureBand.year_start!)}
                  y={margin.top}
                  width={xScale(failureBand.year_end!) - xScale(failureBand.year_start!)}
                  height={innerH}
                  fill="#ef4444"
                  opacity={0.06}
                />
                <line
                  x1={xScale(failureBand.year_start!)}
                  y1={margin.top}
                  x2={xScale(failureBand.year_start!)}
                  y2={margin.top + innerH}
                  stroke="#ef4444"
                  strokeWidth={1}
                  strokeDasharray="4 3"
                  opacity={0.5}
                />
                <text
                  x={xScale(failureBand.year_start!) + 4}
                  y={margin.top + 12}
                  fill="#ef4444"
                  opacity={0.7}
                  fontSize={8}
                  fontWeight="bold"
                >
                  {failureBand.label}
                </text>
              </g>
            )}

            {/* Grid lines */}
            {yTicks.map((v) => (
              <g key={`y-${v}`}>
                <line
                  x1={margin.left}
                  y1={yScale(v)}
                  x2={chartW - margin.right}
                  y2={yScale(v)}
                  stroke="#27272a"
                  strokeWidth={0.5}
                />
                <text
                  x={margin.left - 6}
                  y={yScale(v) + 3}
                  textAnchor="end"
                  fill="#52525b"
                  fontSize={8}
                >
                  {v}
                </text>
              </g>
            ))}

            {/* X-axis */}
            {xTicks.map((y) => (
              <text
                key={`x-${y}`}
                x={xScale(y)}
                y={chartH - 6}
                textAnchor="middle"
                fill="#52525b"
                fontSize={8}
              >
                {y}
              </text>
            ))}

            {/* Y-axis label */}
            <text
              x={14}
              y={margin.top + innerH / 2}
              textAnchor="middle"
              transform={`rotate(-90, 14, ${margin.top + innerH / 2})`}
              fill="#52525b"
              fontSize={8}
            >
              {showNormalized ? "Citations per 1K total" : "Citations / year"}
            </text>

            {/* Concept lines */}
            {paths.map(({ idx, lineColor, survivalColor, points, concept }) => {
              const isHovered = hoveredConcept === idx;
              const isAnyHovered = hoveredConcept !== null;
              const opacity = isAnyHovered ? (isHovered ? 1 : 0.12) : 0.75;

              return (
                <g key={idx}>
                  <polyline
                    points={points}
                    fill="none"
                    stroke={lineColor}
                    strokeWidth={isHovered ? 3 : 1.5}
                    opacity={opacity}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    style={{ cursor: "pointer", transition: "opacity 0.15s" }}
                    onMouseEnter={() => setHoveredConcept(idx)}
                    onMouseLeave={() => setHoveredConcept(null)}
                  />
                  {/* Peak label on hover */}
                  {isHovered && concept.peakYear && (
                    <g>
                      {concept.yearData
                        .filter((d) => d.year >= minYear && d.year <= maxYear && d.citations > 0)
                        .map((d) => {
                          const val = showNormalized && concept.totalCitations > 0
                            ? (d.citations / concept.totalCitations) * 1000
                            : d.citations;
                          return (
                            <circle
                              key={d.year}
                              cx={xScale(d.year)}
                              cy={yScale(val)}
                              r={2}
                              fill={lineColor}
                            />
                          );
                        })}
                      <text
                        x={xScale(concept.peakYear) + 4}
                        y={yScale(
                          showNormalized && concept.totalCitations > 0
                            ? (concept.peakCitations / concept.totalCitations) * 1000
                            : concept.peakCitations
                        ) - 6}
                        fill={lineColor}
                        fontSize={8}
                        fontWeight="bold"
                      >
                        {concept.name}
                      </text>
                    </g>
                  )}
                  {/* Survival indicator dot at the end of each line */}
                  {(() => {
                    const lastNonZero = [...concept.yearData]
                      .reverse()
                      .find((d) => d.citations > 0 && d.year >= minYear && d.year <= maxYear);
                    if (!lastNonZero) return null;
                    const val = showNormalized && concept.totalCitations > 0
                      ? (lastNonZero.citations / concept.totalCitations) * 1000
                      : lastNonZero.citations;
                    return (
                      <circle
                        cx={xScale(lastNonZero.year)}
                        cy={yScale(val)}
                        r={3}
                        fill={survivalColor}
                        stroke="#09090b"
                        strokeWidth={1}
                        opacity={isAnyHovered && !isHovered ? 0.2 : 0.9}
                      />
                    );
                  })()}
                </g>
              );
            })}

            {/* Stat annotations (Kim et al.) */}
            {showAnnotations && stats.map((stat, i) => (
              <g key={`stat-${i}`}>
                <text
                  x={xScale(stat.year!) + 4}
                  y={margin.top + 26 + i * 14}
                  fill="#f59e0b"
                  opacity={0.8}
                  fontSize={8}
                  fontWeight="bold"
                >
                  {stat.label}
                </text>
              </g>
            ))}

            {/* Callout annotations */}
            {showAnnotations && callouts.map((callout, i) => {
              const conceptData = concepts.find((c) => c.name === callout.concept);
              if (!conceptData) return null;
              const yearPt = conceptData.yearData.find((d) => d.year === callout.year);
              if (!yearPt) return null;
              const val = showNormalized && conceptData.totalCitations > 0
                ? (yearPt.citations / conceptData.totalCitations) * 1000
                : yearPt.citations;
              const cx = xScale(callout.year!);
              const cy = yScale(val);
              return (
                <g key={`callout-${i}`}>
                  <line
                    x1={cx}
                    y1={cy}
                    x2={cx}
                    y2={cy - 30 - i * 8}
                    stroke="#ef4444"
                    strokeWidth={0.5}
                    opacity={0.5}
                    strokeDasharray="2 2"
                  />
                  <text
                    x={cx + 4}
                    y={cy - 32 - i * 8}
                    fill="#ef4444"
                    opacity={0.7}
                    fontSize={7}
                  >
                    {callout.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Tooltip */}
          {tooltip && (
            <div
              className="absolute z-50 pointer-events-none bg-zinc-900/95 border border-border rounded-lg px-2.5 py-1.5 shadow-xl"
              style={{
                left: `${Math.min(tooltip.x, 75)}%`,
                top: `${Math.max(tooltip.y - 5, 5)}%`,
              }}
            >
              <div className="text-[9px] text-dim font-bold mb-0.5">{tooltip.year}</div>
              {tooltip.concepts.slice(0, 8).map((c, i) => (
                <div key={i} className="flex items-center gap-1.5 text-[9px]">
                  <span className="w-2 h-0.5 rounded shrink-0" style={{ background: c.color }} />
                  <span className="text-zinc-400 truncate" style={{ maxWidth: 200 }}>
                    {c.name}
                  </span>
                  <span className="text-zinc-300 ml-auto shrink-0">{c.citations}</span>
                </div>
              ))}
              {tooltip.concepts.length > 8 && (
                <div className="text-[8px] text-dim mt-0.5">
                  +{tooltip.concepts.length - 8} more
                </div>
              )}
            </div>
          )}
        </div>

        {/* Concept legend / selector */}
        <div className="w-72 shrink-0 border-l border-border overflow-y-auto">
          <div className="px-3 py-1.5 border-b border-border/50 flex items-center justify-between">
            <span className="text-[9px] text-dim uppercase tracking-wider">
              Concepts ({selectedConcepts.size}/{concepts.length})
            </span>
            <div className="flex gap-1">
              <button
                onClick={selectAll}
                className="text-[8px] text-dim hover:text-accent transition cursor-pointer"
              >
                all
              </button>
              <button
                onClick={selectNone}
                className="text-[8px] text-dim hover:text-accent transition cursor-pointer"
              >
                none
              </button>
            </div>
          </div>
          <div className="space-y-0.5 py-1 px-1">
            {concepts.map((c, i) => {
              const lineColor = CONCEPT_LINE_COLORS[i % CONCEPT_LINE_COLORS.length];
              const isSelected = selectedConcepts.has(i);
              const isHovered = hoveredConcept === i;
              const survivalStyle = SURVIVAL_COLORS[c.survival] || SURVIVAL_COLORS.below_threshold;

              return (
                <div
                  key={i}
                  className={`flex items-start gap-1.5 px-2 py-1 rounded cursor-pointer transition ${
                    isHovered ? "bg-white/[0.06]" : "hover:bg-white/[0.03]"
                  }`}
                  onClick={() => toggleConcept(i)}
                  onMouseEnter={() => setHoveredConcept(i)}
                  onMouseLeave={() => setHoveredConcept(null)}
                >
                  <span
                    className={`w-2.5 h-2.5 rounded-sm shrink-0 mt-0.5 border ${
                      isSelected ? "border-transparent" : "border-zinc-600"
                    }`}
                    style={{
                      background: isSelected ? lineColor : "transparent",
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-[9px] leading-tight font-medium ${
                        isSelected ? "text-zinc-200" : "text-zinc-500"
                      }`}
                    >
                      {c.name}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span
                        className="text-[7px] px-1 py-0 rounded uppercase tracking-wider"
                        style={{ background: survivalStyle.bg, color: survivalStyle.stroke }}
                      >
                        {c.survival === "genuinely_lost" ? "lost" :
                         c.survival === "known_but_ignored" ? "ignored" :
                         c.survival === "below_threshold" ? "fading" :
                         c.survival}
                      </span>
                      <span className="text-[8px] text-dim">
                        {c.totalCitations.toLocaleString()}
                      </span>
                      {c.peakYear && (
                        <span className="text-[8px] text-dim">
                          pk {c.peakYear}
                        </span>
                      )}
                    </div>
                    {isHovered && (
                      <div className="text-[8px] text-zinc-500 mt-0.5 leading-tight">
                        {c.description}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
