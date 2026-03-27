import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { Shield, Lock, Server, Activity, Search, Filter, ChevronDown } from 'lucide-react';

const NODES = [
  { id: 'CORE-SEC-01', type: 'Main Auth Server', status: 'ONLINE', latency: '12ms', uptime: '99.99%' },
  { id: 'EDGE-CAM-GROUP-A', type: 'Video Ingestion', status: 'ONLINE', latency: '24ms', uptime: '99.95%' },
  { id: 'AI-INFERENCE-03', type: 'GPU Cluster', status: 'HIGH LOAD', latency: '85ms', uptime: '99.90%' },
  { id: 'DB-REPLICA-WEST', type: 'Database Node', status: 'ONLINE', latency: '18ms', uptime: '99.98%' },
  { id: 'EDGE-CAM-GROUP-B', type: 'Video Ingestion', status: 'OFFLINE', latency: '-', uptime: '95.20%' },
];

export function SecurityLayer({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const filteredNodes = useMemo(() => {
    return NODES.filter(node => {
      const matchesSearch = 
        node.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.type.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesFilter = statusFilter === 'ALL' || node.status === statusFilter;
      
      return matchesSearch && matchesFilter;
    });
  }, [searchQuery, statusFilter]);

  return (
    <div className="flex flex-col h-full">
      <Header 
        title="SECURITY LAYER" 
        subtitle="System Integrity & Encryption Status"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search nodes..." 
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
              <Filter size={14} /> {statusFilter === 'ALL' ? 'FILTER' : statusFilter} <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'ONLINE', 'HIGH LOAD', 'OFFLINE'].map(status => (
                  <button
                    key={status}
                    onClick={() => { setStatusFilter(status); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-800 text-slate-300"
                  >
                    {status === 'ALL' ? 'All Statuses' : status}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </Header>
      <div className="p-6 flex-1 overflow-y-auto">
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="bg-[#151C2C] border border-emerald-500/30 rounded-lg p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-emerald-500/20 rounded-full text-emerald-500">
                <Shield size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-200">Firewall Status</h3>
                <p className="text-sm text-emerald-400">ACTIVE & BLOCKING</p>
              </div>
            </div>
            <div className="space-y-2 text-sm text-slate-400 font-mono">
              <div className="flex justify-between"><span>Packets Inspected:</span> <span className="text-slate-200">1.42B</span></div>
              <div className="flex justify-between"><span>Threats Blocked:</span> <span className="text-slate-200">14,205</span></div>
              <div className="flex justify-between"><span>DDoS Mitigation:</span> <span className="text-emerald-400">STANDBY</span></div>
            </div>
          </div>

          <div className="bg-[#151C2C] border border-cyan-500/30 rounded-lg p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-cyan-500/20 rounded-full text-cyan-500">
                <Lock size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-200">Encryption</h3>
                <p className="text-sm text-cyan-400">AES-256-GCM (End-to-End)</p>
              </div>
            </div>
            <div className="space-y-2 text-sm text-slate-400 font-mono">
              <div className="flex justify-between"><span>Key Rotation:</span> <span className="text-slate-200">2 hrs ago</span></div>
              <div className="flex justify-between"><span>Active Tunnels:</span> <span className="text-slate-200">42</span></div>
              <div className="flex justify-between"><span>Cert Status:</span> <span className="text-emerald-400">VALID</span></div>
            </div>
          </div>
        </div>

        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">Node Health</h3>
        <div className="bg-[#151C2C] border border-slate-800 rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/50 text-slate-400 font-mono text-xs">
              <tr>
                <th className="p-4 font-medium">NODE ID</th>
                <th className="p-4 font-medium">TYPE</th>
                <th className="p-4 font-medium">STATUS</th>
                <th className="p-4 font-medium">LATENCY</th>
                <th className="p-4 font-medium">UPTIME</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-slate-300">
              {filteredNodes.map((node, i) => (
                <tr key={i}>
                  <td className="p-4 font-mono">{node.id}</td>
                  <td className="p-4">{node.type}</td>
                  <td className="p-4">
                    <span className={`flex items-center gap-2 ${
                      node.status === 'ONLINE' ? 'text-emerald-400' : 
                      node.status === 'HIGH LOAD' ? 'text-yellow-400' : 
                      'text-red-400'
                    }`}>
                      <Activity size={14}/> {node.status}
                    </span>
                  </td>
                  <td className="p-4 font-mono">{node.latency}</td>
                  <td className="p-4 font-mono">{node.uptime}</td>
                </tr>
              ))}
              {filteredNodes.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500 font-mono">
                    NO NODES MATCHING CRITERIA
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
