"use client";

import React from "react";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-800/70 rounded-md ${className}`}
    />
  );
}

export function SearchSkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-gray-900/40 border border-gray-800/80 rounded-xl p-5 space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton className="w-10 h-5 rounded-md" />
              <Skeleton className="w-28 h-4 rounded" />
              <Skeleton className="w-16 h-4 rounded" />
            </div>
            <Skeleton className="w-20 h-5 rounded" />
          </div>
          <Skeleton className="w-3/4 h-5 rounded" />
          <Skeleton className="w-full h-4 rounded" />
          <Skeleton className="w-5/6 h-4 rounded" />
        </div>
      ))}
    </div>
  );
}

export function ClusterSkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-gray-900/40 border border-gray-800/80 rounded-xl p-5 space-y-4"
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2 flex-1">
              <Skeleton className="w-3/4 h-5 rounded" />
              <Skeleton className="w-20 h-3 rounded" />
            </div>
            <Skeleton className="w-24 h-6 rounded-full" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="w-14 h-4 rounded" />
            <Skeleton className="w-16 h-4 rounded" />
            <Skeleton className="w-12 h-4 rounded" />
          </div>
          <div className="space-y-2 pt-2 border-t border-gray-800/60">
            <Skeleton className="w-full h-2 rounded-full" />
            <div className="flex justify-between">
              <Skeleton className="w-40 h-3 rounded" />
              <Skeleton className="w-12 h-3 rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ChatAnswerSkeleton() {
  return (
    <div className="space-y-4 py-2">
      <div className="flex items-center gap-2 text-indigo-400 text-xs font-medium">
        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
        <span>Synthesizing cross-lingual perspectives...</span>
      </div>
      <div className="space-y-2.5">
        <Skeleton className="w-full h-4 rounded" />
        <Skeleton className="w-11/12 h-4 rounded" />
        <Skeleton className="w-4/5 h-4 rounded" />
        <Skeleton className="w-9/12 h-4 rounded" />
      </div>
      <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
    </div>
  );
}
