import React, { useState } from 'react';
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
            <h1 className="text-xl font-bold text-cyan-400 tracking-wider uppercase whitespace-nowrap">
              RAILGUARD AI
            </h1>
            <p className="text-[10px] text-slate-500 tracking-widest uppercase mt-1 whitespace-nowrap">
              ISEA Phase III Initiative
            </p>
          </>
        )}
      </div>

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
                    <span className="truncate">{item.label}</span>
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