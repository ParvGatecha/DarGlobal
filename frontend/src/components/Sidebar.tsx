"use client";

import React from "react";
import {
  Plus,
  MessageSquare,
  Building2,
  Database,
  Info,
  Trash2,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  X,
} from "lucide-react";
import { ChatSession, HealthStatus } from "@/lib/types";

interface SidebarProps {
  currentSessionId: string | null;
  sessions: ChatSession[];
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  onOpenAbout: () => void;
  activeView: "chat" | "properties";
  setActiveView: (view: "chat" | "properties") => void;
  health: HealthStatus | null;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({
  currentSessionId,
  sessions,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onOpenAbout,
  activeView,
  setActiveView,
  health,
  isOpenMobile,
  onCloseMobile,
}: SidebarProps) {
  const directCount = health?.provenance_distribution?.["DIRECTLY_SCRAPED"] ?? 4;
  const fallbackCount = health?.provenance_distribution?.["PUBLICLY_VERIFIED_FALLBACK"] ?? 28;
  const totalCount = health?.total_indexed_chunks ?? 32;

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden"
        />
      )}

      {/* Main Sidebar Panel */}
      <aside
        className={`fixed md:static top-0 bottom-0 left-0 z-50 w-72 sm:w-80 bg-charcoal-950 border-r border-charcoal-800 flex flex-col justify-between transition-transform duration-300 ease-in-out ${
          isOpenMobile ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full overflow-hidden">
          {/* Header & Mobile Close */}
          <div className="p-4 border-b border-charcoal-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-gold-500 to-gold-300 flex items-center justify-center text-black font-serif font-black text-sm shadow-gold">
                DG
              </div>
              <div>
                <h2 className="font-serif font-bold text-sm text-zinc-100 tracking-wide">
                  DarGlobal <span className="text-gold-400 font-sans font-semibold text-xs">Intelligence</span>
                </h2>
                <p className="text-[10px] text-zinc-400 font-mono">v1.0.0 Production</p>
              </div>
            </div>

            <button
              onClick={onCloseMobile}
              className="p-1 rounded-md text-zinc-400 hover:text-white md:hidden"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* New Conversation Button */}
          <div className="p-3">
            <button
              onClick={() => {
                onNewSession();
                onCloseMobile();
              }}
              className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-forest-900 hover:bg-forest-850 text-gold-300 hover:text-gold-200 border border-forest-border hover:border-gold-border font-medium text-xs transition-all shadow-sm group cursor-pointer"
            >
              <Plus className="h-4 w-4 text-gold-400 group-hover:rotate-90 transition-transform duration-200" />
              <span>New Conversation</span>
            </button>
          </div>

          {/* View Switcher: Chat vs Property Catalog */}
          <div className="px-3 pb-2">
            <div className="grid grid-cols-2 p-1 rounded-lg bg-charcoal-900 border border-charcoal-800 text-xs">
              <button
                onClick={() => {
                  setActiveView("chat");
                  onCloseMobile();
                }}
                className={`flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-all ${
                  activeView === "chat"
                    ? "bg-forest-850 text-gold-300 border border-forest-border shadow-sm font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>AI Chat</span>
              </button>
              <button
                onClick={() => {
                  setActiveView("properties");
                  onCloseMobile();
                }}
                className={`flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-all ${
                  activeView === "properties"
                    ? "bg-forest-850 text-gold-300 border border-forest-border shadow-sm font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Building2 className="h-3.5 w-3.5" />
                <span>Properties</span>
              </button>
            </div>
          </div>

          {/* Conversation History */}
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
            <div className="px-2 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-400 flex items-center justify-between">
              <span>Conversation History</span>
              <span className="text-[9px] text-zinc-400 font-mono">
                {sessions.length} {sessions.length === 1 ? "chat" : "chats"}
              </span>
            </div>

            {sessions.length === 0 ? (
              <div className="p-4 text-center rounded-lg border border-dashed border-charcoal-800 bg-charcoal-900/40 my-2">
                <p className="text-xs text-zinc-400 font-medium">No previous sessions</p>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Your research inquiries will be saved here automatically.
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {sessions.map((sess) => {
                  const isActive = sess.id === currentSessionId;
                  return (
                    <div
                      key={sess.id}
                      className={`group flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-all cursor-pointer ${
                        isActive
                          ? "bg-charcoal-850 border border-gold-border/60 text-gold-200"
                          : "hover:bg-charcoal-900 border border-transparent text-zinc-300 hover:text-zinc-100"
                      }`}
                      onClick={() => {
                        onSelectSession(sess.id);
                        onCloseMobile();
                      }}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <MessageSquare
                          className={`h-3.5 w-3.5 shrink-0 ${
                            isActive ? "text-gold-400" : "text-zinc-400 group-hover:text-zinc-300"
                          }`}
                        />
                        <span className="truncate max-w-[170px] text-xs font-medium">
                          {sess.title}
                        </span>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(sess.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 text-zinc-400 hover:text-red-400 transition-opacity"
                        title="Delete conversation"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Live Data Sources Section */}
          <div className="p-3 border-t border-charcoal-800 bg-charcoal-900/60 space-y-2">
            <div className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-400 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Database className="h-3 w-3 text-gold-400" />
                Active Data Sources
              </span>
              <span className="text-[9px] text-emerald-400 flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Live
              </span>
            </div>

            {/* DarGlobal Card */}
            <div className="p-2 rounded-lg bg-charcoal-950 border border-charcoal-800 text-[11px] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-zinc-200">DarGlobal Official</span>
                <a
                  href="https://www.darglobal.co.uk/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-gold-400 hover:underline flex items-center gap-0.5"
                >
                  <span>Portal</span>
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
              </div>
              <p className="text-[10px] text-zinc-400">
                UK LSE Listed Developer (Dubai, Spain, Oman, Qatar)
              </p>
            </div>

            {/* Wasalt Card */}
            <div className="p-2 rounded-lg bg-charcoal-950 border border-charcoal-800 text-[11px] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-zinc-200">Wasalt Marketplace</span>
                <a
                  href="https://wasalt.sa/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-gold-400 hover:underline flex items-center gap-0.5"
                >
                  <span>Portal</span>
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
              </div>
              <p className="text-[10px] text-zinc-400">
                Premier Saudi Real Estate (Riyadh, Jeddah, Al Khobar)
              </p>
            </div>

            {/* Provenance Pills */}
            <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-zinc-400">
              <span className="flex items-center gap-1 text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                {directCount} Direct
              </span>
              <span className="text-charcoal-700">|</span>
              <span className="flex items-center gap-1 text-gold-300">
                <ShieldCheck className="h-3 w-3" />
                {fallbackCount} Fallback
              </span>
              <span className="text-charcoal-700">|</span>
              <span>{totalCount} Total Chunks</span>
            </div>
          </div>

          {/* Footer: About Platform Button */}
          <div className="p-3 border-t border-charcoal-800 bg-charcoal-950">
            <button
              onClick={() => {
                onOpenAbout();
                onCloseMobile();
              }}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-charcoal-900 hover:bg-charcoal-850 border border-charcoal-800 text-xs text-zinc-300 hover:text-white transition-colors"
            >
              <span className="flex items-center gap-2">
                <Info className="h-3.5 w-3.5 text-gold-400" />
                <span>About the Platform</span>
              </span>
              <span className="text-[10px] font-mono text-zinc-400">Audit Info</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
