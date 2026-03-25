import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Camera, FileText, BarChart3, Route,
  Settings, Shield, Cpu, ChevronLeft, ChevronRight, Radio
} from 'lucide-react';
import useAppStore from '../../store/useAppStore';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/cameras', icon: Camera, label: 'Cameras' },
  { path: '/incidents', icon: FileText, label: 'Incidents' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  { path: '/tracking', icon: Route, label: 'Tracking' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, systemStatus } = useAppStore();
  const location = useLocation();

  return (
    <aside
      className={`
        fixed left-0 top-0 bottom-0 z-40
        glass-heavy flex flex-col
        transition-all duration-300 ease-in-out
        ${sidebarOpen ? 'w-60' : 'w-[72px]'}
      `}
    >
      {/* Logo / Brand */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-border-subtle">
        <div className="w-9 h-9 rounded-lg bg-cyber/10 flex items-center justify-center flex-shrink-0">
          <Shield className="w-5 h-5 text-cyber" />
        </div>
        {sidebarOpen && (
          <div className="animate-fade-in overflow-hidden">
            <h1 className="text-sm font-bold text-text-primary tracking-wide">RAILGUARD</h1>
            <p className="text-[10px] text-cyber tracking-widest">AI SURVEILLANCE</p>
          </div>
        )}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map(({ path, icon: Icon, label }) => {
          const isActive = location.pathname === path;
          return (
            <NavLink
              key={path}
              to={path}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg
                transition-all duration-200 group relative
                ${isActive
                  ? 'bg-cyber/10 text-cyber shadow-glow-cyan'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                }
              `}
            >
              {/* Active indicator bar */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-cyber rounded-r-full" />
              )}
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-cyber' : 'group-hover:text-text-primary'}`} />
              {sidebarOpen && (
                <span className="text-sm font-medium truncate animate-fade-in">{label}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="px-3 py-4 border-t border-border-subtle space-y-2">
        {sidebarOpen ? (
          <>
            <div className="flex items-center gap-2 px-2">
              <Cpu className="w-3.5 h-3.5 text-success" />
              <span className="text-[11px] text-text-secondary">AI Engine</span>
              <span className={`ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                systemStatus.aiActive ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'
              }`}>
                {systemStatus.aiActive ? 'ACTIVE' : 'OFFLINE'}
              </span>
            </div>
            <div className="flex items-center gap-2 px-2">
              <Radio className="w-3.5 h-3.5 text-cyber" />
              <span className="text-[11px] text-text-secondary">Secure Mode</span>
              <span className={`ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                systemStatus.secureMode ? 'bg-cyber/15 text-cyber' : 'bg-danger/15 text-danger'
              }`}>
                {systemStatus.secureMode ? 'ON' : 'OFF'}
              </span>
            </div>
            <div className="flex items-center gap-2 px-2">
              <div className="w-3.5 h-3.5 flex items-center justify-center">
                <div className="status-dot online" />
              </div>
              <span className="text-[11px] text-text-secondary">System</span>
              <span className="ml-auto text-[10px] text-success font-mono">{systemStatus.systemHealth}%</span>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="status-dot online" title="System Online" />
            <Cpu className="w-3.5 h-3.5 text-success" title="AI Active" />
          </div>
        )}
      </div>

      {/* Toggle button */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-8 w-6 h-6 rounded-full bg-bg-secondary border border-border-subtle
          flex items-center justify-center text-text-secondary hover:text-cyber hover:border-cyber/30
          transition-all duration-200 z-50"
      >
        {sidebarOpen ? <ChevronLeft className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
      </button>
    </aside>
  );
}
