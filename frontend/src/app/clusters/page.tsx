"use client";

import React, { useState, useEffect } from "react";
import {
  Layers,
  X,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Search,
  FolderGit2,
  Newspaper,
  Tag,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { ClusterCard } from "@/components/ClusterCard";
import { ClusterSkeletonGrid, Skeleton } from "@/components/LoadingSkeleton";
import { getClusters, getClusterDetail } from "@/lib/api";
import { Cluster, ClusterDetail, ClusterArticle } from "@/types";

const LANG_CONFIG: Record<string, { label: string; badge: string }> = {
  en: { label: "EN", badge: "bg-blue-500/15 text-blue-400 border-blue-500/30" },
  hi: { label: "HI", badge: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  bn: { label: "BN", badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  ta: { label: "TA", badge: "bg-purple-500/15 text-purple-400 border-purple-500/30" },
};

export default function ClustersPage() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [filterQuery, setFilterQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected cluster for detail drawer
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [detailData, setDetailData] = useState<ClusterDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const loadClusters = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getClusters();
      setClusters(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load story clusters.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadClusters();
  }, []);

  const handleSelectCluster = async (cluster: Cluster) => {
    setSelectedCluster(cluster);
    setPage(1);
    setIsDetailLoading(true);
    try {
      const detail = await getClusterDetail(cluster.id, 1, pageSize);
      setDetailData(detail);
    } catch {
      // In case detail fails, fallback with minimal
      setDetailData({
        cluster,
        articles: [],
        total: cluster.size,
      });
    } finally {
      setIsDetailLoading(false);
    }
  };

  const handlePageChange = async (newPage: number) => {
    if (!selectedCluster || newPage < 1) return;
    setPage(newPage);
    setIsDetailLoading(true);
    try {
      const detail = await getClusterDetail(selectedCluster.id, newPage, pageSize);
      setDetailData(detail);
    } finally {
      setIsDetailLoading(false);
    }
  };

  const filteredClusters = clusters.filter(
    (c) =>
      c.label.toLowerCase().includes(filterQuery.toLowerCase()) ||
      c.top_terms.some((t) => t.toLowerCase().includes(filterQuery.toLowerCase()))
  );

  const totalStories = clusters.reduce((acc, c) => acc + c.size, 0);

  return (
    <div className="flex flex-col min-h-[calc(100vh-3.5rem)] lg:min-h-screen bg-gray-950 px-4 sm:px-8 py-6 max-w-7xl w-full mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-100 tracking-tight flex items-center gap-2">
            <span>Cross-Lingual Story Clusters</span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              HDBSCAN + IndicBERT
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-gray-400 mt-1">
            Unsupervised cross-lingual clustering grouping shared events across English, Hindi, Bengali, and Tamil
          </p>
        </div>

        {/* Global Stats */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-2 rounded-xl bg-gray-900/80 border border-gray-800 text-xs">
            <span className="text-gray-400">Total Clusters:</span>{" "}
            <span className="font-semibold text-gray-100 font-mono">
              {clusters.length}
            </span>
          </div>
          <div className="px-3.5 py-2 rounded-xl bg-gray-900/80 border border-gray-800 text-xs">
            <span className="text-gray-400">Indexed Articles:</span>{" "}
            <span className="font-semibold text-indigo-400 font-mono">
              {totalStories}
            </span>
          </div>
          <button
            onClick={loadClusters}
            className="p-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
            title="Refresh clusters"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="relative flex items-center max-w-md">
        <Search className="w-4 h-4 text-gray-400 absolute left-3.5 pointer-events-none" />
        <input
          type="text"
          value={filterQuery}
          onChange={(e) => setFilterQuery(e.target.value)}
          placeholder="Filter clusters by topic or keyword..."
          className="w-full pl-10 pr-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl text-xs text-gray-100 placeholder-gray-400 focus:outline-none focus:border-indigo-500/60"
        />
        {filterQuery && (
          <button
            onClick={() => setFilterQuery("")}
            className="absolute right-3 text-gray-400 hover:text-gray-200 p-0.5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div>
            <div className="font-semibold">Failed to fetch clusters</div>
            <p className="text-xs text-rose-300/80">{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading ? (
        <ClusterSkeletonGrid count={6} />
      ) : (
        /* 3-Column Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClusters.map((cluster) => (
            <ClusterCard
              key={cluster.id}
              cluster={cluster}
              onClick={handleSelectCluster}
              isSelected={selectedCluster?.id === cluster.id}
            />
          ))}
        </div>
      )}

      {/* Slide-over Detail Panel */}
      {selectedCluster && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
            onClick={() => setSelectedCluster(null)}
          />

          {/* Slide-over Drawer */}
          <div className="fixed inset-y-0 right-0 max-w-2xl w-full bg-gray-950 border-l border-gray-800 z-50 shadow-2xl flex flex-col transform transition-transform duration-300 ease-out">
            {/* Header */}
            <div className="p-5 border-b border-gray-800/80 flex items-start justify-between gap-4 bg-gray-950/80">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    Cluster #{selectedCluster.id}
                  </span>
                  <span className="text-xs text-gray-400">
                    {selectedCluster.size} total articles
                  </span>
                </div>
                <h2 className="text-lg font-bold text-gray-100 leading-snug">
                  {selectedCluster.label}
                </h2>
              </div>

              <button
                onClick={() => setSelectedCluster(null)}
                className="p-1.5 rounded-lg bg-gray-900 border border-gray-800 text-gray-400 hover:text-gray-100 hover:bg-gray-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Cluster Metadata Details */}
            <div className="p-5 border-b border-gray-800/80 bg-gray-900/30 space-y-4">
              {/* Top terms */}
              <div>
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Salient Cross-Lingual Keywords
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {selectedCluster.top_terms.map((term, i) => (
                    <span
                      key={i}
                      className="text-xs font-mono px-2.5 py-1 rounded-md bg-gray-800 text-gray-200 border border-gray-700/80"
                    >
                      #{term}
                    </span>
                  ))}
                </div>
              </div>

              {/* Language Distribution Breakdown */}
              <div>
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Language Distribution
                </span>
                <div className="grid grid-cols-4 gap-2">
                  <div className="p-2.5 rounded-lg bg-blue-950/30 border border-blue-900/40 text-center">
                    <div className="text-[11px] font-semibold text-blue-400">English</div>
                    <div className="text-base font-bold text-gray-100 font-mono">
                      {selectedCluster.lang_counts.en || 0}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-900/40 text-center">
                    <div className="text-[11px] font-semibold text-amber-400">Hindi</div>
                    <div className="text-base font-bold text-gray-100 font-mono">
                      {selectedCluster.lang_counts.hi || 0}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-900/40 text-center">
                    <div className="text-[11px] font-semibold text-emerald-400">Bengali</div>
                    <div className="text-base font-bold text-gray-100 font-mono">
                      {selectedCluster.lang_counts.bn || 0}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-purple-950/30 border border-purple-900/40 text-center">
                    <div className="text-[11px] font-semibold text-purple-400">Tamil</div>
                    <div className="text-base font-bold text-gray-100 font-mono">
                      {selectedCluster.lang_counts.ta || 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Articles List in Cluster */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                <span className="font-semibold uppercase tracking-wider text-gray-300">
                  Cluster Articles ({detailData?.articles.length || 0})
                </span>
                <span>Page {page}</span>
              </div>

              {isDetailLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="p-4 rounded-xl bg-gray-900/50 border border-gray-800/80 space-y-2"
                    >
                      <Skeleton className="w-1/3 h-4" />
                      <Skeleton className="w-3/4 h-5" />
                      <Skeleton className="w-1/2 h-3" />
                    </div>
                  ))}
                </div>
              ) : detailData && detailData.articles.length > 0 ? (
                detailData.articles.map((art: ClusterArticle, i) => {
                  const lang = (art.lang || "en").toLowerCase();
                  const langStyle = LANG_CONFIG[lang] || {
                    label: lang.toUpperCase(),
                    badge: "bg-gray-500/15 text-gray-300 border-gray-500/30",
                  };

                  return (
                    <div
                      key={art.article_id || i}
                      className="p-4 rounded-xl bg-gray-900/60 hover:bg-gray-900 border border-gray-800/80 hover:border-gray-700 transition-colors space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border ${langStyle.badge}`}
                          >
                            {langStyle.label}
                          </span>
                          <span className="text-xs font-semibold text-gray-300 flex items-center gap-1">
                            <Newspaper className="w-3 h-3 text-gray-400" />
                            {art.source}
                          </span>
                          {art.category && (
                            <span className="text-[11px] text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                              {art.category}
                            </span>
                          )}
                        </div>

                        {art.url && (
                          <a
                            href={art.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-gray-400 hover:text-indigo-400 p-1 rounded"
                            title="Open article"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>

                      <h4 className="text-sm font-semibold text-gray-100 leading-snug">
                        {art.url ? (
                          <a
                            href={art.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-indigo-300"
                          >
                            {art.title}
                          </a>
                        ) : (
                          art.title
                        )}
                      </h4>

                      <div className="text-[10px] font-mono text-gray-400">
                        Article ID: {art.article_id}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-gray-400 text-xs">
                  No articles loaded for this cluster.
                </div>
              )}
            </div>

            {/* Pagination Controls */}
            <div className="p-4 border-t border-gray-800/80 flex items-center justify-between bg-gray-950/90">
              <button
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1 || isDetailLoading}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 disabled:opacity-40 text-xs text-gray-300 hover:text-white transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous</span>
              </button>

              <span className="text-xs text-gray-400 font-mono">
                Page {page}
              </span>

              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={isDetailLoading || (detailData ? detailData.articles.length < pageSize : false)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 disabled:opacity-40 text-xs text-gray-300 hover:text-white transition-colors"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
