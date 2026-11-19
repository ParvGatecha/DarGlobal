"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, CheckCircle2, ExternalLink, Sparkles } from "lucide-react";
import { ChatMessage, Citation } from "@/lib/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ExecutionTraceCard } from "./ExecutionTraceCard";
import { WelcomeScreen } from "./WelcomeScreen";

interface ChatInterfaceProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (msg: string) => void;
  onSelectCitation: (citation: Citation) => void;
  sourceFilter: string;
}

export function ChatInterface({
  messages,
  isLoading,
  onSendMessage,
  onSelectCitation,
  sourceFilter,
}: ChatInterfaceProps) {
  const [input, setInput] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full bg-charcoal-950 overflow-hidden font-sans">
      {/* Message History Feed or Welcome Screen */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {!hasMessages ? (
          <WelcomeScreen onSelectPrompt={onSendMessage} />
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === "user";

            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-4xl ${isUser ? "ml-auto justify-end" : "mr-auto"}`}
              >
                {/* Assistant Avatar */}
                {!isUser && (
                  <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-gold-500 via-gold-400 to-gold-200 flex items-center justify-center text-black shrink-0 shadow-gold">
                    <Bot className="h-4 w-4 stroke-[2.5]" />
                  </div>
                )}

                <div className={`flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"} max-w-full`}>
                  {/* Agent Execution Trace if available */}
                  {!isUser && msg.execution_trace && msg.execution_trace.length > 0 && (
                    <div className="w-full max-w-2xl">
                      <ExecutionTraceCard traces={msg.execution_trace} />
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div
                    className={`rounded-2xl px-4 py-3 text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? "bg-forest-900 border border-forest-border text-gold-100 font-medium rounded-tr-none shadow-forest"
                        : "bg-charcoal-900 border border-charcoal-700/80 text-zinc-200 rounded-tl-none shadow-sm"
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <MarkdownRenderer
                        content={msg.content}
                        citations={msg.citations}
                        onSelectCitation={onSelectCitation}
                      />
                    )}
                  </div>

                  {/* Assistant Source Citations Ribbon */}
                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-1 w-full">
                      <p className="text-[10px] uppercase font-mono tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-gold-400" />
                        Verified Grounding ({msg.citations.length} Sources Cited):
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((c) => {
                          const isDg = c.source.toLowerCase().includes("darglobal");
                          const isDirect = c.is_directly_scraped || c.provenance_class === "DIRECTLY_SCRAPED";
                          return (
                            <button
                              key={c.citation_id}
                              onClick={() => onSelectCitation(c)}
                              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border transition-all text-left cursor-pointer ${
                                isDg
                                  ? "bg-forest-900/60 border-forest-border hover:bg-forest-850 text-gold-300"
                                  : "bg-charcoal-900 border-charcoal-700 hover:bg-charcoal-850 text-zinc-200"
                              }`}
                            >
                              <span className="h-4 w-4 rounded-full bg-charcoal-800 text-gold-400 font-bold text-[10px] flex items-center justify-center font-mono">
                                [{c.citation_id}]
                              </span>
                              <span className="font-medium truncate max-w-[150px]">{c.title}</span>
                              <span
                                className={`text-[9px] font-mono px-1 py-0.2 rounded ${
                                  isDirect
                                    ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/80"
                                    : "bg-charcoal-800 text-gold-300 border border-charcoal-700"
                                }`}
                              >
                                {isDirect ? "Direct" : "Fallback"}
                              </span>
                              <ExternalLink className="h-2.5 w-2.5 shrink-0 opacity-70" />
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Timestamp & Model Telemetry */}
                  <div className="flex items-center gap-2 text-[10px] text-zinc-400 px-1 font-mono">
                    <span>{msg.timestamp}</span>
                    {!isUser && msg.model_used && (
                      <>
                        <span>|</span>
                        <span className="text-zinc-400">
                          {msg.model_used.replace(":free", "")}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* User Avatar */}
                {isUser && (
                  <div className="h-8 w-8 rounded-xl bg-charcoal-850 flex items-center justify-center text-gold-300 shrink-0 border border-charcoal-700">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Streaming / Agent Reasoning Indicator */}
        {isLoading && (
          <div className="flex gap-3 max-w-xl mr-auto">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-gold-500 via-gold-400 to-gold-200 flex items-center justify-center text-black shrink-0 shadow-gold">
              <Bot className="h-4 w-4 stroke-[2.5]" />
            </div>
            <div className="bg-charcoal-900 border border-charcoal-700 rounded-2xl rounded-tl-none px-4 py-3 flex items-center gap-2.5 text-zinc-300 text-xs shadow-sm">
              <div className="flex space-x-1">
                <div className="h-2 w-2 bg-gold-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <div className="h-2 w-2 bg-gold-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <div className="h-2 w-2 bg-gold-400 rounded-full animate-bounce" />
              </div>
              <span className="font-mono text-[11px] text-zinc-400">
                Executing agent tools & fusing hybrid vector chunks...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompt Chips (above composer) */}
      <div className="px-4 py-2 border-t border-charcoal-800/80 bg-charcoal-950 overflow-x-auto flex items-center gap-2 no-scrollbar">
        <span className="text-[10px] uppercase font-mono tracking-wider text-gold-400 flex items-center gap-1 shrink-0">
          <Sparkles className="h-3 w-3" /> Quick Inquiries:
        </span>
        {[
          "Explore luxury developments in Dubai.",
          "Find properties in Riyadh under SAR 5 million.",
          "Compare real estate opportunities.",
          "Explore DarGlobal projects.",
        ].map((promptText) => (
          <button
            key={promptText}
            type="button"
            disabled={isLoading}
            onClick={() => onSendMessage(promptText)}
            className="text-[11px] font-medium text-zinc-300 hover:text-gold-200 bg-charcoal-900 hover:bg-forest-900 border border-charcoal-800 hover:border-gold-border px-3 py-1 rounded-full whitespace-nowrap transition-colors shrink-0 disabled:opacity-50 cursor-pointer"
          >
            {promptText}
          </button>
        ))}
      </div>

      {/* Input Composer */}
      <div className="p-4 border-t border-charcoal-800 bg-charcoal-950/95 backdrop-blur-md">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex items-end gap-2 relative">
          <div className="relative flex-1">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about Pagani Tower, Missoni Urban Oasis, AIDA Oman, Riyadh smart villas, prices, amenities..."
              className="w-full bg-charcoal-900 border border-charcoal-700/80 rounded-2xl px-4 py-3 text-xs sm:text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-gold-border transition-all resize-none max-h-32 shadow-inner"
            />
            {sourceFilter !== "all" && (
              <span className="absolute right-3 bottom-3 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-charcoal-800 text-gold-300 border border-charcoal-700">
                Filtered: {sourceFilter.toUpperCase()}
              </span>
            )}
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="h-11 w-11 rounded-2xl bg-gold-500 hover:bg-gold-400 disabled:bg-charcoal-800 disabled:text-zinc-600 text-black flex items-center justify-center shrink-0 transition-all shadow-gold cursor-pointer"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
