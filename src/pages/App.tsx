import React, { useState, useEffect } from 'react';
import { Login } from './pages/Login';
import { Layout } from './components/Layout';
import { Overview } from './pages/Overview';
import { LiveFeeds } from './pages/LiveFeeds';
import { ThreatAlerts } from './pages/ThreatAlerts';
import { PersonTracking } from './pages/PersonTracking';
import { CrowdAnalytics } from './pages/CrowdAnalytics';
import { AIAgents } from './pages/AIAgents';
import { SecurityLayer } from './pages/SecurityLayer';
import { IncidentReports } from './pages/IncidentReports';
import { SystemConfig } from './pages/SystemConfig';
import { Notifications } from './pages/Notifications';
import { Profile } from './pages/Profile';
import useSystemStore, { startMetricsSimulation, startBridgePoller } from './store/useSystemStore';

export type Page =
  | 'overview'
  | 'live-feeds'
  | 'threat-alerts'
  | 'person-tracking'
  | 'crowd-analytics'
  | 'ai-agents'
  | 'security-layer'
  | 'incident-reports'
  | 'system-config'
  | 'notifications'
  | 'profile';

export interface OperatorInfo {
  id:           string;
  display_name: string;
  role:         string;
  clearance:    string;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [operator, setOperator]               = useState<OperatorInfo | null>(null);
  const [currentPage, setCurrentPage]         = useState<Page>('overview');
  const [authChecked, setAuthChecked]         = useState(false);

  // Pull connectWebSocket from store so we can start it after auth
  const connectWebSocket = useSystemStore(state => state.connectWebSocket);

  // ── On mount: restore session from localStorage ───────────────────────────
  useEffect(() => {
    const token = localStorage.getItem('railguard_token');
    const opRaw = localStorage.getItem('railguard_operator');

    if (token && opRaw) {
      try {
        // Decode JWT payload (base64) — just check expiry client-side
        const payload  = JSON.parse(atob(token.split('.')[1]));
        const expireAt = payload.exp * 1000;

        if (Date.now() < expireAt) {
          setIsAuthenticated(true);
          setOperator(JSON.parse(opRaw));
        } else {
          // Expired — clear
          localStorage.removeItem('railguard_token');
          localStorage.removeItem('railguard_operator');
        }
      } catch {
        localStorage.removeItem('railguard_token');
        localStorage.removeItem('railguard_operator');
      }
    }
    setAuthChecked(true);
  }, []);

  // ── Start background services once authenticated ──────────────────────────
  useEffect(() => {
    if (!isAuthenticated) return;

    // Start WebSocket listener (alerts, metrics, camera state)
    connectWebSocket();

    // Start polling loops
    const metricsTimer = startMetricsSimulation();
    const bridgeTimer  = startBridgePoller();

    return () => {
      clearInterval(metricsTimer);
      clearInterval(bridgeTimer);
    };
  }, [isAuthenticated, connectWebSocket]);

  // ── Auth handlers ─────────────────────────────────────────────────────────
  const handleLoginSuccess = (_token: string, op: OperatorInfo) => {
    setOperator(op);
    setIsAuthenticated(true);
    setCurrentPage('overview');
  };

  const handleLogout = () => {
    localStorage.removeItem('railguard_token');
    localStorage.removeItem('railguard_operator');
    setIsAuthenticated(false);
    setOperator(null);
    setCurrentPage('overview');
  };

  // ── Page renderer ─────────────────────────────────────────────────────────
  const renderPage = () => {
    switch (currentPage) {
      case 'overview':         return <Overview         onNavigate={setCurrentPage} />;
      case 'live-feeds':       return <LiveFeeds        onNavigate={setCurrentPage} />;
      case 'threat-alerts':    return <ThreatAlerts     onNavigate={setCurrentPage} />;
      case 'person-tracking':  return <PersonTracking   onNavigate={setCurrentPage} />;
      case 'crowd-analytics':  return <CrowdAnalytics   onNavigate={setCurrentPage} />;
      case 'ai-agents':        return <AIAgents         onNavigate={setCurrentPage} />;
      case 'security-layer':   return <SecurityLayer    onNavigate={setCurrentPage} />;
      case 'incident-reports': return <IncidentReports  onNavigate={setCurrentPage} />;
      case 'system-config':    return <SystemConfig     onNavigate={setCurrentPage} />;
      case 'notifications':    return <Notifications    onNavigate={setCurrentPage} />;
      case 'profile':          return <Profile          onNavigate={setCurrentPage} />;
      default:
        return <div className="p-8 text-slate-400 font-mono">PAGE UNDER CONSTRUCTION</div>;
    }
  };

  // ── Prevent flash: wait for localStorage check ────────────────────────────
  if (!authChecked) {
    return (
      <div className="min-h-screen w-full bg-[#05080F] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border border-cyan-500/40 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-[11px] font-mono text-slate-500 tracking-widest uppercase">
            Initializing RailGuard AI...
          </span>
        </div>
      </div>
    );
  }

  // ── CONDITIONAL RENDERING GATEWAY ─────────────────────────────────────────
  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <Layout
      currentPage={currentPage}
      onNavigate={setCurrentPage}
      onLogout={handleLogout}
      operator={operator}
    >
      {renderPage()}
    </Layout>
  );
}

export default App;