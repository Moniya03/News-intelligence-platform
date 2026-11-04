"use client";

import React from "react";
import { FolderGit2, ChevronRight, Layers } from "lucide-react";
import { Cluster } from "@/types";

interface ClusterCardProps {
  cluster: Cluster;
  onClick: (cluster: Cluster) => void;
  isSelected?: boolean;
}

export function ClusterCard({ cluster, onClick, isSelected = false }: ClusterCardProps) {
  const { en = 0, hi = 0, bn = 0, ta = 0 } = cluster.lang_counts;
  const totalInLangs = (en + hi + bn + ta) || cluster.size || 1;

  const pctEn = Math.round((en / totalInLangs) * 100);
  const pctHi = Math.round((hi / totalInLangs) * 100);
  const pctBn = Math.round((bn / totalInLangs) * 100);
  const pctTa = Math.round((ta / totalInLangs) * 100);

  return (
    <div
      onClick={() => onClick(cluster)}
      className={`group cursor-pointer rounded-xl p-5 border transition-all duration-200 flex flex-col justify-between ${
        isSelected
          ? "bg-gray-900 border-indigo-500/80 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/50"
          : "bg-gray-900/70 hover:bg-gray-900 border-gray-800/80 hover:border-gray-700"
      }`}
    >
      <div>
        {/* Top Header: Cluster label & Article count */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 group-hover:scale-105 transition-transform shrink-0 mt-0.5">
              <FolderGit2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-100 group-hover:text-indigo-300 transition-colors leading-snug">
                {cluster.label}
              </h3>
              <span className="text-[11px] text-gray-400 font-mono">
                Cluster #{cluster.id}
              </span>
            </div>
          </div>

          <div className="text-right shrink-0">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700/60 text-xs font-medium text-gray-200">
              <Layers className="w-3 h-3 text-indigo-400" />
              <span>{cluster.size} articles</span>
            </span>
          </div>
        </div>

        {/* Top terms as pills */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {cluster.top_terms.slice(0, 5).map((term, i) => (
            <span
              key={i}
              className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-gray-800/60 text-gray-300 border border-gray-700/50 group-hover:border-gray-700 transition-colors"
            >
              #{term}
            </span>
          ))}
          {cluster.top_terms.length > 5 && (
            <span className="text-[11px] text-gray-400 self-center">
              +{cluster.top_terms.length - 5}
            </span>
          )}
        </div>
      </div>

      {/* Language Distribution */}
      <div className="pt-3 border-t border-gray-800/60">
        {/* Stacked bar */}
        <div className="w-full h-2 rounded-full overflow-hidden flex bg-gray-800 mb-2">
          {en > 0 && (
            <div
              style={{ width: `${pctEn}%` }}
              className="bg-blue-500 h-full"
              title={`English: ${en} (${pctEn}%)`}
            />
          )}
          {hi > 0 && (
            <div
              style={{ width: `${pctHi}%` }}
              className="bg-amber-500 h-full"
              title={`Hindi: ${hi} (${pctHi}%)`}
            />
          )}
          {bn > 0 && (
            <div
              style={{ width: `${pctBn}%` }}
              className="bg-emerald-500 h-full"
              title={`Bengali: ${bn} (${pctBn}%)`}
            />
          )}
          {ta > 0 && (
            <div
              style={{ width: `${pctTa}%` }}
              className="bg-purple-500 h-full"
              title={`Tamil: ${ta} (${pctTa}%)`}
            />
          )}
        </div>

        {/* Counts Legend */}
        <div className="flex items-center justify-between text-[11px] font-mono text-gray-400">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span className="text-gray-300">EN:</span> {en}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              <span className="text-gray-300">HI:</span> {hi}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="text-gray-300">BN:</span> {bn}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
              <span className="text-gray-300">TA:</span> {ta}
            </span>
          </div>

          <div className="flex items-center text-indigo-400 text-xs font-sans group-hover:translate-x-0.5 transition-transform">
            <span>Explore</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>
    </div>
  );
}
