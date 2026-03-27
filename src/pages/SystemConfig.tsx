import React from 'react';
import { Header } from '../components/Header';
import { Settings, Save } from 'lucide-react';

export function SystemConfig({ onNavigate }: { onNavigate?: (page: any) => void }) {
  return (
    <div className="flex flex-col h-full">
      <Header 
        title="SYSTEM CONFIGURATION" 
        subtitle="Global Parameters & Thresholds"
        onNavigate={onNavigate}
      >
        <button className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors">
          <Save size={16} /> SAVE CHANGES
        </button>
      </Header>
      <div className="p-6 flex-1 overflow-y-auto">
        <div className="max-w-3xl space-y-6">
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
              <Settings size={18} className="text-cyan-400" /> AI Detection Thresholds
            </h3>
            <div className="space-y-4">
              <ConfigSlider label="Threat Detection Confidence" value="85%" />
              <ConfigSlider label="Facial Re-ID Match Threshold" value="92%" />
              <ConfigSlider label="Crowd Density Alert Trigger" value="4.5 persons/m²" />
            </div>
          </div>

          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
              <Settings size={18} className="text-cyan-400" /> Privacy & Retention
            </h3>
            <div className="space-y-4">
              <ConfigToggle label="Enable Differential Privacy (Re-ID)" active={true} />
              <ConfigToggle label="Auto-blur Faces (Non-Threats)" active={false} />
              <div className="flex justify-between items-center py-2 border-b border-slate-800/50">
                <span className="text-sm text-slate-300">Data Retention Period</span>
                <select className="bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-1 outline-none focus:border-cyan-500">
                  <option>24 Hours</option>
                  <option>7 Days</option>
                  <option>30 Days</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfigSlider({ label, value }: { label: string, value: string }) {
  return (
    <div className="py-2 border-b border-slate-800/50">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-slate-300">{label}</span>
        <span className="text-xs font-mono text-cyan-400">{value}</span>
      </div>
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full bg-cyan-500 w-[85%]"></div>
      </div>
    </div>
  );
}

function ConfigToggle({ label, active }: { label: string, active: boolean }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-800/50">
      <span className="text-sm text-slate-300">{label}</span>
      <div className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${active ? 'bg-cyan-500' : 'bg-slate-700'}`}>
        <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${active ? 'left-6' : 'left-1'}`}></div>
      </div>
    </div>
  );
}
