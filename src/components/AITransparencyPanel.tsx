import React from 'react';
import useAlertStore from '../store/useAlertStore';
import { ALERT_TYPES, SEVERITY_CONFIG } from '../store/useAlertStore';
import { X, Brain, Target, Clock, Route, Crosshair } from 'lucide-react';

export function AITransparencyPanel() {
  const selectedAlert = useAlertStore((s) => s.selectedAlert);
  const selectAlert = useAlertStore((s) => s.selectAlert);

  if (!selectedAlert || !selectedAlert.transparency) return null;

  const t = selectedAlert.transparency;
  const typeConfig = ALERT_TYPES[selectedAlert.type];
  const severityConfig = SEVERITY_CONFIG[selectedAlert.severity];

  return (
    <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/50" style={{ borderLeftColor: severityConfig.color, borderLeftWidth: '3px' }}>
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-cyan-400" />
          <span className="text-[10px] text-slate-300 uppercase tracking-wider font-bold">AI TRANSPARENCY</span>
        </div>
        <button onClick={() => selectAlert(null)} className="text-slate-500 hover:text-slate-300 transition-colors">
          <X size={14} />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Alert Type */}
        <div>
          <span className="text-[9px] text-slate-500 uppercase tracking-wider">ALERT TYPE</span>
          <div className="text-sm font-semibold mt-0.5" style={{ color: severityConfig.color }}>
            {typeConfig?.label || selectedAlert.type}
          </div>
        </div>

        {/* Model Used */}
        <div className="flex items-start gap-2">
          <Target size={12} className="text-cyan-500 mt-0.5 shrink-0" />
          <div>
            <span className="text-[9px] text-slate-500 uppercase tracking-wider">MODEL USED</span>
            <div className="text-xs text-slate-200 font-mono mt-0.5">{t.model_used}</div>
          </div>
        </div>

        {/* Confidence */}
        <div>
          <span className="text-[9px] text-slate-500 uppercase tracking-wider">CONFIDENCE SCORE</span>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-2xl font-light text-slate-100 font-mono">{(t.confidence * 100).toFixed(1)}%</span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${t.confidence * 100}%`,
                  backgroundColor: t.confidence > 0.9 ? '#10b981' : t.confidence > 0.7 ? '#f59e0b' : '#ef4444',
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Time to Detection */}
        <div className="flex items-start gap-2">
          <Clock size={12} className="text-emerald-500 mt-0.5 shrink-0" />
          <div>
            <span className="text-[9px] text-slate-500 uppercase tracking-wider">TIME TO DETECTION</span>
            <div className="text-xs text-emerald-400 font-mono mt-0.5">{t.time_to_detection_ms}ms</div>
          </div>
        </div>

        {/* Bounding Box */}
        {t.bbox && (
          <div className="flex items-start gap-2">
            <Crosshair size={12} className="text-amber-500 mt-0.5 shrink-0" />
            <div>
              <span className="text-[9px] text-slate-500 uppercase tracking-wider">BOUNDING BOX</span>
              <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                [{t.bbox.join(', ')}]
              </div>
            </div>
          </div>
        )}

        {/* Track ID History */}
        {t.track_id_history.length > 0 && (
          <div className="flex items-start gap-2">
            <Route size={12} className="text-purple-500 mt-0.5 shrink-0" />
            <div>
              <span className="text-[9px] text-slate-500 uppercase tracking-wider">TRACK ID HISTORY</span>
              <div className="flex gap-1.5 mt-1 flex-wrap">
                {t.track_id_history.map((id, i) => (
                  <span key={i} className="text-[10px] font-mono text-purple-300 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
                    {id}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Why Triggered */}
        <div className="pt-2 border-t border-slate-800/50">
          <div className="flex items-center gap-1.5 mb-2">
            <Brain size={11} className="text-cyan-400" />
            <span className="text-[9px] text-cyan-400 uppercase tracking-wider font-bold">WHY THIS ALERT TRIGGERED</span>
          </div>
          <ul className="space-y-1.5">
            {t.reasoning.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-[11px] text-slate-300">
                <span className="text-cyan-600 mt-0.5 shrink-0">›</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
