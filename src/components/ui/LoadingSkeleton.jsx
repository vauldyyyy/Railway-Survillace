import React from 'react';

/**
 * LoadingSkeleton — Shimmer placeholder for loading states.
 * @param {number} lines - Number of skeleton lines
 * @param {string} type - 'text' | 'card' | 'chart'
 */
export default function LoadingSkeleton({ lines = 3, type = 'text', className = '' }) {
  if (type === 'card') {
    return (
      <div className={`glass-card p-4 space-y-3 ${className}`}>
        <div className="skeleton h-4 w-1/3" />
        <div className="skeleton h-8 w-2/3" />
        <div className="skeleton h-3 w-1/2" />
      </div>
    );
  }

  if (type === 'chart') {
    return (
      <div className={`glass-card p-4 ${className}`}>
        <div className="skeleton h-4 w-1/4 mb-4" />
        <div className="flex items-end gap-2 h-40">
          {[40, 65, 45, 80, 55, 70, 50, 85, 60, 75].map((h, i) => (
            <div key={i} className="skeleton flex-1" style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-3"
          style={{ width: `${Math.random() * 40 + 60}%` }}
        />
      ))}
    </div>
  );
}
