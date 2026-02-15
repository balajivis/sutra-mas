"use client";

import { useState } from "react";
import { ObservatoryPanel } from "./ObservatoryPanel";
import { JudgmentCheckpoint } from "./JudgmentCheckpoint";
import { ReasoningTree } from "./ReasoningTree";
import { ProvenanceFlow } from "./ProvenanceFlow";
import { SensemakingCanvas } from "./SensemakingCanvas";
import { CitationCliff } from "./CitationCliff";

const TABS = [
  { id: "canvas", label: "Sensemaking Canvas", tag: "P1+P6", color: "#34d399" },
  { id: "checkpoint", label: "Judgment Checkpoint", tag: "P2", color: "#fbbf24" },
  { id: "provenance", label: "Provenance Flow", tag: "P3", color: "#22d3ee" },
  { id: "reasoning", label: "Reasoning Tree", tag: "P4", color: "#a78bfa" },
  { id: "observatory", label: "Observatory", tag: "P5", color: "#60a5fa" },
  { id: "cliff", label: "Citation Cliff", tag: "VIZ", color: "#f87171" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function Agent0Console() {
  const [activeTab, setActiveTab] = useState<TabId>("canvas");

  return (
    <div className="flex flex-col h-[calc(100vh-2.5rem)] overflow-hidden">
      {/* Header + Tab bar */}
      <header className="px-5 py-2 border-b border-border shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-sm font-bold tracking-widest uppercase">
              <span className="text-accent">Agent 0</span>{" "}
              <span className="text-dim">Console</span>
            </h1>
            <p className="text-[10px] text-dim">
              Six HCI patterns for human-agent research collaboration &middot;
              Thread 21 prototype
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot" />
            <span className="text-[10px] text-dim">Pipeline active</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 text-[10px] uppercase tracking-wider rounded-t transition cursor-pointer border-b-2 ${
                  isActive
                    ? "text-white bg-white/[0.04]"
                    : "text-dim hover:text-zinc-300 border-transparent"
                }`}
                style={{
                  borderBottomColor: isActive ? tab.color : "transparent",
                }}
              >
                <span className="mr-1.5">{tab.label}</span>
                <span
                  className="text-[8px] px-1 py-0.5 rounded"
                  style={{
                    color: isActive ? tab.color : "#71717a",
                    background: isActive ? tab.color + "20" : "transparent",
                  }}
                >
                  {tab.tag}
                </span>
              </button>
            );
          })}
        </div>
      </header>

      {/* Tab content — full remaining height */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === "canvas" && <SensemakingCanvas />}
        {activeTab === "checkpoint" && <JudgmentCheckpoint />}
        {activeTab === "provenance" && <ProvenanceFlow />}
        {activeTab === "reasoning" && <ReasoningTree />}
        {activeTab === "observatory" && <ObservatoryFull />}
        {activeTab === "cliff" && <CitationCliff />}
      </div>
    </div>
  );
}

/** Full-page Observatory layout — wider than sidebar version */
function ObservatoryFull() {
  return (
    <div className="h-full flex">
      <div className="w-96 border-r border-border overflow-y-auto">
        <ObservatoryPanel />
      </div>
      <div className="flex-1 flex items-center justify-center text-dim">
        <div className="text-center space-y-2 px-8">
          <div className="text-[10px] uppercase tracking-wider text-blue-400">
            Pattern 5: Observatory
          </div>
          <div className="text-xs text-zinc-400 leading-relaxed max-w-md">
            The Observatory gives Agent 0 a control-shell view of the entire
            pipeline. Every agent&apos;s status, throughput, token cost, and anomalies
            are visible at a glance — implementing Nii&apos;s blackboard control
            shell as an operational interface.
          </div>
          <div className="text-[10px] text-zinc-600 mt-4">
            Live data from pipeline database. 30s polling.
          </div>
        </div>
      </div>
    </div>
  );
}
