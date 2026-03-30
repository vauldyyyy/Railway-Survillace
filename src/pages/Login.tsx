import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck, Lock, User, AlertTriangle, Eye, EyeOff,
  Terminal, Wifi, Activity
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface LoginProps {
  onLoginSuccess: (token: string, operator: OperatorInfo) => void;
}

interface OperatorInfo {
  id:           string;
  display_name: string;
  role:         string;
  clearance:    string;
}

// ─── Boot log lines shown in the terminal panel ───────────────────────────────

const BOOT_LINES = [
  '> Initializing RailGuard AI v3.1.0...',
  '> Loading YOLOv8n model weights... OK',
  '> Binding CamGear streams [6/6]... OK',
  '> AES-256-GCM encryption layer... ACTIVE',
  '> Differential privacy engine (ε=1.2)... ACTIVE',
  '> Adversarial patch defense... ACTIVE',
  '> Prompt injection guard... ACTIVE',
  '> JWT HS256 auth service... LISTENING',
  '> ISEA Phase III — CyberDome 2026',
  '> Awaiting operator authentication...',
];

// ─── Scanline grid SVG background ────────────────────────────────────────────

function GridBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Dot grid */}
      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage: 'radial-gradient(#06b6d4 1px, transparent 1px)',
          backgroundSize:  '28px 28px',
        }}
      />
      {/* Radial glow top-left */}
      <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-cyan-500/5 blur-3xl" />
      {/* Radial glow bottom-right */}
      <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] rounded-full bg-indigo-500/5 blur-3xl" />
      {/* Horizontal scan lines */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, #06b6d4 2px, #06b6d4 3px)',
          backgroundSize:  '100% 6px',
        }}
      />
    </div>
  );
}

// ─── Animated terminal boot log ───────────────────────────────────────────────

function BootLog() {
  const [lines, setLines] = useState<string[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < BOOT_LINES.length) {
        setLines(prev => [...prev, BOOT_LINES[i]]);
        i++;
      } else {
        clearInterval(interval);
      }
    }, 280);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines]);

  return (
    <div
      ref={ref}
      className="font-mono text-[11px] text-emerald-400/80 space-y-1 overflow-y-auto max-h-52 pr-1"
      style={{ scrollbarWidth: 'none' }}
    >
      {lines.map((l, i) => {
        const lineStr = l || '';
        return (
          <div key={i} className="flex items-start gap-1">
            <span className="text-emerald-600 shrink-0">
              {lineStr.startsWith('>') ? '' : '  '}
            </span>
            <span>{lineStr}</span>
          </div>
        );
      })}
      {lines.length < BOOT_LINES.length && (
        <div className="flex items-center gap-1 text-cyan-400">
          <span className="inline-block w-2 h-3 bg-cyan-400 animate-pulse" />
        </div>
      )}
    </div>
  );
}

// ─── Status indicator row ─────────────────────────────────────────────────────

function StatusRow() {
  return (
    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-slate-800/80 pt-3 mt-3">
      <div className="flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-emerald-500">SYSTEM NOMINAL</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <Wifi size={9} /> 6 CAMS
        </span>
        <span className="flex items-center gap-1">
          <Activity size={9} /> 94.2% ACC
        </span>
        <span>AES-256-GCM</span>
      </div>
    </div>
  );
}

// ─── Main Login Component ─────────────────────────────────────────────────────

export function Login({ onLoginSuccess }: LoginProps) {
  const [operatorId, setOperatorId] = useState('');
  const [password,   setPassword]   = useState('');
  const [showPass,   setShowPass]   = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [locked,     setLocked]     = useState(false);
  const [lockSecs,   setLockSecs]   = useState(0);
  const [attempts,   setAttempts]   = useState<number | null>(null);
  const lockTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Countdown timer when locked
  useEffect(() => {
    if (locked && lockSecs > 0) {
      lockTimerRef.current = setInterval(() => {
        setLockSecs(s => {
          if (s <= 1) {
            setLocked(false);
            setError(null);
            clearInterval(lockTimerRef.current!);
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    }
    return () => { if (lockTimerRef.current) clearInterval(lockTimerRef.current); };
  }, [locked]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (locked || loading) return;

    setLoading(true);
    setError(null);
    setAttempts(null);

    try {
      const res = await fetch('http://127.0.0.1:8001/api/login', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ operator_id: operatorId, password }),
      });

      const data = await res.json();

      if (res.status === 200) {
        // Success
        localStorage.setItem('railguard_token',    data.access_token);
        localStorage.setItem('railguard_operator', JSON.stringify(data.operator));
        onLoginSuccess(data.access_token, data.operator);

      } else if (res.status === 429) {
        // Locked out
        setLocked(true);
        setLockSecs(data.detail?.remaining ?? 900);
        setError(data.detail?.message ?? 'Account locked.');

      } else {
        // 401 invalid credentials
        setError(data.detail?.message ?? 'Authentication failed.');
        if (data.detail?.remaining_attempts !== undefined) {
          setAttempts(data.detail.remaining_attempts);
        }
      }
    } catch {
      setError('Cannot reach RailGuard server. Ensure backend is running on :8001');
    } finally {
      setLoading(false);
    }
  };

  const fmtTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  return (
    <div className="min-h-screen w-full bg-[#05080F] flex items-center justify-center relative overflow-hidden">
      <GridBackground />

      {/* ── Top bar ── */}
      <div className="absolute top-0 inset-x-0 border-b border-slate-800/60 bg-[#0B0F19]/70 backdrop-blur px-8 py-3 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
            <span className="text-cyan-400 font-bold text-sm font-mono">R</span>
          </div>
          <div>
            <span className="text-sm font-bold text-cyan-400 tracking-widest uppercase font-mono">
              RAILGUARD AI
            </span>
            <span className="ml-3 text-[10px] font-mono text-slate-500">
              ISEA PHASE III INITIATIVE
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            SYSTEM ONLINE
          </span>
          <span>IIT MADRAS × BITS GOA</span>
          <span>MADGAON JUNCTION</span>
        </div>
      </div>

      {/* ── Main card ── */}
      <div className="relative z-10 w-full max-w-4xl mx-4 grid grid-cols-2 gap-0 rounded-2xl overflow-hidden border border-slate-700/60 shadow-2xl shadow-black/60"
           style={{ minHeight: '560px' }}>

        {/* ── LEFT: Terminal panel ── */}
        <div className="bg-[#060c14] border-r border-slate-800/60 p-8 flex flex-col">
          {/* Header */}
          <div className="flex items-center gap-2 mb-6">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/70" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
            </div>
            <span className="ml-2 text-[11px] font-mono text-slate-500">
              railguard-v3 — boot.log
            </span>
          </div>

          <BootLog />

          <div className="mt-auto pt-6 space-y-4">
            {/* Security badges */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'ENCRYPTION',  value: 'AES-256-GCM', color: 'emerald' },
                { label: 'AUTH',        value: 'JWT HS256',    color: 'cyan'    },
                { label: 'HASH',        value: 'ARGON2ID',     color: 'violet'  },
                { label: 'PRIVACY',     value: 'DP ε=1.2',     color: 'amber'   },
              ].map(b => (
                <div key={b.label}
                     className={`bg-slate-900/60 border border-slate-800 rounded px-3 py-2`}>
                  <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">
                    {b.label}
                  </div>
                  <div className={`text-[11px] font-mono font-bold text-${b.color}-400 mt-0.5`}>
                    {b.value}
                  </div>
                </div>
              ))}
            </div>

            <StatusRow />
          </div>
        </div>

        {/* ── RIGHT: Login form ── */}
        <div className="bg-[#0B0F19] p-8 flex flex-col justify-center">
          {/* Title */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
                <ShieldCheck size={22} className="text-cyan-400" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-100 tracking-wide uppercase font-mono">
                  Operator Auth
                </h1>
                <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                  Zero-Trust Clearance Gateway
                </p>
              </div>
            </div>
            <div className="h-px bg-gradient-to-r from-cyan-500/40 via-slate-700/40 to-transparent" />
          </div>

          {/* ── Lockout banner ── */}
          {locked && (
            <div className="mb-5 bg-red-950/40 border border-red-500/40 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5 animate-pulse" />
              <div>
                <p className="text-xs font-bold text-red-400 font-mono uppercase tracking-wider mb-1">
                  ⚠ ACCOUNT LOCKED — BRUTE FORCE PROTECTION
                </p>
                <p className="text-[11px] text-red-300/80 font-mono">
                  Too many failed attempts. Access suspended.
                </p>
                <p className="text-[11px] text-red-400 font-mono font-bold mt-2">
                  Retry in: <span className="text-white">{fmtTime(lockSecs)}</span>
                </p>
              </div>
            </div>
          )}

          {/* ── Generic error ── */}
          {error && !locked && (
            <div className="mb-5 bg-red-950/30 border border-red-800/50 rounded-lg px-4 py-3 flex items-center gap-3">
              <AlertTriangle size={15} className="text-red-400 shrink-0" />
              <div>
                <p className="text-[11px] text-red-300 font-mono">{error}</p>
                {attempts !== null && (
                  <p className="text-[10px] text-red-500 font-mono mt-1">
                    {attempts} attempt{attempts !== 1 ? 's' : ''} remaining before lockout
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── Form ── */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Operator ID */}
            <div>
              <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-2">
                Operator ID
              </label>
              <div className="relative">
                <User
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  type="text"
                  value={operatorId}
                  onChange={e => setOperatorId(e.target.value)}
                  placeholder="operator_id"
                  disabled={locked || loading}
                  autoComplete="username"
                  required
                  className="
                    w-full bg-[#060c14] border border-slate-700/80 rounded-lg
                    pl-10 pr-4 py-3
                    text-sm text-slate-200 placeholder-slate-600 font-mono
                    focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/20
                    disabled:opacity-40 disabled:cursor-not-allowed
                    transition-colors
                  "
                />
              </div>
            </div>

            {/* Passphrase */}
            <div>
              <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-2">
                Encrypted Passphrase
              </label>
              <div className="relative">
                <Lock
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={locked || loading}
                  autoComplete="current-password"
                  required
                  className="
                    w-full bg-[#060c14] border border-slate-700/80 rounded-lg
                    pl-10 pr-11 py-3
                    text-sm text-slate-200 placeholder-slate-600 font-mono
                    focus:outline-none focus:border-cyan-500/60 focus:ring-1 focus:ring-cyan-500/20
                    disabled:opacity-40 disabled:cursor-not-allowed
                    transition-colors
                  "
                />
                <button
                  type="button"
                  onClick={() => setShowPass(v => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={locked || loading || !operatorId || !password}
              className="
                w-full mt-2 py-3 px-4 rounded-lg font-mono text-sm font-bold
                tracking-widest uppercase
                transition-all duration-200
                flex items-center justify-center gap-2
                disabled:opacity-40 disabled:cursor-not-allowed
                bg-cyan-500/15 border border-cyan-500/50 text-cyan-400
                hover:bg-cyan-500/25 hover:border-cyan-400 hover:text-cyan-300
                hover:shadow-[0_0_20px_rgba(6,182,212,0.15)]
                focus:outline-none focus:ring-2 focus:ring-cyan-500/30
              "
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border border-cyan-400/40 border-t-cyan-400 rounded-full animate-spin" />
                  AUTHENTICATING...
                </>
              ) : locked ? (
                <>
                  <AlertTriangle size={14} />
                  ACCESS SUSPENDED
                </>
              ) : (
                <>
                  <ShieldCheck size={14} />
                  AUTHENTICATE
                </>
              )}
            </button>
          </form>

          {/* Footer note */}
          <div className="mt-8 pt-5 border-t border-slate-800/60">
            <div className="flex items-start gap-2">
              <Terminal size={12} className="text-slate-600 mt-0.5 shrink-0" />
              <p className="text-[10px] font-mono text-slate-600 leading-relaxed">
                This system is for authorised RPF/GRP personnel only.
                All access attempts are logged and monitored.
                Unauthorised access will be prosecuted under IT Act 2000.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div className="absolute bottom-0 inset-x-0 border-t border-slate-800/60 bg-[#0B0F19]/60 backdrop-blur px-8 py-2.5 flex items-center justify-between z-10">
        <span className="text-[10px] font-mono text-slate-600">
          RAILGUARD AI — MINISTRY OF RAILWAYS | CYBERDOME 2026
        </span>
        <span className="text-[10px] font-mono text-slate-600">
          THREAT INDEX: 0.5/10 [LOW] • 5 ML MODELS ACTIVE
        </span>
      </div>
    </div>
  );
}