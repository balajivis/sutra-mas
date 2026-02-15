"use client";

import { useState, useEffect, useCallback } from "react";
import { PipelineStatus } from "./PipelineStatus";
import { CorpusCards } from "./CorpusCards";
import { TopPapers } from "./TopPapers";
import { AnalysisCard, LostCanaryCard } from "./AnalysisCard";
import { RelevanceCard } from "./RelevanceCard";
import { ScoutCard } from "./ScoutCard";
import { ExperimentationCard } from "./ExperimentationCard";

interface Props {
  dashboardUrl: string;
}

export function StatusDashboard({ dashboardUrl }: Props) {
  const [stats, setStats] = useState<Record<string, number>>({});

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
    loadStats();
    const iv = setInterval(loadStats, 10_000);
    return () => clearInterval(iv);
  }, [loadStats]);

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-base font-bold tracking-widest text-accent uppercase">
            Sutra Research Desk
          </h1>
          <p className="text-xs text-dim flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot" />
            Live dashboard &mdash;{" "}
            {new Date().toLocaleDateString("en-CA")}{" "}
            {new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
          </p>
        </div>
        <a
          href={dashboardUrl}
          className="text-xs text-dim hover:text-accent transition border border-border rounded px-3 py-1.5"
        >
          Assembly Line (Python)
        </a>
      </header>

      {/* Stats strip — filtered to relevance 4-5 */}
      <div className="px-6 py-3 border-b border-border flex items-center gap-8 text-center">
        <StatItem value={stats.total || 0} label="Total" color="#d4d4d8" />
        <StatItem value={stats.analyzed || 0} label="Analyzed" color="#34d399" />
        <StatItem value={stats.pattern_count || 0} label="Patterns" color="#22d3ee" />
        <StatItem value={stats.classical || 0} label="Classical" color="#fbbf24" />
        <StatItem value={stats.modern || 0} label="Modern" color="#60a5fa" />
        <span className="text-[9px] text-dim/60 ml-auto">relevance 4-5 only</span>
      </div>

      {/* Pipeline */}
      <div className="px-6 py-4 border-b border-border">
        <h2 className="text-xs uppercase tracking-widest text-dim mb-4">
          Assembly Line &mdash; 6 Stations
        </h2>
        <PipelineStatus />
      </div>

      {/* Era + Citation cards */}
      <div className="px-6 py-4 border-b border-border">
        <CorpusCards />
      </div>

      {/* Analysis + Lost Canary */}
      <div className="px-6 py-4 border-b border-border grid grid-cols-1 lg:grid-cols-2 gap-3">
        <AnalysisCard />
        <LostCanaryCard />
      </div>

      {/* Scout + Feasibility + Experimentation Candidates */}
      <div className="px-6 py-4 border-b border-border grid grid-cols-1 xl:grid-cols-2 gap-3">
        <ScoutCard />
        <ExperimentationCard />
      </div>

      {/* Relevance + MAS Branches */}
      <div className="px-6 py-4 border-b border-border">
        <RelevanceCard />
      </div>

      {/* Top Papers */}
      <div className="px-6 py-4">
        <TopPapers />
      </div>
    </div>
  );
}

function StatItem({
  value,
  label,
  color,
}: {
  value: number;
  label: string;
  color: string;
}) {
  return (
    <div className="min-w-[60px]">
      <div className="text-2xl font-bold tabular-nums" style={{ color }}>
        {value.toLocaleString()}
      </div>
      <div className="text-[10px] text-dim uppercase tracking-wider">{label}</div>
    </div>
  );
}
