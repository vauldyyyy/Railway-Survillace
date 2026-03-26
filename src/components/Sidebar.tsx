import React from 'react';
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
  Activity,
  HeartPulse
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Page } from '../App';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: Page) => void;
}

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'live-feeds', label: 'Live Feeds', icon: Video },
    { id: 'threat-alerts', label: 'Threat Alerts', icon: AlertTriangle },
    { id: 'person-tracking', label: 'Person Tracking', icon: UserSearch },
    { id: 'crowd-analytics', label: 'Crowd Analytics', icon: Users },
    { id: 'ai-agents', label: 'AI Agents', icon: Cpu },
    { id: 'security-layer', label: 'Security Layer', icon: Shield },
    { id: 'incident-reports', label: 'Incident Reports', icon: FileText },
    { id: 'system-config', label: 'System Config', icon: Settings },
    { id: 'model-dashboard', label: 'Model Dashboard', icon: Activity },
    { id: 'ai-health', label: 'AI Health', icon: HeartPulse },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ];

  return (
    <aside className="w-64 bg-[#0B0F19] border-r border-slate-800/50 flex flex-col h-full z-20 shrink-0">
      <div className="p-6">
        <h1 className="text-xl font-bold text-cyan-400 tracking-wider flex items-center gap-2 uppercase">
          RAILGUARD AI
        </h1>
        <p className="text-[10px] text-slate-500 tracking-widest uppercase mt-1">ISEA Phase III Initiative</p>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onNavigate(item.id as Page)}
                  className={cn(
                    "w-full flex items-center gap-3 px-6 py-3 text-sm transition-colors relative",
                    isActive 
                      ? "text-cyan-400 bg-cyan-950/20" 
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
                  )}
                >
                  {isActive && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]" />
                  )}
                  <Icon size={18} className={isActive ? "text-cyan-400" : "text-slate-500"} />
                  {item.label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="p-6 space-y-4">
        <div className="bg-[#151C2C] border border-slate-800 rounded-md p-3 flex items-center gap-3">
           <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden shrink-0">
             <img src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=100" alt="User" className="w-full h-full object-cover" />
           </div>
           <div className="flex flex-col">
             <span className="text-xs font-bold text-slate-200">RPF_GOA_01</span>
             <span className="text-[9px] text-emerald-500 uppercase tracking-wider">System Operational</span>
           </div>
        </div>

        <button className="flex items-center gap-3 text-sm text-slate-400 hover:text-slate-200 transition-colors px-2 w-full uppercase tracking-wider font-semibold">
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </aside>
  );
}
