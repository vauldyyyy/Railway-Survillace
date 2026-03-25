import React from 'react';
import { Route as RouteIcon, Camera, MapPin, Clock, AlertTriangle, ArrowRight, User, Cpu } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import { trackingData } from '../data/analytics';

/**
 * Tracking — Multi-camera person tracking simulation with timeline view.
 */
export default function Tracking() {
  const { trackId, subject, confidence, status, path } = trackingData;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <RouteIcon className="w-6 h-6 text-cyber" />
            Multi-Camera Tracking
          </h1>
          <p className="text-sm text-text-secondary mt-1">Cross-camera subject tracking and journey analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge severity="info" label={`Track: ${trackId}`} size="md" />
          <StatusBadge severity={status === 'active' ? 'warning' : 'info'} label={status.toUpperCase()} pulse size="md" />
        </div>
      </div>

      {/* Subject Info Card */}
      <GlassCard glowColor="cyan" hoverable={false} className="p-5">
        <div className="flex items-center gap-6 flex-wrap">
          {/* Avatar placeholder */}
          <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-cyber/20 to-cyber/5 border border-cyber/30 flex items-center justify-center flex-shrink-0">
            <User className="w-10 h-10 text-cyber/60" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-text-primary">{subject}</h3>
            <p className="text-sm text-text-secondary mt-1">Tracking ID: <span className="font-mono text-cyber">{trackId}</span></p>
            <div className="flex items-center gap-4 mt-2 flex-wrap">
              <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                <Camera className="w-3.5 h-3.5" />
                <span>{path.length} camera transitions</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                <Clock className="w-3.5 h-3.5" />
                <span>Duration: 26 min</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyber" />
                <span className="text-xs font-bold text-cyber">AI Confidence: {confidence}%</span>
              </div>
            </div>
          </div>
          {/* Path summary flow */}
          <div className="hidden lg:flex items-center gap-2">
            {path.map((p, i) => (
              <React.Fragment key={i}>
                <div className={`px-2 py-1 rounded text-[10px] font-mono ${
                  i === path.length - 1 ? 'bg-danger/15 text-danger border border-danger/30' : 'bg-bg-secondary text-text-secondary border border-border-subtle'
                }`}>
                  {p.location.split(' - ')[0].split(' ').slice(0, 2).join(' ')}
                </div>
                {i < path.length - 1 && <ArrowRight className="w-3 h-3 text-text-muted flex-shrink-0" />}
              </React.Fragment>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* Visual Path Timeline */}
      <div className="space-y-0">
        <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyber" />
          Journey Timeline
        </h3>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[23px] top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyber via-warning to-danger" />

          {path.map((step, index) => {
            const isLast = index === path.length - 1;
            const isAlert = step.event.includes('⚠') || step.event.includes('Alert');
            const time = new Date(step.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

            return (
              <div key={index} className="relative flex gap-4 pb-8 last:pb-0">
                {/* Timeline node */}
                <div className={`
                  relative z-10 w-[48px] h-[48px] rounded-xl flex items-center justify-center flex-shrink-0
                  ${isAlert ? 'bg-danger/20 border border-danger/40 animate-pulse-glow' :
                    isLast ? 'bg-warning/20 border border-warning/40' :
                    'bg-bg-secondary border border-border-subtle'}
                `}>
                  <Camera className={`w-5 h-5 ${isAlert ? 'text-danger' : isLast ? 'text-warning' : 'text-cyber'}`} />
                </div>

                {/* Content card */}
                <GlassCard
                  hoverable={true}
                  glowColor={isAlert ? 'red' : 'none'}
                  className={`flex-1 p-4 ${isAlert ? 'animate-flash-critical' : ''}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-text-primary">{step.event}</span>
                        {isAlert && <StatusBadge severity="critical" size="sm" pulse />}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-text-secondary mb-2">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {step.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <Camera className="w-3 h-3" />
                          {step.camera}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {time}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted">{step.snapshot}</p>
                    </div>

                    {/* Camera thumbnail */}
                    <div className="w-32 h-20 rounded-lg bg-gradient-to-br from-slate-800 to-gray-900 flex-shrink-0 relative overflow-hidden camera-frame scan-line-overlay">
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-[10px] font-mono text-text-muted">{step.camera}</span>
                      </div>
                      <div className="absolute top-1 right-1">
                        <span className="text-[8px] font-mono text-cyber bg-black/60 px-1 py-0.5 rounded">
                          ● LIVE
                        </span>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
