import React, { useState, useEffect, useRef } from 'react';
import { Header } from '../components/Header';
import { Cpu, Network, Database, Users, Shield, Zap, Activity, GitBranch, CheckCircle2, Clock, RefreshCw } from 'lucide-react';
import useSystemStore from '../store/useSystemStore';

// ── Agent definitions ──────────────────────────────────────────────────────

const AGENTS = [
  {
    id: 'yolo-world',
    name: 'YOLO-World Foundation',
    type: 'Zero-Shot Object Detection',
    arch: 'YOLO-World v8s',
    modelKey: 'coco',
    color: 'cyan',
    icon: Cpu,
    cameras: ['CAM-01 (Our Camera)', 'CAM-02 (Track View)', 'CAM-03 (Platform)', 'CAM-04 (Entry)', 'CAM-05 (Exit)', 'CAM-06 (Edge)'],
    tasks: ['Unattended Baggage', 'Person on Track', 'Fire & Smoke', 'Foreign Object'],
    params: [
      { k: 'Input', v: '640×640 px' },
      { k: 'Backbone', v: 'CSPDarknet' },
      { k: 'Text Prompts', v: '12 classes' },
      { k: 'Threshold', v: '0.55 conf' },
    ],
    badge: 'ZERO-SHOT',
  },
  {
    id: 'railfod',
    name: 'RailFOD YOLOv8',
    type: 'Custom-Trained Detector',
    arch: 'YOLOv8s (Fine-tuned)',
    modelKey: 'railfod',
    color: 'violet',
    icon: Zap,
    cameras: ['CAM-01 (Our Camera)', 'CAM-03 (Platform View)', 'CAM-06 (Edge Camera)'],
    tasks: ['Unattended Baggage Detection', 'Overcrowding & Stampede Risk'],
    params: [
      { k: 'Dataset', v: 'RailFOD23 + YouTube' },
      { k: 'mAP50', v: '≥ 0.82' },
      { k: 'Epochs', v: '120 (2-stage)' },
      { k: 'Augment', v: 'Adverse Conditions' },
    ],
    badge: 'CUSTOM-TRAINED',
  },
  {
    id: 'osnet-reid',
    name: 'OSNet Re-ID Tracker',
    type: 'Cross-Camera Person Tracking',
    arch: 'OSNet (512-dim)',
    modelKey: 'tracker',
    color: 'amber',
    icon: Database,
    cameras: ['ALL 6 CAMERAS (Zero-Knowledge)'],
    tasks: ['Cross-Camera Person Re-Identification', 'Trajectory Mapping', 'Dwell Time Analysis'],
    params: [
      { k: 'Embedding', v: '512-dim L2-norm' },
      { k: 'Threshold', v: 'cosine ≤ 0.72' },
      { k: 'DP Noise', v: 'σ=0.1 Gaussian' },
      { k: 'Privacy', v: 'ε=1.2 guaranteed' },
    ],
    badge: 'DIFFERENTIAL PRIVACY',
  },
  {
    id: 'lstm',
    name: 'LSTM Crowd Forecaster',
    type: 'Temporal Sequence Analysis',
    arch: 'LSTM v2.4 (Bi-directional)',
    modelKey: 'lstm',
    color: 'emerald',
    icon: GitBranch,
    cameras: ['CAM-01 (Our Camera)', 'CAM-03 (Platform View)', 'CAM-06 (Edge Camera)'],
    tasks: ['Overcrowding Prediction', 'Stampede Risk Scoring', 'Density Forecasting (T+3hr)'],
    params: [
      { k: 'Sequence', v: '30-frame window' },
      { k: 'Layers', v: '3× BiLSTM 256' },
      { k: 'Output', v: 'Risk 0.0–1.0' },
      { k: 'Latency', v: '< 5ms' },
    ],
    badge: 'REAL-TIME FORECAST',
  },
  {
    id: 'temporal',
    name: 'Temporal Filter',
    type: 'Hardening & False-Positive Reduction',
    arch: 'Kalman + Hit-streak Filter',
    modelKey: 'uav',
    color: 'rose',
    icon: Shield,
    cameras: ['ALL 6 CAMERAS (Post-processing)'],
    tasks: ['False Positive Suppression', 'Alert Deduplication', 'Track Lifecycle Management'],
    params: [
      { k: 'Min Hits', v: '5 frames' },
      { k: 'Max Age', v: '15 frames' },
      { k: 'Kalman σ', v: '0.1 process' },
      { k: 'Tamper', v: 'SSIM < 0.6' },
    ],
    badge: 'HARDENING LAYER',
  },
];

const COLOR_MAP: Record<string, { border: string; bg: string; text: string; pill: string; barBg: string }> = {
  cyan:    { border: 'border-cyan-500/30',    bg: 'bg-cyan-500/5',    text: 'text-cyan-400',    pill: 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300',    barBg: 'bg-cyan-500' },
  violet:  { border: 'border-violet-500/30',  bg: 'bg-violet-500/5',  text: 'text-violet-400',  pill: 'bg-violet-500/15 border-violet-500/30 text-violet-300',  barBg: 'bg-violet-500' },
  amber:   { border: 'border-amber-500/30',   bg: 'bg-amber-500/5',   text: 'text-amber-400',   pill: 'bg-amber-500/15 border-amber-500/30 text-amber-300',   barBg: 'bg-amber-500' },
  emerald: { border: 'border-emerald-500/30', bg: 'bg-emerald-500/5', text: 'text-emerald-400', pill: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300', barBg: 'bg-emerald-500' },
  rose:    { border: 'border-rose-500/30',    bg: 'bg-rose-500/5',    text: 'text-rose-400',    pill: 'bg-rose-500/15 border-rose-500/30 text-rose-300',    barBg: 'bg-rose-500' },
};

// ── Animated inference log ─────────────────────────────────────────────────

const LOG_TEMPLATES = [
  (fps: number) => `[YOLO-World] Frame inference @ ${fps.toFixed(1)} FPS — 0 detections`,
  (fps: number) => `[OSNet-ReID] Gallery updated — ${Math.floor(Math.random()*5)+1} tracklets active`,
  (fps: number) => `[LSTM] Crowd density prediction: ${(0.2 + Math.random()*0.5).toFixed(2)} risk score`,
  (fps: number) => `[TempFilter] Kalman update — 0 confirmed alerts`,
  (fps: number) => `[RailFOD] Inference complete — no objects flagged`,
  (fps: number) => `[Pipeline] Frame latency: ${(1000/fps).toFixed(0)}ms • FPS: ${fps.toFixed(1)}`,
];

// ── Main Component ─────────────────────────────────────────────────────────

export function AIAgents({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [selected, setSelected] = useState('yolo-world');
  const [logs, setLogs] = useState<string[]>([]);
  const logsRef = useRef<HTMLDivElement>(null);
  const modelMetrics = useSystemStore(state => state.modelMetrics);
  const globalConfidence = useSystemStore(state => state.globalConfidence);

  // Simulated inference log stream
  useEffect(() => {
    const timer = setInterval(() => {
      const fps = 28 + Math.random() * 8;
      const template = LOG_TEMPLATES[Math.floor(Math.random() * LOG_TEMPLATES.length)];
      const ts = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setLogs(prev => [`${ts}  ${template(fps)}`, ...prev.slice(0, 29)]);
    }, 800);
    return () => clearInterval(timer);
  }, []);

  const active = AGENTS.find(a => a.id === selected)!;
  const c = COLOR_MAP[active.color];
  const Icon = active.icon;
  const metrics = modelMetrics[active.modelKey as keyof typeof modelMetrics];

  // GPU/CPU load bar percentage
  const gpuPct = metrics?.gpu_util_pct ?? 0;
  const fpsPct = Math.min(100, ((metrics?.fps ?? 0) / 220) * 100);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="AI AGENTS — INFERENCE NODES"
        subtitle="Autonomous Multi-Model Surveillance Intelligence"
        onNavigate={onNavigate}
      >
        <div className="flex items-center gap-2 text-[10px] font-mono px-3 py-1 rounded-full border border-emerald-500/40 text-emerald-400 bg-emerald-500/10">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          5 AGENTS RUNNING
        </div>
        <div className="text-right">
          <div className="text-[10px] font-mono text-slate-500">AVG CONFIDENCE</div>
          <div className="text-sm font-bold font-mono text-cyan-400">{globalConfidence.toFixed(1)}%</div>
        </div>
      </Header>

      <div className="flex flex-1 overflow-hidden">

        {/* Left: Agent list */}
        <div className="w-64 border-r border-slate-800 bg-[#0B0F19] flex flex-col shrink-0 overflow-y-auto">
          <div className="p-4 border-b border-slate-800 text-[10px] font-mono text-slate-500 uppercase tracking-wider">
            Pipeline Nodes (5/5)
          </div>
          {AGENTS.map(agent => {
            const AIcon = agent.icon;
            const ac = COLOR_MAP[agent.color];
            const isActive = selected === agent.id;
            const am = modelMetrics[agent.modelKey as keyof typeof modelMetrics];
            return (
              <button
                key={agent.id}
                onClick={() => setSelected(agent.id)}
                className={`w-full text-left p-4 border-b border-slate-800/50 transition-all relative ${
                  isActive ? `${ac.bg} border-l-2 ${ac.border}` : 'hover:bg-slate-900/30'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-1.5 rounded-md ${isActive ? `${ac.bg} border ${ac.border}` : 'bg-slate-800'}`}>
                    <AIcon size={14} className={isActive ? ac.text : 'text-slate-500'} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={`text-xs font-bold truncate ${isActive ? ac.text : 'text-slate-300'}`}>{agent.name}</div>
                    <div className="text-[10px] text-slate-500 font-mono truncate">{agent.type}</div>
                  </div>
                </div>
                {isActive && (
                  <div className="mt-2.5 w-full h-0.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full ${ac.barBg} transition-all duration-1000`} style={{ width: `${fpsPct}%` }} />
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Right: Detail + Log */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">

            {/* Agent Header Card */}
            <div className={`rounded-xl border ${c.border} ${c.bg} shadow-[0_0_24px_rgba(0,0,0,0.4)] p-6`}>
              <div className="flex items-start justify-between mb-5">
                <div className="flex items-center gap-4">
                  <div className={`p-4 rounded-xl ${c.bg} border ${c.border}`}>
                    <Icon size={28} className={c.text} />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h2 className={`text-xl font-bold ${c.text}`}>{active.name}</h2>
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${c.pill}`}>{active.badge}</span>
                    </div>
                    <p className="text-sm text-slate-400">{active.type}</p>
                    <p className="text-[11px] text-slate-600 font-mono mt-1">{active.arch}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono px-3 py-1.5 rounded-full border border-emerald-500/40 text-emerald-400 bg-emerald-500/10">
                  <Activity size={10} className="animate-pulse" />
                  INFERENCE ACTIVE
                </div>
              </div>

              {/* Live metrics */}
              <div className="grid grid-cols-4 gap-4 mb-5">
                {[
                  { label: 'FPS', value: metrics?.fps?.toFixed(1) ?? '—', sub: 'frames/sec' },
                  { label: 'Latency', value: `${metrics?.latency_ms?.toFixed(0) ?? '—'}ms`, sub: 'per frame' },
                  { label: 'Precision', value: `${((metrics?.precision ?? 0) * 100).toFixed(1)}%`, sub: 'mAP@0.5' },
                  { label: 'GPU Load', value: `${metrics?.gpu_util_pct?.toFixed(0) ?? 0}%`, sub: 'utilization' },
                ].map(m => (
                  <div key={m.label} className="bg-[#0B0F19] rounded-lg p-3 border border-slate-800">
                    <div className="text-[10px] font-mono text-slate-500 mb-1">{m.label}</div>
                    <div className={`text-lg font-bold font-mono ${c.text}`}>{m.value}</div>
                    <div className="text-[9px] text-slate-600 font-mono">{m.sub}</div>
                  </div>
                ))}
              </div>

              {/* Load bars */}
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-500 mb-1">
                    <span>Throughput</span>
                    <span className={c.text}>{metrics?.fps?.toFixed(1) ?? 0} / 220 FPS max</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full ${c.barBg} transition-all duration-700`} style={{ width: `${fpsPct}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-500 mb-1">
                    <span>GPU Utilization</span>
                    <span className={gpuPct > 80 ? 'text-amber-400' : c.text}>{gpuPct.toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full transition-all duration-700 ${gpuPct > 80 ? 'bg-amber-500' : c.barBg}`} style={{ width: `${gpuPct}%` }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Camera scope + tasks + model params */}
            <div className="grid grid-cols-3 gap-4">
              {/* Camera scope */}
              <div className="stat-card-premium rounded-xl p-4">
                <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-3">Camera Scope</div>
                <div className="space-y-1.5">
                  {active.cameras.map((cam, i) => (
                    <div key={i} className={`flex items-center gap-2 text-[11px] font-mono px-2 py-1.5 rounded-lg ${c.bg} border ${c.border}`}>
                      <CheckCircle2 size={10} className={c.text} />
                      <span className="text-slate-300">{cam}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Active tasks */}
              <div className="stat-card-premium rounded-xl p-4">
                <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-3">Detection Tasks</div>
                <div className="space-y-1.5">
                  {active.tasks.map((task, i) => (
                    <div key={i} className="flex items-center gap-2 text-[11px] px-2 py-1.5 rounded-lg bg-slate-800/50">
                      <span className={`w-1.5 h-1.5 rounded-full ${c.barBg} shrink-0`} />
                      <span className="text-slate-300">{task}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Model params */}
              <div className="stat-card-premium rounded-xl p-4">
                <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-3">Model Params</div>
                <div className="space-y-2">
                  {active.params.map((p, i) => (
                    <div key={i} className="flex justify-between items-center text-[11px] font-mono">
                      <span className="text-slate-500">{p.k}</span>
                      <span className={`${c.text} font-bold`}>{p.v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Real-time inference log */}
          <div className="border-t border-slate-800 bg-[#060a12] flex flex-col" style={{ height: '170px' }}>
            <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-800/50">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Real-Time Inference Log</span>
              <RefreshCw size={10} className="text-slate-600 animate-spin" />
            </div>
            <div ref={logsRef} className="flex-1 overflow-y-auto no-scrollbar px-4 py-2 space-y-0.5 font-mono text-[10px] text-slate-500">
              {logs.map((log, i) => (
                <div key={i} className={`${i === 0 ? 'text-slate-300' : ''} transition-colors`}>
                  {log}
                </div>
              ))}
              {logs.length === 0 && (
                <div className="text-slate-700 cursor-blink">Awaiting inference frames</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
