"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import type { ChatMessage, Citation } from "@/types";

const SUGGESTIONS = [
  "Why did Video A outperform Video B?",
  "Compare the hooks in the first 5 seconds.",
  "Suggest improvements for Video B.",
  "Who created Video B and what's their follower count?",
  "What should I copy from Video A?",
];

function CitationTag({ c }: { c: Citation }) {
  return (
    <span className="inline-flex items-center font-mono text-[9px] tracking-wider bg-white/[0.05] border border-border/40 px-1.5 py-0.5 rounded">
      [{c.tag}]
    </span>
  );
}

function Bubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-2.5", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="h-5 w-5 rounded-full bg-white/[0.06] border border-border/40 flex items-center justify-center shrink-0 mt-1">
          <span className="font-mono text-[8px] font-bold">IQ</span>
        </div>
      )}
      <div className={cn(
        "max-w-[88%] text-sm leading-relaxed rounded-xl px-3.5 py-2.5",
        isUser
          ? "bg-white/[0.08] border border-white/[0.1] rounded-tr-sm"
          : "bg-white/[0.03] border border-border/30 rounded-tl-sm"
      )}>
        <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        {msg.streaming && <span className="inline-block h-3.5 w-0.5 bg-white/40 animate-pulse ml-0.5 align-middle" />}
        {!isUser && msg.citations && msg.citations.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border/20 flex flex-wrap gap-1">
            {msg.citations.map((c, i) => <CitationTag key={i} c={c} />)}
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatPanel({ analysisId }: { analysisId: string }) {
  const { messages, isStreaming, sendMessage } = useChat(analysisId);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        {messages.length === 0 ? (
          <div className="space-y-1.5 pt-2">
            <p className="font-mono text-[9px] tracking-widest text-muted-foreground/40 uppercase mb-4">Suggested questions</p>
            {SUGGESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => { setInput(q); inputRef.current?.focus(); }}
                className="w-full text-left text-xs text-muted-foreground hover:text-foreground bg-white/[0.02] hover:bg-white/[0.04] border border-border/30 hover:border-border/60 rounded-lg px-3 py-2.5 transition-all leading-relaxed"
              >
                {q}
              </button>
            ))}
          </div>
        ) : (
          messages.map((msg) => <Bubble key={msg.id} msg={msg} />)
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border/40 shrink-0">
        <div className="flex gap-2 items-center bg-white/[0.04] border border-border/40 focus-within:border-white/20 rounded-xl px-3 py-2 transition-colors">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask about these videos…"
            disabled={isStreaming}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/40 outline-none"
          />
          <button
            onClick={send}
            disabled={isStreaming || !input.trim()}
            className="h-6 w-6 flex items-center justify-center text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors shrink-0"
          >
            {isStreaming ? (
              <span className="h-3 w-3 border border-muted-foreground/40 border-t-foreground rounded-full animate-spin" />
            ) : (
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
        <p className="font-mono text-[9px] text-muted-foreground/30 text-center mt-2 tracking-wider">
          Memory preserved across turns · Citations included
        </p>
      </div>
    </div>
  );
}
