"use client";

import { useState, useCallback, useEffect, useRef } from "react";

/**
 * Pattern 4: Reasoning Tree Manipulation (Hippo, UIST 2025)
 *
 * Interactive visualization of agent reasoning chains as a tree.
 * Users can: revise node content, regenerate subtrees, add branches.
 *
 * Now wired to real data: select a paper, see Agent 3b's analysis JSONB as a tree.
 */

interface TreeNode {
  id: string;
  label: string;
  content: string;
  children: TreeNode[];
  isEditing?: boolean;
  isRegenerating?: boolean;
  status: "ok" | "warning" | "error" | "edited";
}

interface SearchResult {
  id: number;
  title: string;
  year: number;
  citations: number;
  pattern: string;
  summary: string;
}

interface PaperAnalysis {
  id: number;
  title: string;
  year: number;
  pipeline_status: string;
  analysis: Record<string, unknown> | null;
  citations: number;
}

function buildTreeFromAnalysis(paper: PaperAnalysis): TreeNode {
  const a = paper.analysis || {};
  const pattern = (a.coordination_pattern as string) || "none";
  const grounding = (a.theoretical_grounding as string) || "unknown";
  const missing = (a.classical_concepts_missing as string) || "";
  const summary = (a.key_contribution_summary as string) || "";
  const unique = (a.unique_contribution as string) || "";
  const results = (a.key_results as string) || "";
  const sections = a.sections_to_embed as string[] | undefined;
  const rosettaClassical = (a.rosetta_classical as string) || "";
  const rosettaModern = (a.rosetta_modern as string) || "";

  const children: TreeNode[] = [];

  // Pattern
  children.push({
    id: "pattern",
    label: "Coordination Pattern",
    content: pattern,
    status: pattern !== "none" ? "ok" : "warning",
    children: [],
  });

  // Key contribution
  if (summary) {
    children.push({
      id: "contribution",
      label: "Key Contribution",
      content: summary,
      status: "ok",
      children: [],
    });
  }

  // Unique contribution
  if (unique) {
    children.push({
      id: "unique",
      label: "Unique Contribution",
      content: unique,
      status: "ok",
      children: [],
    });
  }

  // Key results
  if (results) {
    children.push({
      id: "results",
      label: "Key Results",
      content: results,
      status: "ok",
      children: [],
    });
  }

  // Theoretical grounding
  children.push({
    id: "grounding",
    label: "Theoretical Grounding",
    content: `${grounding}${grounding === "strong" ? " - Cites classical foundations" : grounding === "weak" ? " - Limited classical references" : grounding === "none" ? " - No classical grounding found" : ""}`,
    status: grounding === "strong" ? "ok" : grounding === "weak" ? "warning" : "error",
    children: [],
  });

  // Classical concepts missing (Lost Canary signal)
  if (missing && missing !== "none") {
    children.push({
      id: "missing",
      label: "Classical Concepts Missing",
      content: missing,
      status: "warning",
      children: [],
    });
  }

  // Rosetta entry
  if (rosettaClassical || rosettaModern) {
    children.push({
      id: "rosetta",
      label: "Rosetta Stone Entry",
      content: `Classical: ${rosettaClassical || "?"} \u2192 Modern: ${rosettaModern || "?"}`,
      status: rosettaClassical && rosettaModern ? "ok" : "warning",
      children: [],
    });
  }

  // Sections to embed
  if (sections && Array.isArray(sections) && sections.length > 0) {
    children.push({
      id: "sections",
      label: "Sections to Embed",
      content: sections.join(", "),
      status: "ok",
      children: [],
    });
  }

  // Any other analysis keys we haven't handled
  const handledKeys = new Set([
    "coordination_pattern", "theoretical_grounding",
    "classical_concepts_missing", "key_contribution_summary",
    "unique_contribution", "key_results", "sections_to_embed",
    "rosetta_classical", "rosetta_modern",
  ]);
  for (const [key, value] of Object.entries(a)) {
    if (handledKeys.has(key)) continue;
    if (value == null || value === "" || value === "none") continue;
    const displayValue = typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
    if (displayValue.length > 0) {
      children.push({
        id: `extra-${key}`,
        label: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        content: displayValue.slice(0, 300),
        status: "ok",
        children: [],
      });
    }
  }

  return {
    id: "root",
    label: `Paper #${paper.id}`,
    content: `${paper.title} (${paper.year}) \u2014 ${pattern} \u2014 ${paper.citations} citations`,
    status: "ok",
    children,
  };
}

function getStatusColor(status: TreeNode["status"]) {
  switch (status) {
    case "ok": return "#34d399";
    case "warning": return "#fbbf24";
    case "error": return "#f87171";
    case "edited": return "#a78bfa";
  }
}

function TreeNodeComponent({
  node, depth, onEdit, onRegenerate, onBranch,
}: {
  node: TreeNode;
  depth: number;
  onEdit: (id: string, content: string) => void;
  onRegenerate: (id: string) => void;
  onBranch: (id: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(node.content);
  const [hovering, setHovering] = useState(false);

  const statusColor = getStatusColor(node.status);
  const hasChildren = node.children.length > 0;
  const indent = depth * 20;

  const handleSave = useCallback(() => {
    onEdit(node.id, editContent);
    setEditing(false);
  }, [node.id, editContent, onEdit]);

  return (
    <div>
      <div
        className="flex items-start gap-2 py-1 pr-2 rounded transition group"
        style={{ paddingLeft: indent + 8 }}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
      >
        <button
          className={`w-4 h-4 flex items-center justify-center text-[10px] text-dim shrink-0 mt-0.5 cursor-pointer ${
            hasChildren ? "hover:text-text" : "invisible"
          }`}
          onClick={() => setCollapsed(!collapsed)}
        >
          {hasChildren ? (collapsed ? "+" : "-") : ""}
        </button>

        <span
          className="w-2 h-2 rounded-full shrink-0 mt-1.5"
          style={{ background: statusColor }}
        />

        <div className="flex-1 min-w-0">
          <div
            className="text-[10px] font-bold uppercase tracking-wider"
            style={{ color: statusColor }}
          >
            {node.label}
          </div>

          {editing ? (
            <div className="mt-1">
              <textarea
                className="w-full h-16 bg-zinc-900 border border-purple-400/40 rounded px-2 py-1.5 text-[10px] text-zinc-200 resize-none focus:outline-none focus:border-purple-400"
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                autoFocus
              />
              <div className="flex gap-1 mt-1">
                <button
                  onClick={handleSave}
                  className="px-2 py-0.5 text-[9px] rounded bg-purple-400/20 text-purple-400 hover:bg-purple-400/30 transition cursor-pointer"
                >
                  Save & regenerate below
                </button>
                <button
                  onClick={() => {
                    setEditing(false);
                    setEditContent(node.content);
                  }}
                  className="px-2 py-0.5 text-[9px] rounded text-dim hover:text-text transition cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="text-[10px] text-zinc-400 mt-0.5 leading-snug whitespace-pre-wrap">
              {node.content}
            </div>
          )}
        </div>

        {hovering && !editing && (
          <div className="flex items-center gap-1 shrink-0 mt-0.5">
            <button
              onClick={() => setEditing(true)}
              className="px-1.5 py-0.5 text-[9px] rounded text-dim hover:text-purple-400 hover:bg-purple-400/10 transition cursor-pointer"
              title="Edit this reasoning step"
            >
              edit
            </button>
            <button
              onClick={() => onRegenerate(node.id)}
              className="px-1.5 py-0.5 text-[9px] rounded text-dim hover:text-cyan-400 hover:bg-cyan-400/10 transition cursor-pointer"
              title="Regenerate from this node"
            >
              regen
            </button>
            <button
              onClick={() => onBranch(node.id)}
              className="px-1.5 py-0.5 text-[9px] rounded text-dim hover:text-amber-400 hover:bg-amber-400/10 transition cursor-pointer"
              title="Branch: explore alternative reasoning"
            >
              branch
            </button>
          </div>
        )}
      </div>

      {!collapsed &&
        node.children.map((child) => (
          <TreeNodeComponent
            key={child.id}
            node={child}
            depth={depth + 1}
            onEdit={onEdit}
            onRegenerate={onRegenerate}
            onBranch={onBranch}
          />
        ))}
    </div>
  );
}

export function ReasoningTree() {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Paper search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedPaper, setSelectedPaper] = useState<PaperAnalysis | null>(null);
  const [loadingPaper, setLoadingPaper] = useState(false);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  // Select paper -> fetch full -> build tree
  const selectPaper = useCallback(async (id: number) => {
    setLoadingPaper(true);
    setSearchResults([]);
    setSearchQuery("");
    try {
      const res = await fetch(`/api/paper/${id}`);
      if (!res.ok) throw new Error("Failed");
      const paper = await res.json();
      setSelectedPaper(paper);
      if (paper.analysis) {
        setTree(buildTreeFromAnalysis(paper));
      } else {
        setTree({
          id: "root",
          label: `Paper #${paper.id}`,
          content: `${paper.title} (${paper.year}) \u2014 No analysis available yet (status: ${paper.pipeline_status})`,
          status: "warning",
          children: [],
        });
      }
    } catch {
      // ignore
    } finally {
      setLoadingPaper(false);
    }
  }, []);

  // Load default paper on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/search?q=coordination&top=1");
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

  const handleEdit = useCallback((id: string, content: string) => {
    setTree((prev) => prev ? updateNode(prev, id, { content, status: "edited" }) : prev);
    setNotification(`Node "${id}" edited. Subtree will regenerate.`);
    setTimeout(() => setNotification(null), 3000);
  }, []);

  const handleRegenerate = useCallback((id: string) => {
    setNotification(
      `Regenerating subtree from "${id}"... (would call LLM in production)`
    );
    setTimeout(() => setNotification(null), 3000);
  }, []);

  const handleBranch = useCallback((id: string) => {
    setNotification(
      `Branching from "${id}"... (would create alternative reasoning path)`
    );
    setTimeout(() => setNotification(null), 3000);
  }, []);

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
            placeholder="Search for a paper to inspect its analysis..."
            className="w-full bg-zinc-900 border border-border rounded px-2 py-1 text-[10px] text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-accent/50"
          />
          {searching && (
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-dim animate-pulse">
              ...
            </span>
          )}
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

      {/* Header */}
      <div className="px-4 py-1.5 flex items-center justify-between">
        <div className="text-[9px] text-dim">
          {selectedPaper
            ? `Agent 3b analysis \u00b7 ${selectedPaper.title} (${selectedPaper.year}) \u00b7 ${selectedPaper.citations} citations`
            : "Select a paper to view its reasoning tree"}
        </div>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#34d399" }} />
            ok
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#fbbf24" }} />
            check
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#f87171" }} />
            issue
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#a78bfa" }} />
            edited
          </span>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div className="mx-4 mb-1 px-2.5 py-1 rounded bg-purple-400/10 border border-purple-400/20 text-[10px] text-purple-300">
          {notification}
        </div>
      )}

      {/* Tree */}
      <div className="flex-1 overflow-auto px-2">
        {tree ? (
          <TreeNodeComponent
            node={tree}
            depth={0}
            onEdit={handleEdit}
            onRegenerate={handleRegenerate}
            onBranch={handleBranch}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-[10px] text-dim">
              Search for a paper above to view its analysis tree
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function updateNode(
  node: TreeNode,
  id: string,
  updates: Partial<TreeNode>
): TreeNode {
  if (node.id === id) return { ...node, ...updates };
  return {
    ...node,
    children: node.children.map((c) => updateNode(c, id, updates)),
  };
}
