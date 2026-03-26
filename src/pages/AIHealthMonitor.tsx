import React from 'react';
import { Header } from '../components/Header';
import useSystemStore from '../store/useSystemStore';
import type { EdgeNodeHealth } from '../store/useSystemStore';
import { Server, Cpu, HardDrive, Activity, Wifi, WifiOff, Clock, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, AreaChart, Area } from 'recharts';

function EdgeNodeCard({ node }: { node: EdgeNodeHealth }) {
  const statusConfig = {
    healthy: { color: '#10b981', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: <CheckCircle2 size={12} className="text-emerald-400" />, label: 'HEALTHY' },
    degraded: { color: '#f59e0b', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', icon: <AlertTriangle size={12} className="text-yellow-400" />, label: 'DEGRADED' },
    offline: { color: '#ef4444', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: <XCircle size={12} className="text-red-400" />, label: 'OFFLINE' },
  };
  const cfg = statusConfig[node.status];

  return (
    <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-800/50" style={{ borderLeftWidth: '3px', borderLeftColor: cfg.color }}>
        <Server size={16} style={{ color: cfg.color }} />
        <div className="flex-1">
          <div className="text-sm font-semibold text-slate-200">{node.station}</div>
          <div className="text-[10px] text-slate-500 font-mono">{node.id}</div>
        </div>
        <div className={`flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded ${cfg.bg} ${cfg.border} border`}>
          {cfg.icon}
          <span style={{ color: cfg.color }}>{cfg.label}</span>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Resource Gauges */}
        <div className="grid grid-cols-3 gap-3">
          <ResourceGauge label="CPU" value={node.cpu_pct} icon={<Cpu size={10} />} />
          <ResourceGauge label="GPU" value={node.gpu_pct} icon={<Activity size={10} />} />
          <ResourceGauge label="MEM" value={node.memory_pct} icon={<HardDrive size={10} />} />
        </div>

        {/* Info Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#05080F] rounded p-2">
            <div className="text-[8px] text-slate-600 uppercase tracking-wider">MODELS LOADED</div>
            <div className="text-sm font-mono text-cyan-400 font-bold mt-0.5">{node.models_loaded} / 4</div>
          </div>
          <div className="bg-[#05080F] rounded p-2">
            <div className="text-[8px] text-slate-600 uppercase tracking-wider">UPTIME</div>
            <div className="text-sm font-mono text-slate-300 font-bold mt-0.5">{node.uptime_hours}h</div>
          </div>
        </div>

        {/* Last Heartbeat */}
        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
          <Clock size={10} />
          <span>Last heartbeat: {Math.round((Date.now() - node.last_heartbeat) / 1000)}s ago</span>
        </div>
      </div>
    </div>
  );
}

function ResourceGauge({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  const color = value > 85 ? '#ef4444' : value > 60 ? '#f59e0b' : '#10b981';
  return (
    <div className="text-center">
      <div className="relative w-14 h-14 mx-auto">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="15" fill="none" stroke="#1e293b" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15" fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${value * 0.94} 94`}
            strokeLinecap="round"
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[10px] font-mono font-bold" style={{ color }}>{value}%</span>
        </div>
      </div>
      <div className="flex items-center justify-center gap-1 mt-1">
        <span className="text-slate-600">{icon}</span>
        <span className="text-[8px] text-slate-500 uppercase tracking-wider">{label}</span>
      </div>
    </div>
  );
}

// Simulated latency history
const latencyHistory = Array.from({ length: 30 }, (_, i) => ({
  t: `${i}s`,
  coco: 28 + Math.random() * 10,
  railfod: 32 + Math.random() * 8,
  lstm: 3 + Math.random() * 4,
}));

export function AIHealthMonitor({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const edgeNodes = useSystemStore((s) => s.edgeNodes);
  const metrics = useSystemStore((s) => s.modelMetrics);
  const wsConnected = useSystemStore((s) => s.wsConnected);

  const allModelsLoaded = Object.values(metrics).every((m) => m.status === 'active');
  const healthyNodes = edgeNodes.filter((n) => n.status === 'healthy').length;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="AI HEALTH MONITOR"
        subtitle="EDGE NODE STATUS & INFERENCE PIPELINE HEALTH"
        onNavigate={onNavigate}
      >
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1.5 text-[10px] font-mono px-2.5 py-1 rounded border ${wsConnected ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20'}`}>
            {wsConnected ? <Wifi size={11} /> : <WifiOff size={11} />}
            {wsConnected ? 'WS CONNECTED' : 'WS DISCONNECTED'}
          </div>
        </div>
      </Header>

      <div className="p-6 space-y-6 flex-1 overflow-y-auto">
        {/* Status Summary */}
        <div className="grid grid-cols-4 gap-4">
          <StatusSummaryCard label="EDGE NODES" value={`${healthyNodes}/${edgeNodes.length}`} sub="ONLINE" color={healthyNodes === edgeNodes.length ? '#10b981' : '#f59e0b'} />
          <StatusSummaryCard label="MODELS" value={allModelsLoaded ? '5/5' : `${Object.values(metrics).filter(m => m.status === 'active').length}/5`} sub="LOADED" color={allModelsLoaded ? '#10b981' : '#f59e0b'} />
          <StatusSummaryCard label="AVG LATENCY" value={`${(Object.values(metrics).reduce((s, m) => s + m.latency_ms, 0) / 5).toFixed(0)}ms`} sub="PIPELINE" color="#06b6d4" />
          <StatusSummaryCard label="WEBSOCKET" value={wsConnected ? 'LIVE' : 'DOWN'} sub="STATUS" color={wsConnected ? '#10b981' : '#ef4444'} />
        </div>

        {/* Edge Nodes */}
        <div>
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">EDGE NODES</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {edgeNodes.map((node) => (
              <EdgeNodeCard key={node.id} node={node} />
            ))}
          </div>
        </div>

        {/* Inference Latency Chart */}
        <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg p-5">
          <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-2">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">INFERENCE LATENCY TIMELINE</h3>
            <span className="text-[10px] text-slate-500 font-mono">LAST 30 SECONDS</span>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyHistory} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                <XAxis dataKey="t" fontSize={9} stroke="#334155" tickLine={false} axisLine={false} />
                <YAxis fontSize={9} stroke="#334155" tickLine={false} axisLine={false} unit="ms" />
                <Line type="monotone" dataKey="coco" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="COCO YOLO" />
                <Line type="monotone" dataKey="railfod" stroke="#a855f7" strokeWidth={1.5} dot={false} name="RailFOD" />
                <Line type="monotone" dataKey="lstm" stroke="#10b981" strokeWidth={1.5} dot={false} name="LSTM" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-4 mt-2 text-[10px] font-mono text-slate-500 justify-center">
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-cyan-500 inline-block"></span> COCO YOLO</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-500 inline-block"></span> RailFOD</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-emerald-500 inline-block"></span> LSTM</span>
          </div>
        </div>

        {/* Model Load Status */}
        <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg p-5">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 border-b border-slate-800 pb-2">MODEL LOAD STATUS</h3>
          <div className="space-y-2">
            {Object.entries(metrics).map(([key, model]) => (
              <div key={key} className="flex items-center gap-3 bg-[#05080F] rounded px-4 py-2.5">
                <div className={`w-2 h-2 rounded-full ${model.status === 'active' ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]' : 'bg-red-500 animate-pulse'}`}></div>
                <span className="text-xs text-slate-300 font-semibold flex-1">{model.name}</span>
                <span className="text-[10px] text-slate-500 font-mono">{model.fps.toFixed(1)} FPS</span>
                <span className="text-[10px] text-slate-500 font-mono">{model.latency_ms.toFixed(0)}ms</span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${model.status === 'active' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                  {model.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusSummaryCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="bg-[#0B0F19] border-l-2 p-4" style={{ borderLeftColor: color }}>
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
      <div className="text-2xl font-light font-mono mt-1" style={{ color }}>{value}</div>
      <div className="text-[9px] text-slate-600 font-mono mt-0.5">{sub}</div>
    </div>
  );
}
