"use client";

import React, { useState } from "react";
import { ExternalLink, ChevronDown, ChevronUp, ShieldCheck, AlertTriangle, AlertCircle } from "lucide-react";
import { Citation } from "@/types";

interface CitationCardProps {
  citation: Citation;
  index?: number;
}

const LANG_CONFIG: Record<string, { label: string; badge: string }> = {
  en: { label: "EN", badge: "bg-blue-500/15 text-blue-400 border-blue-500/30" },
  hi: { label: "HI", badge: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  bn: { label: "BN", badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  ta: { label: "TA", badge: "bg-purple-500/15 text-purple-400 border-purple-500/30" },
};

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const langStyle = LANG_CONFIG[citation.lang.toLowerCase()] || {
    label: citation.lang.toUpperCase(),
    badge: "bg-gray-500/15 text-gray-300 border-gray-500/30",
  };

  const getVeracityBadge = () => {
    const v = citation.veracity.toLowerCase();
    if (v.includes("reliable")) {
      return {
        icon: ShieldCheck,
        style: "bg-emerald-950/60 text-emerald-300 border-emerald-800/60",
        dot: "bg-emerald-400",
      };
    }
    if (v.includes("uncertain")) {
      return {
        icon: AlertTriangle,
        style: "bg-amber-950/60 text-amber-300 border-amber-800/60",
        dot: "bg-amber-400",
      };
    }
    return {
      icon: AlertCircle,
      style: "bg-rose-950/60 text-rose-300 border-rose-800/60",
      dot: "bg-rose-400",
    };
  };

  const veracity = getVeracityBadge();
  const VeracityIcon = veracity.icon;

  return (
    <div className="bg-gray-900/80 hover:bg-gray-900 border border-gray-800/80 hover:border-gray-700/80 rounded-xl p-4 transition-all duration-200 shadow-sm flex flex-col justify-between">
      <div>
        {/* Header: Lang badge, source, optional index */}
        <div className="flex items-center justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-md border tracking-wider ${langStyle.badge}`}
            >
              {langStyle.label}
            </span>
            <span className="text-xs font-semibold text-gray-300 truncate max-w-[200px]">
              {citation.source}
            </span>
            {index !== undefined && (
              <span className="text-[10px] font-mono text-gray-400">
                [#{index + 1}]
              </span>
            )}
          </div>

          {citation.url && (
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-indigo-400 transition-colors p-1 rounded-md hover:bg-gray-800"
              title="Open source article"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>

        {/* Title */}
        <h4 className="text-sm font-semibold text-gray-100 leading-snug mb-2 group">
          {citation.url ? (
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-300 transition-colors"
            >
              {citation.title}
            </a>
          ) : (
            citation.title
          )}
        </h4>

        {/* Snippet with Expand / Collapse */}
        <div className="text-xs text-gray-300 mb-3">
          <p
            className={`leading-relaxed italic border-l-2 border-gray-700 pl-2.5 py-0.5 text-gray-300 ${
              !expanded ? "line-clamp-2" : ""
            }`}
          >
            &ldquo;{citation.snippet}&rdquo;
          </p>
          {citation.snippet.length > 110 && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 mt-1 flex items-center gap-0.5 font-medium cursor-pointer"
            >
              {expanded ? (
                <>
                  <span>Show less</span>
                  <ChevronUp className="w-3 h-3" />
                </>
              ) : (
                <>
                  <span>Show more</span>
                  <ChevronDown className="w-3 h-3" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Veracity Footer */}
      <div className="pt-2 border-t border-gray-800/60 mt-1">
        <div
          className={`flex items-start gap-1.5 px-2.5 py-1.5 rounded-lg border text-[11px] leading-tight ${veracity.style}`}
        >
          <VeracityIcon className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">{citation.veracity}</span>
            {citation.reason && (
              <span className="text-gray-300 opacity-90 block mt-0.5">
                {citation.reason}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
