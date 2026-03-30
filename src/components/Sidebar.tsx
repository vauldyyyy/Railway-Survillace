import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Video,
  AlertTriangle,
  UserSearch,
  Users,
  Cpu,
  Shield,
  FileText,
  Settings,
  Bell,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Page } from '../App';
import useSystemStore from '../store/useSystemStore';
import useAlertStore from '../store/useAlertStore';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: Page) => void;
}

const NAV_ITEMS = [
  { id: 'overview',          label: 'Overview',         icon: LayoutDashboard },
  { id: 'live-feeds',        label: 'Live Feeds',       icon: Video },
  { id: 'threat-alerts',     label: 'Threat Alerts',    icon: AlertTriangle },
  { id: 'person-tracking',   label: 'Person Tracking',  icon: UserSearch },
  { id: 'crowd-analytics',   label: 'Crowd Analytics',  icon: Users },
  { id: 'ai-agents',         label: 'AI Agents',        icon: Cpu },
  { id: 'security-layer',    label: 'Security Layer',   icon: Shield },
  { id: 'incident-reports',  label: 'Incident Reports', icon: FileText },
  { id: 'system-config',     label: 'System Config',    icon: Settings },
  { id: 'notifications',     label: 'Notifications',    icon: Bell },
];

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const globalConfidence = useSystemStore(state => state.globalConfidence);
  const wsConnected = useSystemStore(state => state.wsConnected);
  const gpuBridge = useSystemStore(state => state.gpuBridge);
  const toggleGpuBridge = useSystemStore(state => state.toggleGpuBridge);
  const unacknowledgedCount = useAlertStore(state => state.getUnacknowledgedCount());
  const [clock, setClock] = useState('');
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    const tick = () => {
      setClock(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
      setUptime(t => t + 1);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const uptimeStr = (() => {
    const h = Math.floor(uptime / 3600);
    const m = Math.floor((uptime % 3600) / 60);
    const s = uptime % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  })();

  return (
    <aside
      className={`
        relative bg-[#0B0F19] border-r border-slate-800/50
        flex flex-col h-full z-20 shrink-0
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* Toggle button */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="
          absolute -right-3 top-20 z-30
          w-6 h-6 rounded-full
          bg-[#0B0F19] border border-slate-700
          flex items-center justify-center
          text-slate-400 hover:text-cyan-400
          hover:border-cyan-500/50 transition-colors
          shadow-lg
        "
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>

      {/* Logo */}
      <div className={`p-4 border-b border-slate-800/50 overflow-hidden ${collapsed ? 'px-3' : 'px-6'}`}>
        {collapsed ? (
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
            <span className="text-cyan-400 font-bold text-sm">R</span>
          </div>
        ) : (
          <>
            <h1 className="text-xl font-bold text-cyan-400 tracking-wider uppercase whitespace-nowrap glow-text-cyan">
              RAILGUARD AI
            </h1>
            <p className="text-[10px] text-slate-500 tracking-widest uppercase mt-1 whitespace-nowrap">
              ISEA Phase III Initiative
            </p>
            <div className="mt-3 flex items-center justify-between">
              <div className="text-[11px] font-mono text-slate-300 font-bold">{clock}</div>
              <div className={`flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded ${
                wsConnected ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-600 bg-slate-800'
              }`}>
                <span className={`w-1 h-1 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                {wsConnected ? 'WS LIVE' : 'WS OFF'}
              </div>
            </div>
          </>
        )}
      </div>

      {/* GPU Bridge Status */}
      {!collapsed && (
        <div className="px-4 py-2 border-b border-slate-800/50">
          <div className={`flex items-center justify-between px-2.5 py-1.5 rounded-md text-[10px] font-mono transition-all duration-500 ${
            gpuBridge?.connected
              ? 'bg-emerald-500/10 border border-emerald-500/30'
              : gpuBridge?.mode === 'remote'
                ? 'bg-amber-500/10 border border-amber-500/30'
                : 'bg-slate-800/60 border border-slate-700/50'
          }`}>
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${
                gpuBridge?.connected
                  ? 'bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.7)]'
                  : gpuBridge?.mode === 'remote'
                    ? 'bg-amber-400 animate-pulse'
                    : 'bg-slate-500'
              }`} />
              <span className={`uppercase tracking-wider font-bold ${
                gpuBridge?.connected ? 'text-emerald-400' : gpuBridge?.mode === 'remote' ? 'text-amber-400' : 'text-slate-500'
              }`}>
                {gpuBridge?.connected ? 'GPU BRIDGE' : gpuBridge?.mode === 'remote' ? 'WAKING UP GPU' : 'LOCAL CPU'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {gpuBridge?.connected && (
                <span className="text-emerald-300/80 mr-1">{gpuBridge.latency_ms}ms</span>
              )}
              <button
                onClick={toggleGpuBridge}
                className={`relative inline-flex h-3 w-6 shrink-0 items-center rounded-full transition-colors ${
                  gpuBridge?.mode === 'remote' ? 'bg-emerald-500' : 'bg-slate-600'
                }`}
                title={gpuBridge?.mode === 'remote' ? "Disable GPU Bridge" : "Enable GPU Bridge"}
              >
                <span className={`inline-block h-2 w-2 transform rounded-full bg-white transition-transform ${
                  gpuBridge?.mode === 'remote' ? 'translate-x-[14px]' : 'translate-x-0.5'
                }`} />
              </button>
            </div>
          </div>
        </div>
      )}
      {collapsed && (
        <div className="flex justify-center py-2 border-b border-slate-800/50" title={gpuBridge?.connected ? `GPU Bridge: ${gpuBridge.latency_ms}ms` : 'Local CPU'}>
          <span className={`w-2 h-2 rounded-full ${
            gpuBridge?.connected
              ? 'bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.7)]'
              : 'bg-slate-500'
          }`} />
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 overflow-x-hidden">
        <ul className="space-y-0.5">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onNavigate(item.id as Page)}
                  title={collapsed ? item.label : undefined}
                  className={`
                    w-full flex items-center gap-3 py-3 text-sm
                    transition-colors relative group
                    ${collapsed ? 'px-0 justify-center' : 'px-6'}
                    ${isActive
                      ? 'text-cyan-400 bg-cyan-950/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/20'
                    }
                  `}
                >
                  {/* Active bar */}
                  {isActive && (
                    <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.5)]" />
                  )}

                  <Icon
                    size={18}
                    className={`shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'}`}
                  />

                  {/* Label — hidden when collapsed */}
                  {!collapsed && (
                    <div className="flex-1 flex items-center justify-between">
                      <span className="truncate">{item.label}</span>
                      {item.id === 'threat-alerts' && unacknowledgedCount > 0 && (
                        <span className="bg-red-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full animate-pulse">
                          {unacknowledgedCount}
                        </span>
                      )}
                      {item.id === 'notifications' && (
                        <span className="bg-cyan-500/20 text-cyan-400 text-[9px] font-bold px-1.5 py-0.5 rounded-full border border-cyan-500/40">
                          3
                        </span>
                      )}
                    </div>
                  )}

                  {/* Tooltip when collapsed */}
                  {collapsed && (
                    <div className="
                      absolute left-full ml-2 px-2 py-1
                      bg-[#151C2C] border border-slate-700 rounded
                      text-xs font-mono text-slate-200 whitespace-nowrap
                      opacity-0 group-hover:opacity-100
                      pointer-events-none z-50
                      transition-opacity duration-150
                    ">
                      {item.label}
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ML Accuracy + System Stats display */}
      {!collapsed && (
        <div className="px-4 py-3 border-t border-slate-800/50 space-y-3">
          {/* Confidence bar */}
          <div>
            <div className="text-[10px] font-mono text-slate-500 uppercase flex justify-between mb-1.5">
              <span>Model Accuracy</span>
              <span className="text-cyan-400 glow-text-cyan">{globalConfidence.toFixed(1)}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.8)] transition-all duration-500" style={{ width: `${globalConfidence}%` }} />
            </div>
          </div>
          {/* System mini-stats */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-900/60 rounded-md p-2 border border-slate-800/50">
              <div className="text-[8px] font-mono text-slate-600 uppercase mb-0.5">Session Uptime</div>
              <div className="text-[11px] font-mono text-slate-300 font-bold">{uptimeStr}</div>
            </div>
            <div className="bg-slate-900/60 rounded-md p-2 border border-slate-800/50">
              <div className="text-[8px] font-mono text-slate-600 uppercase mb-0.5">AES Encryption</div>
              <div className="text-[11px] font-mono text-emerald-400 font-bold">AES-256-GCM</div>
            </div>
          </div>
          {/* Pipeline tag */}
          <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-600">
            <span className="w-1 h-1 rounded-full bg-cyan-500 animate-ping shrink-0" />
            5 ML models active • CyberDome 2026
          </div>
        </div>
      )}

      {/* User info */}
      <div className={`border-t border-slate-800/50 ${collapsed ? 'p-3' : 'p-4'} space-y-3`}>
        {collapsed ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-700 border border-slate-600 overflow-hidden">
              <img
                src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=100"
                alt="User"
                className="w-full h-full object-cover"
              />
            </div>
            <button
              className="text-slate-500 hover:text-red-400 transition-colors"
              title="Logout"
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <>
            <div className="bg-[#151C2C] border border-slate-800 rounded-md p-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden shrink-0">
                <img
                  src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=100"
                  alt="User"
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-slate-200 truncate">RPF_GOA_01</span>
                <span className="text-[9px] text-emerald-500 uppercase tracking-wider">System Operational</span>
              </div>
            </div>
            <button className="flex items-center gap-3 text-sm text-slate-400 hover:text-red-400 transition-colors px-2 w-full uppercase tracking-wider font-semibold">
              <LogOut size={16} />
              Logout
            </button>
          </>
        )}
      </div>
    </aside>
  );
}
