"use client";

import React, { useState, useEffect } from "react";
import {
  Search as SearchIcon,
  SlidersHorizontal,
  Sparkles,
  Zap,
  BookOpen,
  Filter,
  X,
  AlertCircle,
} from "lucide-react";
import { LangFilter } from "@/components/LangFilter";
import { SearchResultCard } from "@/components/SearchResultCard";
import { SearchSkeletonList } from "@/components/LoadingSkeleton";
import { searchArticles } from "@/lib/api";
import { SearchResult } from "@/types";

type SearchMode = "hybrid" | "dense" | "bm25";

const MODES: { id: SearchMode; label: string; desc: string; icon: React.ElementType }[] = [
  {
    id: "hybrid",
    label: "Hybrid",
    desc: "Dense semantic + Sparse BM25 fused",
    icon: Sparkles,
  },
  {
    id: "dense",
    label: "Dense",
    desc: "Multilingual vector embeddings",
    icon: Zap,
  },
  {
    id: "bm25",
    label: "BM25",
    desc: "Lexical & exact keyword index",
    icon: BookOpen,
  },
];

const SUGGESTED_QUERIES = [
  "Elections and voting reforms",
  "Cricket World Cup finals",
  "Reserve Bank repo rate",
  "South Asian monsoon climate",
  "Semiconductor hardware startups",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [selectedLangs, setSelectedLangs] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performSearch = async (targetQuery?: string) => {
    const q = (targetQuery ?? query).trim();
    if (!q) return;

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const data = await searchArticles({
        query: q,
        mode,
        lang_filter: selectedLangs.length > 0 ? selectedLangs : null,
        top_k: 20,
      });
      setResults(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search query failed.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Trigger search when mode changes if query exists
  const handleModeChange = (newMode: SearchMode) => {
    setMode(newMode);
    if (query.trim() && hasSearched) {
      // Re-run with new mode
      setTimeout(() => {
        performSearch();
      }, 50);
    }
  };

  // Re-run search if lang filter changes when search has happened
  const handleLangChange = (langs: string[]) => {
    setSelectedLangs(langs);
    if (query.trim() && hasSearched) {
      setTimeout(() => {
        performSearch();
      }, 50);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-3.5rem)] lg:min-h-screen bg-gray-950 px-4 sm:px-8 py-6 max-w-6xl w-full mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100 tracking-tight flex items-center gap-2">
          <span>Multilingual News Search</span>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Cross-Lingual Index
          </span>
        </h1>
        <p className="text-xs sm:text-sm text-gray-400 mt-1">
          Search over thousands of indexed articles across English, Hindi, Bengali, and Tamil with hybrid reranking
        </p>
      </div>

      {/* Main Search Controls Box */}
      <div className="bg-gray-900/80 border border-gray-800/80 rounded-2xl p-4 sm:p-5 shadow-lg space-y-4">
        {/* Search Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            performSearch();
          }}
          className="relative flex items-center"
        >
          <div className="absolute left-4 text-gray-400 pointer-events-none">
            <SearchIcon className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search keywords, headlines, or entities across all languages..."
            className="w-full pl-12 pr-28 py-3.5 bg-gray-950/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-400 focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/40 transition-all"
          />

          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-24 text-gray-400 hover:text-gray-200 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="absolute right-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold rounded-lg transition-all shadow-md shadow-indigo-600/30"
          >
            Search
          </button>
        </form>

        {/* Filter and Mode Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-1 border-t border-gray-800/60">
          {/* Mode Selector */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-gray-400 mr-1">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Retrieval Mode:</span>
            </div>

            <div className="inline-flex rounded-xl bg-gray-950 p-1 border border-gray-800">
              {MODES.map((m) => {
                const isSelected = mode === m.id;
                const Icon = m.icon;

                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => handleModeChange(m.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isSelected
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "text-gray-400 hover:text-gray-200 hover:bg-gray-900"
                    }`}
                    title={m.desc}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{m.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Language filter */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Filter className="w-3.5 h-3.5" />
              <span>Languages:</span>
            </div>
            <LangFilter
              selected={selectedLangs}
              onChange={handleLangChange}
              showAllOption={true}
            />
          </div>
        </div>
      </div>

      {/* Suggested Quick Queries (if user hasn't searched yet or wants quick ideas) */}
      {!hasSearched && (
        <div className="space-y-2">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Suggested Queries
          </span>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUERIES.map((sq, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(sq);
                  performSearch(sq);
                }}
                className="px-3 py-1.5 rounded-lg bg-gray-900/60 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 text-xs text-gray-300 transition-colors"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results Header / Sorting Meta */}
      {hasSearched && !isLoading && (
        <div className="flex items-center justify-between text-xs text-gray-400 border-b border-gray-800/60 pb-3">
          <div>
            <span>Found </span>
            <span className="font-semibold text-gray-200">{results.length} articles</span>
            <span> matching &ldquo;{query}&rdquo;</span>
          </div>

          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span>Sorted by:</span>
            <span className="text-indigo-400 font-semibold uppercase">
              {mode} Relevance Score
            </span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div>
            <div className="font-semibold">Search request failed</div>
            <p className="text-xs text-rose-300/80">{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && <SearchSkeletonList count={4} />}

      {/* Results List */}
      {!isLoading && hasSearched && results.length > 0 && (
        <div className="space-y-3.5">
          {results.map((item, index) => (
            <SearchResultCard
              key={item.article_id || index}
              result={item}
              index={index}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && hasSearched && results.length === 0 && !error && (
        <div className="text-center py-16 bg-gray-900/30 border border-gray-800/60 rounded-2xl p-6">
          <BookOpen className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-200">
            No matching articles found
          </h3>
          <p className="text-xs text-gray-400 max-w-md mx-auto mt-1 mb-4">
            Try adjusting your query or resetting language filters to broaden coverage across
            English, Hindi, Bengali, and Tamil corpora.
          </p>
          <button
            onClick={() => {
              setSelectedLangs([]);
              performSearch(query);
            }}
            className="px-3.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-200 border border-gray-700 transition-colors"
          >
            Clear Language Filters & Re-search
          </button>
        </div>
      )}
    </div>
  );
}
