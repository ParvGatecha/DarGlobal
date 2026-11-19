"use client";

import React from "react";
import { Building2, Menu, Database } from "lucide-react";
import { HealthStatus } from "@/lib/types";

interface SystemHeaderProps {
  sourceFilter: string;
  setSourceFilter: (filter: string) => void;
  health: HealthStatus | null;
  onToggleMobileMenu: () => void;
  activeView: "chat" | "properties";
  setActiveView: (view: "chat" | "properties") => void;
  onOpenAbout: () => void;
}

export function SystemHeader({
  sourceFilter,
  setSourceFilter,
  health,
  onToggleMobileMenu,
  activeView,
  setActiveView,
  onOpenAbout,
}: SystemHeaderProps) {
  const isOnline = !!health && health.status === "HEALTHY";
  const totalChunks = health?.total_indexed_chunks ?? 32;
  const directCount = health?.provenance_distribution?.["DIRECTLY_SCRAPED"] ?? 4;
  const fallbackCount = health?.provenance_distribution?.["PUBLICLY_VERIFIED_FALLBACK"] ?? 28;

  return (
    <header className="border-b border-charcoal-800 bg-charcoal-950/95 backdrop-blur-md sticky top-0 z-30 px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        {/* Left: Hamburger (mobile) & Branding */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMobileMenu}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-charcoal-850 md:hidden"
            aria-label="Toggle navigation menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-gold-500 via-gold-400 to-gold-200 flex items-center justify-center text-black shadow-gold">
              <Building2 className="h-4 w-4 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif font-bold text-sm sm:text-base text-zinc-100 tracking-wider">
                  DAR<span className="text-gold-400">GLOBAL</span>
                </span>
                <span className="font-sans font-medium text-xs text-zinc-400 tracking-widest uppercase">
                  INTELLIGENCE
                </span>
                <span className="hidden sm:inline-block text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-forest-900 text-gold-300 border border-forest-border">
                  Agentic RAG
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center: Source Filter Selectors (Desktop) */}
        <div className="hidden md:flex items-center gap-1 bg-charcoal-900 p-1 rounded-xl border border-charcoal-800 text-xs">
          <button
            onClick={() => setSourceFilter("all")}
            className={`px-3 py-1 rounded-lg font-medium transition-all ${
              sourceFilter === "all"
                ? "bg-forest-850 text-gold-300 border border-forest-border shadow-sm font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            All Sources
          </button>
          <button
            onClick={() => setSourceFilter("darglobal")}
            className={`px-3 py-1 rounded-lg font-medium transition-all ${
              sourceFilter === "darglobal"
                ? "bg-forest-850 text-gold-300 border border-forest-border shadow-sm font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            DarGlobal UK
          </button>
          <button
            onClick={() => setSourceFilter("wasalt")}
            className={`px-3 py-1 rounded-lg font-medium transition-all ${
              sourceFilter === "wasalt"
                ? "bg-forest-850 text-gold-300 border border-forest-border shadow-sm font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Wasalt SA
          </button>
        </div>

        {/* Right: Online Status & Data Source Indicator */}
        <div className="flex items-center gap-2.5 sm:gap-4">
          {/* Online Indicator */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-charcoal-900 border border-charcoal-800 text-[11px] font-mono">
            <span className="relative flex h-2 w-2">
              {isOnline && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              )}
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isOnline ? "bg-emerald-400" : "bg-amber-400"
                }`}
              ></span>
            </span>
            <span className="text-zinc-300 hidden sm:inline">
              {isOnline ? "System Online" : "Connecting..."}
            </span>
          </div>

          {/* Data Source Indicator */}
          <button
            onClick={onOpenAbout}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-forest-900/60 hover:bg-forest-900 border border-forest-border text-[11px] font-mono text-gold-300 transition-colors cursor-pointer"
            title="Inspect Data Source Transparency"
          >
            <Database className="h-3 w-3 text-gold-400" />
            <span>{totalChunks} Chunks</span>
            <span className="hidden lg:inline text-zinc-400">
              ({directCount} Scraped / {fallbackCount} Fallback)
            </span>
          </button>

          {/* View Switcher Button (Mobile/Tablet) */}
          <button
            onClick={() => setActiveView(activeView === "chat" ? "properties" : "chat")}
            className="md:hidden px-2.5 py-1 rounded-lg bg-charcoal-850 border border-charcoal-700 text-xs text-gold-300 font-medium"
          >
            {activeView === "chat" ? "Properties" : "Chat"}
          </button>
        </div>
      </div>
    </header>
  );
}
