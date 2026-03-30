import React, { useState, useEffect, useRef } from 'react';
import { Header } from '../components/Header';
import {
  Maximize2, X, AlertTriangle, ShieldAlert, Flame,
  Users, Package, Train, Camera, Wifi,
  Link as LinkIcon, Save, Edit3, Plus
} from 'lucide-react';
import useSystemStore from '../store/useSystemStore';

// ─── Camera definitions ────────────────────────────────────────────────────

interface CamDef {
  id: string;
  label: string;
  streamUrl: string;
  location: string;
  features: string[];
  featureIcons: React.ReactNode[];
}

const INITIAL_CAMERAS: CamDef[] = [
  {
    id: 'cam1',
    label: 'CAM-01_PLATFORM',
    location: 'Crowd Stress Test',
    streamUrl: 'http://localhost:8001/video/cam1',
    features: ['Baggage', 'Track', 'Crowd', 'Fire', 'Re-ID'],
    featureIcons: [
      <Package size={10} key="b" />,
      <Train size={10} key="t" />,
      <Users size={10} key="c" />,
      <Flame size={10} key="f" />,
      <Camera size={10} key="r" />,
    ],
  },
  {
    id: 'cam2',
    label: 'CAM-02_NIGHT',
    location: 'Low Light / Rain',
    streamUrl: 'http://localhost:8001/video/cam2',
    features: ['Track', 'Re-ID'],
    featureIcons: [<Train size={10} key="t" />, <Camera size={10} key="r" />],
  },
  {
    id: 'cam3',
    label: 'CAM-03_SMOKE',
    location: 'Industrial Zone',
    streamUrl: 'http://localhost:8001/video/cam3',
    features: ['Baggage', 'Crowd', 'Re-ID'],
    featureIcons: [
      <Package size={10} key="b" />,
      <Users size={10} key="c" />,
      <Camera size={10} key="r" />,
    ],
  },
  {
    id: 'cam4',
    label: 'CAM-04_BAGGAGE',
    location: 'Terminal Concourse',
    streamUrl: 'http://localhost:8001/video/cam4',
    features: ['Re-ID'],
    featureIcons: [<Camera size={10} key="r" />],
  },
  {
    id: 'cam5',
    label: 'CAM-05',
    location: 'Exit View',
    streamUrl: 'http://localhost:8001/video/cam5',
    features: ['Re-ID'],
    featureIcons: [<Camera size={10} key="r" />],
  },
  {
    id: 'cam6',
    label: 'CAM-06',
    location: 'Edge Camera',
    streamUrl: 'http://localhost:8001/video/cam6',
    features: ['Baggage', 'Crowd', 'Re-ID'],
    featureIcons: [
      <Package size={10} key="b" />,
      <Users size={10} key="c" />,
      <Camera size={10} key="r" />,
    ],
  },
  // Placeholder slots so 3x3 grid looks full
  { id: 'p1', label: 'CAM-07', location: 'Reserved', streamUrl: '', features: [], featureIcons: [] },
  { id: 'p2', label: 'CAM-08', location: 'Reserved', streamUrl: '', features: [], featureIcons: [] },
  { id: 'p3', label: 'CAM-09', location: 'Reserved', streamUrl: '', features: [], featureIcons: [] },
];

// Feature badge colours
const FEATURE_COLORS: Record<string, string> = {
  Baggage: 'text-orange-400 border-orange-500/40 bg-orange-500/10',
  Track:   'text-red-400   border-red-500/40   bg-red-500/10',
  Crowd:   'text-yellow-400 border-yellow-500/40 bg-yellow-500/10',
  Fire:    'text-rose-400  border-rose-500/40  bg-rose-500/10',
  'Re-ID': 'text-cyan-400  border-cyan-500/40  bg-cyan-500/10',
};

// ─── Alert Banner ──────────────────────────────────────────────────────────

interface AlertEntry {
  id: string;
  cam: string;
  type: string;
  desc: string;
  ts: number;
}

// ─── Main Component ────────────────────────────────────────────────────────

export function LiveFeeds({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [cameras, setCameras] = useState<CamDef[]>(INITIAL_CAMERAS);
  const [zoomed, setZoomed] = useState<CamDef | null>(null);
  const [alerts, setAlerts] = useState<AlertEntry[]>([]);
  const [backendOk, setBackendOk] = useState(true);
  const [stats, setStats] = useState({ total_tracked: 0, flagged: 0, cameras_active: 6, recent_alerts: 0 });
  const globalConfidence = useSystemStore(state => state.globalConfidence);

  // Poll alerts + stats
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [aRes, sRes] = await Promise.all([
          fetch('http://127.0.0.1:8001/api/alerts'),
          fetch('http://127.0.0.1:8001/api/stats'),
        ]);
        if (aRes.ok) setAlerts(await aRes.json());
        if (sRes.ok) setStats(await sRes.json());
        setBackendOk(true);
      } catch {
        setBackendOk(false);
      }
    };
    fetchData();
    const t = setInterval(fetchData, 3000);
    return () => clearInterval(t);
  }, []);

  const handleUpdateSource = async (cameraId: string, newSource: string) => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/stream/source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: cameraId, source: newSource }),
      });
      if (res.ok) {
        // Update local state to show it's "Real" now
        setCameras(prev => prev.map(c => 
          c.id === cameraId 
            ? { ...c, streamUrl: `http://127.0.0.1:8001/video/${cameraId}`, location: 'Custom Stream' } 
            : c
        ));
      }
    } catch (err) {
      console.error("Failed to update source", err);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="LIVE SURVEILLANCE FEEDS"
        subtitle={`Madgaon Junction — ${stats.cameras_active} Active Cameras | AI Analysis Running`}
        onNavigate={onNavigate}
      >
        <div className={`flex items-center gap-2 text-[10px] font-mono px-3 py-1 rounded-full border ${
          backendOk
            ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
            : 'border-red-500/40 text-red-400 bg-red-500/10'
        }`}>
          {backendOk
            ? <><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />AI ENGINE LIVE</>
            : <><ShieldAlert size={10} /> BACKEND OFFLINE</>
          }
        </div>
      </Header>

      {/* Alert ticker */}
      {alerts.length > 0 && (
        <div className="bg-red-950/30 border-b border-red-900/50 px-6 py-2 flex items-center gap-4 overflow-hidden">
          <span className="text-[10px] font-mono text-red-400 font-bold shrink-0 flex items-center gap-1">
            <AlertTriangle size={12} className="animate-pulse" /> LIVE ALERTS
          </span>
          <div className="flex gap-6 overflow-x-auto no-scrollbar">
            {alerts.slice(0, 5).map(a => (
              <span key={a.id} className="text-[10px] font-mono text-slate-300 whitespace-nowrap">
                <span className={`mr-1 ${
                  a.type === 'FIRE' || a.type === 'SMOKE' ? 'text-rose-400' :
                  a.type === 'TRACK_INTRUSION' ? 'text-red-400' :
                  a.type === 'UNATTENDED_BAGGAGE' ? 'text-orange-400' :
                  a.type === 'OVERCROWDING' ? 'text-yellow-400' : 'text-slate-400'
                }`}>[{a.type}]</span>
                {a.cam} — {a.desc}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="px-6 py-3 border-b border-slate-800 grid grid-cols-4 gap-4">
        {[
          { label: 'CAMERAS ACTIVE', value: `${stats.cameras_active}/9`, color: 'text-cyan-400' },
          { label: 'PERSONS TRACKED', value: stats.total_tracked, color: 'text-slate-200' },
          { label: 'FLAGGED', value: stats.flagged, color: stats.flagged > 0 ? 'text-red-400' : 'text-slate-400' },
          { label: 'RECENT ALERTS (5m)', value: stats.recent_alerts, color: stats.recent_alerts > 0 ? 'text-yellow-400' : 'text-slate-400' },
        ].map(s => (
          <div key={s.label} className="bg-[#0B0F19] border border-slate-800 rounded px-4 py-2">
            <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{s.label}</div>
            <div className={`text-xl font-light font-mono ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* 3×3 Camera Grid */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="grid grid-cols-3 gap-4 h-full" style={{ gridAutoRows: '1fr' }}>
          {cameras.map(cam => (
            <CameraCard
              key={cam.id}
              cam={cam}
              isReal={!!cam.streamUrl}
              onZoom={() => cam.streamUrl && setZoomed(cam)}
              confidence={globalConfidence}
              onUpdateSource={(src) => handleUpdateSource(cam.id, src)}
            />
          ))}
        </div>
      </div>

      {/* Feature Legend */}
      <div className="px-6 py-3 border-t border-slate-800 bg-[#0B0F19] flex items-center gap-6 flex-wrap">
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">AI FEATURES:</span>
        {Object.entries(FEATURE_COLORS).map(([name, cls]) => (
          <span key={name} className={`text-[10px] font-mono px-2 py-0.5 rounded border ${cls}`}>
            {name}
          </span>
        ))}
        <span className="ml-auto text-[10px] font-mono text-slate-500">
          ENC: AES-256-GCM | DP: ε=1.2 | OPERATOR: RPF_GOA_01
        </span>
      </div>

      {/* Zoom Modal */}
      {zoomed && (
        <ZoomModal cam={zoomed} onClose={() => setZoomed(null)} />
      )}
    </div>
  );
}

// ─── Camera Card ───────────────────────────────────────────────────────────

function CameraCard({
  cam, isReal, onZoom, confidence, onUpdateSource
}: { 
  cam: CamDef; 
  isReal: boolean; 
  onZoom: () => void; 
  confidence?: number;
  onUpdateSource: (src: string) => void;
}) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [showInput, setShowInput] = useState(false);
  const [newUrl, setNewUrl] = useState('');

  // Reset when cam changes
  useEffect(() => { setShowInput(false); setNewUrl(''); }, [cam.id]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newUrl.trim()) {
      onUpdateSource(newUrl.trim());
      setShowInput(false);
      setNewUrl('');
    }
  };

  if (!isReal) {
    return (
      <div className="bg-[#0B0F19] border border-slate-800 rounded-lg overflow-hidden flex flex-col group relative">
        <div className="px-3 py-2 border-b border-slate-800/50 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-slate-700" />
          <span className="text-[10px] font-mono text-slate-600">{cam.label} • {cam.location}</span>
        </div>
        
        <div className="flex-1 flex flex-col items-center justify-center bg-[#060a12] p-4">
          {!showInput ? (
            <button 
              onClick={() => setShowInput(true)}
              className="text-slate-500 font-mono text-xs text-center group-hover:text-cyan-400 transition-colors"
            >
              <Plus size={24} className="mx-auto mb-2 opacity-30 group-hover:opacity-100" />
              ADD STREAM SOURCE
            </button>
          ) : (
            <form onSubmit={handleSubmit} className="w-full space-y-2">
              <input 
                autoFocus
                type="text"
                placeholder="YouTube or Stream URL..."
                className="w-full bg-[#0B0F19] border border-slate-700 rounded px-2 py-1.5 text-[10px] font-mono text-slate-200 outline-none focus:border-cyan-500/50"
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
              />
              <div className="flex gap-2">
                <button type="submit" className="flex-1 bg-cyan-500/20 text-cyan-400 text-[9px] font-mono py-1 rounded border border-cyan-500/30 hover:bg-cyan-500/30">
                  ACTIVATE
                </button>
                <button type="button" onClick={() => setShowInput(false)} className="px-2 py-1 text-slate-500 hover:text-white">
                  <X size={12} />
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="bg-[#0B0F19] border border-slate-800 rounded-lg overflow-hidden flex flex-col group transition-colors relative"
    >
      {/* Card Header */}
      <div className="px-3 py-2 border-b border-slate-800/50 flex items-center gap-2 bg-[#0B0F19]/90 z-10">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
        <span className="text-[10px] font-mono text-cyan-400 font-semibold">{cam.label}</span>
        <span className="text-[10px] font-mono text-slate-500 truncate max-w-[80px]">• {cam.location}</span>
        
        <div className="ml-auto flex items-center gap-2">
           <button 
            onClick={(e) => { e.stopPropagation(); setShowInput(!showInput); }}
            className={`p-1 rounded hover:bg-slate-800 transition-colors ${showInput ? 'text-cyan-400' : 'text-slate-500'}`}
            title="Update Stream Source"
          >
            <LinkIcon size={12} />
          </button>
          <div className="flex gap-1">
            {cam.features.map((f, i) => (
              <span
                key={f}
                className={`text-[8px] font-mono px-1.5 py-0.5 rounded border flex items-center gap-0.5 ${FEATURE_COLORS[f] ?? 'text-slate-400 border-slate-700'}`}
                title={f}
              >
                {cam.featureIcons[i]}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* URL Edit Overlay */}
      {showInput && (
        <div className="absolute inset-0 z-20 bg-[#0B0F19]/95 backdrop-blur-md p-4 flex flex-col justify-center">
          <h4 className="text-[10px] font-mono text-cyan-400 mb-2 uppercase tracking-widest">Update Stream</h4>
          <form onSubmit={handleSubmit} className="space-y-3">
            <input 
              autoFocus
              type="text"
              placeholder="Paste new URL here..."
              className="w-full bg-black/40 border border-slate-700 rounded px-2 py-2 text-[10px] font-mono text-slate-200 outline-none focus:border-cyan-500/50"
              value={newUrl}
              onChange={e => setNewUrl(e.target.value)}
            />
            <div className="flex gap-2">
              <button type="submit" className="flex-1 bg-cyan-500/20 text-cyan-400 text-[10px] font-mono py-1.5 rounded border border-cyan-500/30 hover:bg-cyan-500/40 transition-all flex items-center justify-center gap-2">
                <Save size={12} /> UPDATE FEED
              </button>
              <button 
                type="button" 
                onClick={() => setShowInput(false)} 
                className="px-3 bg-slate-800 text-slate-400 rounded hover:text-white transition-colors"
              >
                CANCEL
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Stream Area — always visible, never blocked by error state */}
      <div 
        className="flex-1 relative bg-[#060a12] overflow-hidden cursor-pointer" 
        style={{ minHeight: '160px' }}
        onClick={onZoom}
      >
        {/* Live pulse indicator */}
        <div className="absolute top-2 right-2 z-20 flex items-center gap-1 pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[8px] font-mono text-emerald-400 opacity-80">LIVE</span>
        </div>

        {/* MJPEG stream — always rendered */}
        <img
          key={cam.streamUrl}
          ref={imgRef}
          src={cam.streamUrl}
          alt={cam.label}
          className="w-full h-full object-cover"
        />

        {/* Hover zoom overlay */}
        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
          <div className="bg-[#0B0F19]/80 backdrop-blur p-2.5 rounded-full border border-slate-700 text-white">
            <Maximize2 size={20} />
          </div>
        </div>
        
        {/* Detection confidence HUD */}
        <div className="absolute bottom-4 right-3 flex flex-col items-end gap-1 pointer-events-none">
          {confidence && isReal && (
            <div className="bg-[#0B0F19]/95 border border-slate-700/50 px-3 py-2 rounded-lg shadow-xl text-right backdrop-blur-md pointer-events-auto min-w-[90px]">
              <div className="text-[9px] font-mono text-slate-500 uppercase tracking-tight mb-1">Detection Conf</div>
              <div className="text-sm font-mono font-bold text-cyan-400 leading-tight">{confidence.toFixed(1)}%</div>
            </div>
          )}
        </div>
      </div>

      {/* Card Footer */}
      <div className="px-3 py-1.5 bg-[#060a12] border-t border-slate-800/50 flex justify-between items-center">
        <div className="flex gap-3 text-[9px] font-mono text-slate-500">
          {cam.features.length > 0 ? cam.features.map(f => (
            <span key={f} className={`${FEATURE_COLORS[f]?.split(' ')[0] ?? 'text-slate-500'}`}>{f}</span>
          )) : <span>STANDBY</span>}
        </div>
        <span className="text-[9px] font-mono text-slate-600">LIVE</span>
      </div>
    </div>
  );
}

// ─── Zoom Modal ────────────────────────────────────────────────────────────

function ZoomModal({ cam, onClose }: { cam: CamDef; onClose: () => void }) {
  const [zoomLevel, setZoomLevel] = useState(1);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-[#05080F]/95 backdrop-blur-sm flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl bg-[#0B0F19] border border-slate-700 rounded-xl overflow-hidden shadow-2xl flex flex-col"
        style={{ maxHeight: '90vh' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800 bg-[#060a12]">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <div>
              <h2 className="text-base font-mono font-bold text-slate-200">{cam.label} — {cam.location}</h2>
              <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                FEATURES: {cam.features.length > 0 ? cam.features.join(' • ') : 'NONE'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Stream */}
        <div className="flex-1 relative bg-black overflow-hidden flex items-center justify-center" style={{ minHeight: '400px' }}>
          <div
            className="w-full h-full transition-transform duration-300 origin-center"
            style={{ transform: `scale(${zoomLevel})` }}
          >
            <img
              src={cam.streamUrl}
              alt={cam.label}
              className="w-full h-full object-contain"
            />
          </div>

          {/* Zoom controls */}
          <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex gap-1 bg-[#0B0F19]/80 backdrop-blur border border-slate-700 rounded-full px-2 py-1.5 z-10">
            {[1, 2, 4].map(z => (
              <button
                key={z}
                onClick={() => setZoomLevel(z)}
                className={`px-4 py-1 text-xs font-mono rounded-full transition-colors ${
                  zoomLevel === z
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-cyan-400 hover:bg-slate-800'
                }`}
              >
                {z}×
              </button>
            ))}
            <div className="w-px bg-slate-700 mx-1" />
            <button className="px-3 py-1 text-xs font-mono text-red-400 hover:bg-red-500/10 rounded-full flex items-center gap-1.5 transition-colors">
              <AlertTriangle size={11} /> FLAG
            </button>
          </div>
        </div>

        {/* Feature badges */}
        <div className="px-6 py-3 border-t border-slate-800 bg-[#060a12] flex items-center gap-3 flex-wrap">
          <span className="text-[10px] font-mono text-slate-500">ACTIVE AI MODULES:</span>
          {cam.features.map((f, i) => (
            <span
              key={f}
              className={`text-[10px] font-mono px-2.5 py-1 rounded border flex items-center gap-1.5 ${FEATURE_COLORS[f] ?? ''}`}
            >
              {cam.featureIcons[i]} {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
