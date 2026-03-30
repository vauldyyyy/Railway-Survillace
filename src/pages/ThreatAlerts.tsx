import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { AlertTriangle, ShieldAlert, Crosshair, CheckCircle, Search, Filter, ChevronDown } from 'lucide-react';
import useAlertStore from '../store/useAlertStore';

export function ThreatAlerts({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const alerts = useAlertStore(state => state.alerts);

  const filteredThreats = useMemo(() => {
    return alerts.filter(threat => {
      const matchesSearch = 
        threat.threat_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        threat.camera_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        threat.command.toLowerCase().includes(searchQuery.toLowerCase());
      
      const level = String(threat.threat_level).toUpperCase();
      const matchesFilter = levelFilter === 'ALL' || level === levelFilter;
      
      return matchesSearch && matchesFilter;
    });
  }, [alerts, searchQuery, levelFilter]);

  const criticalCount = alerts.filter(a => a.threat_level === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.threat_level === 'HIGH').length;
  const infoCount = alerts.filter(a => a.threat_level === 'LOW' || a.threat_level === 'MEDIUM').length;

  return (
    <div className="flex flex-col h-full">
      <Header 
        title="THREAT ALERTS" 
        subtitle="Active Security Incidents & Automated Responses"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search alerts..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#151C2C] border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 w-64"
            />
          </div>
          <div className="relative">
            <button 
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className="flex items-center gap-2 bg-[#151C2C] border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
            >
              <Filter size={14} /> {levelFilter === 'ALL' ? 'FILTER' : levelFilter} <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
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
              <div className="text-2xl font-light text-emerald-400">{String(infoCount).padStart(2, '0')}</div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Information</div>
            </div>
          </div>
        </div>

        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">Active Incidents</h3>
        
        {filteredThreats.map(threat => (
          <ThreatCard key={threat.id} {...threat} />
        ))}

        {filteredThreats.length === 0 && (
          <div className="flex items-center justify-center text-slate-500 font-mono py-12 border border-dashed border-slate-800 rounded-lg">
            NO THREAT ALERTS MATCHING CRITERIA
          </div>
        )}
      </div>
    </div>
  );
}

function ThreatCard({ id, threat_type, camera_id, timestamp, threat_level, command, confidence }: any) {
  const timeStr = new Date(timestamp).toLocaleTimeString();
  const level = String(threat_level).toUpperCase();
  const image = "https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&q=80&w=400"; // Placeholder
 
  return (
    <div className={`bg-[#151C2C] border ${threat_level === 'CRITICAL' ? 'border-red-500/30' : 'border-slate-800'} rounded-lg overflow-hidden flex`}>
      <div className="w-64 shrink-0 relative bg-slate-900">
        <img src={image} alt={threat_type} className="w-full h-full object-cover opacity-80" />
        <div className={`absolute top-2 left-2 ${threat_level === 'CRITICAL' ? 'bg-red-500' : 'bg-amber-500'} text-white text-[10px] font-bold px-2 py-1 rounded`}>
          {level}
        </div>
      </div>
      <div className="p-5 flex-1 flex flex-col">
        <div className="flex justify-between items-start mb-2">
          <div>
            <div className="text-xs text-slate-500 font-mono mb-1">{id} • {timeStr}</div>
            <h4 className="text-lg font-bold text-slate-200">{threat_type}</h4>
            <div className="text-sm text-cyan-400 flex items-center gap-1 mt-1">
              <Crosshair size={14} /> {camera_id} — {command}
            </div>
          </div>
          <button className="bg-red-500 text-white border border-red-500 px-4 py-2 rounded text-xs font-bold tracking-wider hover:bg-red-600 transition-colors">
            DISPATCH TEAM
          </button>
        </div>
        <div className="flex gap-2 mt-4 text-[10px] font-mono text-slate-500 italic">
            <span>Model: TICE Engine V3</span>
            <span>• Conf: {Math.round((confidence || 0) * 100)}%</span>
        </div>
        <div className="flex gap-2 mt-4">
          <button className="text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded border border-slate-700 transition-colors">
            View Analytics
          </button>
        </div>
      </div>
    </div>
  );
}
