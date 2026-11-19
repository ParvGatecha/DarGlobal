"use client";

import React from "react";
import { Sparkles, Building2, Scale, Compass, ArrowRight, ShieldCheck, Database, Cpu } from "lucide-react";

interface WelcomeScreenProps {
  onSelectPrompt: (prompt: string) => void;
  indexedCount?: number;
}

export function WelcomeScreen({ onSelectPrompt, indexedCount = 32 }: WelcomeScreenProps) {
  const suggestedPrompts = [
    {
      title: "Explore luxury developments in Dubai.",
      subtitle: "DaVinci Tower by Pagani, W Residences Downtown & Urban Oasis by Missoni.",
      prompt: "Explore luxury developments in Dubai. What are their starting prices, locations, and branded amenities?",
      icon: Building2,
      tag: "Dubai Portfolio",
    },
    {
      title: "Find properties in Riyadh.",
      subtitle: "Smart independent villas in Al Malqa & contemporary duplexes in Al Narjis under SAR 5M.",
      prompt: "Find luxury properties in Riyadh under SAR 5 million on Wasalt with verified pricing and amenities.",
      icon: Compass,
      tag: "Wasalt Saudi",
    },
    {
      title: "Compare real estate opportunities.",
      subtitle: "Side-by-side verified attribute comparison between Dubai Canal and Riyadh.",
      prompt: "Compare DarGlobal projects in Dubai with properties in Riyadh on Wasalt using verified attributes.",
      icon: Scale,
      tag: "Comparative RAG",
    },
    {
      title: "Explore DarGlobal projects.",
      subtitle: "Tierra Viva by Lamborghini in Spain, AIDA Trump Golf in Oman, Les Vagues in Qatar.",
      prompt: "Explore DarGlobal international projects across Spain, Oman, and Qatar with handover timelines.",
      icon: Sparkles,
      tag: "International",
    },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 md:p-12 max-w-4xl mx-auto text-center">
      {/* Luxury Crest Badge */}
      <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-forest-900/80 border border-forest-border text-gold-300 text-xs font-mono font-medium tracking-widest uppercase mb-6 shadow-forest">
        <Sparkles className="h-3.5 w-3.5 text-gold-400" />
        <span>DarGlobal Intelligence</span>
      </div>

      {/* Main Hero Header */}
      <h1 className="text-3xl sm:text-4xl md:text-5xl font-serif font-bold text-zinc-100 tracking-tight leading-tight">
        Discover Real Estate. <span className="text-gold-400 italic">Intelligently.</span>
      </h1>

      <p className="mt-3 text-base sm:text-lg text-zinc-400 max-w-xl font-normal leading-relaxed">
        Your AI-powered research assistant for <span className="text-zinc-200 font-medium">DarGlobal</span> and{" "}
        <span className="text-zinc-200 font-medium">Wasalt</span>.
      </p>

      {/* 4 Suggested Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full mt-10 text-left">
        {suggestedPrompts.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group flex flex-col justify-between p-4 rounded-xl bg-charcoal-900/90 hover:bg-forest-900/70 border border-charcoal-700 hover:border-gold-border/80 transition-all duration-300 shadow-sm hover:shadow-gold hover:-translate-y-0.5 cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-charcoal-800 text-gold-300 border border-charcoal-700 group-hover:border-gold-border">
                    {item.tag}
                  </span>
                  <div className="h-7 w-7 rounded-lg bg-charcoal-800 group-hover:bg-gold-500/10 flex items-center justify-center text-zinc-400 group-hover:text-gold-400 transition-colors">
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                </div>

                <h2 className="text-sm font-semibold text-zinc-100 group-hover:text-gold-200 transition-colors leading-snug">
                  {item.title}
                </h2>
                <p className="text-xs text-zinc-400 mt-1 leading-relaxed line-clamp-2">
                  {item.subtitle}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-charcoal-800/80 group-hover:border-forest-border flex items-center justify-between text-[11px] font-medium text-zinc-400 group-hover:text-gold-300">
                <span>Inquire with AI Agent</span>
                <ArrowRight className="h-3.5 w-3.5 transform group-hover:translate-x-1 transition-transform" />
              </div>
            </button>
          );
        })}
      </div>

      {/* Data Integrity Footnote */}
      <div className="mt-10 pt-6 border-t border-charcoal-800/80 w-full flex flex-wrap items-center justify-center gap-6 text-[11px] font-mono text-zinc-400">
        <span className="flex items-center gap-1.5">
          <Database className="h-3.5 w-3.5 text-emerald-400" />
          <span>{indexedCount} Verified Documents</span>
        </span>
        <span className="text-charcoal-700">|</span>
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-gold-400" />
          <span>Strict Provenance (0 Fabrications)</span>
        </span>
        <span className="text-charcoal-700">|</span>
        <span className="flex items-center gap-1.5">
          <Cpu className="h-3.5 w-3.5 text-zinc-400" />
          <span>Autonomous Python Tool Calling</span>
        </span>
      </div>
    </div>
  );
}
