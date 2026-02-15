"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { LineageGraph } from "@/components/LineageGraph";

function LineageContent() {
  const params = useSearchParams();
  const paperId = params.get("paper_id")
    ? parseInt(params.get("paper_id")!, 10)
    : undefined;
  const clusterId = params.get("cluster_id")
    ? parseInt(params.get("cluster_id")!, 10)
    : undefined;
  const depth = params.get("depth")
    ? parseInt(params.get("depth")!, 10)
    : 2;

  return (
    <div className="flex flex-col h-[calc(100vh-40px)]">
      {/* Header */}
      <header className="px-4 py-2.5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-sm font-bold uppercase tracking-widest text-accent">
            Citation Lineage
          </h1>
          <p className="text-[10px] text-dim mt-0.5">
            {paperId
              ? `Paper #${paperId} — ${depth}-hop citation neighborhood`
              : clusterId
              ? `Cluster #${clusterId} — internal citations`
              : "Top cited papers — corpus-wide citation flow"}
            {" "}&middot; X = year, Y = coordination pattern
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          {paperId && (
            <>
              {[1, 2, 3].map((d) => (
                <a
                  key={d}
                  href={`/lineage?paper_id=${paperId}&depth=${d}`}
                  className={`px-2 py-1 rounded border transition ${
                    d === depth
                      ? "border-accent/40 text-accent bg-accent/10"
                      : "border-border text-dim hover:text-text"
                  }`}
                >
                  {d}-hop
                </a>
              ))}
            </>
          )}
        </div>
      </header>

      {/* Graph */}
      <div className="flex-1 min-h-0">
        <LineageGraph paperId={paperId} clusterId={clusterId} depth={depth} />
      </div>
    </div>
  );
}

export default function LineagePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[calc(100vh-40px)]">
          <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        </div>
      }
    >
      <LineageContent />
    </Suspense>
  );
}
