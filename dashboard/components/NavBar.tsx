"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const INSIGHT_TYPES = [
  { key: "lost_canary", label: "Lost Canary Signals", color: "#fbbf24" },
  { key: "pattern_distribution", label: "Coordination Patterns", color: "#34d399" },
  { key: "grounding_gaps", label: "Grounding Gaps", color: "#f87171" },
  { key: "rosetta_entries", label: "Rosetta Stone", color: "#60a5fa" },
  { key: "cross_era_bridges", label: "Cross-Era Bridges", color: "#a78bfa" },
];

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/explore", label: "Explore" },
  { href: "/lineage", label: "Lineage" },
  { href: "/reinvention", label: "Reinvention" },
  { href: "/chat", label: "Chat" },
  { href: "/papers", label: "Papers" },
  { href: "/seed", label: "Seed" },
  { href: "/citation-cliff", label: "Citation Cliff" },
  { href: "/agent0", label: "Agent 0" },
];

export function NavBar() {
  const pathname = usePathname();
  const [insightsOpen, setInsightsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setInsightsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Close dropdown on navigation
  useEffect(() => {
    setInsightsOpen(false);
  }, [pathname]);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const isInsightActive = pathname.startsWith("/insight");

  return (
    <nav className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 flex items-center h-10 gap-1">
        <Link
          href="/"
          className="text-accent font-bold text-sm tracking-widest uppercase mr-4 shrink-0"
        >
          Sutra
        </Link>

        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-2.5 py-1 text-xs rounded transition ${
              isActive(item.href)
                ? "text-accent bg-accent/10"
                : "text-dim hover:text-text hover:bg-white/[0.03]"
            }`}
          >
            {item.label}
          </Link>
        ))}

        {/* Insights dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setInsightsOpen(!insightsOpen)}
            className={`px-2.5 py-1 text-xs rounded transition flex items-center gap-1 ${
              isInsightActive
                ? "text-accent bg-accent/10"
                : "text-dim hover:text-text hover:bg-white/[0.03]"
            }`}
          >
            Insights
            <svg
              className={`w-3 h-3 transition-transform ${insightsOpen ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {insightsOpen && (
            <div className="absolute top-full left-0 mt-1 w-52 bg-card border border-border rounded-lg shadow-xl py-1 z-50">
              {INSIGHT_TYPES.map((t) => (
                <Link
                  key={t.key}
                  href={`/insight/${t.key}`}
                  className={`block px-3 py-1.5 text-xs transition hover:bg-white/[0.04] ${
                    pathname === `/insight/${t.key}` ? "text-text" : "text-dim hover:text-text"
                  }`}
                >
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full mr-2"
                    style={{ background: t.color }}
                  />
                  {t.label}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
