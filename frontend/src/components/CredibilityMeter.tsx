"use client";

import React from "react";
import { ShieldCheck, AlertTriangle, ShieldAlert, Sparkles } from "lucide-react";
import { Credibility } from "@/types";

interface CredibilityMeterProps {
  credibility: Credibility;
  className?: string;
}

export function CredibilityMeter({ credibility, className = "" }: CredibilityMeterProps) {
  const score = credibility.agreement_score;
  const percentage = Math.round(score * 100);

  // Color config based on score threshold
  const getColorConfig = (val: number) => {
    if (val >= 0.7) {
      return {
        bar: "bg-gradient-to-r from-emerald-500 to-teal-400",
        badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
        text: "text-emerald-400",
        icon: ShieldCheck,
        glow: "shadow-emerald-500/20",
      };
    }
    if (val >= 0.4) {
      return {
        bar: "bg-gradient-to-r from-amber-500 to-yellow-400",
        badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
        text: "text-amber-400",
        icon: AlertTriangle,
        glow: "shadow-amber-500/20",
      };
    }
    return {
      bar: "bg-gradient-to-r from-rose-500 to-red-400",
      badge: "bg-rose-500/15 text-rose-400 border-rose-500/30",
      text: "text-rose-400",
      icon: ShieldAlert,
      glow: "shadow-rose-500/20",
    };
  };

  const config = getColorConfig(score);
  const Icon = config.icon;

  return (
    <div
      className={`bg-gray-900/60 border border-gray-800/80 rounded-xl p-3.5 backdrop-blur-sm ${className}`}
    >
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg border ${config.badge}`}>
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-200 flex items-center gap-1.5">
              <span>Cross-source agreement: {percentage}%</span>
              <span className="text-gray-400">·</span>
              <span className={config.text}>{credibility.agreement_label}</span>
            </div>
            <p className="text-[11px] text-gray-400">
              Evaluated across independent regional news outlets and official communiqués
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 text-[11px] font-mono font-medium text-gray-400">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          <span>IndicConsensus v1</span>
        </div>
      </div>

      {/* Progress Bar Container */}
      <div className="w-full bg-gray-800/80 rounded-full h-2 overflow-hidden relative">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${config.bar} ${config.glow}`}
          style={{ width: `${Math.min(100, Math.max(5, percentage))}%` }}
        />
      </div>

      <div className="flex justify-between items-center text-[10px] text-gray-400 mt-1.5 font-mono">
        <span>0% Disputed</span>
        <span>50% Moderate</span>
        <span>100% High Agreement</span>
      </div>
    </div>
  );
}
