import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Bell, Search, Clock, Wifi } from 'lucide-react';
import Sidebar from './Sidebar';
import AlertToastContainer from '../alerts/AlertToastContainer';
import useAppStore from '../../store/useAppStore';
import useAlertStore from '../../store/useAlertStore';

export default function Layout() {
  const { sidebarOpen, currentTime, updateTime } = useAppStore();
  const alerts = useAlertStore((s) => s.alerts);
  const unacknowledged = alerts.filter(a => !a.acknowledged).length;

  // Clock and alert simulation
  useEffect(() => {
    const clockInterval = setInterval(updateTime, 1000);
    const alertInterval = useAlertStore.getState().startSimulation();
    return () => {
      clearInterval(clockInterval);
      clearInterval(alertInterval);
    };
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  };
  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-bg-primary noise-bg">
      <Sidebar />
      
      {/* Main content area */}
      <div
        className={`transition-all duration-300 ${sidebarOpen ? 'ml-60' : 'ml-[72px]'}`}
      >
        {/* Top Bar */}
        <header className="sticky top-0 z-30 glass-heavy border-b border-border-subtle">
          <div className="flex items-center justify-between px-6 py-3">
            {/* Left: Page context */}
            <div className="flex items-center gap-4">
              <div className="hidden md:flex items-center gap-2 text-xs text-text-secondary">
                <Wifi className="w-3.5 h-3.5 text-success" />
                <span className="font-mono">12ms</span>
              </div>
            </div>

            {/* Center: System banner */}
            <div className="hidden lg:flex items-center gap-3 px-4 py-1.5 rounded-full bg-cyber/5 border border-cyber/20">
              <div className="w-2 h-2 rounded-full bg-cyber animate-pulse-glow" />
              <span className="text-[11px] font-medium text-cyber tracking-wider">
                RAILGUARD AI — LIVE MONITORING ACTIVE
              </span>
            </div>

            {/* Right: Clock + Alerts */}
            <div className="flex items-center gap-4">
              {/* Clock */}
              <div className="hidden sm:flex items-center gap-2 text-xs text-text-secondary">
                <Clock className="w-3.5 h-3.5" />
                <span className="font-mono text-text-primary">{formatTime(currentTime)}</span>
                <span className="text-text-muted">{formatDate(currentTime)}</span>
              </div>

              {/* Alert bell */}
              <button className="relative p-2 rounded-lg hover:bg-bg-hover transition-colors group">
                <Bell className="w-5 h-5 text-text-secondary group-hover:text-cyber transition-colors" />
                {unacknowledged > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-5 h-5 rounded-full bg-danger text-white text-[10px] font-bold flex items-center justify-center animate-pulse-glow">
                    {unacknowledged > 9 ? '9+' : unacknowledged}
                  </span>
                )}
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      {/* Toast notifications overlay */}
      <AlertToastContainer />
    </div>
  );
}
