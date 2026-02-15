"use client";

import { useState, useCallback } from "react";

/* ---------- Types ---------- */

interface PaperInfo {
  s2Id: string;
  arxivId: string | null;
  doi: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  cites: number;
  authors: string[];
  keyContribution: string;
  inDb: boolean;
}

interface CitePaper {
  s2Id: string;
  arxivId: string | null;
  doi: string | null;
  title: string;
  year: number | null;
  cites: number;
  abstractSnippet: string | null;
  inDb: boolean;
}

type CiteTab = "references" | "citations";

/* ---------- Component ---------- */

export function SeedPanel() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [paper, setPaper] = useState<PaperInfo | null>(null);
  const [references, setReferences] = useState<CitePaper[]>([]);
  const [citations, setCitations] = useState<CitePaper[]>([]);

  const [selectedRefs, setSelectedRefs] = useState<Set<string>>(new Set());
  const [selectedCites, setSelectedCites] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<CiteTab>("references");

  const [enqueuing, setEnqueuing] = useState(false);
  const [enqueueResult, setEnqueueResult] = useState<string | null>(null);

  /* Resolve URL */
  const resolve = useCallback(async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setPaper(null);
    setReferences([]);
    setCitations([]);
    setSelectedRefs(new Set());
    setSelectedCites(new Set());
    setEnqueueResult(null);

    try {
      const res = await fetch("/api/seed/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || `HTTP ${res.status}`);
        return;
      }
      setPaper(data.paper);
      setReferences(data.references || []);
      setCitations(data.citations || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setLoading(false);
    }
  }, [url]);

  /* Toggle selection */
  const toggle = (s2Id: string, tab: CiteTab) => {
    const set = tab === "references" ? selectedRefs : selectedCites;
    const setter = tab === "references" ? setSelectedRefs : setSelectedCites;
    const next = new Set(set);
    if (next.has(s2Id)) next.delete(s2Id);
    else next.add(s2Id);
    setter(next);
  };

  const selectAll = (tab: CiteTab) => {
    const list = tab === "references" ? references : citations;
    const setter = tab === "references" ? setSelectedRefs : setSelectedCites;
    const notInDb = list.filter((p) => !p.inDb).map((p) => p.s2Id);
    setter(new Set(notInDb));
  };

  const selectNone = (tab: CiteTab) => {
    const setter = tab === "references" ? setSelectedRefs : setSelectedCites;
    setter(new Set());
  };

  /* Enqueue */
  const enqueue = useCallback(async () => {
    const allPapers: CitePaper[] = [];
    const refList = references.filter((p) => selectedRefs.has(p.s2Id));
    const citeList = citations.filter((p) => selectedCites.has(p.s2Id));
    allPapers.push(...refList, ...citeList);

    // Also enqueue the main paper if not in DB
    if (paper && !paper.inDb) {
      allPapers.push({
        s2Id: paper.s2Id,
        arxivId: paper.arxivId,
        doi: paper.doi,
        title: paper.title,
        year: paper.year,
        cites: paper.cites,
        abstractSnippet: paper.abstract?.slice(0, 200) || null,
        inDb: false,
      });
    }

    if (allPapers.length === 0) {
      setEnqueueResult("No new papers selected.");
      return;
    }

    setEnqueuing(true);
    setEnqueueResult(null);
    try {
      const res = await fetch("/api/seed/enqueue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ papers: allPapers }),
      });
      const data = await res.json();
      if (!res.ok) {
        setEnqueueResult(`Error: ${data.error}`);
        return;
      }
      const parts: string[] = [];
      if (data.inserted > 0) {
        parts.push(`Added ${data.inserted} paper${data.inserted !== 1 ? "s" : ""} to queue`);
      }
      if (data.skipped > 0) {
        const dupNames = (data.duplicates as string[]) || [];
        const dupList = dupNames.length > 0
          ? `: ${dupNames.slice(0, 3).map((t: string) => `"${t.length > 50 ? t.slice(0, 50) + "..." : t}"`).join(", ")}${dupNames.length > 3 ? ` and ${dupNames.length - 3} more` : ""}`
          : "";
        parts.push(`${data.skipped} already in corpus${dupList}`);
      }
      setEnqueueResult(parts.join(" — ") || "No papers to add");
      // Mark enqueued papers as inDb
      if (paper && !paper.inDb) setPaper({ ...paper, inDb: true });
      setReferences((prev) =>
        prev.map((p) => (selectedRefs.has(p.s2Id) ? { ...p, inDb: true } : p)),
      );
      setCitations((prev) =>
        prev.map((p) => (selectedCites.has(p.s2Id) ? { ...p, inDb: true } : p)),
      );
      setSelectedRefs(new Set());
      setSelectedCites(new Set());
    } catch (e) {
      setEnqueueResult(e instanceof Error ? e.message : "Network error");
    } finally {
      setEnqueuing(false);
    }
  }, [paper, references, citations, selectedRefs, selectedCites]);

  const totalSelected = selectedRefs.size + selectedCites.size + (paper && !paper.inDb ? 1 : 0);
  const currentList = activeTab === "references" ? references : citations;
  const currentSelected = activeTab === "references" ? selectedRefs : selectedCites;

  return (
    <div className="flex flex-col h-[calc(100vh-2.5rem)] overflow-hidden">
      {/* Header */}
      <header className="px-6 py-3 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-sm font-bold tracking-widest text-accent uppercase">
            Seed Queue
          </h1>
          <p className="text-[10px] text-dim">
            Add papers to the research pipeline via URL
          </p>
        </div>
        {null}
      </header>

      {/* URL input */}
      <div className="px-6 py-4 border-b border-border shrink-0">
        <div className="flex gap-3">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && resolve()}
            placeholder="Paste arXiv URL, DOI, or Semantic Scholar link..."
            className="flex-1 bg-zinc-900 border border-border rounded px-3 py-2 text-sm text-text placeholder:text-zinc-600 focus:outline-none focus:border-accent/50"
          />
          <button
            onClick={resolve}
            disabled={loading || !url.trim()}
            className="px-5 py-2 bg-accent/20 text-accent text-sm font-medium rounded border border-accent/30 hover:bg-accent/30 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? "Resolving..." : "Resolve"}
          </button>
        </div>
        {error && (
          <p className="text-xs text-red-400 mt-2">{error}</p>
        )}
        <p className="text-[10px] text-zinc-600 mt-1.5">
          Supported: arxiv.org/abs/..., doi.org/..., semanticscholar.org/paper/..., or bare arXiv ID
        </p>
      </div>

      {/* Results */}
      {paper && (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Paper card */}
          <div className="px-6 py-4 border-b border-border shrink-0">
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-sm font-bold text-text truncate">{paper.title}</h2>
                  {paper.inDb && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 shrink-0">
                      IN DB
                    </span>
                  )}
                </div>
                <p className="text-xs text-dim">
                  {paper.authors.slice(0, 5).join(", ")}
                  {paper.authors.length > 5 && ` +${paper.authors.length - 5} more`}
                  {paper.year && ` (${paper.year})`}
                  {paper.venue && ` \u2014 ${paper.venue}`}
                  {` \u2014 ${paper.cites.toLocaleString()} citations`}
                </p>
                {paper.keyContribution && (
                  <div className="mt-2 px-3 py-2 bg-zinc-900/80 border border-border rounded text-xs text-zinc-300 leading-relaxed">
                    <span className="text-accent font-medium">Key contribution:</span>{" "}
                    {paper.keyContribution}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Citation tabs + list */}
          <div className="flex-1 flex flex-col min-h-0">
            {/* Tab bar */}
            <div className="px-6 border-b border-border flex items-center justify-between shrink-0">
              <div className="flex">
                {(["references", "citations"] as CiteTab[]).map((tab) => {
                  const list = tab === "references" ? references : citations;
                  const sel = tab === "references" ? selectedRefs : selectedCites;
                  return (
                    <button
                      key={tab}
                      className={`px-4 py-2.5 text-xs transition cursor-pointer ${
                        activeTab === tab
                          ? "text-accent border-b-2 border-accent"
                          : "text-dim hover:text-zinc-300"
                      }`}
                      onClick={() => setActiveTab(tab)}
                    >
                      {tab === "references" ? "References" : "Cited By"} ({list.length})
                      {sel.size > 0 && (
                        <span className="ml-1 text-accent">[{sel.size}]</span>
                      )}
                    </button>
                  );
                })}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => selectAll(activeTab)}
                  className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
                >
                  Select all new
                </button>
                <button
                  onClick={() => selectNone(activeTab)}
                  className="text-[10px] text-dim hover:text-accent transition cursor-pointer"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Paper list */}
            <div className="flex-1 overflow-y-auto px-6 py-2">
              {currentList.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-dim text-xs">
                  No {activeTab === "references" ? "references" : "citing papers"} found
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-bg z-10">
                    <tr className="text-[10px] text-dim uppercase tracking-wider">
                      <th className="w-8 pb-2" />
                      <th className="text-left pb-2 font-medium">Title</th>
                      <th className="text-right pb-2 font-medium w-14">Year</th>
                      <th className="text-right pb-2 font-medium w-20">Cites</th>
                      <th className="text-right pb-2 font-medium w-16">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentList.map((p) => (
                      <tr
                        key={p.s2Id}
                        className={`border-t border-border/30 transition cursor-pointer ${
                          p.inDb
                            ? "opacity-50"
                            : currentSelected.has(p.s2Id)
                              ? "bg-accent/5"
                              : "hover:bg-zinc-900/50"
                        }`}
                        onClick={() => !p.inDb && toggle(p.s2Id, activeTab)}
                      >
                        <td className="py-1.5 text-center">
                          {p.inDb ? (
                            <span className="text-[10px] text-accent">&#x2713;</span>
                          ) : (
                            <input
                              type="checkbox"
                              checked={currentSelected.has(p.s2Id)}
                              onChange={() => toggle(p.s2Id, activeTab)}
                              className="w-3.5 h-3.5 accent-emerald-500 cursor-pointer"
                            />
                          )}
                        </td>
                        <td className="py-1.5 pr-3 max-w-0">
                          <span className="block truncate text-text">{p.title}</span>
                          {p.abstractSnippet && (
                            <span className="block truncate text-[10px] text-zinc-600 mt-0.5">
                              {p.abstractSnippet}
                            </span>
                          )}
                        </td>
                        <td className="py-1.5 text-right text-dim tabular-nums">
                          {p.year || "?"}
                        </td>
                        <td className="py-1.5 text-right text-text tabular-nums font-medium">
                          {p.cites.toLocaleString()}
                        </td>
                        <td className="py-1.5 text-right">
                          {p.inDb ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                              in db
                            </span>
                          ) : (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-zinc-800 text-zinc-500 border border-zinc-700">
                              new
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Footer: enqueue bar */}
          <div className="px-6 py-3 border-t border-border flex items-center justify-between shrink-0 bg-card">
            <div className="text-xs text-dim">
              {totalSelected > 0
                ? `${totalSelected} paper${totalSelected !== 1 ? "s" : ""} selected (incl. main paper)`
                : "Select papers to add to the seed queue"}
              {enqueueResult && (
                <span className={`ml-3 ${enqueueResult.startsWith("Error") ? "text-red-400" : enqueueResult.includes("already in corpus") && !enqueueResult.includes("Added") ? "text-amber-400" : "text-accent"}`}>
                  {enqueueResult}
                </span>
              )}
            </div>
            <button
              onClick={enqueue}
              disabled={enqueuing || totalSelected === 0}
              className="px-5 py-2 bg-accent text-bg text-sm font-bold rounded hover:bg-accent/90 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              {enqueuing ? "Adding..." : `Add ${totalSelected} to Queue`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
