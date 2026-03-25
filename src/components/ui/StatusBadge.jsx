import React from 'react';
import { SEVERITY_CONFIG } from '../../data/alerts';

/**
 * StatusBadge — Color-coded severity/status badge.
 * @param {string} severity - 'critical' | 'warning' | 'info' 
 * @param {string} label - Override label text
 * @param {boolean} pulse - Animate with pulse
 * @param {string} size - 'sm' | 'md'
 */
export default function StatusBadge({ severity = 'info', label, pulse = false, size = 'sm' }) {
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;
  const displayLabel = label || config.label;

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-3 py-1',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full font-semibold uppercase tracking-wider
        ${sizeClasses[size]}
        ${pulse ? 'animate-pulse-glow' : ''}
      `}
      style={{
        color: config.color,
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
      }}
    >
      {pulse && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: config.color }}
        />
      )}
      {displayLabel}
    </span>
  );
}
