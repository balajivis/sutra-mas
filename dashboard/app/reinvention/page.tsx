"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ReinventionRadar } from "@/components/ReinventionRadar";

function ReinventionContent() {
  const params = useSearchParams();
  const concept = params.get("concept") || undefined;
  const pattern = params.get("pattern") || undefined;

  return (
    <div className="flex flex-col h-[calc(100vh-40px)]">
      {/* Header */}
      <header className="px-4 py-2.5 border-b border-border shrink-0">
        <h1 className="text-sm font-bold uppercase tracking-widest text-accent">
          Reinvention Radar
        </h1>
        <p className="text-[10px] text-dim mt-0.5">
          Modern papers that discuss classical MAS concepts but don&apos;t cite the
          originating work. <span className="text-red-400">Dashed red</span> ={" "}
          reinvention (no citation).{" "}
          <span className="text-emerald-400">Solid green</span> = acknowledged
          (cited).
        </p>
      </header>

      {/* Radar */}
      <div className="flex-1 min-h-0">
        <ReinventionRadar concept={concept} pattern={pattern} />
      </div>
    </div>
  );
}

export default function ReinventionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[calc(100vh-40px)]">
          <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        </div>
      }
    >
      <ReinventionContent />
    </Suspense>
  );
}
