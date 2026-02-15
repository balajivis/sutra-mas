"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface ClusterDetail {
  cluster: {
    cluster_id: number;
    label: string;
    description: string | null;
    top_concepts: string[] | null;
    top_patterns: string[] | null;
    paper_count: number;
  };
  topPapers: {
    id: number;
    title: string;
    year: number | null;
    citations: number;
    abstract: string | null;
    pattern: string | null;
    contribution: string | null;
    distance: string;
  }[];
  insight: string | null;
  landmarkPaper: {
    id: number;
    title: string;
    year: number | null;
    citations: number;
    abstract: string | null;
    pattern: string | null;
    refCount: number;
  } | null;
  surveyPaper: {
    id: number;
    title: string;
    year: number | null;
    citations: number;
    abstract: string | null;
    pattern: string | null;
    refCount: number;
  } | null;
}

export function ClusterInsightPanel({
  clusterId,
  onClose,
}: {
  clusterId: number;
  onClose: () => void;
}) {
  const [data, setData] = useState<ClusterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    setData(null);

    fetch(`/api/cluster/${clusterId}`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((d) => setData(d))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [clusterId]);

  // Skeleton loading state
  if (loading) {
    return (
      <div className="flex flex-col h-full px-4 py-3 space-y-4">
        <div className="flex items-center justify-between">
          <div className="h-5 w-40 bg-zinc-800 rounded animate-pulse" />
          <button
            onClick={onClose}
            className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
          >
            Back to Search
          </button>
        </div>
        <div className="h-16 bg-zinc-800/50 rounded animate-pulse" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-zinc-800/30 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // Error or missing data
  if (error || !data) {
    return (
      <div className="flex flex-col h-full px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-zinc-200">
            Cluster {clusterId}
          </span>
          <button
            onClick={onClose}
            className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
          >
            Back to Search
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center text-dim text-xs">
          Insight unavailable for this cluster.
        </div>
      </div>
    );
  }

  const { cluster, topPapers, insight, landmarkPaper, surveyPaper } = data;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-white leading-snug">
              {cluster.label}
            </h2>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-zinc-400">
                {cluster.paper_count} papers
              </span>
              <Link
                href={`/cluster/${cluster.cluster_id}`}
                className="text-[11px] text-accent hover:underline"
              >
                Full details
              </Link>
              <Link
                href={`/lineage?cluster_id=${cluster.cluster_id}`}
                className="text-[11px] text-zinc-400 hover:text-accent hover:underline"
              >
                Citation lineage
              </Link>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[11px] text-zinc-400 hover:text-accent transition cursor-pointer shrink-0 mt-0.5"
          >
            Back to Search
          </button>
        </div>
        {cluster.description && (
          <p className="text-[11px] text-zinc-300 mt-1.5 leading-relaxed">
            {cluster.description}
          </p>
        )}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* LLM Insight */}
        {insight && (
          <div className="border-l-2 border-accent pl-3 py-1.5">
            <div className="text-[10px] text-accent uppercase tracking-wider mb-1.5 font-semibold">
              Field Review
            </div>
            <div className="space-y-2">
              {insight.split(/\n\n+/).map((para, i) => (
                <p key={i} className="text-[12px] text-zinc-200 leading-relaxed">
                  {para}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Landmark + Survey Papers */}
        {(landmarkPaper || surveyPaper) && (
          <div className="space-y-2">
            {landmarkPaper && (
              <div>
                <div className="text-[10px] text-amber-400 uppercase tracking-wider mb-1.5 font-semibold">
                  Landmark Paper
                  <span className="text-zinc-500 normal-case font-normal ml-1">most cited</span>
                </div>
                <Link
                  href={`/paper/${landmarkPaper.id}`}
                  className="block border border-amber-500/30 rounded-lg px-3 py-2.5 hover:border-amber-400/50 transition bg-amber-500/5"
                >
                  <div className="text-[12px] text-white font-medium leading-snug">
                    {landmarkPaper.title}
                  </div>
                  <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-zinc-300 mt-1">
                    <span>{landmarkPaper.year || "?"}</span>
                    <span className="text-amber-400 font-semibold">
                      {landmarkPaper.citations.toLocaleString()} cites
                    </span>
                    {landmarkPaper.pattern && landmarkPaper.pattern !== "none" && (
                      <span className="text-accent">{landmarkPaper.pattern}</span>
                    )}
                  </div>
                </Link>
              </div>
            )}
            {surveyPaper && (
              <div>
                <div className="text-[10px] text-blue-400 uppercase tracking-wider mb-1.5 font-semibold">
                  Survey Paper
                  <span className="text-zinc-500 normal-case font-normal ml-1">{surveyPaper.refCount} references</span>
                </div>
                <Link
                  href={`/paper/${surveyPaper.id}`}
                  className="block border border-blue-500/30 rounded-lg px-3 py-2.5 hover:border-blue-400/50 transition bg-blue-500/5"
                >
                  <div className="text-[12px] text-white font-medium leading-snug">
                    {surveyPaper.title}
                  </div>
                  <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-zinc-300 mt-1">
                    <span>{surveyPaper.year || "?"}</span>
                    <span className="text-blue-400 font-semibold">
                      {surveyPaper.citations.toLocaleString()} cites
                    </span>
                    {surveyPaper.pattern && surveyPaper.pattern !== "none" && (
                      <span className="text-accent">{surveyPaper.pattern}</span>
                    )}
                  </div>
                </Link>
              </div>
            )}
          </div>
        )}

        {/* Top Papers */}
        {topPapers.length > 0 && (
          <div>
            <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-2 font-semibold">
              Central Papers
            </div>
            <div className="space-y-2">
              {topPapers.slice(0, 3).map((p) => (
                <Link
                  key={p.id}
                  href={`/paper/${p.id}`}
                  className="block border border-zinc-700 rounded-lg px-3 py-2.5 hover:border-accent/50 transition bg-zinc-900/50"
                >
                  <div className="text-[12px] text-white font-medium leading-snug">
                    {p.title}
                  </div>
                  <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-zinc-300 mt-1">
                    <span>{p.year || "?"}</span>
                    <span>{p.citations.toLocaleString()} cites</span>
                    {p.pattern && p.pattern !== "none" && (
                      <span className="text-accent">{p.pattern}</span>
                    )}
                  </div>
                  {p.abstract && (
                    <div className="text-[11px] text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
                      {p.abstract}
                    </div>
                  )}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Concept & Pattern pills */}
        {((cluster.top_concepts && cluster.top_concepts.length > 0) ||
          (cluster.top_patterns && cluster.top_patterns.length > 0)) && (
          <div>
            {cluster.top_concepts && cluster.top_concepts.length > 0 && (
              <div className="mb-2">
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1.5 font-semibold">
                  Concepts
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {cluster.top_concepts.map((c) => (
                    <span
                      key={c}
                      className="text-[10px] px-2 py-1 rounded-full bg-zinc-800 text-zinc-200 border border-zinc-700"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {cluster.top_patterns && cluster.top_patterns.length > 0 && (
              <div>
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1.5 font-semibold">
                  Patterns
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {cluster.top_patterns.map((p) => (
                    <span
                      key={p}
                      className="text-[10px] px-2 py-1 rounded-full bg-accent/15 text-accent border border-accent/30"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
