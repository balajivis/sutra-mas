"use client";

import { useState, useCallback, useEffect, useRef } from "react";

/**
 * Pattern 3: Structured Comparison / Provenance Flow (ChainForge, CHI 2024)
 *
 * Flow-based visual: each pipeline stage is a node, edges show data flow.
 * Every output is traceable to its origin through the pipeline.
 *
 * Now wired to real paper data: select a paper, see its actual pipeline journey.
 */

interface FlowNode {
  id: string;
  agent: string;
  label: string;
  color: string;
  x: number;
  y: number;
  input: string;
  output: string;
  model?: string;
  tokens?: number;
  confidence?: number;
  reached: boolean;
}

interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

interface SearchResult {
  id: number;
  title: string;
  year: number;
  citations: number;
  pattern: string;
  summary: string;
}

interface PaperData {
  id: number;
  title: string;
  year: number;
  source: string;
  pipeline_status: string;
  relevance_score: number | null;
  relevance_rationale: string | null;
  analysis: Record<string, unknown> | null;
  modernity_score: number | null;
  has_code: boolean;
  repo_url: string | null;
  reproduction_feasibility: string | null;
  citations: number;
}

// Pipeline status progression
const PIPELINE_STAGES = [
  "seed", "collected", "filtering", "relevant", "marginal",
  "analyzing", "analyzed", "enriching", "enriched",
  "scouting", "scouted", "planning_reproduction", "reproduction_planned",
];

function stageReached(paperStatus: string, targetStage: string): boolean {
  const paperIdx = PIPELINE_STAGES.indexOf(paperStatus);
  const targetIdx = PIPELINE_STAGES.indexOf(targetStage);
  if (paperIdx === -1 || targetIdx === -1) return false;
  return paperIdx >= targetIdx;
}

function buildFlowFromPaper(p: PaperData): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const a = p.analysis || {};
  const status = p.pipeline_status;

  const nodes: FlowNode[] = [
    {
      id: "seed",
      agent: "A0/A1",
      label: "Seed",
      color: "#34d399",
      x: 40, y: 80,
      input: `Source: ${p.source || "unknown"}`,
      output: `paper_id=${p.id}, "${p.title}" (${p.year})`,
      reached: true,
    },
    {
      id: "filter",
      agent: "A2",
      label: "Filter",
      color: "#fbbf24",
      x: 200, y: 80,
      input: "Paper sent for relevance scoring",
      output: p.relevance_score != null
        ? `Relevance: ${p.relevance_score}/5. ${(p.relevance_rationale || "").slice(0, 120)}`
        : "Not yet scored",
      model: "gpt-5-mini",
      confidence: p.relevance_score != null ? (p.relevance_score as number) / 5 : undefined,
      reached: stageReached(status, "relevant") || stageReached(status, "marginal") || stageReached(status, "filtering"),
    },
    {
      id: "analyze",
      agent: "A3b",
      label: "Analyze",
      color: "#60a5fa",
      x: 400, y: 40,
      input: "Deep extraction via GPT-5.1",
      output: a.key_contribution_summary
        ? `Pattern: ${a.coordination_pattern || "none"}. ${(a.key_contribution_summary as string).slice(0, 150)}`
        : "Not yet analyzed",
      model: "gpt-5.1",
      confidence: a.theoretical_grounding === "strong" ? 0.9 : a.theoretical_grounding === "weak" ? 0.5 : a.theoretical_grounding === "none" ? 0.2 : undefined,
      reached: stageReached(status, "analyzed") || stageReached(status, "analyzing"),
    },
    {
      id: "enrich",
      agent: "A4",
      label: "Enrich",
      color: "#a78bfa",
      x: 400, y: 120,
      input: "Citation expansion via OpenAlex",
      output: p.citations > 0
        ? `${p.citations} citations. Modernity: ${p.modernity_score != null ? Number(p.modernity_score).toFixed(2) : "?"}`
        : "Not yet enriched",
      model: "API",
      reached: stageReached(status, "enriched") || stageReached(status, "enriching"),
    },
    {
      id: "scout",
      agent: "A5",
      label: "Scout",
      color: "#22d3ee",
      x: 620, y: 40,
      input: "Papers with Code + GitHub search",
      output: p.has_code
        ? `Code found: ${p.repo_url || "yes"}. Feasibility: ${p.reproduction_feasibility || "unknown"}`
        : stageReached(status, "scouted")
          ? "No code repository found"
          : "Not yet scouted",
      reached: stageReached(status, "scouted") || stageReached(status, "scouting"),
    },
    {
      id: "cluster",
      agent: "A8",
      label: "Cluster",
      color: "#fb923c",
      x: 620, y: 120,
      input: "Embedding + k-means assignment",
      output: a.coordination_pattern
        ? `Pattern: ${a.coordination_pattern}. Missing: ${(a.classical_concepts_missing as string || "none").slice(0, 80)}`
        : "Not yet clustered",
      reached: p.analysis != null,
    },
    {
      id: "finding",
      agent: "A0",
      label: "Finding",
      color: "#34d399",
      x: 820, y: 80,
      input: "All pipeline data aggregated",
      output: a.key_contribution_summary
        ? `Grounding: ${a.theoretical_grounding || "?"}. ${a.classical_concepts_missing ? `Lost: ${(a.classical_concepts_missing as string).slice(0, 80)}` : "No lost concepts detected."}`
        : "Awaiting pipeline completion",
      reached: stageReached(status, "analyzed"),
    },
  ];

  const edges: FlowEdge[] = [
    { from: "seed", to: "filter", label: "paper" },
    { from: "filter", to: "analyze", label: p.relevance_score != null ? `${p.relevance_score}/5` : "?" },
    { from: "filter", to: "enrich", label: "citations" },
    { from: "analyze", to: "scout", label: "analysis" },
    { from: "analyze", to: "cluster", label: "embedding" },
    { from: "enrich", to: "finding", label: "modernity" },
    { from: "cluster", to: "finding", label: "cluster" },
    { from: "scout", to: "finding", label: "code" },
  ];

  return { nodes, edges };
}

export function ProvenanceFlow() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [highlightPath, setHighlightPath] = useState<Set<string>>(new Set());

  // Paper search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedPaper, setSelectedPaper] = useState<PaperData | null>(null);
  const [loadingPaper, setLoadingPaper] = useState(false);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Flow data (built from selected paper)
  const [flowNodes, setFlowNodes] = useState<FlowNode[]>([]);
  const [flowEdges, setFlowEdges] = useState<FlowEdge[]>([]);

  // Debounced search
  const handleSearch = useCallback((q: string) => {
    setSearchQuery(q);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (q.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    searchTimeout.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&top=8`);
        if (!res.ok) return;
        const data = await res.json();
        setSearchResults(data.results || []);
      } catch {
        // ignore
      } finally {
        setSearching(false);
      }
    }, 300);
  }, []);

  // Select a paper -> fetch full data -> build flow
  const selectPaper = useCallback(async (id: number) => {
    setLoadingPaper(true);
    setSearchResults([]);
    setSearchQuery("");
    try {
      const res = await fetch(`/api/paper/${id}`);
      if (!res.ok) throw new Error("Failed to fetch paper");
      const paper = await res.json();
      setSelectedPaper(paper);
      const { nodes, edges } = buildFlowFromPaper(paper);
      setFlowNodes(nodes);
      setFlowEdges(edges);
      setSelectedNode(null);
      setHighlightPath(new Set());
    } catch {
      // ignore
    } finally {
      setLoadingPaper(false);
    }
  }, []);

  // Load a default paper on mount (most recently analyzed)
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/search?q=multi-agent&top=1");
        if (!res.ok) return;
        const data = await res.json();
        if (data.results?.length > 0) {
          selectPaper(data.results[0].id);
        }
      } catch {
        // ignore
      }
    })();
  }, [selectPaper]);

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(nodeId === selectedNode ? null : nodeId);
    if (nodeId === selectedNode) {
      setHighlightPath(new Set());
      return;
    }
    const path = new Set<string>();
    const queue = [nodeId];
    while (queue.length > 0) {
      const current = queue.shift()!;
      path.add(current);
      for (const edge of flowEdges) {
        if (edge.to === current && !path.has(edge.from)) {
          queue.push(edge.from);
        }
      }
    }
    setHighlightPath(path);
  };

  const selected = flowNodes.find((n) => n.id === selectedNode);

  return (
    <div className="h-full flex flex-col">
      {/* Paper search bar */}
      <div className="px-4 py-1.5 border-b border-border flex items-center gap-2 relative">
        <span className="text-[9px] text-dim uppercase tracking-wider shrink-0">
          Paper:
        </span>
        <div className="flex-1 relative">
          <input
            type="text"
            value={searchQuery || (selectedPaper ? `${selectedPaper.title} (${selectedPaper.year})` : "")}
            onChange={(e) => handleSearch(e.target.value)}
            onFocus={() => {
              if (selectedPaper && !searchQuery) setSearchQuery("");
            }}
            placeholder="Search for a paper to trace..."
            className="w-full bg-zinc-900 border border-border rounded px-2 py-1 text-[10px] text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-accent/50"
          />
          {searching && (
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-dim animate-pulse">
              ...
            </span>
          )}
          {/* Dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-0.5 bg-zinc-900 border border-border rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto">
              {searchResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => selectPaper(r.id)}
                  className="w-full text-left px-2.5 py-1.5 hover:bg-white/[0.04] transition cursor-pointer"
                >
                  <div className="text-[10px] text-zinc-200 truncate">
                    {r.title}
                  </div>
                  <div className="text-[9px] text-dim">
                    {r.year} &middot; {r.citations} citations &middot; {r.pattern}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        {loadingPaper && (
          <span className="text-[9px] text-dim animate-pulse shrink-0">Loading...</span>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 flex min-h-0">
        {/* Flow diagram */}
        <div className="flex-1 min-w-0 overflow-auto">
          {flowNodes.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-[10px] text-dim text-center">
                Search for a paper above to trace its pipeline journey
              </div>
            </div>
          ) : (
            <>
              <div className="px-4 py-1.5 text-[9px] text-dim">
                Provenance trace: &quot;{selectedPaper?.title}&quot; &middot;
                Status: <span className="text-accent">{selectedPaper?.pipeline_status}</span> &middot;
                Click any node to trace its origin
              </div>
              <svg
                viewBox="0 0 920 170"
                className="w-full"
                style={{ minWidth: 800, height: "auto" }}
              >
                {/* Edges */}
                {flowEdges.map((e) => {
                  const from = flowNodes.find((n) => n.id === e.from)!;
                  const to = flowNodes.find((n) => n.id === e.to)!;
                  if (!from || !to) return null;
                  const isHighlighted =
                    highlightPath.has(e.from) && highlightPath.has(e.to);
                  const bothReached = from.reached && to.reached;

                  const x1 = from.x + 60;
                  const y1 = from.y + 18;
                  const x2 = to.x;
                  const y2 = to.y + 18;

                  return (
                    <g key={`${e.from}-${e.to}`}>
                      <line
                        x1={x1} y1={y1} x2={x2} y2={y2}
                        stroke={isHighlighted ? "#34d399" : bothReached ? "#3f3f46" : "#1e1e2e"}
                        strokeWidth={isHighlighted ? 2 : 1}
                        strokeDasharray={bothReached ? undefined : "4 3"}
                      />
                      <circle
                        cx={x2 - 2} cy={y2} r={2}
                        fill={isHighlighted ? "#34d399" : bothReached ? "#3f3f46" : "#1e1e2e"}
                      />
                      {e.label && (
                        <text
                          x={(x1 + x2) / 2}
                          y={(y1 + y2) / 2 - 5}
                          textAnchor="middle"
                          className="text-[8px]"
                          fill="#71717a"
                        >
                          {e.label}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Nodes */}
                {flowNodes.map((n) => {
                  const isSelected = selectedNode === n.id;
                  const isOnPath = highlightPath.has(n.id);

                  return (
                    <g
                      key={n.id}
                      className="cursor-pointer"
                      onClick={() => handleNodeClick(n.id)}
                      opacity={n.reached ? 1 : 0.35}
                    >
                      <rect
                        x={n.x} y={n.y}
                        width={120} height={36} rx={6}
                        fill={
                          isSelected
                            ? n.color + "30"
                            : isOnPath
                              ? n.color + "15"
                              : "#12121a"
                        }
                        stroke={isSelected || isOnPath ? n.color : "#1e1e2e"}
                        strokeWidth={isSelected ? 2 : 1}
                      />
                      <rect
                        x={n.x + 4} y={n.y + 4}
                        width={28} height={12} rx={3}
                        fill={n.color + "33"}
                      />
                      <text
                        x={n.x + 18} y={n.y + 13}
                        textAnchor="middle"
                        className="text-[7px] font-bold"
                        fill={n.color}
                      >
                        {n.agent}
                      </text>
                      <text
                        x={n.x + 60} y={n.y + 26}
                        textAnchor="middle"
                        className="text-[9px]"
                        fill={isOnPath ? "#d4d4d8" : n.reached ? "#71717a" : "#3f3f46"}
                      >
                        {n.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </>
          )}
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="w-72 shrink-0 border-l border-border overflow-y-auto px-3 py-2 space-y-2">
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-bold"
                style={{ color: selected.color }}
              >
                {selected.agent}
              </span>
              <span className="text-[10px] text-dim">{selected.label}</span>
              {!selected.reached && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500">
                  not reached
                </span>
              )}
            </div>

            <div>
              <div className="text-[9px] text-dim uppercase tracking-wider mb-0.5">
                Input
              </div>
              <div className="text-[10px] text-zinc-400 leading-snug px-2 py-1.5 rounded bg-zinc-900/60 border border-border/40">
                {selected.input}
              </div>
            </div>

            <div>
              <div className="text-[9px] text-dim uppercase tracking-wider mb-0.5">
                Output
              </div>
              <div className="text-[10px] text-zinc-300 leading-snug px-2 py-1.5 rounded bg-zinc-900/60 border border-border/40">
                {selected.output}
              </div>
            </div>

            {selected.model && (
              <div className="flex gap-3 text-[9px]">
                <span className="text-dim">
                  Model:{" "}
                  <span className="text-zinc-300">{selected.model}</span>
                </span>
                {selected.tokens !== undefined && selected.tokens > 0 && (
                  <span className="text-dim">
                    Tokens:{" "}
                    <span className="text-zinc-300">
                      {(selected.tokens / 1000).toFixed(0)}K
                    </span>
                  </span>
                )}
              </div>
            )}

            {selected.confidence !== undefined && (
              <div>
                <div className="text-[9px] text-dim mb-0.5">
                  Confidence: {Math.round(selected.confidence * 100)}%
                </div>
                <div className="h-1.5 rounded bg-zinc-800 overflow-hidden">
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${selected.confidence * 100}%`,
                      background: selected.color,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
