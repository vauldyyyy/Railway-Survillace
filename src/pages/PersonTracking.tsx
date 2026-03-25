import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { Search, Layers, ZoomIn, Target, ShieldCheck, Video } from 'lucide-react';

const TRACKLETS = [
  {
    id: "TRK-0042",
    status: "FLAGGED",
    cam: "CAM-07 • Platform 2",
    time: "2 min ago",
    journey: "3 cameras",
    image: "https://images.unsplash.com/photo-1509305717900-84f40e786d82?auto=format&fit=crop&q=80&w=200",
  },
  {
    id: "TRK-0051",
    status: "NORMAL",
    cam: "CAM-12 • Concourse",
    time: "5 min ago",
    image: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=200",
  },
  {
    id: "TRK-0058",
    status: "NORMAL",
    cam: "CAM-04 • Entry G12",
    time: "8 min ago",
    image: "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&q=80&w=200",
  },
  {
    id: "TRK-0062",
    status: "FLAGGED",
    cam: "CAM-09 • South Gate",
    time: "12 min ago",
    journey: "2 cameras",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=200",
  },
  {
    id: "TRK-0075",
    status: "NORMAL",
    cam: "CAM-15 • Waiting Area",
    time: "15 min ago",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=200",
  }
];

export function PersonTracking({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTrackletId, setActiveTrackletId] = useState('TRK-0042');

  const filteredTracklets = useMemo(() => {
    return TRACKLETS.filter(t => 
      t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.cam.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.status.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [searchQuery]);

  const activeTracklet = TRACKLETS.find(t => t.id === activeTrackletId) || TRACKLETS[0];

  return (
    <div className="flex flex-col h-full">
      <Header 
        title="Multi-Camera Person Re-Identification — Zero-Knowledge Mode" 
        subtitle="OSNET 512-DIM EMBEDDINGS • DIFFERENTIAL PRIVACY PROTECTED (E=1.2)"
        onNavigate={onNavigate}
      >
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search by Track ID or visual description..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-[#151C2C] border border-slate-700 rounded-md py-2 pl-9 pr-4 text-sm text-slate-200 placeholder-slate-500 w-80 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </Header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Tracklets */}
        <div className="w-80 border-r border-slate-800 bg-[#0B0F19] flex flex-col">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center text-xs font-mono text-slate-400">
            <span>ACTIVE TRACKLETS ({filteredTracklets.length})</span>
            <span className="flex items-center gap-1 cursor-pointer hover:text-slate-200">
              <span className="text-slate-500">≡</span> SORT: RECENT
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {filteredTracklets.map(t => (
              <div key={t.id} onClick={() => setActiveTrackletId(t.id)}>
                <TrackletCard 
                  {...t}
                  active={t.id === activeTrackletId}
                />
              </div>
            ))}
            {filteredTracklets.length === 0 && (
              <div className="text-center text-slate-500 font-mono py-8">
                NO TRACKLETS FOUND
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Map/Timeline */}
        <div className="flex-1 bg-[#0F1523] p-6 flex flex-col relative">
          {/* Top Controls */}
          <div className="flex justify-between items-start mb-6 z-10">
            <div className="bg-[#151C2C] border border-slate-700 rounded-md p-3">
              <div className="text-xs text-slate-400 font-mono mb-1">TARGET FOCUS: {activeTracklet.id}</div>
              <div className="text-[10px] text-slate-500 font-mono">RE-ID CONFIDENCE: 94.2%</div>
            </div>
            <div className="flex gap-2">
              <button className="p-2 bg-[#151C2C] border border-slate-700 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800">
                <Layers size={18} />
              </button>
              <button className="p-2 bg-[#151C2C] border border-slate-700 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800">
                <ZoomIn size={18} />
              </button>
              <button className="p-2 bg-[#151C2C] border border-slate-700 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800">
                <Target size={18} />
              </button>
            </div>
          </div>

          {/* Visualization Area */}
          <div className="flex-1 relative border border-slate-800/50 rounded-lg bg-[#0B0F19] overflow-hidden flex items-center justify-center">
            {/* Abstract Map/Path Visualization */}
            <div className="absolute inset-0 opacity-20" style={{
              backgroundImage: 'linear-gradient(#1e293b 1px, transparent 1px), linear-gradient(90deg, #1e293b 1px, transparent 1px)',
              backgroundSize: '40px 40px'
            }}></div>
            
            {/* Path SVG */}
            <svg className="absolute inset-0 w-full h-full" style={{ filter: 'drop-shadow(0 0 8px rgba(6, 182, 212, 0.3))' }}>
              <path 
                d="M 200 200 Q 400 200 500 300 T 700 400" 
                fill="none" 
                stroke="#06b6d4" 
                strokeWidth="2" 
                strokeDasharray="4 4" 
                className="opacity-50"
              />
            </svg>

            {/* Nodes */}
            <div className="absolute top-[180px] left-[180px] flex flex-col items-center">
              <div className="w-10 h-10 bg-[#151C2C] border border-slate-600 rounded-lg flex items-center justify-center mb-2">
                <Video size={16} className="text-slate-400" />
              </div>
              <span className="text-[10px] font-mono text-slate-400">CAM-01 (ENTRY)</span>
            </div>

            <div className="absolute top-[180px] left-[380px] flex flex-col items-center">
              <div className="w-10 h-10 bg-[#151C2C] border border-slate-600 rounded-lg flex items-center justify-center mb-2">
                <Video size={16} className="text-slate-400" />
              </div>
              <span className="text-[10px] font-mono text-slate-400">CAM-04 (WAITING)</span>
            </div>

            <div className="absolute top-[380px] left-[680px] flex flex-col items-center">
              <div className="w-12 h-12 bg-cyan-950/50 border-2 border-cyan-500 rounded-lg flex items-center justify-center mb-2 relative">
                <div className="absolute inset-0 bg-cyan-500/20 animate-ping rounded-lg"></div>
                <Video size={20} className="text-cyan-400" />
              </div>
              <span className="text-[10px] font-mono text-cyan-400 font-bold">CAM-07 (PLATFORM 2)</span>
            </div>
          </div>

          {/* Bottom Timeline & Info */}
          <div className="mt-6 grid grid-cols-3 gap-6">
            <div className="col-span-2 bg-[#151C2C] border border-slate-800 rounded-lg p-4 flex flex-col justify-center">
              <div className="relative h-1 bg-slate-800 rounded-full w-full mb-6 mt-2">
                <div className="absolute top-1/2 -translate-y-1/2 left-[10%] w-3 h-3 rounded-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.8)]"></div>
                <div className="absolute top-1/2 -translate-y-1/2 left-[50%] w-3 h-3 rounded-full bg-slate-600"></div>
                <div className="absolute top-1/2 -translate-y-1/2 left-[90%] w-3 h-3 rounded-full bg-slate-600"></div>
                
                <div className="absolute top-4 left-[10%] -translate-x-1/2 text-center">
                  <div className="text-xs font-bold text-slate-200">13:42</div>
                  <div className="text-[10px] text-slate-500">Gate 13</div>
                </div>
                <div className="absolute top-4 left-[50%] -translate-x-1/2 text-center">
                  <div className="text-xs font-bold text-slate-400">13:45</div>
                  <div className="text-[10px] text-slate-500">Waiting Area</div>
                </div>
                <div className="absolute top-4 left-[90%] -translate-x-1/2 text-center">
                  <div className="text-xs font-bold text-cyan-400">13:51</div>
                  <div className="text-[10px] text-cyan-600">Platform 2</div>
                </div>
              </div>
            </div>
            
            <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-4 flex justify-around items-center">
              <div className="text-center">
                <div className="text-[10px] text-slate-500 font-mono mb-1 uppercase">Dwell Time</div>
                <div className="text-2xl font-light text-slate-200">09:12<span className="text-sm text-slate-500">s</span></div>
              </div>
              <div className="w-px h-10 bg-slate-800"></div>
              <div className="text-center">
                <div className="text-[10px] text-slate-500 font-mono mb-1 uppercase">Node Count</div>
                <div className="text-2xl font-light text-slate-200">03</div>
              </div>
            </div>
          </div>

          {/* Privacy Notice */}
          <div className="mt-4 bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4 flex items-start gap-4">
            <div className="p-2 bg-emerald-900/40 rounded-md text-emerald-500">
              <ShieldCheck size={20} />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-emerald-400 mb-1">Privacy Notice: Differential Privacy Active</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                All Re-ID embeddings are generated and stored with Gaussian Differential Privacy noise (σ=0.1, ε=1.2). Biometric reconstruction from feature vectors is mathematically prevented. No PII is stored alongside tracklets. Logs are purged after 24 hours.
              </p>
            </div>
            <button className="px-4 py-2 bg-[#151C2C] border border-slate-700 rounded-md text-xs font-mono text-slate-300 hover:bg-slate-800">
              AUDIT<br/>LOGS
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TrackletCard({ id, status, cam, time, journey, image, active }: any) {
  return (
    <div className={`rounded-lg p-3 flex gap-4 transition-colors cursor-pointer relative overflow-hidden ${active ? 'bg-[#151C2C] border border-cyan-500/30' : 'bg-[#151C2C]/50 border border-slate-800 hover:bg-[#151C2C]'}`}>
      {active && <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyan-500"></div>}
      
      <div className="w-16 h-20 rounded bg-slate-800 overflow-hidden relative shrink-0">
        <img src={image} alt={id} className={`w-full h-full object-cover ${!active && 'grayscale opacity-60'}`} />
        <div className="absolute bottom-1 right-1 w-4 h-4 bg-emerald-500/20 backdrop-blur rounded flex items-center justify-center">
          <ShieldCheck size={10} className="text-emerald-400" />
        </div>
      </div>
      
      <div className="flex-1 flex flex-col justify-center">
        <div className="flex justify-between items-start mb-2">
          <span className={`font-bold ${active ? 'text-slate-200' : 'text-slate-400'}`}>{id}</span>
          <span className={`text-[9px] font-mono px-2 py-0.5 rounded-full border ${status === 'FLAGGED' ? 'border-red-500/50 text-red-400 bg-red-500/10' : 'border-slate-600 text-slate-400'}`}>
            {status}
          </span>
        </div>
        <div className="space-y-1 text-[10px] font-mono text-slate-500">
          <div className="flex items-center gap-2">
            <Video size={10} /> {cam}
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 text-center">⏱</span> {time}
          </div>
          {journey && (
            <div className="flex items-center gap-2 text-cyan-600/70">
              <span className="w-2.5 text-center">↹</span> Journey: {journey}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
