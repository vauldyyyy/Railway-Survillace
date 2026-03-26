import React from 'react';
import { Header } from '../components/Header';
import useSystemStore from '../store/useSystemStore';
import type { ModelMetrics } from '../store/useSystemStore';
import { Activity, Cpu, Gauge, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, AreaChart, Area } from 'recharts';

function ModelCard({ modelKey, model, accent }: { modelKey: string; model: ModelMetrics; accent: string }) {
  const fpsHistory = Array.from({ length: 20 }, (_, i) => ({
    t: i,
    fps: Math.max(0, model.fps + (Math.random() - 0.5) * 8),
  }));

  const confDistribution = [
    { range: '50-60', count: Math.floor(Math.random() * 5) },
    { range: '60-70', count: Math.floor(Math.random() * 12) + 3 },
    { range: '70-80', count: Math.floor(Math.random() * 25) + 10 },
    { range: '80-90', count: Math.floor(Math.random() * 40) + 20 },
    { range: '90-100', count: Math.floor(Math.random() * 30) + 15 },
  ];

  return (
    <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg overflow-hidden">
      {/* Card Header */}
      <div className={`flex items-center gap-3 px-5 py-3 border-b border-slate-800/50`} style={{ borderLeftWidth: '3px', borderLeftColor: accent }}>
        <Cpu size={16} style={{ color: accent }} />
        <div className="flex-1">
          <div className="text-sm font-semibold text-slate-200">{model.name}</div>
          <div className="text-[10px] text-slate-500 font-mono uppercase">{modelKey.toUpperCase()} ENGINE</div>
        </div>
        <div className={`flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded ${model.status === 'active' ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20' : 'text-slate-500 bg-slate-800'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${model.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600'}`}></span>
          {model.status.toUpperCase()}
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* KPI Row */}
        <div className="grid grid-cols-4 gap-3">
          <KPICell label="FPS" value={model.fps.toFixed(1)} color={model.fps > 25 ? '#10b981' : model.fps > 15 ? '#f59e0b' : '#ef4444'} />
          <KPICell label="LATENCY" value={`${model.latency_ms.toFixed(0)}ms`} color="#06b6d4" />
          <KPICell label="GPU" value={`${model.gpu_util_pct.toFixed(0)}%`} color={model.gpu_util_pct > 80 ? '#ef4444' : '#06b6d4'} />
          <KPICell label="DRIFT" value={model.drift_score.toFixed(3)} color={model.drift_score > 0.1 ? '#f59e0b' : '#10b981'} />
        </div>

        {/* FPS Chart */}
        <div>
          <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-2 font-mono">REAL-TIME FPS</div>
          <div className="h-20">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fpsHistory} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id={`fps-${modelKey}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={accent} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={accent} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="fps" stroke={accent} fill={`url(#fps-${modelKey})`} strokeWidth={1.5} dot={false} />
                <YAxis fontSize={8} stroke="#334155" tickLine={false} axisLine={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Precision / Recall */}
        <div className="grid grid-cols-2 gap-4">
          <MetricBar label="PRECISION" value={model.precision} color="#10b981" />
          <MetricBar label="RECALL" value={model.recall} color="#06b6d4" />
        </div>

        {/* Confidence Distribution */}
        <div>
          <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-2 font-mono">CONFIDENCE DISTRIBUTION</div>
          <div className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={confDistribution} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <Bar dataKey="count" fill={accent} radius={[2, 2, 0, 0]} opacity={0.7} />
                <XAxis dataKey="range" fontSize={7} stroke="#334155" tickLine={false} axisLine={false} />
                <YAxis fontSize={7} stroke="#334155" tickLine={false} axisLine={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICell({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-[#05080F] rounded p-2 text-center">
      <div className="text-[8px] text-slate-600 uppercase tracking-wider">{label}</div>
      <div className="text-sm font-mono font-bold mt-0.5" style={{ color }}>{value}</div>
    </div>
  );
}

function MetricBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-[9px] text-slate-500 uppercase tracking-wider">{label}</span>
        <span className="text-[10px] font-mono" style={{ color }}>{(value * 100).toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${value * 100}%`, backgroundColor: color }}></div>
      </div>
    </div>
  );
}

export function ModelDashboard({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const metrics = useSystemStore((s) => s.modelMetrics);

  const accents: Record<string, string> = {
    coco: '#06b6d4',
    railfod: '#a855f7',
    uav: '#f59e0b',
    lstm: '#10b981',
    tracker: '#3b82f6',
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="MODEL PERFORMANCE DASHBOARD"
        subtitle="REAL-TIME AI MODEL INFERENCE METRICS & HEALTH MONITORING"
        onNavigate={onNavigate}
      >
        <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1">
          <CheckCircle2 size={12} className="text-emerald-400" />
          <span className="text-[10px] text-emerald-400 font-mono">ALL MODELS ACTIVE</span>
        </div>
      </Header>

      <div className="p-6 space-y-6 flex-1 overflow-y-auto">
        {/* Summary Strip */}
        <div className="grid grid-cols-5 gap-3">
          <SummaryCard icon={<Activity size={14} className="text-cyan-400" />} label="TOTAL FPS" value={Object.values(metrics).reduce((s, m) => s + m.fps, 0).toFixed(0)} />
          <SummaryCard icon={<Gauge size={14} className="text-purple-400" />} label="AVG LATENCY" value={`${(Object.values(metrics).reduce((s, m) => s + m.latency_ms, 0) / 5).toFixed(0)}ms`} />
          <SummaryCard icon={<Cpu size={14} className="text-amber-400" />} label="GPU TOTAL" value={`${Object.values(metrics).reduce((s, m) => s + m.gpu_util_pct, 0).toFixed(0)}%`} />
          <SummaryCard icon={<TrendingUp size={14} className="text-emerald-400" />} label="AVG PRECISION" value={`${(Object.values(metrics).reduce((s, m) => s + m.precision, 0) / 5 * 100).toFixed(1)}%`} />
          <SummaryCard icon={<AlertTriangle size={14} className="text-red-400" />} label="MAX DRIFT" value={Math.max(...Object.values(metrics).map(m => m.drift_score)).toFixed(3)} />
        </div>

        {/* Model Cards Grid */}
        <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(metrics).map(([key, model]) => (
            <ModelCard key={key} modelKey={key} model={model} accent={accents[key]} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-[#0B0F19] border-l-2 border-slate-700 p-3 flex items-center gap-3">
      {icon}
      <div>
        <div className="text-[9px] text-slate-500 uppercase tracking-wider">{label}</div>
        <div className="text-lg font-light text-slate-100 font-mono">{value}</div>
      </div>
    </div>
  );
}
