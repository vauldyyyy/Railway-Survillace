import React, { useState, useEffect } from 'react';
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
import { Login } from './pages/Login';


export interface OperatorInfo {
  username: string;
  display_name: string;
  role: string;
  avatar?: string;
}

export type Page = 'overview' | 'live-feeds' | 'threat-alerts' | 'person-tracking' | 'crowd-analytics' | 'ai-agents' | 'security-layer' | 'incident-reports' | 'system-config' | 'notifications' | 'profile';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('overview');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [operator, setOperator] = useState<any>(null);
  const [isVerifying, setIsVerifying] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('railguard_token');
    const opStr = localStorage.getItem('railguard_operator');
    if (token) {
      if (opStr) {
        try { setOperator(JSON.parse(opStr)); } catch(e) {}
      }
      
      fetch('http://127.0.0.1:8001/api/verify', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => {
        if (res.ok) {
          setIsAuthenticated(true);
        } else {
          // invalid token
          localStorage.removeItem('railguard_token');
          localStorage.removeItem('railguard_operator');
        }
      })
      .catch(() => {
        // server unreachable -> logout as per requirement 
        localStorage.removeItem('railguard_token');
        localStorage.removeItem('railguard_operator');
      })
      .finally(() => setIsVerifying(false));
    } else {
      setIsVerifying(false);
    }
  }, []);

  const handleLoginSuccess = (token: string, op: any) => {
    setIsAuthenticated(true);
    setOperator(op);
  };

  const handleLogout = () => {
    localStorage.removeItem('railguard_token');
    localStorage.removeItem('railguard_operator');
    setIsAuthenticated(false);
    setOperator(null);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'overview': return <Overview onNavigate={setCurrentPage} />;
      case 'live-feeds': return <LiveFeeds onNavigate={setCurrentPage} />;
      case 'threat-alerts': return <ThreatAlerts onNavigate={setCurrentPage} />;
      case 'person-tracking': return <PersonTracking onNavigate={setCurrentPage} />;
      case 'crowd-analytics': return <CrowdAnalytics onNavigate={setCurrentPage} />;
      case 'ai-agents': return <AIAgents onNavigate={setCurrentPage} />;
      case 'security-layer': return <SecurityLayer onNavigate={setCurrentPage} />;
      case 'incident-reports': return <IncidentReports onNavigate={setCurrentPage} />;
      case 'system-config': return <SystemConfig onNavigate={setCurrentPage} />;
      case 'notifications': return <Notifications onNavigate={setCurrentPage} />;
      case 'profile': return <Profile onNavigate={setCurrentPage} />;
      default: return <div className="p-8 text-slate-400">Page under construction</div>;
    }
  };

  if (isVerifying) {
    return <div className="h-screen w-full bg-[#05080F] flex items-center justify-center font-mono text-cyan-400 text-sm tracking-widest uppercase animate-pulse">Establishing Secure Session...</div>;
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <Layout currentPage={currentPage} onNavigate={setCurrentPage} onLogout={handleLogout} operator={operator}>
      {renderPage()}
    </Layout>
  );
}

export default App;
