"use client";

import React, { useState, useEffect, useCallback } from "react";
import { PropertyItem } from "@/lib/types";
import { fetchProperties } from "@/lib/api";
import { PropertyCard } from "@/components/PropertyCard";
import { Search, Building2, Filter, X, RefreshCw } from "lucide-react";

interface PropertyExplorerProps {
  onAskAboutProperty: (property: PropertyItem) => void;
  sourceFilter: string;
  setSourceFilter?: (filter: string) => void;
  isFullView?: boolean;
}

export function PropertyExplorer({
  onAskAboutProperty,
  sourceFilter,
  setSourceFilter,
  isFullView = false,
}: PropertyExplorerProps) {
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [selectedCity, setSelectedCity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const loadProperties = useCallback(() => {
    setLoading(true);
    fetchProperties({
      source: sourceFilter === "all" ? undefined : sourceFilter,
      city: selectedCity === "all" ? undefined : selectedCity,
      search: search.trim() || undefined,
    })
      .then((data) => {
        let filtered = data;
        if (selectedCategory !== "all") {
          filtered = filtered.filter((p) =>
            p.property_type?.toLowerCase().includes(selectedCategory.toLowerCase())
          );
        }
        setProperties(filtered);
      })
      .catch((err) => console.error("Failed to load properties:", err))
      .finally(() => setLoading(false));
  }, [sourceFilter, selectedCity, selectedCategory, search]);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadProperties();
  };

  const clearFilters = () => {
    setSearch("");
    setSelectedCity("all");
    setSelectedCategory("all");
    if (setSourceFilter) setSourceFilter("all");
  };

  const hasActiveFilters =
    search.trim() !== "" ||
    selectedCity !== "all" ||
    selectedCategory !== "all" ||
    sourceFilter !== "all";

  const categories = [
    { id: "all", label: "All Types" },
    { id: "apartment", label: "Apartments & Penthouses" },
    { id: "villa", label: "Villas" },
    { id: "duplex", label: "Duplexes" },
    { id: "commercial", label: "Commercial" },
  ];

  const cities = ["all", "Dubai", "Riyadh", "Muscat", "Marbella", "Jeddah", "Lusail"];

  return (
    <div className="flex flex-col h-full overflow-hidden bg-charcoal-950">
      {/* Top Search & Filter Bar */}
      <div className="p-4 sm:p-5 border-b border-charcoal-800 bg-charcoal-900/60 backdrop-blur-md flex flex-col gap-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-gold-500/15 flex items-center justify-center text-gold-400">
              <Building2 className="h-3.5 w-3.5" />
            </div>
            <div>
              <h2 className="font-serif font-bold text-sm sm:text-base text-zinc-100">
                Verified Real Estate Portfolio
              </h2>
              <p className="text-[11px] text-zinc-400 font-mono">
                Indexed DarGlobal Developments & Wasalt Saudi Listings
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-charcoal-800 text-gold-300 border border-charcoal-700">
              {properties.length} {properties.length === 1 ? "Property" : "Properties"}
            </span>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-gold-300 transition-colors"
                title="Clear all filters"
              >
                <X className="h-3 w-3" />
                <span className="hidden sm:inline">Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative">
          <input
            type="text"
            placeholder="Search by project name, developer, luxury brand, or amenity..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-9 py-2 bg-charcoal-950 border border-charcoal-700 rounded-xl text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-gold-border transition-colors shadow-inner"
          />
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-400" />
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                loadProperties();
              }}
              className="absolute right-3 top-2.5 text-zinc-500 hover:text-zinc-300"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </form>

        {/* Category & Location Filters */}
        <div className="flex flex-col gap-2 pt-1">
          {/* Location Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider shrink-0 mr-1">
              Location:
            </span>
            {cities.map((city) => (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap transition-all cursor-pointer ${
                  selectedCity === city
                    ? "bg-forest-850 text-gold-300 border border-forest-border font-semibold shadow-sm"
                    : "bg-charcoal-850 text-zinc-400 hover:text-zinc-200 border border-transparent"
                }`}
              >
                {city === "all" ? "All Locations" : city}
              </button>
            ))}
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider shrink-0 mr-1">
              Category:
            </span>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap transition-all cursor-pointer ${
                  selectedCategory === cat.id
                    ? "bg-gold-500/15 text-gold-300 border border-gold-border font-semibold shadow-sm"
                    : "bg-charcoal-850 text-zinc-400 hover:text-zinc-200 border border-transparent"
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Property Cards Grid */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3 text-zinc-400 text-xs">
            <RefreshCw className="h-5 w-5 text-gold-400 animate-spin" />
            <span>Loading verified properties from vector store...</span>
          </div>
        ) : properties.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-zinc-400 text-xs border border-dashed border-charcoal-800 rounded-2xl bg-charcoal-900/30">
            <Filter className="h-6 w-6 text-zinc-500 mb-2" />
            <p className="font-semibold text-zinc-300 mb-1">No matching properties found</p>
            <p className="max-w-xs text-zinc-500 mb-3">
              No indexed properties match your current search and location criteria.
            </p>
            <button
              onClick={clearFilters}
              className="px-3 py-1.5 rounded-lg bg-charcoal-800 hover:bg-charcoal-700 text-gold-300 text-xs font-medium"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div
            className={`grid gap-4 ${
              isFullView
                ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
                : "grid-cols-1"
            }`}
          >
            {properties.map((property) => (
              <PropertyCard
                key={property.id}
                property={property}
                onAskAbout={onAskAboutProperty}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
