import React from 'react';
import { Header } from '../components/Header';
import { Users, Activity, TrendingUp } from 'lucide-react';

export function CrowdAnalytics({ onNavigate }: { onNavigate?: (page: any) => void }) {
  return (
    <div className="flex flex-col h-full">
      <Header 
        title="CROWD ANALYTICS" 
        subtitle="Density & Flow Monitoring"
        onNavigate={onNavigate}
      />
      <div className="p-6 flex-1 overflow-y-auto">
        <div className="grid grid-cols-3 gap-6 mb-6">
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Total Station Occupancy</span>
              <Users size={16} className="text-cyan-400" />
            </div>
            <div className="text-3xl font-light text-slate-200">4,285</div>
            <div className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
              <TrendingUp size={12} /> -5% vs expected
            </div>
          </div>
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Peak Density Area</span>
              <Activity size={16} className="text-yellow-400" />
            </div>
            <div className="text-xl font-bold text-slate-200 mt-1">Platform 2 North</div>
            <div className="text-xs text-yellow-400 mt-1 font-mono">3.2 persons/m²</div>
          </div>
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Flow Rate (In/Out)</span>
              <TrendingUp size={16} className="text-emerald-400" />
            </div>
            <div className="text-xl font-bold text-slate-200 mt-1">120 / 85 <span className="text-sm font-normal text-slate-500">per min</span></div>
            <div className="text-xs text-slate-400 mt-1">Net positive accumulation</div>
          </div>
        </div>

        <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6 h-[400px] flex flex-col">
          <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">Live Heatmap (Concourse)</h3>
          <div className="flex-1 relative bg-slate-900 rounded border border-slate-800 overflow-hidden flex items-center justify-center">
            {/* Abstract Heatmap */}
            <div className="absolute inset-0 opacity-30" style={{
              backgroundImage: 'radial-gradient(circle at 30% 40%, rgba(239, 68, 68, 0.8) 0%, transparent 40%), radial-gradient(circle at 70% 60%, rgba(234, 179, 8, 0.6) 0%, transparent 30%), radial-gradient(circle at 50% 80%, rgba(6, 182, 212, 0.4) 0%, transparent 50%)'
            }}></div>
            <div className="absolute inset-0" style={{
              backgroundImage: 'linear-gradient(#1e293b 1px, transparent 1px), linear-gradient(90deg, #1e293b 1px, transparent 1px)',
              backgroundSize: '20px 20px',
              opacity: 0.2
            }}></div>
            <span className="text-slate-500 font-mono text-sm z-10 bg-[#0B0F19]/80 px-4 py-2 rounded">HEATMAP_RENDER_ACTIVE</span>
          </div>
        </div>
      </div>
    </div>
  );
}
