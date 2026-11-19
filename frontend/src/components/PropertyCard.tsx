"use client";

import React, { useState } from "react";
import { PropertyItem } from "@/lib/types";
import { MapPin, ExternalLink, Calendar, ShieldCheck, CheckCircle2, MessageSquare, ChevronDown, ChevronUp } from "lucide-react";

interface PropertyCardProps {
  property: PropertyItem;
  onAskAbout?: (property: PropertyItem) => void;
}

export function PropertyCard({ property, onAskAbout }: PropertyCardProps) {
  const [expanded, setExpanded] = useState<boolean>(false);
  const isDarGlobal = property.source?.toLowerCase().includes("darglobal");
  const isDirect = property.is_directly_scraped || property.provenance_class === "DIRECTLY_SCRAPED";

  return (
    <div className="flex flex-col bg-charcoal-900/90 border border-charcoal-700/80 rounded-xl overflow-hidden hover:border-gold-border transition-all duration-300 shadow-sm hover:shadow-gold group">
      {/* Visual Header */}
      <div className="relative h-28 w-full bg-gradient-to-tr from-charcoal-950 via-charcoal-900 to-forest-900/40 flex items-center justify-between p-3 border-b border-charcoal-800">
        {/* Source Badge */}
        <div className="flex items-center gap-1.5">
          <span
            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shadow-sm ${
              isDarGlobal
                ? "bg-forest-850 text-gold-300 border border-forest-border font-mono"
                : "bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono"
            }`}
          >
            {property.source}
          </span>
        </div>

        {/* Provenance Badge */}
        <div>
          <span
            className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 border font-mono ${
              isDirect
                ? "bg-emerald-950/80 text-emerald-400 border-emerald-800/80"
                : "bg-charcoal-850 text-gold-400 border-gold-border/60"
            }`}
          >
            {isDirect ? (
              <>
                <CheckCircle2 className="h-2.5 w-2.5" />
                Direct Sitemap Scrape
              </>
            ) : (
              <>
                <ShieldCheck className="h-2.5 w-2.5 text-gold-400" />
                Verified Fallback
              </>
            )}
          </span>
        </div>

        {/* Price Tag Overlay */}
        {property.price && (
          <div className="absolute bottom-2.5 left-2.5">
            <span className="font-mono font-bold text-sm text-gold-300 drop-shadow-md">
              {property.price}
            </span>
          </div>
        )}
      </div>

      {/* Details Body */}
      <div className="p-4 flex flex-col flex-1 justify-between gap-3 text-xs">
        <div>
          <div className="flex items-center gap-1 text-zinc-400 text-[11px] mb-1">
            <MapPin className="h-3 w-3 text-gold-400 shrink-0" />
            <span className="truncate">{property.location}</span>
          </div>

          <h3 className="font-serif font-bold text-sm sm:text-base text-zinc-100 group-hover:text-gold-200 transition-colors line-clamp-1">
            {property.title}
          </h3>

          <p className="text-xs text-zinc-400 mt-2 line-clamp-2 leading-relaxed">
            {property.description}
          </p>

          {/* Tags */}
          <div className="flex flex-wrap gap-1.5 mt-3">
            {property.brand_partner && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-forest-900/60 border border-forest-border text-gold-300">
                {property.brand_partner}
              </span>
            )}
            {property.handover_date && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-charcoal-800 text-zinc-300 flex items-center gap-1">
                <Calendar className="h-2.5 w-2.5 text-zinc-400" />
                {property.handover_date}
              </span>
            )}
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-charcoal-800 text-zinc-400">
              {property.property_type}
            </span>
          </div>

          {/* Expandable Amenities */}
          {expanded && property.amenities && property.amenities.length > 0 && (
            <div className="mt-3 pt-3 border-t border-charcoal-800 animate-in fade-in duration-200">
              <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1.5">
                Key Verified Amenities:
              </span>
              <ul className="space-y-1">
                {property.amenities.map((am, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 text-[11px] text-zinc-300">
                    <span className="text-gold-400 leading-4">-</span>
                    <span>{am}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Action Footers */}
        <div className="pt-2.5 border-t border-charcoal-800 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {onAskAbout && (
              <button
                onClick={() => onAskAbout(property)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-forest-900 hover:bg-forest-850 text-gold-300 border border-forest-border text-xs font-medium transition-colors cursor-pointer"
              >
                <MessageSquare className="h-3 w-3" />
                <span>Inquire</span>
              </button>
            )}

            {property.amenities && property.amenities.length > 0 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-0.5 cursor-pointer"
              >
                <span>{expanded ? "Less" : "Amenities"}</span>
                {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </button>
            )}
          </div>

          <a
            href={property.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-zinc-400 hover:text-gold-300 flex items-center gap-1 transition-colors"
          >
            <span>Original Source</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
