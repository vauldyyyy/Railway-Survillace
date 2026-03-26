import React, { useMemo } from 'react';
import useSystemStore from '../store/useSystemStore';

export function ThreatSeverityIndex() {
  const threatScore = useSystemStore((s) => s.threatScore);
  const threatLevel = useSystemStore((s) => s.threatLevel);

  const config = useMemo(() => {
    if (threatScore >= 8) return { color: '#FF3B3B', glow: 'rgba(255,59,59,0.3)', label: 'CRITICAL' };
    if (threatScore >= 6) return { color: '#FFA500', glow: 'rgba(255,165,0,0.3)', label: 'HIGH' };
    if (threatScore >= 3) return { color: '#FBBF24', glow: 'rgba(251,191,36,0.2)', label: 'MEDIUM' };
    return { color: '#10B981', glow: 'rgba(16,185,129,0.2)', label: 'LOW' };
  }, [threatScore]);

  // SVG arc calculation
  const radius = 52;
  const circumference = Math.PI * radius; // semicircle
  const progress = (threatScore / 10) * circumference;

  return (
    <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg p-5">
      <div className="flex justify-between items-center mb-3 border-b border-slate-800 pb-2">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">THREAT SEVERITY INDEX</h3>
        <span
          className="text-[10px] font-mono px-2 py-0.5 rounded border"
          style={{
            color: config.color,
            borderColor: config.color + '44',
            backgroundColor: config.color + '15',
          }}
        >
          {config.label}
        </span>
      </div>

      <div className="flex flex-col items-center py-2">
        {/* Arc Gauge */}
        <svg width="140" height="80" viewBox="0 0 140 80" className="overflow-visible">
          {/* Background arc */}
          <path
            d="M 10 75 A 55 55 0 0 1 130 75"
            fill="none"
            stroke="#1e293b"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Progress arc */}
          <path
            d="M 10 75 A 55 55 0 0 1 130 75"
            fill="none"
            stroke={config.color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${progress} ${circumference}`}
            className="transition-all duration-700 ease-out"
            style={{
              filter: `drop-shadow(0 0 8px ${config.glow})`,
            }}
          />
          {/* Score text */}
          <text x="70" y="65" textAnchor="middle" fill={config.color} fontSize="28" fontWeight="300" fontFamily="JetBrains Mono, monospace">
            {threatScore.toFixed(1)}
          </text>
          <text x="70" y="78" textAnchor="middle" fill="#64748b" fontSize="8" fontFamily="Inter, sans-serif" letterSpacing="2">
            / 10.0
          </text>
        </svg>

        {/* Factors */}
        <div className="flex gap-4 mt-3 text-[10px] text-slate-500 font-mono">
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> Active Threats
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500"></span> Crowd Density
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500"></span> Model Confidence
          </div>
        </div>
      </div>
    </div>
  );
}
