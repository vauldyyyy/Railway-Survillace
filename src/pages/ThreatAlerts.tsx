import React, { useState, useMemo, useEffect } from 'react';
import { Header } from '../components/Header';
import { 
  AlertTriangle, ShieldAlert, Crosshair, CheckCircle, 
  Search, Filter, ChevronDown, Video, UserSearch, X 
} from 'lucide-react';
import useAlertStore, { Alert, AlertSeverity } from '../store/alertStore';
import { formatDistanceToNow } from 'date-fns';
import { ThomasAI } from '../components/ThomasAI';

// ─── Severity helpers ──────────────────────────────────────────────────────────

function severityBg(s: AlertSeverity | string) {
  const upperS = String(s).toUpperCase();
  switch (upperS) {
    case 'CRITICAL': return 'bg-red-500';
    case 'HIGH':     return 'bg-orange-500';
    case 'WARNING':  return 'bg-yellow-500';
    case 'LOW':      return 'bg-blue-500';
    default:         return 'bg-slate-500';
  }
}

function severityBorder(s: AlertSeverity | string) {
  const upperS = String(s).toUpperCase();
  switch (upperS) {
    case 'CRITICAL': return 'border-red-500/30';
    case 'HIGH':     return 'border-orange-500/30';
    case 'WARNING':  return 'border-yellow-500/30';
    case 'LOW':      return 'border-blue-500/30';
    default:         return 'border-slate-500/30';
  }
}

// ─── Camera Feed Modal ────────────────────────────────────────────────────────

function CameraModal({
  cam, onClose
}: { cam: string; onClose: () => void }) {
  // Map cam label to stream URL
  const streamUrl = (() => {
    const c = String(cam).toUpperCase();
    if (c.includes('CAM-01') || c.includes('CAM_01')) return 'http://127.0.0.1:8001/video/cam1';
    if (c.includes('CAM-02') || c.includes('CAM_02')) return 'http://127.0.0.1:8001/video/cam2';
    if (c.includes('CAM-03') || c.includes('CAM_03')) return 'http://127.0.0.1:8001/video/cam3';
    if (c.includes('CAM-04') || c.includes('CAM_04')) return 'http://127.0.0.1:8001/video/cam4';
    if (c.includes('CAM-05') || c.includes('CAM_05')) return 'http://127.0.0.1:8001/video/cam5';
    if (c.includes('CAM-06') || c.includes('CAM_06')) return 'http://127.0.0.1:8001/video/cam6';
    return `http://127.0.0.1:8001/video/cam1`;
  })();

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h) ;
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-[#05080F]/95 backdrop-blur-sm flex items-center justify-center p-8"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl bg-[#0B0F19] border border-slate-700 rounded-xl overflow-hidden shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800 bg-[#060a12]">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-sm font-mono font-bold text-slate-200">{cam} — LIVE FEED</h2>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="bg-black" style={{ minHeight: '360px' }}>
          <img
            src={streamUrl}
            alt={cam}
            className="w-full h-full object-contain"
            style={{ minHeight: '360px' }}
          />
        </div>
        <div className="px-6 py-3 bg-[#060a12] border-t border-slate-800">
          <p className="text-[10px] font-mono text-slate-500">
            LIVE MJPEG STREAM • RAILGUARD AI ENGINE • {cam}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function ThreatAlerts({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [cameraModal, setCameraModal] = useState<string | null>(null);

  const alerts = useAlertStore(s => s.alerts);
  const backendOk = useAlertStore(s => s.backendOk);
  const startPolling = useAlertStore(s => s.startPolling);
  const markAsResolved = useAlertStore(s => s.markAsResolved);
  const markAsFalseAlarm = useAlertStore(s => s.markAsFalseAlarm);

  useEffect(() => {
    const stop = startPolling();
    return stop;
  }, [startPolling]);

  // Derive counts from merged data
  const criticalCount = alerts.filter(a => String(a.severity || (a as any).threat_level).toUpperCase() === 'CRITICAL').length;
  const warningCount = alerts.filter(a => {
    const s = String(a.severity || (a as any).threat_level).toUpperCase();
    return s === 'HIGH' || s === 'WARNING';
  }).length;
  const resolvedToday = alerts.filter(a => a.status === 'RESOLVED').length;
  const infoCount = alerts.filter(a => {
      const s = String(a.severity || (a as any).threat_level).toUpperCase();
      return s === 'LOW' || s === 'INFO';
  }).length;

  const filteredThreats = useMemo(() => {
    return alerts.filter(t => {
      const q = searchQuery.toLowerCase();
      const typeStr = (t.type || (t as any).threat_type || '').toLowerCase();
      const locStr = (t.location || (t as any).camera_id || '').toLowerCase();
      const descStr = (t.description || (t as any).command || '').toLowerCase();
      
      const matchSearch =
        t.id?.toLowerCase().includes(q) ||
        typeStr.includes(q) ||
        locStr.includes(q) ||
        descStr.includes(q);

      const level = String(t.severity || (t as any).threat_level).toUpperCase();
      const matchFilter = levelFilter === 'ALL' || level === levelFilter;
      
      return matchSearch && matchFilter;
    });
  }, [alerts, searchQuery, levelFilter]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="THREAT ALERTS"
        subtitle="Active Security Incidents & Automated Responses"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          <div className={`flex items-center gap-1.5 text-[10px] font-mono px-2.5 py-1 rounded-full border ${
            backendOk
              ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
              : 'border-red-500/40 text-red-400 bg-red-500/10'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${backendOk ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
            {backendOk ? 'LIVE' : 'OFFLINE'}
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search alerts..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="bg-[#151C2C] border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 w-64"
            />
          </div>

          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(v => !v)}
              className="flex items-center gap-2 bg-[#151C2C] border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
            >
              <Filter size={14} />
              {levelFilter === 'ALL' ? 'FILTER' : levelFilter}
              <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'CRITICAL', 'HIGH', 'WARNING', 'LOW'].map(level => (
                  <button
                    key={level}
                    onClick={() => { setLevelFilter(level); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-800 text-slate-300"
                  >
                    {level === 'ALL' ? 'All Levels' : level}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </Header>

      <div className="p-6 flex-1 overflow-y-auto space-y-4">
        {/* Metric Cards (Vauldy UI) */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <div className="bg-red-950/20 border border-red-900/50 rounded-lg p-4 flex items-center gap-4">
            <div className="p-3 bg-red-500/20 rounded-full text-red-500">
              <AlertTriangle size={24} />
            </div>
            <div>
              <div className="text-2xl font-light text-red-400">{String(criticalCount).padStart(2, '0')}</div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Critical Threats</div>
            </div>
          </div>

          <div className="bg-yellow-950/20 border border-yellow-900/50 rounded-lg p-4 flex items-center gap-4">
            <div className="p-3 bg-yellow-500/20 rounded-full text-yellow-500">
              <ShieldAlert size={24} />
            </div>
            <div>
              <div className="text-2xl font-light text-yellow-400">{String(warningCount).padStart(2, '0')}</div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Warnings</div>
            </div>
          </div>

          <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4 flex items-center gap-4">
            <div className="p-3 bg-emerald-500/20 rounded-full text-emerald-500">
              <CheckCircle size={24} />
            </div>
            <div>
              <div className="text-2xl font-light text-emerald-400">
                {String(resolvedToday || infoCount).padStart(2, '0')}
              </div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">{resolvedToday > 0 ? 'Resolved Today' : 'Information'}</div>
            </div>
          </div>
        </div>

        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">Active Incidents</h3>

        {filteredThreats.length === 0 && (
          <div className="flex items-center justify-center text-slate-500 font-mono py-12 border border-dashed border-slate-800 rounded-lg">
            {backendOk ? 'NO THREAT ALERTS MATCHING CRITERIA' : 'BACKEND OFFLINE — Check server on port 8001'}
          </div>
        )}

        {filteredThreats.map(threat => (
          <ThreatCard
            key={threat.id}
            threat={threat}
            onResolve={() => markAsResolved(threat.id)}
            onFalseAlarm={() => markAsFalseAlarm(threat.id)}
            onViewCamera={() => setCameraModal(threat.location || (threat as any).camera_id)}
            onTrackSuspect={() => onNavigate?.('person-tracking')}
          />
        ))}
      </div>

      {cameraModal && <CameraModal cam={cameraModal} onClose={() => setCameraModal(null)} />}
      <ThomasAI />
    </div>
  );
}

// ─── Threat Card (Vauldy UI merged with Soham features) ───────────────────────

function ThreatCard({ threat, onResolve, onFalseAlarm, onViewCamera, onTrackSuspect }: any) {
  const typeStr = threat.type || threat.threat_type || 'UNKNOWN THREAT';
  const locStr = threat.location || threat.camera_id || 'UNKNOWN LOCATION';
  const severity = (threat.severity || threat.threat_level || 'INFO').toUpperCase();
  const timeStr = threat.timestamp ? (threat.timestamp.includes('T') ? formatDistanceToNow(new Date(threat.timestamp)) + ' ago' : new Date(threat.timestamp).toLocaleTimeString()) : 'Now';
  const image = threat.imageUrl || "https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&q=80&w=400";
 
  return (
    <div className={`bg-[#151C2C] border ${severityBorder(severity)} rounded-lg overflow-hidden flex`}>
      <div className="w-64 shrink-0 relative bg-slate-900 overflow-hidden" style={{ minHeight: '160px' }}>
        <img src={image} alt={typeStr} className="w-full h-full object-cover opacity-80" style={{ minHeight: '160px' }} />
        <div className={`absolute top-2 left-2 ${severityBg(severity)} text-white text-[10px] font-bold px-2 py-1 rounded`}>
          {severity}
        </div>
        <div className="absolute bottom-2 right-2 flex items-center gap-1 bg-[#0B0F19]/80 px-1.5 py-0.5 rounded text-[9px] font-mono text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          LIVE
        </div>
      </div>

      <div className="p-5 flex-1 flex flex-col min-w-0">
        <div className="flex justify-between items-start mb-2 gap-4">
          <div className="min-w-0">
            <div className="text-xs text-slate-500 font-mono mb-1">{threat.id} • {timeStr}</div>
            <h4 className="text-lg font-bold text-slate-200 truncate">{typeStr.replace(/_/g, ' ')}</h4>
            <div className="text-sm text-cyan-400 flex items-center gap-1 mt-1">
              <Crosshair size={14} /> {locStr} {threat.command && `— ${threat.command}`}
            </div>
          </div>
          <button 
            onClick={onResolve}
            className="shrink-0 bg-red-500/10 hover:bg-emerald-500/20 text-red-400 hover:text-emerald-400 hover:border-emerald-500/30 border border-red-500/30 px-4 py-2 rounded text-xs font-bold tracking-wider transition-colors"
          >
            DISPATCH / RESOLVE
          </button>
        </div>

        <p className="text-sm text-slate-400 mt-2 flex-1">{threat.description || 'No additional details provided.'}</p>

        <div className="flex gap-2 mt-4 flex-wrap items-center">
          <button 
            onClick={onViewCamera}
            className="flex items-center gap-1.5 text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded border border-slate-700 transition-colors"
          >
            <Video size={12} /> View Camera Feed
          </button>
          <button 
            onClick={onTrackSuspect}
            className="flex items-center gap-1.5 text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded border border-slate-700 transition-colors"
          >
            <UserSearch size={12} /> Track Suspect
          </button>
          <button 
            onClick={onFalseAlarm}
            className="text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded border border-slate-700 transition-colors"
          >
            Mark False Alarm
          </button>
          
          <div className="ml-auto flex gap-2 text-[10px] font-mono text-slate-500 italic">
            <span>Model: {threat.transparency?.model_used || 'TICE Engine'}</span>
            <span>• Conf: {threat.aiConfidence || Math.round((threat.confidence || 0) * 100)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}