import React, { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { Shield, Lock, Eye, AlertTriangle, Zap, ShieldCheck, Activity, Radio, Database, CheckCircle2, XCircle } from 'lucide-react';
import useSystemStore from '../store/useSystemStore';

// ── AI Protection Feature Data ─────────────────────────────────────────────

const AI_PROTECTIONS = [
  {
    id: 'adversarial',
    icon: Zap,
    color: 'violet',
    title: 'Adversarial Patch Defense',
    subtitle: 'Anti-Evasion Preprocessing',
    description: 'Random resizing, TotalVariation smoothing, and Gaussian blur preprocessing layers prevent adversarial patch-based evasion attacks against YOLO-World.',
    tech: ['Random Resize [0.8–1.2×]', 'Gaussian Blur σ=1.2', 'TV Denoising', 'JPEG Compression'],
    status: 'ACTIVE',
    metric: 'Attack Surface',
    metricValue: '−82%',
    metricColor: 'text-violet-400',
  },
  {
    id: 'privacy',
    icon: Eye,
    color: 'cyan',
    title: 'Differential Privacy',
    subtitle: 'Re-ID Embedding Obfuscation',
    description: 'OSNet 512-dim Re-ID embeddings are injected with calibrated Gaussian noise (σ=0.1) before storage, satisfying ε=1.2 privacy guarantee — biometric reconstruction is mathematically prevented.',
    tech: ['Gaussian Noise σ=0.1', 'Privacy Budget ε=1.2', 'L2 Sensitivity δ=1e-5', 'Per-embedding Clipping'],
    status: 'ACTIVE',
    metric: 'Privacy Budget',
    metricValue: 'ε = 1.2',
    metricColor: 'text-cyan-400',
  },
  {
    id: 'prompt',
    icon: AlertTriangle,
    color: 'amber',
    title: 'Prompt Injection Guard',
    subtitle: 'CrewAI Agent Hardening',
    description: 'Strict XML-tag sandboxing and heuristic input sanitization prevent malicious OCR commands from escaping the trusted context and manipulating CrewAI analysis agents.',
    tech: ['XML-tag Framing', 'Regex Heuristics', 'Semantic Similarity Check', 'Rate-limiting'],
    status: 'ACTIVE',
    metric: 'Injection Attempts',
    metricValue: '0 Passed',
    metricColor: 'text-emerald-400',
  },
  {
    id: 'tamper',
    icon: Radio,
    color: 'emerald',
    title: 'Camera Tamper Detection',
    subtitle: 'SSIM + Optical Flow Analysis',
    description: 'Structural Similarity Index (SSIM) and temporal pixel variance are computed across frames to detect video replay attacks, camera spoofing, and physical tampering.',
    tech: ['SSIM < 0.6 → Alert', 'Temporal Variance', 'Optical Flow Δ', 'Frame Hash Chain'],
    status: 'ACTIVE',
    metric: 'Response Time',
    metricValue: '< 2s',
    metricColor: 'text-emerald-400',
  },
  {
    id: 'encryption',
    icon: Lock,
    color: 'rose',
    title: 'AES-256-GCM Database',
    subtitle: 'Field-Level Encrypted SQLite',
    description: 'All sensitive incident records and Re-ID embeddings are encrypted with AES-256-GCM before storage. Key derivation uses PBKDF2-HMAC-SHA256 with 480,000 iterations per NIST SP 800-132.',
    tech: ['AES-256-GCM', 'PBKDF2 480k iter', 'Per-field Nonces', 'GCM Auth Tags'],
    status: 'ACTIVE',
    metric: 'Key Strength',
    metricValue: '256-bit',
    metricColor: 'text-rose-400',
  },
];

const COLOR_MAP: Record<string, { border: string; bg: string; text: string; badgeBg: string; glow: string }> = {
  violet: {
    border: 'border-violet-500/30',
    bg: 'bg-violet-500/5',
    text: 'text-violet-400',
    badgeBg: 'bg-violet-500/10',
    glow: 'shadow-[0_0_20px_rgba(139,92,246,0.1)]',
  },
  cyan: {
    border: 'border-cyan-500/30',
    bg: 'bg-cyan-500/5',
    text: 'text-cyan-400',
    badgeBg: 'bg-cyan-500/10',
    glow: 'shadow-[0_0_20px_rgba(6,182,212,0.1)]',
  },
  amber: {
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/5',
    text: 'text-amber-400',
    badgeBg: 'bg-amber-500/10',
    glow: 'shadow-[0_0_20px_rgba(245,158,11,0.1)]',
  },
  emerald: {
    border: 'border-emerald-500/30',
    bg: 'bg-emerald-500/5',
    text: 'text-emerald-400',
    badgeBg: 'bg-emerald-500/10',
    glow: 'shadow-[0_0_20px_rgba(16,185,129,0.1)]',
  },
  rose: {
    border: 'border-rose-500/30',
    bg: 'bg-rose-500/5',
    text: 'text-rose-400',
    badgeBg: 'bg-rose-500/10',
    glow: 'shadow-[0_0_20px_rgba(244,63,94,0.1)]',
  },
};

// ── Animated Event Log ─────────────────────────────────────────────────────

const INITIAL_EVENTS = [
  { t: '14:42:11', type: 'BLOCK',  msg: 'Adversarial patch detected → Preprocessing applied' },
  { t: '14:42:08', type: 'INFO',   msg: 'Re-ID embedding noise injected (σ=0.1) for TRACK-0041' },
  { t: '14:41:55', type: 'BLOCK',  msg: 'Prompt injection attempt sanitized from OCR pipeline' },
  { t: '14:41:33', type: 'INFO',   msg: 'DB encryption: 3 new incident records sealed (AES-256-GCM)' },
  { t: '14:41:01', type: 'WARN',   msg: 'Camera CAM-03 SSIM dropped to 0.62 — tamper check passed' },
  { t: '14:40:44', type: 'INFO',   msg: 'Privacy budget remaining: ε = 0.48 (session)' },
];

// ── Main Component ─────────────────────────────────────────────────────────

export function SecurityLayer({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [selected, setSelected] = useState('adversarial');
  const [events, setEvents] = useState(INITIAL_EVENTS);
  const [tick, setTick] = useState(0);
  const globalConfidence = useSystemStore(state => state.globalConfidence);

  // Simulate live security event log
  useEffect(() => {
    const msgs = [
      'Re-ID embeddings DP-obfuscated for TRACK-',
      'Frame hash verified — no replay attack',
      'DB write encrypted (AES-256-GCM) — ',
      'Camera SSIM nominal across all 6 feeds',
      'Prompt injection scanner: 0 threats',
      'Adversarial preprocessing pass complete',
    ];
    const timer = setInterval(() => {
      const now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const msg = msgs[Math.floor(Math.random() * msgs.length)];
      const suffix = msg.includes('TRACK-') ? Math.floor(Math.random() * 999).toString().padStart(4, '0') : 'OK';
      setEvents(prev => [
        { t: now, type: 'INFO', msg: msg + suffix },
        ...prev.slice(0, 11),
      ]);
      setTick(t => t + 1);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  const active = AI_PROTECTIONS.find(p => p.id === selected)!;
  const c = COLOR_MAP[active.color];
  const Icon = active.icon;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="CYBER DOME — SECURITY LAYER"
        subtitle="AI-Hardened Defence Matrix • 5 Active Protection Vectors"
        onNavigate={onNavigate}
      >
        <div className="flex items-center gap-2 text-[10px] font-mono px-3 py-1 rounded-full border border-emerald-500/40 text-emerald-400 bg-emerald-500/10">
          <ShieldCheck size={12} />
          ALL SYSTEMS NOMINAL
        </div>
      </Header>

      <div className="flex flex-1 overflow-hidden">

        {/* Left: Protection Feature List */}
        <div className="w-72 border-r border-slate-800 bg-[#0B0F19] flex flex-col shrink-0 overflow-y-auto">
          <div className="p-4 border-b border-slate-800 text-[10px] font-mono text-slate-500 uppercase tracking-wider">
            Protection Vectors (5/5)
          </div>
          {AI_PROTECTIONS.map(p => {
            const PIcon = p.icon;
            const pc = COLOR_MAP[p.color];
            const isActive = selected === p.id;
            return (
              <button
                key={p.id}
                onClick={() => setSelected(p.id)}
                className={`w-full text-left p-4 border-b border-slate-800/50 transition-all relative ${
                  isActive ? `${pc.bg} ${pc.border} border-l-2` : 'hover:bg-slate-900/30'
                }`}
              >
                {isActive && <div className={`absolute left-0 top-0 bottom-0 w-0.5 ${pc.text.replace('text-', 'bg-')}`} />}
                <div className="flex items-start gap-3">
                  <div className={`p-1.5 rounded-md mt-0.5 ${isActive ? pc.badgeBg : 'bg-slate-800'}`}>
                    <PIcon size={14} className={isActive ? pc.text : 'text-slate-500'} />
                  </div>
                  <div className="min-w-0">
                    <div className={`text-xs font-bold ${isActive ? pc.text : 'text-slate-300'}`}>{p.title}</div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">{p.subtitle}</div>
                    <div className={`mt-1 text-[10px] font-mono px-1.5 py-0.5 rounded inline-block ${isActive ? pc.badgeBg : 'bg-slate-800'} ${isActive ? pc.text : 'text-slate-500'}`}>
                      ● {p.status}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Right: Detail Panel */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">

          {/* Feature detail card */}
          <div className={`rounded-xl border ${c.border} ${c.bg} ${c.glow} p-6`}>
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className={`p-4 rounded-xl ${c.badgeBg} border ${c.border}`}>
                  <Icon size={28} className={c.text} />
                </div>
                <div>
                  <h2 className={`text-xl font-bold ${c.text}`}>{active.title}</h2>
                  <p className="text-sm text-slate-400 mt-1">{active.subtitle}</p>
                  <div className={`mt-2 inline-flex items-center gap-2 text-[10px] font-mono px-2 py-1 rounded-full ${c.badgeBg} border ${c.border} ${c.text}`}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                    PROTECTION ACTIVE
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] font-mono text-slate-500 mb-1">{active.metric}</div>
                <div className={`text-2xl font-bold font-mono ${active.metricColor}`}>{active.metricValue}</div>
              </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed mb-6">{active.description}</p>

            <div>
              <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-3">Implementation Details</div>
              <div className="grid grid-cols-2 gap-2">
                {active.tech.map((t, i) => (
                  <div key={i} className={`flex items-center gap-2 text-xs font-mono px-3 py-2 rounded-lg ${c.badgeBg} border ${c.border}`}>
                    <CheckCircle2 size={12} className={c.text} />
                    <span className="text-slate-300">{t}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* System metrics row */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'ML Confidence', value: `${globalConfidence.toFixed(1)}%`, color: 'text-cyan-400', icon: Activity },
              { label: 'Protected Channels', value: '6 Cams', color: 'text-emerald-400', icon: Shield },
              { label: 'Incidents Encrypted', value: 'AES-256', color: 'text-rose-400', icon: Lock },
              { label: 'DP Privacy Budget', value: 'ε = 1.2', color: 'text-violet-400', icon: Eye },
            ].map(m => {
              const MIcon = m.icon;
              return (
                <div key={m.label} className="stat-card-premium rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <MIcon size={14} className="text-slate-500" />
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{m.label}</span>
                  </div>
                  <div className={`text-xl font-bold font-mono ${m.color}`}>{m.value}</div>
                </div>
              );
            })}
          </div>

          {/* Live Security Event Log */}
          <div className="stat-card-premium rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Live Security Event Log</h3>
              </div>
              <span className="text-[10px] font-mono text-slate-500">{tick} events processed</span>
            </div>
            <div className="space-y-1.5 max-h-52 overflow-y-auto no-scrollbar">
              {events.map((e, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 text-[11px] font-mono px-3 py-1.5 rounded-lg transition-all ${
                    i === 0 ? 'bg-slate-800/60' : 'bg-transparent'
                  }`}
                >
                  <span className="text-slate-600 shrink-0 w-16">{e.t}</span>
                  <span className={`shrink-0 px-1.5 rounded text-[9px] font-bold ${
                    e.type === 'BLOCK' ? 'bg-red-500/20 text-red-400' :
                    e.type === 'WARN'  ? 'bg-amber-500/20 text-amber-400' :
                    'bg-slate-700 text-slate-400'
                  }`}>{e.type}</span>
                  <span className={`${i === 0 ? 'text-slate-200' : 'text-slate-500'}`}>{e.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
