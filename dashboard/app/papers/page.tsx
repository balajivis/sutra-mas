"use client";

import { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { PaperCard, type PaperCardData } from "@/components/PaperCard";

type SortKey = "citations" | "year" | "relevance" | "title";
type SortDir = "asc" | "desc";

interface ClusterOption { id: number; label: string; count: number }
interface EraOption { label: string; count: number }
interface CiteOption { label: string; count: number }
interface ScoreOption { score: number; label: string; count: number }
interface BranchOption { branch: string; count: number }

const SORT_OPTIONS: { key: SortKey; label: string; defaultDir: SortDir }[] = [
  { key: "citations", label: "Citations", defaultDir: "desc" },
  { key: "relevance", label: "Relevance", defaultDir: "desc" },
  { key: "year", label: "Year", defaultDir: "desc" },
  { key: "title", label: "Title", defaultDir: "asc" },
];

const CHEVRON_SVG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2371717a' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4'/%3E%3C/svg%3E")`;

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-dim uppercase tracking-wider whitespace-nowrap">
        {label}:
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs bg-card border border-border rounded px-2 py-1 text-text cursor-pointer focus:outline-none focus:border-accent transition appearance-none pr-6 max-w-[200px]"
        style={{
          backgroundImage: CHEVRON_SVG,
          backgroundRepeat: "no-repeat",
          backgroundPosition: "right 6px center",
        }}
      >
        {children}
      </select>
    </div>
  );
}

function PapersContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Current filter state from URL
  const pattern = searchParams.get("pattern") || "";
  const era = searchParams.get("era") || "";
  const citations = searchParams.get("citations") || "";
  const relevance = searchParams.get("relevance") || "";
  const branch = searchParams.get("branch") || "";
  const cluster = searchParams.get("cluster") || "";
  const clusterLabel = searchParams.get("clusterLabel") || "";
  const q = searchParams.get("q") || "";
  const hasCode = searchParams.get("has_code") || "";
  const feasibility = searchParams.get("feasibility") || "";
  const minRelevance = searchParams.get("min_relevance") || "";

  const [searchInput, setSearchInput] = useState(q);
  const [papers, setPapers] = useState<PaperCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>(q ? "relevance" : "citations");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Filter options (loaded once)
  const [clusters, setClusters] = useState<ClusterOption[]>([]);
  const [eras, setEras] = useState<EraOption[]>([]);
  const [cites, setCites] = useState<CiteOption[]>([]);
  const [scores, setScores] = useState<ScoreOption[]>([]);
  const [branches, setBranches] = useState<BranchOption[]>([]);

  const hasFilter = !!(pattern || era || citations || relevance || branch || cluster || q || hasCode || feasibility);

  // Load filter options on mount
  useEffect(() => {
    fetch("/api/clusters")
      .then((r) => r.json())
      .then((d) => {
        if (d.clusters) {
          setClusters(
            (d.clusters as { cluster_id: number; label: string; paper_count: number }[])
              .sort((a, b) => b.paper_count - a.paper_count)
              .map((c) => ({ id: c.cluster_id, label: c.label, count: c.paper_count }))
          );
        }
      })
      .catch(() => {});

    fetch("/api/corpus-stats")
      .then((r) => r.json())
      .then((d) => {
        if (d.eras) setEras(d.eras);
        if (d.citations) setCites(d.citations);
      })
      .catch(() => {});

    fetch("/api/relevance")
      .then((r) => r.json())
      .then((d) => {
        if (d.scores) setScores(d.scores);
        if (d.branches) setBranches(d.branches);
      })
      .catch(() => {});
  }, []);

  // Build URL from current filters, replacing one key
  const navigate = useCallback(
    (overrides: Record<string, string>) => {
      const current: Record<string, string> = {};
      if (q) current.q = q;
      if (pattern) current.pattern = pattern;
      if (era) current.era = era;
      if (citations) current.citations = citations;
      if (relevance) current.relevance = relevance;
      if (branch) current.branch = branch;
      if (hasCode) current.has_code = hasCode;
      if (feasibility) current.feasibility = feasibility;
      if (minRelevance) current.min_relevance = minRelevance;
      if (cluster) {
        current.cluster = cluster;
        if (clusterLabel) current.clusterLabel = clusterLabel;
      }

      // Apply overrides (empty string = remove)
      for (const [k, v] of Object.entries(overrides)) {
        if (v) {
          current[k] = v;
        } else {
          delete current[k];
          if (k === "cluster") delete current.clusterLabel;
        }
      }

      const params = new URLSearchParams(current);
      router.replace(`/papers?${params.toString()}`, { scroll: false });
    },
    [q, pattern, era, citations, relevance, branch, cluster, clusterLabel, hasCode, feasibility, minRelevance, router]
  );

  const load = useCallback(async () => {
    if (!hasFilter) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (pattern) params.set("pattern", pattern);
      if (era) params.set("era", era);
      if (citations) params.set("citations", citations);
      if (relevance) params.set("relevance", relevance);
      if (branch) params.set("branch", branch);
      if (cluster) params.set("cluster", cluster);
      if (hasCode) params.set("has_code", hasCode);
      if (feasibility) params.set("feasibility", feasibility);
      if (minRelevance) params.set("min_relevance", minRelevance);
      params.set("limit", "200");

      const res = await fetch(`/api/papers-filter?${params.toString()}`);
      const data = await res.json();
      setPapers(data.papers || []);
      setTotal(data.total || 0);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [hasFilter, q, pattern, era, citations, relevance, branch, cluster, hasCode, feasibility, minRelevance]);

  useEffect(() => {
    load();
  }, [load]);

  const sorted = useMemo(() => {
    const arr = [...papers];
    const dir = sortDir === "asc" ? 1 : -1;
    arr.sort((a, b) => {
      switch (sortKey) {
        case "citations":
          return ((a.citations || 0) - (b.citations || 0)) * dir;
        case "year":
          return ((a.year || 0) - (b.year || 0)) * dir;
        case "relevance":
          return ((a.relevance || 0) - (b.relevance || 0)) * dir;
        case "title":
          return (a.title || "").localeCompare(b.title || "") * dir;
        default:
          return 0;
      }
    });
    return arr;
  }, [papers, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      const opt = SORT_OPTIONS.find((o) => o.key === key);
      setSortKey(key);
      setSortDir(opt?.defaultDir || "desc");
    }
  };

  const handleClusterChange = (value: string) => {
    const overrides: Record<string, string> = { cluster: value };
    if (value) {
      const cl = clusters.find((c) => String(c.id) === value);
      if (cl) overrides.clusterLabel = cl.label;
    }
    navigate(overrides);
  };

  const SCORE_LABELS: Record<string, string> = {
    "1": "Off-topic",
    "2": "Tangential",
    "3": "Marginal",
    "4": "Relevant",
    "5": "Core MAS",
  };

  // Build display title from active filters
  const titleParts: string[] = [];
  if (q) titleParts.push(`"${q}"`);
  if (pattern) {
    const name = pattern.split(",")[0].replace(/_/g, " ");
    const vc = pattern.split(",").length - 1;
    titleParts.push(name + (vc > 0 ? ` +${vc}` : ""));
  }
  if (era) titleParts.push(`Era: ${era}`);
  if (citations) titleParts.push(`Cites: ${citations}`);
  if (relevance) titleParts.push(`R${relevance}: ${SCORE_LABELS[relevance] || ""}`);
  if (branch) titleParts.push(`Branch: ${branch}`);
  if (cluster) titleParts.push(`Cluster: ${clusterLabel || cluster}`);
  if (hasCode === "true") titleParts.push("Has Code");
  if (hasCode === "false") titleParts.push("No Code");
  if (feasibility) titleParts.push(`Feasibility: ${feasibility}`);
  const title = titleParts.length > 0 ? titleParts.join(" / ") : "Papers";

  // Count active filters
  const activeFilters = [q, pattern, era, citations, relevance, branch, cluster, hasCode, feasibility].filter(Boolean).length;

  return (
    <div className="flex flex-col">
      <header className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h1 className="text-base font-bold tracking-widest text-accent uppercase">
            {title}
          </h1>
          <p className="text-xs text-dim">
            {loading
              ? "Loading..."
              : `${total} paper${total !== 1 ? "s" : ""}`}
            {!relevance && !cluster && !loading && total > 0 && (
              <span className="ml-2 text-dim/60">
                (relevance &ge; 3 only)
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {activeFilters > 0 && (
            <Link
              href="/papers?relevance=5"
              onClick={(e) => {
                e.preventDefault();
                // Clear all filters -- go to a sensible default
                router.replace("/papers?relevance=5", { scroll: false });
              }}
              className="text-[10px] text-dim hover:text-accent transition"
            >
              Clear filters
            </Link>
          )}
          {null}
        </div>
      </header>

      {/* Sort + filter toolbar */}
      <div className="px-6 py-2 border-b border-border space-y-2">
        {/* Row 0: Search */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-dim uppercase tracking-wider mr-1 whitespace-nowrap">
            Search:
          </span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                navigate({ q: searchInput.trim() });
              }
              if (e.key === "Escape") {
                setSearchInput("");
                navigate({ q: "" });
              }
            }}
            placeholder="e.g. blackboard, BDI, contract net..."
            className="flex-1 max-w-md bg-card border border-border rounded px-2.5 py-1 text-xs text-text placeholder:text-dim/50 focus:outline-none focus:border-accent transition"
          />
          {q && (
            <button
              onClick={() => { setSearchInput(""); navigate({ q: "" }); }}
              className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
            >
              clear
            </button>
          )}
        </div>

        {/* Row 1: Sort */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-dim uppercase tracking-wider mr-1">
            Sort:
          </span>
          {SORT_OPTIONS.map((opt) => {
            const active = sortKey === opt.key;
            return (
              <button
                key={opt.key}
                onClick={() => handleSort(opt.key)}
                className={`text-xs px-2.5 py-1 rounded border transition cursor-pointer ${
                  active
                    ? "border-accent/50 text-accent bg-accent/10"
                    : "border-border text-dim hover:text-text hover:border-border"
                }`}
              >
                {opt.label}
                {active && (
                  <span className="ml-1 text-[10px]">
                    {sortDir === "desc" ? "\u2193" : "\u2191"}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Row 2: Filters */}
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-[10px] text-dim uppercase tracking-wider">
            Filter:
          </span>

          {/* Era */}
          {eras.length > 0 && (
            <FilterSelect label="Era" value={era} onChange={(v) => navigate({ era: v })}>
              <option value="">Any era</option>
              {eras.map((e) => (
                <option key={e.label} value={e.label}>
                  {e.label} ({e.count.toLocaleString()})
                </option>
              ))}
            </FilterSelect>
          )}

          {/* Citations */}
          {cites.length > 0 && (
            <FilterSelect label="Cites" value={citations} onChange={(v) => navigate({ citations: v })}>
              <option value="">Any</option>
              {cites.map((c) => (
                <option key={c.label} value={c.label}>
                  {c.label} ({c.count.toLocaleString()})
                </option>
              ))}
            </FilterSelect>
          )}

          {/* Relevance */}
          {scores.length > 0 && (
            <FilterSelect label="Relevance" value={relevance} onChange={(v) => navigate({ relevance: v })}>
              <option value="">Any</option>
              {scores.map((s) => (
                <option key={s.score} value={String(s.score)}>
                  {s.score}/5 {s.label} ({s.count.toLocaleString()})
                </option>
              ))}
            </FilterSelect>
          )}

          {/* Branch */}
          {branches.length > 0 && (
            <FilterSelect label="Branch" value={branch} onChange={(v) => navigate({ branch: v })}>
              <option value="">Any</option>
              {branches.map((b) => (
                <option key={b.branch} value={b.branch}>
                  {b.branch} ({b.count.toLocaleString()})
                </option>
              ))}
            </FilterSelect>
          )}

          {/* Cluster */}
          {clusters.length > 0 && (
            <FilterSelect label="Cluster" value={cluster} onChange={handleClusterChange}>
              <option value="">Any</option>
              {clusters.map((cl) => (
                <option key={cl.id} value={String(cl.id)}>
                  {cl.label} ({cl.count})
                </option>
              ))}
            </FilterSelect>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-3xl mx-auto space-y-2">
          {!hasFilter ? (
            <div className="text-center py-12 space-y-4">
              <p className="text-dim text-sm">
                Search or filter to browse papers
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {["blackboard", "contract net", "BDI architecture", "LLM agent coordination", "SharedPlans", "multi-agent debate", "stigmergy"].map((s) => (
                  <button
                    key={s}
                    onClick={() => { setSearchInput(s); navigate({ q: s }); }}
                    className="text-xs px-3 py-1.5 rounded-full border border-border text-dim hover:text-accent hover:border-accent/40 transition cursor-pointer"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : loading ? (
            <div className="text-dim text-xs text-center py-8">
              Loading papers...
            </div>
          ) : papers.length === 0 ? (
            <div className="text-dim text-xs text-center py-8">
              No papers found for this combination of filters.
            </div>
          ) : (
            sorted.map((p, i) => (
              <PaperCard key={p.id} paper={p} index={i + 1} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default function PapersPage() {
  return (
    <Suspense
      fallback={<div className="text-dim text-xs p-6">Loading...</div>}
    >
      <PapersContent />
    </Suspense>
  );
}
