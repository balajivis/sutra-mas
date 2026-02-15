"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface ClusterPaper {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  abstract: string | null;
  pattern: string | null;
  contribution: string | null;
  distance: string;
}

interface KeyPaper {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  abstract: string | null;
  pattern: string | null;
  refCount: number;
}

interface ClusterData {
  cluster: {
    cluster_id: number;
    label: string;
    description: string | null;
    top_concepts: string[] | null;
    top_patterns: string[] | null;
    paper_count: number;
  };
  topPapers: ClusterPaper[];
  insight: string | null;
  landmarkPaper: KeyPaper | null;
  surveyPaper: KeyPaper | null;
}

function Section({
  title,
  accent,
  children,
}: {
  title: string;
  accent?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-border rounded-lg p-5">
      <h3
        className="text-xs font-bold uppercase tracking-widest mb-3 pb-2 border-b border-border"
        style={{ color: accent || "var(--color-accent)" }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

function PaperCard({
  paper,
  badge,
  badgeColor,
  showAbstract,
}: {
  paper: { id: number; title: string; year: number | null; citations: number; abstract?: string | null; pattern?: string | null; contribution?: string | null };
  badge?: string;
  badgeColor?: string;
  showAbstract?: boolean;
}) {
  return (
    <Link
      href={`/paper/${paper.id}`}
      className="block border border-border rounded-lg px-4 py-3 hover:border-accent/40 transition bg-zinc-900/30"
    >
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-sm text-white font-medium leading-snug">
          {paper.title}
        </h4>
        {badge && (
          <span
            className="text-[10px] px-2 py-0.5 rounded-full shrink-0 font-semibold"
            style={{
              color: badgeColor || "#fbbf24",
              background: (badgeColor || "#fbbf24") + "15",
              border: `1px solid ${badgeColor || "#fbbf24"}40`,
            }}
          >
            {badge}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-zinc-400 mt-1.5">
        <span>{paper.year || "?"}</span>
        <span>{paper.citations.toLocaleString()} citations</span>
        {paper.pattern && paper.pattern !== "none" && (
          <span className="text-accent">{paper.pattern}</span>
        )}
      </div>
      {showAbstract && (paper.contribution || paper.abstract) && (
        <p className="text-xs text-zinc-400 mt-2 leading-relaxed line-clamp-3">
          {paper.contribution || paper.abstract}
        </p>
      )}
    </Link>
  );
}

export default function ClusterDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<ClusterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/cluster/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error("Cluster not found");
        return r.json();
      })
      .then((d) => setData(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-dim text-sm">{error || "Cluster not found"}</p>
        <Link href="/explore" className="text-xs text-accent hover:underline">
          Back to Explore
        </Link>
      </div>
    );
  }

  const { cluster, topPapers, insight, landmarkPaper, surveyPaper } = data;

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="px-6 py-5 border-b border-border">
        <div className="max-w-5xl">
          <div className="flex items-center gap-3 mb-2 text-xs text-zinc-500">
            <Link href="/explore" className="hover:text-accent transition">
              Explore
            </Link>
            <span>/</span>
            <span className="text-zinc-400">Cluster {cluster.cluster_id}</span>
          </div>
          <h1 className="text-xl font-bold text-white leading-snug mb-2">
            {cluster.label}
          </h1>
          <div className="flex items-center gap-4 text-sm text-zinc-400">
            <span>{cluster.paper_count} papers</span>
            <Link
              href={`/papers?cluster=${cluster.cluster_id}&clusterLabel=${encodeURIComponent(cluster.label)}`}
              className="text-accent hover:underline"
            >
              View all papers
            </Link>
          </div>
          {cluster.description && (
            <p className="text-sm text-zinc-300 mt-3 leading-relaxed max-w-3xl">
              {cluster.description}
            </p>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 px-6 py-6 overflow-auto">
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6 max-w-6xl">
          {/* Main column */}
          <div className="space-y-5 min-w-0">
            {/* Field Review */}
            {insight && (
              <Section title="Field Review">
                <div className="space-y-3">
                  {insight.split(/\n\n+/).map((para, i) => (
                    <p
                      key={i}
                      className="text-sm text-zinc-200 leading-relaxed"
                    >
                      {para}
                    </p>
                  ))}
                </div>
              </Section>
            )}

            {/* Landmark + Survey side by side */}
            {(landmarkPaper || surveyPaper) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {landmarkPaper && (
                  <Section title="Landmark Paper" accent="#fbbf24">
                    <p className="text-[11px] text-zinc-500 mb-3">
                      Most cited paper in this cluster
                    </p>
                    <PaperCard
                      paper={landmarkPaper}
                      badge={`${landmarkPaper.citations.toLocaleString()} cites`}
                      badgeColor="#fbbf24"
                      showAbstract
                    />
                  </Section>
                )}
                {surveyPaper && (
                  <Section title="Survey Paper" accent="#60a5fa">
                    <p className="text-[11px] text-zinc-500 mb-3">
                      Most comprehensive review ({surveyPaper.refCount}{" "}
                      references)
                    </p>
                    <PaperCard
                      paper={surveyPaper}
                      badge={`${surveyPaper.refCount} refs`}
                      badgeColor="#60a5fa"
                      showAbstract
                    />
                  </Section>
                )}
              </div>
            )}

            {/* Central Papers — all 5 */}
            {topPapers.length > 0 && (
              <Section title="Central Papers">
                <p className="text-[11px] text-zinc-500 mb-3">
                  Closest to the cluster centroid in UMAP space, ranked by
                  proximity with citation tie-breaking
                </p>
                <div className="space-y-3">
                  {topPapers.map((p, i) => (
                    <PaperCard
                      key={p.id}
                      paper={p}
                      badge={`#${i + 1}`}
                      badgeColor="#34d399"
                      showAbstract
                    />
                  ))}
                </div>
              </Section>
            )}
          </div>

          {/* Right sidebar */}
          <aside className="space-y-5">
            {/* Concepts */}
            {cluster.top_concepts && cluster.top_concepts.length > 0 && (
              <Section title="Concepts">
                <div className="flex flex-wrap gap-1.5">
                  {cluster.top_concepts.map((c) => (
                    <span
                      key={c}
                      className="text-[11px] px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-200 border border-zinc-700"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {/* Patterns */}
            {cluster.top_patterns && cluster.top_patterns.length > 0 && (
              <Section title="Coordination Patterns">
                <div className="flex flex-wrap gap-1.5">
                  {cluster.top_patterns.map((p) => (
                    <Link
                      key={p}
                      href={`/papers?pattern=${encodeURIComponent(p)}`}
                      className="text-[11px] px-2.5 py-1 rounded-full bg-accent/10 text-accent border border-accent/30 hover:bg-accent/20 transition"
                    >
                      {p}
                    </Link>
                  ))}
                </div>
              </Section>
            )}

            {/* Quick links */}
            <div className="border border-border rounded-lg p-4 space-y-2">
              <Link
                href={`/papers?cluster=${cluster.cluster_id}&clusterLabel=${encodeURIComponent(cluster.label)}`}
                className="block text-xs text-accent hover:underline"
              >
                Browse all {cluster.paper_count} papers
              </Link>
              <Link
                href="/explore"
                className="block text-xs text-zinc-400 hover:text-accent transition"
              >
                Back to Knowledge Map
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
