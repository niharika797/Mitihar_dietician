import React from 'react';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-[#E5E7EB] rounded ${className}`}
    />
  );
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="w-full">
      {/* Header skeleton */}
      <div className="flex gap-4 px-4 py-3 border-b border-[#E5E7EB] bg-[#F9FAFB]">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className={`h-3 ${i === 0 ? 'w-32' : 'flex-1'}`} />
        ))}
      </div>
      {/* Row skeletons */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="flex gap-4 px-4 py-4 border-b border-[#E5E7EB]">
          {Array.from({ length: cols }).map((_, colIdx) => (
            <Skeleton key={colIdx} className={`h-4 ${colIdx === 0 ? 'w-32' : 'flex-1'}`} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-5">
      <div className="flex items-start justify-between mb-3">
        <Skeleton className="w-10 h-10 rounded-full" />
        <Skeleton className="w-12 h-4" />
      </div>
      <Skeleton className="w-20 h-8 mb-2" />
      <Skeleton className="w-28 h-4" />
    </div>
  );
}
