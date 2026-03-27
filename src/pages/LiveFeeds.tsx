import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { Maximize2, ChevronDown, X, Search, Filter, AlertTriangle } from 'lucide-react';

const CAMERAS = [
  {
    id: "CAM-01: MAIN CONCOURSE",
    active: true,
    image: "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?auto=format&fit=crop&q=80&w=800",
    overlay: (
      <>
        <div className="absolute top-1/4 left-1/3 w-24 h-48 border border-cyan-400/50 bg-cyan-400/10">
          <div className="absolute -top-5 left-0 bg-cyan-400/80 text-[#0B0F19] text-[10px] px-1 font-mono font-bold">PERSON_902</div>
        </div>
        <div className="absolute top-1/2 left-[40%] w-16 h-16 border border-yellow-400/50 bg-yellow-400/10">
          <div className="absolute -top-5 left-0 bg-yellow-400/80 text-[#0B0F19] text-[10px] px-1 font-mono font-bold">OBJ_77_BAG</div>
        </div>
      </>
    ),
    stats: { person: 14, obj: 2, fps: 60, time: '14:22:01:04' },
    zone: 'Concourse',
    type: 'Optical'
  },
  {
    id: "CAM-04: PLATFORM 2 WEST",
    warning: true,
    image: "https://images.unsplash.com/photo-1584432810601-6c7f27d2362b?auto=format&fit=crop&q=80&w=800",
    overlay: (
      <div className="absolute top-1/3 left-1/4 right-1/4 bottom-1/3 border-2 border-red-500/50 border-dashed bg-red-500/5 flex items-center justify-center">
        <div className="bg-red-500/80 text-white text-xs px-2 py-1 font-mono font-bold tracking-widest">THREAT_DETECTED</div>
      </div>
    ),
    stats: { threat: 1, fps: 58, time: '14:22:01:04' },
    zone: 'Platform',
    type: 'Optical'
  },
  {
    id: "CAM-07: PERIMETER FENCE (THERMAL)",
    thermal: true,
    image: "https://images.unsplash.com/photo-1474487548417-781cb71495f3?auto=format&fit=crop&q=80&w=800",
    stats: { heat: 0, fps: 30, time: '14:22:01:04' },
    zone: 'Perimeter',
    type: 'Thermal'
  },
  { id: "CAM-08: NORTH_GATE_LOADING", dark: true, stats: { person: 0, time: '14:22:01:04' }, zone: 'Gate', type: 'Optical' },
  { id: "CAM-12: SWITCH_STATION_B", dark: true, stats: { person: 0, time: '14:22:01:04' }, zone: 'Station', type: 'Optical' },
  { id: "CAM-14: TRACK_INSPECTION_UNDER", dark: true, stats: { person: 0, time: '14:22:01:04' }, zone: 'Track', type: 'Optical' },
  { id: "CAM-16: WAITING_LOUNGE_V6", dark: true, stats: { person: 4, time: '14:22:01:04' }, zone: 'Lounge', type: 'Optical' },
  { id: "CAM-19: EXIT_TURNSTILE_02", dark: true, stats: { person: 8, time: '14:22:01:04' }, zone: 'Gate', type: 'Optical' },
  {
    id: "CAM-22: ROOFTOP_HVAC_SECURITY",
    dark: true,
    stats: { person: 0 },
    zone: 'Roof',
    type: 'Optical',
    overlay: (
      <div className="absolute bottom-4 right-4 bg-[#0B0F19]/90 border border-slate-700 rounded p-3 text-[10px] font-mono min-w-[200px]">
        <div className="flex justify-between mb-2">
          <span className="text-slate-400">AI AGENT CONSENSUS</span>
          <span className="text-slate-200 font-bold">98.4%</span>
        </div>
        <div className="w-full h-1 bg-slate-800 rounded-full mb-3">
          <div className="h-full bg-cyan-500 w-[98.4%]"></div>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">NODE_HEALTH</span>
          <span className="text-emerald-400">OPTIMAL</span>
        </div>
      </div>
    )
  }
];

export function LiveFeeds({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [layout, setLayout] = useState<'1x1' | '2x2' | '3x3' | '4x4'>('3x3');
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [zoomedCamera, setZoomedCamera] = useState<any | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const filteredCameras = useMemo(() => {
    return CAMERAS.filter(cam => {
      const matchesFilter = filter === 'ALL' || cam.zone === filter || cam.type === filter || (filter === 'THREATS' && cam.warning);
      const matchesSearch = cam.id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [filter, searchQuery]);

  const gridCols = {
    '1x1': 'grid-cols-1',
    '2x2': 'grid-cols-2',
    '3x3': 'grid-cols-3',
    '4x4': 'grid-cols-4',
  }[layout];

  return (
    <div className="flex flex-col h-full relative">
      <Header 
        title="LIVE SURVEILLANCE FEEDS" 
        subtitle="Madgaon Junction — Zone A Security Perimeter"
        onNavigate={onNavigate}
      >
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search cameras..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#151C2C] border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 w-48"
            />
          </div>
          <div className="flex bg-[#151C2C] border border-slate-700 rounded-md overflow-hidden text-xs font-mono">
            {(['1x1', '2x2', '3x3', '4x4'] as const).map(l => (
              <button 
                key={l}
                onClick={() => setLayout(l)}
                className={`px-3 py-1.5 ${layout === l ? 'bg-slate-700 text-slate-200' : 'text-slate-400 hover:bg-slate-800'} ${l !== '1x1' ? 'border-l border-slate-700' : ''}`}
              >
                {l}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono relative">
            <span>FILTER:</span>
            <button 
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className="flex items-center gap-2 bg-[#151C2C] border border-slate-700 rounded-md px-3 py-1.5 hover:bg-slate-800"
            >
              {filter === 'ALL' ? 'ALL CAMERAS' : filter} <ChevronDown size={14} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-40 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'THREATS', 'Optical', 'Thermal', 'Concourse', 'Platform', 'Gate'].map(f => (
                  <button
                    key={f}
                    onClick={() => { setFilter(f); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 hover:bg-slate-800 text-slate-300"
                  >
                    {f === 'ALL' ? 'All Cameras' : f}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </Header>

      <div className="p-6 flex-1 overflow-y-auto">
        <div className={`grid ${gridCols} gap-4 h-full auto-rows-fr`}>
          {filteredCameras.map((cam, idx) => (
            <FeedCard 
              key={idx}
              {...cam}
              onClick={() => setZoomedCamera(cam)}
            />
          ))}
          {filteredCameras.length === 0 && (
            <div className="col-span-full flex items-center justify-center text-slate-500 font-mono">
              NO CAMERAS MATCHING CRITERIA
            </div>
          )}
        </div>
      </div>

      {/* Zoom Modal */}
      {zoomedCamera && (
        <div className="fixed inset-0 z-50 bg-[#0B0F19]/95 backdrop-blur-sm flex items-center justify-center p-8">
          <div className="w-full h-full max-w-6xl max-h-[80vh] flex flex-col bg-[#151C2C] border border-slate-700 rounded-lg overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-4 border-b border-slate-800 bg-[#0B0F19]">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${zoomedCamera.active ? 'bg-emerald-500' : zoomedCamera.warning ? 'bg-red-500 animate-pulse' : zoomedCamera.thermal ? 'bg-blue-500' : 'bg-slate-600'}`}></div>
                <h2 className="text-lg font-mono font-bold text-slate-200">{zoomedCamera.id}</h2>
                <span className="text-xs font-mono text-slate-500 bg-slate-800 px-2 py-1 rounded">LIVE FEED</span>
              </div>
              <button 
                onClick={() => { setZoomedCamera(null); setZoomLevel(1); }}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 relative bg-black overflow-hidden flex items-center justify-center">
              {zoomedCamera.image ? (
                <div className="w-full h-full relative transition-transform duration-300" style={{ transform: `scale(${zoomLevel})` }}>
                  <img 
                    src={zoomedCamera.image} 
                    alt={zoomedCamera.id} 
                    className={`w-full h-full object-contain ${zoomedCamera.thermal ? 'sepia-[.8] hue-rotate-[320deg] saturate-[3]' : zoomedCamera.dark ? 'opacity-50 grayscale blur-[1px]' : ''}`}
                  />
                  {zoomedCamera.overlay}
                </div>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-slate-700 font-mono text-xl">
                  {zoomedCamera.id.split(':')[1]?.trim() || zoomedCamera.id}
                </div>
              )}
              
              {/* Extra Zoom Controls Overlay */}
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 bg-[#0B0F19]/80 backdrop-blur border border-slate-700 rounded-full p-2 z-10">
                <button onClick={() => setZoomLevel(1)} className={`px-4 py-1 text-xs font-mono rounded-full ${zoomLevel === 1 ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-300 hover:text-cyan-400 hover:bg-slate-800'}`}>1x</button>
                <button onClick={() => setZoomLevel(2)} className={`px-4 py-1 text-xs font-mono rounded-full ${zoomLevel === 2 ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-300 hover:text-cyan-400 hover:bg-slate-800'}`}>2x</button>
                <button onClick={() => setZoomLevel(4)} className={`px-4 py-1 text-xs font-mono rounded-full ${zoomLevel === 4 ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-300 hover:text-cyan-400 hover:bg-slate-800'}`}>4x</button>
                <div className="w-px bg-slate-700 mx-1"></div>
                <button className="px-4 py-1 text-xs font-mono text-slate-300 hover:text-red-400 hover:bg-slate-800 rounded-full flex items-center gap-2">
                  <AlertTriangle size={12} /> FLAG
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer Status Bar */}
      <div className="bg-[#0B0F19] border-t border-slate-800 px-6 py-3 flex items-center justify-between text-[10px] font-mono text-slate-400">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span>THREAT LEVEL</span>
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              <div className="w-2 h-2 rounded-full bg-slate-700"></div>
              <div className="w-2 h-2 rounded-full bg-slate-700"></div>
              <div className="w-2 h-2 rounded-full bg-slate-700"></div>
            </div>
            <span className="text-emerald-500 ml-1">LOW_STEADY</span>
          </div>
          <div>
            <span>STATION LOAD</span>
            <span className="text-cyan-400 ml-2">64.2% NOMINAL</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <span>RECD_BUFFER: 94%</span>
          <span>ENC: AES-256-GCM</span>
          <span>OPERATOR: RPF_GOA_01</span>
        </div>
      </div>
    </div>
  );
}

function FeedCard({ id, active, warning, thermal, dark, image, overlay, stats, onClick }: any) {
  return (
    <div 
      className="bg-[#151C2C] border border-slate-800 rounded-lg overflow-hidden flex flex-col relative group cursor-pointer hover:border-cyan-500/50 transition-colors"
      onClick={onClick}
    >
      {/* Header */}
      <div className="px-3 py-2 flex items-center gap-2 text-[10px] font-mono border-b border-slate-800/50 absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-[#0B0F19]/80 to-transparent">
        <div className={`w-2 h-2 rounded-full ${active ? 'bg-emerald-500' : warning ? 'bg-red-500 animate-pulse' : thermal ? 'bg-blue-500' : 'bg-slate-600'}`}></div>
        <span className="text-slate-200 font-semibold tracking-wider drop-shadow-md">{id}</span>
        {active && <span className="ml-auto text-slate-400">LOCKED: 45.2°N</span>}
      </div>

      {/* Video Area */}
      <div className="flex-1 relative bg-slate-900 overflow-hidden">
        {image ? (
          <img 
            src={image} 
            alt={id} 
            className={`w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 ${thermal ? 'sepia-[.8] hue-rotate-[320deg] saturate-[3]' : dark ? 'opacity-30 grayscale blur-[1px]' : 'opacity-80'}`}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-slate-700 font-mono text-sm">
            {id.split(':')[1]?.trim() || id}
          </div>
        )}
        {overlay}
        
        {/* Hover Zoom Icon */}
        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none z-20">
          <div className="bg-[#0B0F19]/80 backdrop-blur p-3 rounded-full border border-slate-700 text-white">
            <Maximize2 size={24} />
          </div>
        </div>
      </div>

      {/* Footer Stats */}
      <div className="px-3 py-2 bg-[#151C2C] border-t border-slate-800 flex justify-between items-center text-[10px] font-mono text-slate-400">
        <div className="flex gap-4">
          {stats?.person !== undefined && (
            <div className="flex items-center gap-1">
              <span className="text-slate-500">👤</span> {stats.person < 10 ? `0${stats.person}` : stats.person}
            </div>
          )}
          {stats?.obj !== undefined && (
            <div className="flex items-center gap-1">
              <span className="text-slate-500">📦</span> {stats.obj < 10 ? `0${stats.obj}` : stats.obj}
            </div>
          )}
          {stats?.threat !== undefined && (
            <div className="flex items-center gap-1 text-red-400 font-bold">
              <span>⚠️</span> {stats.threat < 10 ? `0${stats.threat}` : stats.threat} THREAT
            </div>
          )}
          {stats?.heat !== undefined && (
            <div className="flex items-center gap-1">
              HEAT_SIG: {stats.heat < 10 ? `0${stats.heat}` : stats.heat}
            </div>
          )}
        </div>
        <div className="flex gap-4">
          {stats?.fps && <span className="text-cyan-600">{stats.fps} FPS</span>}
          <span>{stats?.time || '14:22:01:04'}</span>
        </div>
      </div>
    </div>
  );
}
