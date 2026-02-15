"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { ClusterMap } from "./ClusterMap";
import { ClusterInsightPanel } from "./ClusterInsightPanel";
import { SearchPanel } from "./SearchPanel";
import type { ClusterPoint, ClusterMeta } from "@/lib/types";

export function ResearchDesk() {
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [clusterPoints, setClusterPoints] = useState<ClusterPoint[]>([]);
  const [clusterMeta, setClusterMeta] = useState<ClusterMeta[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [clusterLoading, setClusterLoading] = useState(true);

  const loadClusters = useCallback(async () => {
    try {
      setClusterLoading(true);
      const res = await fetch("/api/clusters");
      const data = await res.json();
      setClusterPoints(data.points || []);
      setClusterMeta(data.clusters || []);
    } catch {
      // Clusters not ready yet
    } finally {
      setClusterLoading(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch("/api/patterns");
      const data = await res.json();
      setStats(data.stats || {});
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadClusters();
    loadStats();
    const interval = setInterval(loadClusters, 120_000);
    return () => clearInterval(interval);
  }, [loadClusters, loadStats]);

  const selectedMeta = clusterMeta.find((c) => c.cluster_id === selectedCluster);
  const selectedPapers = clusterPoints.filter((p) => p.cluster_id === selectedCluster);

  return (
    <div className="flex flex-col h-[calc(100vh-2.5rem)] overflow-hidden">
      {/* Header */}
      <header className="px-5 py-2 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-sm font-bold tracking-widest text-accent uppercase">
            Deep Dive
          </h1>
          <p className="text-[10px] text-dim">
            {stats.total ? `${stats.total.toLocaleString()} papers` : ""}{" "}
            &middot; {clusterMeta.length} clusters &middot;{" "}
            {stats.classical?.toLocaleString() || 0} classical &middot;{" "}
            {stats.modern?.toLocaleString() || 0} modern
          </p>
        </div>
        <button
          className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
          onClick={loadClusters}
        >
          &#x21BB; Refresh
        </button>
      </header>

      {/* Main area: cluster map + side panel */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Cluster map — takes all remaining space */}
        <div className="flex-1 flex flex-col p-3 min-w-0 min-h-0">
          <div className="text-[10px] text-dim uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>
              Knowledge Map
              {clusterPoints.length > 0 && (
                <span className="text-zinc-600 ml-2">
                  {clusterPoints.length} papers
                </span>
              )}
            </span>
            {selectedCluster !== null && (
              <button
                className="text-accent hover:underline cursor-pointer"
                onClick={() => setSelectedCluster(null)}
              >
                clear selection
              </button>
            )}
          </div>
          {clusterLoading && clusterPoints.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-dim text-xs">
              Loading cluster data...
            </div>
          ) : (
            <ClusterMap
              points={clusterPoints}
              clusters={clusterMeta}
              selectedCluster={selectedCluster}
              onSelectCluster={setSelectedCluster}
            />
          )}
        </div>

        {/* Right: Cluster insight or Search */}
        <div className="w-[420px] shrink-0 border-l border-border flex flex-col min-h-0">
          {selectedCluster !== null ? (
            <ClusterInsightPanel
              clusterId={selectedCluster}
              onClose={() => setSelectedCluster(null)}
            />
          ) : (
            <SearchPanel />
          )}
        </div>
      </div>

      {/* Detail panel (selected cluster) */}
      {selectedCluster !== null && selectedPapers.length > 0 && (
        <div className="border-t border-border px-5 py-3 max-h-60 overflow-y-auto bg-card shrink-0">
          <div className="flex items-center gap-3 mb-2">
            <Link
              href={`/papers?cluster=${selectedCluster}&clusterLabel=${encodeURIComponent(selectedMeta?.label || `Cluster ${selectedCluster}`)}`}
              className="text-xs font-bold text-accent hover:text-text transition"
            >
              {selectedMeta?.label || `Cluster ${selectedCluster}`} &#x2197;
            </Link>
            <span className="text-[10px] text-dim">
              {selectedPapers.length} papers
            </span>
            {selectedMeta?.description && (
              <span className="text-[10px] text-zinc-500 italic">
                {selectedMeta.description}
              </span>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {selectedPapers.slice(0, 12).map((p) => (
              <Link
                key={p.paper_id}
                href={`/paper/${p.paper_id}`}
                className="border border-border rounded px-2 py-1.5 text-[11px] hover:border-accent/30 transition block"
              >
                <div className="text-zinc-200 font-medium truncate">
                  {p.title}
                </div>
                <div className="flex gap-2 text-[10px] text-zinc-500 mt-0.5">
                  <span>{p.year || "?"}</span>
                  <span>{p.citations} cites</span>
                  {p.pattern && p.pattern !== "none" && (
                    <span className="text-accent/70">{p.pattern}</span>
                  )}
                  {p.is_classical && (
                    <span className="text-amber-400/70">classical</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
          {selectedPapers.length > 12 && (
            <Link
              href={`/papers?cluster=${selectedCluster}&clusterLabel=${encodeURIComponent(selectedMeta?.label || `Cluster ${selectedCluster}`)}`}
              className="text-[10px] text-accent hover:text-text mt-2 inline-block transition"
            >
              View all {selectedPapers.length} papers &#x2192;
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
