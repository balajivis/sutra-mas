"use client";

import { ChatPanel } from "@/components/ChatPanel";

export default function ChatPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-2.5rem)]">
      <header className="px-5 py-2 border-b border-border shrink-0">
        <h1 className="text-sm font-bold tracking-widest text-accent uppercase">
          Research Chat
        </h1>
        <p className="text-[10px] text-dim">
          Ask questions about the corpus &middot; RAG-powered
        </p>
      </header>
      <div className="flex-1 min-h-0">
        <ChatPanel />
      </div>
    </div>
  );
}
