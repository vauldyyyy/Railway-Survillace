import React, { useState, useEffect } from 'react';
import {
  Camera, AlertTriangle, Activity, Shield, Cpu, Radio,
  Eye, Maximize2, Volume2
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import GlassCard from '../components/ui/GlassCard';
import KPICard from '../components/ui/KPICard';
import StatusBadge from '../components/ui/StatusBadge';
import AlertPanel from '../components/alerts/AlertPanel';
import { cameras } from '../data/cameras';
import { kpiData, crowdDensityData, heatmapZones } from '../data/analytics';
import useAlertStore from '../store/useAlertStore';

/**
 * Dashboard — Main monitoring hub with live feeds, alerts, heatmap, and KPIs.
 */
export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const alerts = useAlertStore((s) => s.alerts);

  // Simulate initial data load
  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  const activeCams = cameras.filter(c => c.status === 'online');

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Command Center</h1>
          <p className="text-sm text-text-secondary mt-1">Real-time surveillance monitoring & threat detection</p>
        </div>
        <div className="hidden md:flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/10 border border-success/20">
            <div className="w-2 h-2 rounded-full bg-success animate-pulse-glow" />
            <span className="text-xs font-semibold text-success">ALL SYSTEMS OPERATIONAL</span>
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          icon={Camera}
          label="Active Cameras"
          value={`${activeCams.length}/${cameras.length}`}
          color="cyan"
          trend="stable"
          trendValue="100%"
        />
        <KPICard
          icon={AlertTriangle}
          label="Alerts Today"
          value={kpiData.totalAlerts}
          color="red"
          trend="up"
          trendValue="+12%"
        />
        <KPICard
          icon={Activity}
          label="System Health"
          value={`${kpiData.systemUptime}%`}
          color="green"
          trend="stable"
          trendValue="Stable"
        />
        <KPICard
          icon={Cpu}
          label="AI Confidence"
          value={`${kpiData.predictionConfidence}%`}
          color="cyan"
          trend="up"
          trendValue="+2.1%"
        />
      </div>

      {/* Main Content — Live Feeds + Alert Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Camera Feeds — 2x2 grid */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Eye className="w-5 h-5 text-cyber" />
              Live Surveillance Feed
            </h2>
            <span className="text-xs text-text-muted font-mono">{activeCams.length} FEEDS ACTIVE</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {cameras.slice(0, 4).map((cam) => (
              <CameraFeedCard key={cam.id} camera={cam} />
            ))}
          </div>
        </div>

        {/* Alert Panel */}
        <div className="lg:col-span-1">
          <AlertPanel />
        </div>
      </div>

      {/* Bottom: Heatmap + Crowd Density */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Station Heatmap */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyber" />
            Station Heatmap — Crowd Distribution
          </h3>
          <StationHeatmap zones={heatmapZones} />
        </GlassCard>

        {/* Crowd Density Chart */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyber" />
            Platform Crowd Density (Today)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={crowdDensityData.slice(4, 14)} barGap={1}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2D4A" />
              <XAxis dataKey="time" tick={{ fill: '#8892A5', fontSize: 11 }} axisLine={{ stroke: '#1E2D4A' }} />
              <YAxis tick={{ fill: '#8892A5', fontSize: 11 }} axisLine={{ stroke: '#1E2D4A' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0F1A2E',
                  border: '1px solid #1E2D4A',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: '#E8EDF5',
                }}
              />
              <Bar dataKey="platform1" name="Platform 1" fill="#00E0FF" radius={[4, 4, 0, 0]} />
              <Bar dataKey="platform2" name="Platform 2" fill="#00E0FF88" radius={[4, 4, 0, 0]} />
              <Bar dataKey="platform3" name="Platform 3" fill="#00E0FF44" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>
    </div>
  );
}

/* ========================
   Sub-components
   ======================== */

function CameraFeedCard({ camera }) {
  const isOnline = camera.status === 'online';

  return (
    <div className="glass-card overflow-hidden group relative camera-frame scan-line-overlay">
      {/* Simulated feed background */}
      <div className="aspect-video bg-gradient-to-br from-slate-800 via-gray-900 to-slate-800 relative overflow-hidden">
        {/* Noise pattern */}
        <div className="absolute inset-0 opacity-20" style={{
          backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,224,255,0.03) 2px, rgba(0,224,255,0.03) 4px)`
        }} />

        {/* Camera info overlay */}
        <div className="absolute inset-0 flex flex-col justify-between p-3">
          {/* Top bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
              <span className="text-[10px] font-mono text-text-primary bg-black/50 px-1.5 py-0.5 rounded">
                {camera.id}
              </span>
              {isOnline && (
                <span className="text-[10px] font-mono text-cyber bg-black/50 px-1.5 py-0.5 rounded live-pulse">
                  ● LIVE
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-mono text-text-secondary bg-black/50 px-1.5 py-0.5 rounded">
                {camera.fps} FPS
              </span>
            </div>
          </div>

          {/* Center — timestamp simulation */}
          <div className="flex items-center justify-center">
            {!isOnline && (
              <div className="px-3 py-1.5 rounded bg-danger/20 border border-danger/30">
                <span className="text-xs font-semibold text-danger">SIGNAL LOST</span>
              </div>
            )}
          </div>

          {/* Bottom bar */}
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-text-primary bg-black/50 px-2 py-0.5 rounded font-medium">
              {camera.name}
            </span>
            <div className="flex items-center gap-1.5">
              {isOnline && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-cyber/20 text-cyber border border-cyber/30">
                  AI {camera.aiConfidence}%
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-cyber/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Maximize2 className="w-8 h-8 text-cyber/60" />
        </div>
      </div>
    </div>
  );
}

function StationHeatmap({ zones }) {
  return (
    <div className="relative w-full aspect-[2/1] bg-bg-primary rounded-lg border border-border-subtle overflow-hidden">
      {/* Grid lines */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        {/* Grid */}
        {Array.from({ length: 10 }).map((_, i) => (
          <React.Fragment key={i}>
            <line x1={i * 10} y1="0" x2={i * 10} y2="100" stroke="#1E2D4A" strokeWidth="0.3" />
            <line x1="0" y1={i * 10} x2="100" y2={i * 10} stroke="#1E2D4A" strokeWidth="0.3" />
          </React.Fragment>
        ))}

        {/* Heat zones */}
        {zones.map((zone) => (
          <g key={zone.id}>
            <rect
              x={zone.x}
              y={zone.y}
              width={zone.w}
              height={zone.h}
              rx="2"
              fill={
                zone.intensity > 0.7
                  ? `rgba(255, 59, 59, ${zone.intensity * 0.4})`
                  : zone.intensity > 0.5
                  ? `rgba(255, 165, 0, ${zone.intensity * 0.4})`
                  : `rgba(0, 224, 255, ${zone.intensity * 0.3})`
              }
              stroke={
                zone.intensity > 0.7
                  ? 'rgba(255, 59, 59, 0.3)'
                  : zone.intensity > 0.5
                  ? 'rgba(255, 165, 0, 0.2)'
                  : 'rgba(0, 224, 255, 0.2)'
              }
              strokeWidth="0.5"
              className="transition-all duration-500"
            />
            <text
              x={zone.x + zone.w / 2}
              y={zone.y + zone.h / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#8892A5"
              fontSize="2.5"
              fontFamily="Inter"
            >
              {zone.name}
            </text>
            <text
              x={zone.x + zone.w / 2}
              y={zone.y + zone.h / 2 + 4}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={zone.intensity > 0.7 ? '#FF3B3B' : zone.intensity > 0.5 ? '#FFA500' : '#00E0FF'}
              fontSize="2"
              fontWeight="bold"
              fontFamily="JetBrains Mono"
            >
              {Math.round(zone.intensity * 100)}%
            </text>
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-2 right-2 flex items-center gap-3 bg-black/50 px-2 py-1 rounded text-[9px]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-danger/60" /> High</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-warning/60" /> Medium</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-cyber/40" /> Low</span>
      </div>
    </div>
  );
}
