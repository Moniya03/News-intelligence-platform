"use client";

import React from "react";

export interface LangFilterProps {
  selected: string[];
  onChange: (langs: string[]) => void;
  className?: string;
  showAllOption?: boolean;
}

interface LanguageOption {
  code: string;
  label: string;
  nativeLabel: string;
  activeColor: string;
  dotColor: string;
}

const LANGUAGES: LanguageOption[] = [
  {
    code: "en",
    label: "English",
    nativeLabel: "EN",
    activeColor: "bg-blue-600 border-blue-500 text-white shadow-blue-500/20",
    dotColor: "bg-blue-400",
  },
  {
    code: "hi",
    label: "Hindi",
    nativeLabel: "हिन्दी",
    activeColor: "bg-amber-600 border-amber-500 text-white shadow-amber-500/20",
    dotColor: "bg-amber-400",
  },
  {
    code: "bn",
    label: "Bengali",
    nativeLabel: "বাংলা",
    activeColor: "bg-emerald-600 border-emerald-500 text-white shadow-emerald-500/20",
    dotColor: "bg-emerald-400",
  },
  {
    code: "ta",
    label: "Tamil",
    nativeLabel: "தமிழ்",
    activeColor: "bg-purple-600 border-purple-500 text-white shadow-purple-500/20",
    dotColor: "bg-purple-400",
  },
];

export function LangFilter({
  selected,
  onChange,
  className = "",
  showAllOption = true,
}: LangFilterProps) {
  const isAllSelected =
    selected.length === 0 || selected.length === LANGUAGES.length;

  const toggleLanguage = (code: string) => {
    if (selected.includes(code)) {
      const next = selected.filter((c) => c !== code);
      onChange(next);
    } else {
      onChange([...selected, code]);
    }
  };

  const handleSelectAll = () => {
    // If all are currently active, select none (which represents all in API, or reset)
    if (isAllSelected) {
      onChange([]);
    } else {
      onChange(LANGUAGES.map((l) => l.code));
    }
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {showAllOption && (
        <button
          type="button"
          onClick={handleSelectAll}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${
            selected.length === 0 || selected.length === 4
              ? "bg-gray-100 text-gray-900 border-white shadow-sm font-semibold"
              : "border-gray-800 text-gray-400 hover:text-gray-200 hover:border-gray-700 bg-gray-900/60"
          }`}
        >
          All Languages
        </button>
      )}

      {LANGUAGES.map((lang) => {
        const isSelected = selected.includes(lang.code);

        return (
          <button
            key={lang.code}
            type="button"
            onClick={() => toggleLanguage(lang.code)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 shadow-sm ${
              isSelected
                ? `${lang.activeColor}`
                : "border-gray-800 text-gray-400 hover:text-gray-200 hover:border-gray-700 bg-gray-900/60"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isSelected ? "bg-white" : lang.dotColor
              }`}
            />
            <span className="font-semibold uppercase tracking-wider">{lang.code}</span>
            <span className="opacity-75 text-[11px] hidden sm:inline">
              ({lang.nativeLabel})
            </span>
          </button>
        );
      })}
    </div>
  );
}
