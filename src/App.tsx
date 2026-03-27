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
import { ModelDashboard } from './pages/ModelDashboard';
import { AIHealthMonitor } from './pages/AIHealthMonitor';
import { startMetricsSimulation } from './store/useSystemStore';
import useAlertStore from './store/useAlertStore.ts';

export type Page = 'overview' | 'live-feeds' | 'threat-alerts' | 'person-tracking' | 'crowd-analytics' | 'ai-agents' | 'security-layer' | 'incident-reports' | 'system-config' | 'notifications' | 'profile' | 'model-dashboard' | 'ai-health';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('overview');

  // Start live simulations on mount
  useEffect(() => {
    // Connect to real-time backend
    import('./store/useSystemStore').then(mod => {
      mod.default.getState().connectWebSocket();
    });

    const metricsInterval = startMetricsSimulation();
    const alertInterval = useAlertStore.getState().startSimulation();
    return () => {
      clearInterval(metricsInterval);
      clearInterval(alertInterval);
    };
  }, []);

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
      case 'model-dashboard': return <ModelDashboard onNavigate={setCurrentPage} />;
      case 'ai-health': return <AIHealthMonitor onNavigate={setCurrentPage} />;
      default: return <div className="p-8 text-slate-400">Page under construction</div>;
    }
  };

  return (
    <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
      {renderPage()}
    </Layout>
  );
}

export default App;
