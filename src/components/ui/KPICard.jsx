import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * KPICard — Key Performance Indicator display card.
 * @param {ReactNode} icon - Lucide icon component
 * @param {string} label - KPI label
 * @param {string|number} value - KPI value
 * @param {string} trend - 'up' | 'down' | 'stable'
 * @param {string} trendValue - e.g. "+12%"
 * @param {string} color - 'cyan' | 'red' | 'orange' | 'green'
 */
export default function KPICard({ icon: Icon, label, value, trend, trendValue, color = 'cyan' }) {
  const colorMap = {
    cyan: { text: 'text-cyber', bg: 'bg-cyber/10', glow: 'shadow-glow-cyan' },
    red: { text: 'text-danger', bg: 'bg-danger/10', glow: 'shadow-glow-red' },
    orange: { text: 'text-warning', bg: 'bg-warning/10', glow: 'shadow-glow-orange' },
    green: { text: 'text-success', bg: 'bg-success/10', glow: '' },
  };

  const colors = colorMap[color] || colorMap.cyan;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-danger' : trend === 'down' ? 'text-success' : 'text-text-secondary';

  return (
    <div className={`glass-card p-4 relative overflow-hidden group transition-all duration-300 hover:${colors.glow}`}>
      {/* Background glow effect */}
      <div className={`absolute -top-10 -right-10 w-24 h-24 ${colors.bg} rounded-full blur-2xl opacity-50 group-hover:opacity-80 transition-opacity`} />
      
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <div className={`p-2 rounded-lg ${colors.bg}`}>
            {Icon && <Icon className={`w-5 h-5 ${colors.text}`} />}
          </div>
          {trend && (
            <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
              <TrendIcon className="w-3 h-3" />
              <span>{trendValue}</span>
            </div>
          )}
        </div>
        <p className="text-2xl font-bold text-text-primary mb-1">{value}</p>
        <p className="text-xs text-text-secondary uppercase tracking-wider">{label}</p>
      </div>
    </div>
  );
}
