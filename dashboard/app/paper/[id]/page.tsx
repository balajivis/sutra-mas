"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { CitationGraph } from "@/components/CitationGraph";

type PaperTab = "analysis" | "citations";

interface PaperLink {
  label: string;
  url: string;
}

interface Analysis {
  key_contribution_summary?: string;
  unique_contribution?: string;
  methodology?: string;
  key_results?: string;
  coordination_pattern?: string;
  theoretical_grounding?: string;
  classical_concepts?: string[];
  modern_mapping?: string[];
  classical_concepts_missing?: string;
  rosetta_entry?: Record<string, string>;
  failure_modes_addressed?: string[];
  sections_to_embed?: { heading: string; summary: string; reason: string }[];
}

interface Paper {
  id: number;
  title: string;
  year: number | null;
  venue: string | null;
  doi: string | null;
  arxiv_id: string | null;
  citations: number;
  authors: string | null;
  abstract: string | null;
  source: string | null;
  is_classical: boolean;
  pipeline_status: string;
  relevance_score: number | null;
  relevance_rationale: string | null;
  mas_branch: string | null;
  analysis: Analysis | null;
  modernity_score: number | null;
  has_code: boolean;
  repo_url: string | null;
  reproduction_feasibility: number | null;
  experiment_notes: string | null;
  links: PaperLink[];
}

interface SimilarPaper {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  is_classical: boolean;
  relevance: number | null;
  pattern: string | null;
  cluster_label: string | null;
  same_cluster: boolean;
  score: number;
  snippet: string | null;
}

interface ClusterInfo {
  id: number;
  label: string;
  description: string | null;
  paper_count: number;
}

interface SimilarData {
  cluster: ClusterInfo | null;
  similar: SimilarPaper[];
  method: string | null;
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

function Tag({ color, label }: { color: string; label: string }) {
  return (
    <span
      className="inline-block text-[11px] px-2 py-0.5 rounded"
      style={{ background: `${color}18`, color }}
    >
      {label}
    </span>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-border rounded-lg p-4">
      <h3 className="text-xs font-bold uppercase tracking-widest text-accent mb-3 pb-2 border-b border-border">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function PaperDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [paper, setPaper] = useState<Paper | null>(null);
  const [similar, setSimilar] = useState<SimilarData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<PaperTab>("analysis");

  useEffect(() => {
    fetch(`/api/paper/${id}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setError(data.error);
        } else {
          setPaper(data);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    fetch(`/api/paper/${id}/similar`)
      .then((r) => r.json())
      .then((data) => {
        if (!data.error) setSimilar(data);
      })
      .catch(() => {});
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-dim text-sm">{error || "Paper not found"}</p>
      </div>
    );
  }

  const a = paper.analysis;

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link
            href={`/lineage?paper_id=${id}&depth=2`}
            className="text-xs px-3 py-1.5 rounded border border-border text-dim hover:text-accent hover:border-accent/30 transition"
          >
            Citation Lineage
          </Link>
        </div>
        <div className="flex items-center gap-2">
          {paper.links.map((l) => (
            <a
              key={l.label}
              href={l.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs px-3 py-1.5 rounded border border-accent/30 text-accent hover:text-text transition"
            >
              {l.label} &#x2197;
            </a>
          ))}
        </div>
      </header>

      {/* Paper title + meta */}
      <div className="px-6 py-5 border-b border-border">
        <div className="max-w-4xl">
          <h1 className="text-lg font-semibold text-text leading-snug mb-3">
            {paper.title}
          </h1>
          <div className="flex items-center gap-3 flex-wrap text-sm">
            <span className="text-dim tabular-nums">{paper.year || "?"}</span>
            <span className="text-dim tabular-nums">
              {paper.citations.toLocaleString()} citations
            </span>
            {paper.venue && (
              <span className="text-dim">{paper.venue}</span>
            )}
            {paper.is_classical && <Tag color="#fbbf24" label="classical" />}
            {paper.mas_branch && (
              <Tag color="#60a5fa" label={paper.mas_branch} />
            )}
            {a?.coordination_pattern &&
              a.coordination_pattern !== "none" &&
              a.coordination_pattern !== "null" && (
                <Tag
                  color={
                    PATTERN_COLORS[a.coordination_pattern] || "#71717a"
                  }
                  label={a.coordination_pattern}
                />
              )}
            {a?.theoretical_grounding &&
              a.theoretical_grounding !== "none" && (
                <Tag color="#a78bfa" label={a.theoretical_grounding} />
              )}
            {paper.has_code && <Tag color="#22d3ee" label="has code" />}
            {paper.relevance_score != null && paper.relevance_score > 0 && (
              <Tag color="#34d399" label={`R${paper.relevance_score}/5`} />
            )}
            {paper.modernity_score != null && (
              <span className="text-xs text-dim">
                Modernity: {(paper.modernity_score as number).toFixed(4)}
              </span>
            )}
            <span className="text-xs text-dim/50">
              pipeline: {paper.pipeline_status}
            </span>
          </div>
          {paper.authors && (
            <p className="text-xs text-dim mt-2 leading-relaxed">
              {paper.authors}
            </p>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-border px-6">
        {(["analysis", "citations"] as PaperTab[]).map((tab) => (
          <button
            key={tab}
            className={`py-2 px-4 text-xs transition cursor-pointer ${
              activeTab === tab
                ? "text-accent border-b-2 border-accent"
                : "text-dim hover:text-zinc-300"
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "analysis" ? "Analysis" : "Citation Network"}
          </button>
        ))}
      </div>

      {/* Citation Graph tab */}
      {activeTab === "citations" && (
        <div className="flex-1 min-h-[500px]">
          <CitationGraph paperId={paper.id} />
        </div>
      )}

      {/* Body — two column layout */}
      {activeTab === "analysis" && <div className="flex-1 px-6 py-5 overflow-auto">
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-6">
        <div className="space-y-4 min-w-0">
          {/* Agent 2: Relevance */}
          {paper.relevance_rationale && (
            <Section title="Agent 2 &mdash; Relevance Filter">
              <p className="text-sm text-text leading-relaxed">
                {paper.relevance_rationale}
              </p>
            </Section>
          )}

          {/* Agent 3: Key Contribution Summary */}
          {a?.key_contribution_summary && (
            <Section title="Agent 3 &mdash; Key Contribution">
              <p className="text-sm text-text leading-relaxed">
                {a.key_contribution_summary}
              </p>
            </Section>
          )}

          {/* Agent 3: Methodology + Key Results side by side */}
          {(a?.methodology || a?.key_results) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {a?.methodology && (
                <Section title="Methodology">
                  <p className="text-sm text-text leading-relaxed">
                    {a.methodology}
                  </p>
                </Section>
              )}
              {a?.key_results && (
                <Section title="Key Results">
                  <p className="text-sm text-text leading-relaxed">
                    {a.key_results}
                  </p>
                </Section>
              )}
            </div>
          )}

          {/* Agent 3: Unique Contribution */}
          {a?.unique_contribution && (
            <Section title="Unique Contribution">
              <p className="text-sm text-text leading-relaxed">
                {a.unique_contribution}
              </p>
            </Section>
          )}

          {/* Classical Concepts + Modern Mapping side by side */}
          {((a?.classical_concepts && a.classical_concepts.length > 0) ||
            (a?.modern_mapping && a.modern_mapping.length > 0)) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {a?.classical_concepts && a.classical_concepts.length > 0 && (
                <Section title="Classical Concepts Used">
                  <div className="flex flex-wrap gap-1.5">
                    {a.classical_concepts.map((c, i) => (
                      <Tag key={i} color="#fbbf24" label={c} />
                    ))}
                  </div>
                </Section>
              )}
              {a?.modern_mapping && a.modern_mapping.length > 0 && (
                <Section title="Modern LLM Mapping">
                  <ul className="space-y-1.5">
                    {a.modern_mapping.map((m, i) => (
                      <li key={i} className="text-xs text-text leading-relaxed">
                        <span className="text-accent mr-1">&rarr;</span> {m}
                      </li>
                    ))}
                  </ul>
                </Section>
              )}
            </div>
          )}

          {/* Rosetta Stone */}
          {a?.rosetta_entry &&
            Object.keys(a.rosetta_entry).length > 0 && (
              <Section title="Rosetta Stone &mdash; Classical to Modern">
                <div className="space-y-2">
                  {Object.entries(a.rosetta_entry).map(
                    ([classical, modern]) => (
                      <div
                        key={classical}
                        className="grid grid-cols-[1fr_auto_1fr] gap-3 items-start"
                      >
                        <span className="text-xs text-amber-400 leading-relaxed">
                          {classical}
                        </span>
                        <span className="text-xs text-dim">&rarr;</span>
                        <span className="text-xs text-emerald-400 leading-relaxed">
                          {modern}
                        </span>
                      </div>
                    )
                  )}
                </div>
              </Section>
            )}

          {/* Missing Classical Concepts */}
          {a?.classical_concepts_missing &&
            a.classical_concepts_missing !== "none" &&
            a.classical_concepts_missing !== "None" && (
              <Section title="Missing Classical Concepts (Gap)">
                <p className="text-sm text-amber-400/90 leading-relaxed">
                  {a.classical_concepts_missing}
                </p>
              </Section>
            )}

          {/* Failure Modes Addressed */}
          {a?.failure_modes_addressed &&
            a.failure_modes_addressed.length > 0 && (
              <Section title="Failure Modes Addressed (Cemri et al.)">
                <div className="flex flex-wrap gap-1.5">
                  {a.failure_modes_addressed.map((f, i) => (
                    <Tag key={i} color="#f87171" label={f} />
                  ))}
                </div>
              </Section>
            )}

          {/* Abstract */}
          {paper.abstract && (
            <Section title="Abstract">
              <p className="text-sm text-dim leading-relaxed">
                {paper.abstract}
              </p>
            </Section>
          )}

          {/* Reproduction */}
          {(paper.has_code || paper.experiment_notes) && (
            <Section title="Reproduction (Agent 5 + 6)">
              <div className="space-y-2">
                {paper.repo_url && (
                  <p className="text-xs">
                    <span className="text-dim">Repo: </span>
                    <a
                      href={paper.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:text-text"
                    >
                      {paper.repo_url}
                    </a>
                  </p>
                )}
                {paper.reproduction_feasibility != null && (
                  <p className="text-xs text-dim">
                    Feasibility: {paper.reproduction_feasibility}/5
                  </p>
                )}
                {paper.experiment_notes && (
                  <pre className="text-xs text-dim bg-zinc-900 rounded p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {typeof paper.experiment_notes === "string"
                      ? paper.experiment_notes
                      : JSON.stringify(paper.experiment_notes, null, 2)}
                  </pre>
                )}
              </div>
            </Section>
          )}
        </div>

        {/* Right sidebar — Cluster + Similar Papers */}
        <aside className="space-y-4">
          {similar?.cluster && (
            <div className="border border-border rounded-lg p-4 sticky top-12">
              <h3 className="text-[10px] uppercase tracking-widest text-dim mb-2">
                Cluster
              </h3>
              <Link
                href={`/cluster/${similar.cluster.id}`}
                className="text-sm text-accent hover:text-text transition block mb-1"
              >
                {similar.cluster.label}
              </Link>
              {similar.cluster.description && (
                <p className="text-[11px] text-dim leading-relaxed mb-2">
                  {similar.cluster.description}
                </p>
              )}
              <span className="text-[10px] text-dim">
                {similar.cluster.paper_count} papers in cluster
              </span>

              {/* Similar papers list */}
              {similar.similar.length > 0 && (
                <div className="mt-4 pt-3 border-t border-border">
                  <h3 className="text-[10px] uppercase tracking-widest text-dim mb-2">
                    Similar Papers
                    <span className="ml-1 text-dim/40">
                      via {similar.method === "vector" ? "embedding" : "UMAP"}
                    </span>
                  </h3>
                  <div className="space-y-2.5">
                    {similar.similar.map((s) => (
                      <Link
                        key={s.id}
                        href={`/paper/${s.id}`}
                        className="block group"
                      >
                        <p className="text-[11px] text-text leading-snug group-hover:text-accent transition line-clamp-2">
                          {s.title}
                        </p>
                        {s.snippet && (
                          <p className="text-[10px] text-dim/60 leading-snug mt-0.5 line-clamp-2">
                            {s.snippet}
                          </p>
                        )}
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-dim tabular-nums">
                            {s.year || "?"}
                          </span>
                          <span className="text-[10px] text-dim tabular-nums">
                            {s.citations.toLocaleString()} cites
                          </span>
                          {s.same_cluster ? (
                            <span className="text-[9px] text-accent/60">same cluster</span>
                          ) : s.cluster_label ? (
                            <span className="text-[9px] text-dim/40">{s.cluster_label}</span>
                          ) : null}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {similar && !similar.cluster && (
            <div className="border border-border rounded-lg p-4">
              <p className="text-[11px] text-dim">
                Not yet clustered. Paper will be assigned to a cluster in the next clustering run.
              </p>
            </div>
          )}
        </aside>
        </div>
      </div>}
    </div>
  );
}
