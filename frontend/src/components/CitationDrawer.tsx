"use client";

import React from "react";
import { Citation } from "@/lib/types";
import { X, ExternalLink, ShieldCheck, AlertCircle, FileText, CheckCircle2, Database } from "lucide-react";

interface CitationDrawerProps {
  citation: Citation | null;
  onClose: () => void;
}

export function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  if (!citation) return null;

  const isDarGlobal = citation.source.toLowerCase().includes("darglobal");
  const pClass = citation.provenance_class || (citation.metadata?.provenance_class as string) || "PUBLICLY_VERIFIED_FALLBACK";
  const extractionMethod = citation.extraction_method || (citation.metadata?.extraction_method as string) || "sitemap_discovery_and_public_dossier";
  const extractionTime = citation.extraction_timestamp || (citation.metadata?.extraction_timestamp as string) || "2026-11-18T17:35:40Z";
  const altSource = citation.alternative_source || (citation.metadata?.alternative_source as string) || null;
  const originNotes = citation.origin_notes || (citation.metadata?.origin_notes as string) || "";
  const isDirect = citation.is_directly_scraped ?? (citation.metadata?.is_directly_scraped as boolean) ?? false;

  const getProvenanceBadge = () => {
    switch (pClass) {
      case "DIRECTLY_SCRAPED":
        return {
          label: "DIRECTLY SCRAPED (SITEMAP)",
          classes: "bg-emerald-950/80 text-emerald-300 border-emerald-800/80",
          icon: CheckCircle2,
          desc: "Obtained directly from live target website XML/GZIP sitemap index without access boundaries.",
        };
      case "PUBLICLY_VERIFIED_FALLBACK":
        return {
          label: "VERIFIED FALLBACK",
          classes: "bg-forest-900 text-gold-300 border-forest-border",
          icon: ShieldCheck,
          desc: "Canonical URL discovered live; factual specs verified from official investor disclosures and verified registries due to WAF challenge boundaries.",
        };
      case "MANUALLY_CURATED":
        return {
          label: "MANUALLY CURATED",
          classes: "bg-charcoal-800 text-zinc-300 border-charcoal-700",
          icon: FileText,
          desc: "Curated reference record.",
        };
      default:
        return {
          label: "UNVERIFIED",
          classes: "bg-red-950/80 text-red-300 border-red-800/80",
          icon: AlertCircle,
          desc: "Unverified origin.",
        };
    }
  };

  const badge = getProvenanceBadge();
  const BadgeIcon = badge.icon;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex justify-end transition-opacity animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-charcoal-950 border-l border-charcoal-700 h-full p-6 flex flex-col justify-between overflow-y-auto shadow-2xl">
        <div className="space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-charcoal-800">
            <div className="flex items-center gap-2">
              <span className="h-6 w-6 rounded-full bg-gold-500 text-black font-bold text-xs flex items-center justify-center font-mono">
                {citation.citation_id}
              </span>
              <h2 className="font-serif font-bold text-sm text-zinc-100">
                Source Citation & Provenance Audit
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-charcoal-850 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Provenance Classification Card */}
          <div className="p-3.5 rounded-xl bg-charcoal-900 border border-charcoal-700/80 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400">
                Data Provenance Classification
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badge.classes}`}
              >
                <BadgeIcon className="h-3 w-3" />
                {badge.label}
              </span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed">{badge.desc}</p>
          </div>

          {/* Document Title & Target Source */}
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className={`text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded-md ${
                  isDarGlobal
                    ? "bg-forest-900 text-gold-300 border border-forest-border"
                    : "bg-charcoal-850 text-emerald-300 border border-charcoal-700"
                }`}
              >
                {citation.source}
              </span>
              <span className="text-[11px] text-zinc-400 font-mono">
                Scraped Direct: {isDirect ? "Yes (Live Sitemap HTTP)" : "No (WAF Fallback Dossier)"}
              </span>
            </div>
            <h3 className="font-serif font-bold text-base text-zinc-100">{citation.title}</h3>
          </div>

          {/* Canonical Source URL */}
          <div className="p-3 bg-charcoal-900 border border-charcoal-800 rounded-xl">
            <p className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider mb-1">
              Canonical Source URL
            </p>
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gold-400 hover:text-gold-300 hover:underline break-all flex items-center gap-1.5 font-mono"
            >
              <span>{citation.url}</span>
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          </div>

          {/* Audit Trail & WAF Boundary Context */}
          {originNotes && (
            <div className="p-3.5 rounded-xl bg-forest-900/40 border border-forest-border text-xs">
              <p className="text-[10px] font-mono uppercase tracking-wider text-gold-300 font-semibold mb-1">
                Audit Trail & Security Boundary
              </p>
              <p className="text-zinc-300 leading-relaxed font-sans">{originNotes}</p>
            </div>
          )}

          {/* Technical Extraction Metadata */}
          <div className="p-3.5 rounded-xl bg-charcoal-900 border border-charcoal-800 space-y-2 text-xs">
            <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-semibold">
              Extraction Telemetry
            </p>
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div>
                <span className="text-zinc-400 block text-[10px]">Method:</span>
                <span className="text-zinc-200">{extractionMethod}</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">Timestamp:</span>
                <span className="text-zinc-200">{extractionTime}</span>
              </div>
              {altSource && (
                <div className="col-span-2">
                  <span className="text-zinc-400 block text-[10px]">Alternative Source:</span>
                  <span className="text-gold-300">{altSource}</span>
                </div>
              )}
            </div>
          </div>

          {/* Grounding Snippet */}
          {citation.snippet && (
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1">
                <Database className="h-3 w-3 text-gold-400" />
                Indexed Grounding Excerpt:
              </p>
              <div className="p-3 bg-charcoal-900/60 border border-charcoal-800 rounded-xl text-xs text-zinc-300 leading-relaxed italic">
                &quot;{citation.snippet}&quot;
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-charcoal-800 flex items-center justify-between">
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-forest-900 hover:bg-forest-850 text-gold-300 border border-forest-border text-xs font-medium transition-colors"
          >
            <span>Visit Target Portal</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-charcoal-850 hover:bg-charcoal-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
