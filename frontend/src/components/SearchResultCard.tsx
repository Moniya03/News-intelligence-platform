"use client";

import React from "react";
import { ExternalLink, Tag, Newspaper } from "lucide-react";
import { SearchResult } from "@/types";

interface SearchResultCardProps {
  result: SearchResult;
  index?: number;
}

const LANG_STYLES: Record<string, { label: string; badge: string }> = {
  en: { label: "EN", badge: "bg-blue-500/15 text-blue-400 border-blue-500/30" },
  hi: { label: "HI", badge: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  bn: { label: "BN", badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  ta: { label: "TA", badge: "bg-purple-500/15 text-purple-400 border-purple-500/30" },
};

export function SearchResultCard({ result, index }: SearchResultCardProps) {
  const lang = (result.lang || "en").toLowerCase();
  const langStyle = LANG_STYLES[lang] || {
    label: lang.toUpperCase(),
    badge: "bg-gray-500/15 text-gray-300 border-gray-500/30",
  };

  const formattedScore = typeof result.score === "number" ? result.score.toFixed(2) : "0.00";

  return (
    <article className="bg-gray-900/70 hover:bg-gray-900 border border-gray-800/80 hover:border-gray-700 rounded-xl p-5 transition-all duration-200 group shadow-sm">
      {/* Top Meta Line: [LANG] source · category ... Score: X */}
      <div className="flex items-center justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-md border tracking-wider ${langStyle.badge}`}
          >
            {langStyle.label}
          </span>
          <div className="flex items-center gap-1.5 text-gray-300 font-medium">
            <Newspaper className="w-3.5 h-3.5 text-gray-400" />
            <span>{result.source || "Indic News Network"}</span>
          </div>
          {result.category && (
            <>
              <span className="text-gray-400">·</span>
              <div className="flex items-center gap-1 text-gray-300 text-[11px] bg-gray-800/60 px-2 py-0.5 rounded">
                <Tag className="w-3 h-3 text-gray-400" />
                <span>{result.category}</span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono font-medium">
            <span className="text-[10px] text-gray-400 uppercase">Score:</span>
            <span>{formattedScore}</span>
          </div>

          {result.url && (
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-indigo-400 p-1 rounded hover:bg-gray-800 transition-colors"
              title="Open external article"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Article Title */}
      <h3 className="text-base font-semibold text-gray-100 group-hover:text-indigo-300 transition-colors mb-2 leading-snug">
        {result.url ? (
          <a href={result.url} target="_blank" rel="noopener noreferrer">
            {result.title}
          </a>
        ) : (
          result.title
        )}
      </h3>

      {/* Snippet */}
      <p className="text-xs text-gray-300 leading-relaxed font-sans line-clamp-3">
        {result.snippet}
      </p>

      {/* Footer info */}
      <div className="mt-3 pt-2.5 border-t border-gray-800/40 flex items-center justify-between text-[11px] text-gray-400 font-mono">
        <span>Article ID: {result.article_id}</span>
        {index !== undefined && <span>Result #{index + 1}</span>}
      </div>
    </article>
  );
}
