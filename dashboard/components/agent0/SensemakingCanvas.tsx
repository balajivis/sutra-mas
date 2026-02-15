"use client";

import { useState, useCallback, useEffect } from "react";

/**
 * Patterns 1 + 6: Multilevel Canvas + Sensemaking Loop
 *
 * Left column = foraging feed (agent outputs from /api/agent0/feed).
 * Right canvas = sensemaking space (human organizes, connects, concludes).
 */

type ZoomLevel = "paper" | "cluster" | "thesis";

interface ForagingItem {
  id: string;
  agent: string;
  agentColor: string;
  timestamp: string;
  type: "extraction" | "citation" | "cluster_update" | "anomaly" | "finding";
  content: string;
  meta?: string;
}

interface CanvasCard {
  id: string;
  x: number;
  y: number;
  width: number;
  content: string;
  color: string;
  level: ZoomLevel;
  linkedForaging?: string;
}

const TYPE_STYLES: Record<
  ForagingItem["type"],
  { icon: string; color: string }
> = {
  extraction: { icon: "E", color: "#a78bfa" },
  citation: { icon: "C", color: "#60a5fa" },
  cluster_update: { icon: "K", color: "#f472b6" },
  anomaly: { icon: "!", color: "#f87171" },
  finding: { icon: "F", color: "#34d399" },
};

const ZOOM_LABELS: Record<ZoomLevel, { label: string; color: string }> = {
  paper: { label: "Paper", color: "#60a5fa" },
  cluster: { label: "Cluster", color: "#a78bfa" },
  thesis: { label: "Thesis", color: "#34d399" },
};

const INITIAL_CANVAS: CanvasCard[] = [
  {
    id: "c1",
    x: 20,
    y: 20,
    width: 250,
    content:
      "THESIS: Modern MAS failures (40-80%) are coordination failures, not model failures. Classical MAS solved these problems.",
    color: "#34d399",
    level: "thesis",
  },
];

export function SensemakingCanvas() {
  const [foraging, setForaging] = useState<ForagingItem[]>([]);
  const [canvas, setCanvas] = useState(INITIAL_CANVAS);
  const [zoomFilter, setZoomFilter] = useState<ZoomLevel | "all">("all");
  const [newCardText, setNewCardText] = useState("");
  const [newCardLevel, setNewCardLevel] = useState<ZoomLevel>("cluster");
  const [dragging, setDragging] = useState<string | null>(null);
  const [feedLoading, setFeedLoading] = useState(true);

  // Fetch foraging feed from API
  const fetchFeed = useCallback(async () => {
    try {
      const res = await fetch("/api/agent0/feed");
      if (!res.ok) return;
      const data = await res.json();
      if (data.items && Array.isArray(data.items)) {
        setForaging((prev) => {
          const existingIds = new Set(prev.map((f) => f.id));
          const newItems = (data.items as ForagingItem[]).filter(
            (item) => !existingIds.has(item.id)
          );
          if (newItems.length === 0) return prev;
          return [...newItems, ...prev];
        });
      }
    } catch {
      // Silently fail, will retry
    } finally {
      setFeedLoading(false);
    }
  }, []);

  // Initial fetch + 60s polling
  useEffect(() => {
    fetchFeed();
    const interval = setInterval(fetchFeed, 60000);
    return () => clearInterval(interval);
  }, [fetchFeed]);

  const addToCanvas = useCallback(
    (foragingId: string) => {
      const item = foraging.find((f) => f.id === foragingId);
      if (!item) return;
      const newCard: CanvasCard = {
        id: `c-${Date.now()}`,
        x: 20 + Math.random() * 200,
        y: 20 + Math.random() * 100,
        width: 220,
        content: item.content,
        color: item.agentColor,
        level: item.type === "cluster_update" ? "cluster" : "paper",
        linkedForaging: foragingId,
      };
      setCanvas((prev) => [...prev, newCard]);
    },
    [foraging]
  );

  const addCustomCard = useCallback(() => {
    if (!newCardText.trim()) return;
    const newCard: CanvasCard = {
      id: `c-${Date.now()}`,
      x: 550 + Math.random() * 100,
      y: 20 + Math.random() * 100,
      width: 220,
      content: newCardText,
      color: ZOOM_LABELS[newCardLevel].color,
      level: newCardLevel,
    };
    setCanvas((prev) => [...prev, newCard]);
    setNewCardText("");
  }, [newCardText, newCardLevel]);

  const removeCard = useCallback((id: string) => {
    setCanvas((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const filteredCanvas =
    zoomFilter === "all"
      ? canvas
      : canvas.filter((c) => c.level === zoomFilter);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-2 border-b border-border flex items-center justify-between">
        <div>
          <span className="text-[10px] text-dim uppercase tracking-wider">
            Sensemaking Workspace
            <span className="text-accent ml-1">P1+P6</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Zoom level filter */}
          <span className="text-[9px] text-dim mr-1">Zoom:</span>
          {(["all", "thesis", "cluster", "paper"] as const).map((level) => (
            <button
              key={level}
              onClick={() => setZoomFilter(level)}
              className={`px-2 py-0.5 text-[9px] rounded transition cursor-pointer ${
                zoomFilter === level
                  ? level === "all"
                    ? "text-zinc-200 bg-zinc-700"
                    : ""
                  : "text-dim hover:text-text"
              }`}
              style={
                zoomFilter === level && level !== "all"
                  ? {
                      color: ZOOM_LABELS[level].color,
                      background: ZOOM_LABELS[level].color + "20",
                    }
                  : undefined
              }
            >
              {level === "all" ? "All" : ZOOM_LABELS[level].label}
            </button>
          ))}
        </div>
      </div>

      {/* Main split */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Foraging feed (agents' output streaming in) */}
        <div className="w-64 shrink-0 border-r border-border flex flex-col">
          <div className="px-3 py-1.5 border-b border-border/50 text-[9px] text-dim uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot" />
            Agent Foraging Feed
            <span className="text-zinc-600 ml-auto normal-case">
              {foraging.length} items
            </span>
          </div>
          <div className="flex-1 overflow-y-auto space-y-0.5 px-1.5 py-1">
            {feedLoading && foraging.length === 0 && (
              <div className="px-2 py-4 text-[10px] text-dim text-center animate-pulse">
                Loading feed...
              </div>
            )}
            {!feedLoading && foraging.length === 0 && (
              <div className="px-2 py-4 text-[10px] text-dim text-center">
                No pipeline activity yet. Run agents to populate.
              </div>
            )}
            {foraging.map((item) => {
              const style = TYPE_STYLES[item.type];
              return (
                <div
                  key={item.id}
                  className="group px-2 py-1.5 rounded transition hover:bg-white/[0.03] cursor-pointer"
                  onClick={() => addToCanvas(item.id)}
                  title="Click to add to canvas"
                >
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3.5 h-3.5 rounded text-[8px] font-bold flex items-center justify-center shrink-0"
                      style={{
                        background: style.color + "22",
                        color: style.color,
                      }}
                    >
                      {style.icon}
                    </span>
                    <span
                      className="text-[9px] font-bold"
                      style={{ color: item.agentColor }}
                    >
                      {item.agent}
                    </span>
                    <span className="text-[8px] text-zinc-600">
                      {item.timestamp}
                    </span>
                    <span className="text-[8px] text-dim opacity-0 group-hover:opacity-100 ml-auto transition">
                      + canvas
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-400 mt-0.5 leading-snug line-clamp-3">
                    {item.content}
                  </div>
                  {item.meta && (
                    <div className="text-[8px] text-zinc-600 mt-0.5">
                      {item.meta}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Sensemaking canvas */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Canvas area */}
          <div className="flex-1 relative overflow-auto bg-[#08080d]">
            {/* Grid background */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              <defs>
                <pattern
                  id="grid"
                  width="40"
                  height="40"
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d="M 40 0 L 0 0 0 40"
                    fill="none"
                    stroke="#1e1e2e"
                    strokeWidth="0.5"
                  />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>

            {/* Canvas cards */}
            {filteredCanvas.map((card) => {
              const levelStyle = ZOOM_LABELS[card.level];
              return (
                <div
                  key={card.id}
                  className="absolute group cursor-move"
                  style={{
                    left: card.x,
                    top: card.y,
                    width: card.width,
                  }}
                  onMouseDown={(e) => {
                    if (
                      (e.target as HTMLElement).tagName === "BUTTON"
                    )
                      return;
                    setDragging(card.id);
                    const startX = e.clientX - card.x;
                    const startY = e.clientY - card.y;
                    const onMove = (ev: MouseEvent) => {
                      setCanvas((prev) =>
                        prev.map((c) =>
                          c.id === card.id
                            ? {
                                ...c,
                                x: ev.clientX - startX,
                                y: ev.clientY - startY,
                              }
                            : c
                        )
                      );
                    };
                    const onUp = () => {
                      setDragging(null);
                      window.removeEventListener("mousemove", onMove);
                      window.removeEventListener("mouseup", onUp);
                    };
                    window.addEventListener("mousemove", onMove);
                    window.addEventListener("mouseup", onUp);
                  }}
                >
                  <div
                    className={`px-2.5 py-2 rounded-lg border transition ${
                      dragging === card.id
                        ? "shadow-lg shadow-black/50 scale-[1.02]"
                        : ""
                    }`}
                    style={{
                      background: "#12121a",
                      borderColor: card.color + "40",
                    }}
                  >
                    {/* Level badge + remove */}
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className="text-[8px] uppercase tracking-wider font-bold"
                        style={{ color: levelStyle.color }}
                      >
                        {levelStyle.label}
                      </span>
                      <button
                        onClick={() => removeCard(card.id)}
                        className="text-[10px] text-zinc-600 hover:text-red-400 transition opacity-0 group-hover:opacity-100 cursor-pointer"
                      >
                        x
                      </button>
                    </div>
                    <div className="text-[10px] text-zinc-300 leading-snug">
                      {card.content}
                    </div>
                    {card.linkedForaging && (
                      <div className="text-[8px] text-zinc-600 mt-1">
                        from foraging feed
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Empty state */}
            {filteredCanvas.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-[10px] text-zinc-600 text-center">
                  No cards at this zoom level.
                  <br />
                  Click items in the foraging feed to add them.
                </div>
              </div>
            )}
          </div>

          {/* Bottom: Add custom insight */}
          <div className="px-3 py-2 border-t border-border flex items-center gap-2">
            <select
              value={newCardLevel}
              onChange={(e) =>
                setNewCardLevel(e.target.value as ZoomLevel)
              }
              className="bg-zinc-900 border border-border rounded px-1.5 py-1 text-[10px] text-dim"
            >
              <option value="paper">Paper</option>
              <option value="cluster">Cluster</option>
              <option value="thesis">Thesis</option>
            </select>
            <input
              type="text"
              value={newCardText}
              onChange={(e) => setNewCardText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addCustomCard()}
              placeholder="Add your own insight to the canvas..."
              className="flex-1 bg-zinc-900 border border-border rounded px-2.5 py-1 text-[10px] text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-accent/50"
            />
            <button
              onClick={addCustomCard}
              disabled={!newCardText.trim()}
              className="px-3 py-1 text-[10px] rounded bg-accent/20 text-accent hover:bg-accent/30 transition cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
