import React, { useState, useEffect } from 'react';
import { Camera as CameraIcon, Maximize2, Wifi, WifiOff, Cpu, MapPin, Grid3X3, List } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import Modal from '../components/ui/Modal';
import LoadingSkeleton from '../components/ui/LoadingSkeleton';
import { cameras } from '../data/cameras';
import { API_BASE } from '../config';

/**
 * Cameras — Multi-camera management grid with fullscreen expand.
 */
export default function Cameras() {
  const [loading, setLoading] = useState(true);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  const onlineCams = cameras.filter(c => c.status === 'online').length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <CameraIcon className="w-6 h-6 text-cyber" />
            Camera Management
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            {onlineCams} of {cameras.length} cameras online
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Online/Offline stats */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg glass">
            <Wifi className="w-4 h-4 text-success" />
            <span className="text-xs font-semibold text-success">{onlineCams}</span>
            <span className="text-xs text-text-muted">|</span>
            <WifiOff className="w-4 h-4 text-danger" />
            <span className="text-xs font-semibold text-danger">{cameras.length - onlineCams}</span>
          </div>
          {/* View mode toggle */}
          <div className="flex items-center glass rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 transition-colors ${viewMode === 'grid' ? 'bg-cyber/15 text-cyber' : 'text-text-secondary hover:text-text-primary'}`}
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 transition-colors ${viewMode === 'list' ? 'bg-cyber/15 text-cyber' : 'text-text-secondary hover:text-text-primary'}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Camera Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <LoadingSkeleton key={i} type="card" />
          ))}
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {cameras.map((cam) => (
            <CameraCard key={cam.id} camera={cam} onClick={() => setSelectedCamera(cam)} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {cameras.map((cam) => (
            <CameraListItem key={cam.id} camera={cam} onClick={() => setSelectedCamera(cam)} />
          ))}
        </div>
      )}

      {/* Fullscreen Modal */}
      <Modal
        isOpen={!!selectedCamera}
        onClose={() => setSelectedCamera(null)}
        title={selectedCamera?.name || 'Camera Feed'}
      >
        {selectedCamera && <CameraExpandedView camera={selectedCamera} />}
      </Modal>
    </div>
  );
}

/* ========================
   Sub-components
   ======================== */

function CameraCard({ camera, onClick }) {
  const isOnline = camera.status === 'online';

  return (
    <div onClick={onClick} className="glass-card overflow-hidden group cursor-pointer camera-frame scan-line-overlay">
      {/* Feed area */}
      <div className="aspect-video bg-black relative overflow-hidden">
        {isOnline && (
          <img
            src={`${API_BASE}/stream/${camera.id}`}
            className="w-full h-full object-cover"
            onError={(e) => { e.target.style.display='none'; }}
          />
        )}
        {!isOnline && (
          <div className="absolute inset-0 bg-gradient-to-br from-slate-800 via-gray-900 to-slate-800" />
        )}

        {/* Scan lines */}
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
          backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,224,255,0.05) 2px, rgba(0,224,255,0.05) 4px)`
        }} />

        {/* Status overlay */}
        <div className="absolute inset-0 flex flex-col justify-between p-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
              <span className="text-[10px] font-mono text-text-primary bg-black/60 px-1.5 py-0.5 rounded">
                {camera.id}
              </span>
            </div>
            {isOnline && (
              <span className="text-[9px] font-mono text-cyber bg-black/60 px-1.5 py-0.5 rounded live-pulse">
                ● LIVE
              </span>
            )}
          </div>

          {!isOnline && (
            <div className="flex items-center justify-center">
              <div className="px-3 py-1.5 rounded bg-danger/20 border border-danger/30">
                <span className="text-xs font-semibold text-danger">OFFLINE</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-text-secondary bg-black/60 px-1.5 py-0.5 rounded">
              {camera.fps} FPS
            </span>
            {isOnline && (
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyber/20 text-cyber border border-cyber/30">
                AI {camera.aiConfidence}%
              </span>
            )}
          </div>
        </div>

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-cyber/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Maximize2 className="w-6 h-6 text-cyber/60" />
        </div>
      </div>

      {/* Info bar */}
      <div className="p-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-text-primary truncate">{camera.name}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <MapPin className="w-3 h-3 text-text-muted" />
              <span className="text-[11px] text-text-secondary">{camera.location}</span>
            </div>
          </div>
          <StatusBadge
            severity={camera.aiStatus === 'active' ? 'info' : 'warning'}
            label={camera.aiStatus === 'active' ? 'AI ON' : 'AI OFF'}
            size="sm"
          />
        </div>
      </div>
    </div>
  );
}

function CameraListItem({ camera, onClick }) {
  const isOnline = camera.status === 'online';

  return (
    <div
      onClick={onClick}
      className="glass-card flex items-center gap-4 p-3 cursor-pointer hover:border-cyber/30"
    >
      <div className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
      <span className="text-xs font-mono text-text-muted w-20">{camera.id}</span>
      <span className="text-sm font-medium text-text-primary flex-1">{camera.name}</span>
      <span className="text-xs text-text-secondary w-24">{camera.location}</span>
      <span className="text-xs font-mono text-text-muted w-16">{camera.fps} FPS</span>
      <StatusBadge
        severity={isOnline ? 'info' : 'warning'}
        label={isOnline ? 'ONLINE' : 'OFFLINE'}
        size="sm"
      />
      {isOnline && (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyber/15 text-cyber">
          AI {camera.aiConfidence}%
        </span>
      )}
    </div>
  );
}

function CameraExpandedView({ camera }) {
  const isOnline = camera.status === 'online';

  return (
    <div className="space-y-4">
      {/* Large feed */}
      <div className="aspect-video bg-black rounded-lg relative overflow-hidden camera-frame scan-line-overlay">
        {isOnline && (
          <img
            src={`${API_BASE}/stream/${camera.id}`}
            className="w-full h-full object-cover"
            onError={(e) => { e.target.style.display='none'; }}
          />
        )}
        {!isOnline && (
          <div className="absolute inset-0 bg-gradient-to-br from-slate-800 via-gray-900 to-slate-800" />
        )}
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{
          backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,224,255,0.04) 3px, rgba(0,224,255,0.04) 6px)`
        }} />

        <div className="absolute inset-0 flex flex-col justify-between p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
              <span className="text-sm font-mono text-text-primary bg-black/50 px-2 py-1 rounded">{camera.id}</span>
              {isOnline && (
                <span className="text-sm font-mono text-cyber bg-black/50 px-2 py-1 rounded live-pulse">● LIVE</span>
              )}
            </div>
            <span className="text-sm font-mono text-text-secondary bg-black/50 px-2 py-1 rounded">
              {new Date().toLocaleTimeString()}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-text-primary bg-black/50 px-2 py-1 rounded">{camera.name}</span>
            {isOnline && (
              <span className="text-sm font-bold px-3 py-1 rounded bg-cyber/20 text-cyber border border-cyber/30">
                AI Confidence: {camera.aiConfidence}%
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Camera stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatBox label="Status" value={isOnline ? 'Online' : 'Offline'} color={isOnline ? 'text-success' : 'text-danger'} />
        <StatBox label="Frame Rate" value={`${camera.fps} FPS`} color="text-cyber" />
        <StatBox label="AI Engine" value={camera.aiStatus === 'active' ? 'Active' : 'Inactive'} color={camera.aiStatus === 'active' ? 'text-success' : 'text-warning'} />
        <StatBox label="Risk Zone" value={camera.zone.replace('-', ' ').toUpperCase()} color={camera.zone === 'high-risk' ? 'text-danger' : camera.zone === 'medium-risk' ? 'text-warning' : 'text-cyber'} />
      </div>
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div className="glass p-3 rounded-lg text-center">
      <p className="text-[11px] text-text-secondary uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-sm font-semibold ${color}`}>{value}</p>
    </div>
  );
}
