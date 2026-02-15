"use client";

import { useState, useCallback } from "react";

interface SearchResult {
  id: number;
  title: string;
  year: number | null;
  venue: string | null;
  citations: number;
  pattern: string;
  summary: string;
  classical: boolean;
  has_code: boolean;
  repo_url: string | null;
  grounding: string | null;
  missing: string | null;
  score: number;
  link: string;
}

export function SearchPanel() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState("");

  const search = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&top=20`);
      const data = await res.json();
      setResults(data.results || []);
      setSource(data.source || "");
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  return (
    <div className="flex flex-col h-full">
      {/* Search input */}
      <div className="p-3 border-b border-border">
        <div className="flex gap-2">
          <input
            className="flex-1 bg-[#0a0a0f] border border-border rounded-md px-3 py-2 text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:border-accent/50 transition"
            placeholder="Search papers..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button
            onClick={search}
            disabled={loading || !query.trim()}
            className="bg-accent/15 border border-accent/30 rounded-md px-3 py-1 text-xs text-accent hover:bg-accent/25 disabled:opacity-30 transition cursor-pointer"
          >
            {loading ? "..." : "Search"}
          </button>
        </div>
        {source && results.length > 0 && (
          <p className="text-[9px] text-zinc-600 mt-1">
            {results.length} results via {source}
          </p>
        )}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {results.length === 0 && !loading && (
          <div className="text-center text-dim text-xs py-8">
            <p>Search the corpus by keyword</p>
            <div className="space-y-1 text-zinc-600 mt-2">
              <p>blackboard architecture</p>
              <p>contract net protocol</p>
              <p>multi-agent coordination</p>
            </div>
          </div>
        )}

        {results.map((r) => (
          <a
            key={r.id}
            href={r.link}
            target="_blank"
            rel="noopener noreferrer"
            className="block border border-border/50 rounded px-2.5 py-2 hover:border-accent/30 hover:bg-zinc-900/30 transition"
          >
            <div className="text-[11px] text-zinc-200 leading-snug">
              {r.title}
            </div>
            <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-zinc-500 mt-1">
              <span>{r.year || "?"}</span>
              <span>{r.citations.toLocaleString()} cites</span>
              {r.venue && <span className="truncate max-w-[120px]">{r.venue}</span>}
              {r.pattern && r.pattern !== "none" && (
                <span className="text-accent/70">{r.pattern}</span>
              )}
              {r.classical && (
                <span className="text-amber-400/70">classical</span>
              )}
              {r.grounding && r.grounding !== "none" && (
                <span className="text-purple-400/70">{r.grounding}</span>
              )}
              {r.has_code && (
                <span className="text-emerald-400/70">has code</span>
              )}
            </div>
            {r.summary && (
              <div className="text-[10px] text-zinc-600 mt-1 line-clamp-2 leading-relaxed">
                {r.summary}
              </div>
            )}
            {r.missing && (
              <div className="text-[10px] text-amber-400/50 mt-0.5">
                Missing: {r.missing}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
