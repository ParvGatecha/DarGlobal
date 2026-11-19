"use client";

import React from "react";
import { Compass, Sparkles, Building, Key } from "lucide-react";

interface QuickPromptsProps {
  onSelectPrompt: (prompt: string) => void;
}

const PROMPTS = [
  {
    icon: Sparkles,
    label: "Pagani DaVinci Tower",
    query: "Tell me about DaVinci Tower by Pagani in Dubai. What are the starting prices and amenities?",
  },
  {
    icon: Building,
    label: "Tierra Viva Marbella",
    query: "What makes Tierra Viva by Automobili Lamborghini in Marbella unique, and what villa types are offered?",
  },
  {
    icon: Key,
    label: "Smart Villa in Riyadh",
    query: "Find verified smart villas for sale in Al Malqa, Riyadh listed on Wasalt.",
  },
  {
    icon: Compass,
    label: "AIDA Trump Golf Community",
    query: "What are the features of AIDA Oman and its collaboration with Trump International?",
  },
];

export function QuickPrompts({ onSelectPrompt }: QuickPromptsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 my-4">
      {PROMPTS.map((p, idx) => {
        const Icon = p.icon;
        return (
          <button
            key={idx}
            onClick={() => onSelectPrompt(p.query)}
            className="flex items-start gap-2.5 p-3 rounded-xl bg-zinc-900/60 hover:bg-zinc-800/80 border border-zinc-800/80 hover:border-amber-500/40 transition-all text-left group"
          >
            <div className="p-1.5 rounded-lg bg-zinc-800 text-amber-400 group-hover:bg-amber-500/20 transition-colors">
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-zinc-200 group-hover:text-amber-300 transition-colors">
                {p.label}
              </p>
              <p className="text-[11px] text-zinc-400 line-clamp-1">{p.query}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
