"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Search,
  LayoutGrid,
  Radio,
  ExternalLink,
  Menu,
  X,
  Languages,
} from "lucide-react";
import { checkHealth } from "@/lib/api";

function GithubIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

const NAV_ITEMS = [
  {
    name: "Chat",
    href: "/chat",
    icon: MessageSquare,
    badge: "AI RAG",
    description: "Multilingual QA & Synthesis",
  },
  {
    name: "Search",
    href: "/search",
    icon: Search,
    badge: "Hybrid",
    description: "Semantic & Keyword Retrieval",
  },
  {
    name: "Clusters",
    href: "/clusters",
    icon: LayoutGrid,
    badge: "Topics",
    description: "Cross-lingual Story Grouping",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function verifyBackend() {
      try {
        const health = await checkHealth();
        if (mounted) {
          setBackendStatus(health.status === "offline" ? "offline" : "online");
        }
      } catch {
        if (mounted) {
          setBackendStatus("offline");
        }
      }
    }
    verifyBackend();
    const timer = setInterval(verifyBackend, 15000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const navContent = (
    <div className="flex flex-col h-full justify-between">
      {/* Top Header / Logo */}
      <div>
        <div className="px-5 py-6 border-b border-gray-800/80">
          <Link href="/chat" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200">
              <Languages className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-base text-gray-100 flex items-center gap-1.5 tracking-tight">
                <span>IndicNews</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Intel
                </span>
              </div>
              <p className="text-xs text-gray-400">Multilingual Intelligence</p>
            </div>
          </Link>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1.5 mt-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/80 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`p-1.5 rounded-lg transition-colors ${
                      isActive
                        ? "bg-indigo-500/20 text-indigo-400"
                        : "text-gray-400 group-hover:text-gray-200 group-hover:bg-gray-800"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="leading-tight">{item.name}</div>
                    <div className="text-[11px] text-gray-400 font-normal leading-none mt-0.5">
                      {item.description}
                    </div>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                    isActive
                      ? "bg-indigo-500/20 text-indigo-300"
                      : "bg-gray-900 text-gray-400 group-hover:bg-gray-800"
                  }`}
                >
                  {item.badge}
                </span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom Footer Section */}
      <div className="p-4 border-t border-gray-800/80 space-y-3 bg-gray-950/60">
        {/* Backend Status indicator */}
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-900/60 border border-gray-800/80 text-xs">
          <div className="flex items-center gap-2">
            <Radio
              className={`w-3.5 h-3.5 ${
                backendStatus === "online"
                  ? "text-emerald-400 animate-pulse"
                  : backendStatus === "checking"
                  ? "text-amber-400"
                  : "text-rose-400"
              }`}
            />
            <span className="text-gray-300 font-medium">FastAPI Engine</span>
          </div>
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
              backendStatus === "online"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : backendStatus === "checking"
                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
            }`}
          >
            {backendStatus === "online" ? "Live :8000" : backendStatus === "checking" ? "Checking" : "Offline / Demo"}
          </span>
        </div>

        {/* Supported Languages Tag */}
        <div className="px-3 py-2 rounded-lg bg-gray-900/40 border border-gray-800/60 text-[11px] text-gray-400 flex items-center justify-between">
          <span>Corpus: Indic 4L</span>
          <div className="flex gap-1 font-mono text-[10px]">
            <span className="text-blue-400">EN</span>
            <span className="text-amber-400">HI</span>
            <span className="text-emerald-400">BN</span>
            <span className="text-purple-400">TA</span>
          </div>
        </div>

        {/* GitHub link */}
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-900/80 transition-colors group"
        >
          <div className="flex items-center gap-2">
            <GithubIcon className="w-4 h-4 text-gray-400 group-hover:text-gray-200" />
            <span>Repository</span>
          </div>
          <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
        </a>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Header Bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-gray-950/90 backdrop-blur-md border-b border-gray-800/80 flex items-center justify-between px-4 z-40">
        <Link href="/chat" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Languages className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-sm text-gray-100">IndicNews Intel</span>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-300 hover:text-white"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/70 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile Drawer */}
      <aside
        className={`lg:hidden fixed top-14 left-0 bottom-0 w-64 bg-gray-950 border-r border-gray-800/80 z-50 transform transition-transform duration-200 ease-in-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {navContent}
      </aside>

      {/* Desktop Fixed Sidebar (width: 240px) */}
      <aside className="hidden lg:flex flex-col fixed top-0 left-0 bottom-0 w-[240px] bg-gray-950 border-r border-gray-800/80 z-30">
        {navContent}
      </aside>
    </>
  );
}
