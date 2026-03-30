import React from 'react';
import useAlertStore from '../store/useAlertStore';
import { ALERT_TYPES, SEVERITY_CONFIG } from '../store/useAlertStore';
import { X, Brain, Target, Clock, Route, Shield } from 'lucide-react';

export function AITransparencyPanel() {
  const selectedAlert = useAlertStore((s) => s.selectedAlert);
  const selectAlert = useAlertStore((s) => s.selectAlert);

  if (!selectedAlert) return null;

  const levelKey = (selectedAlert.threat_level?.toLowerCase() || 'info') as any;
  const severityConfig = (SEVERITY_CONFIG as any)[levelKey] || SEVERITY_CONFIG.info;

  return (
    <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg overflow-hidden animate-fade-in shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/50" style={{ borderLeftColor: severityConfig.color, borderLeftWidth: '3px' }}>
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-cyan-400" />
          <span className="text-[10px] text-slate-300 uppercase tracking-wider font-bold">AI ANALYSIS ENGINE</span>
        </div>
        <button onClick={() => selectAlert(null)} className="text-slate-500 hover:text-slate-300 transition-colors">
          <X size={14} />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Alert Type */}
        <div>
          <span className="text-[9px] text-slate-500 uppercase tracking-wider">THREAT TYPE</span>
          <div className="text-sm font-semibold mt-0.5" style={{ color: severityConfig.color }}>
            {selectedAlert.threat_type}
          </div>
        </div>

        {/* Command */}
        <div className="flex items-start gap-2">
          <Target size={12} className="text-cyan-500 mt-0.5 shrink-0" />
          <div>
            <span className="text-[9px] text-slate-500 uppercase tracking-wider">OPERATIONAL COMMAND</span>
            <div className="text-xs text-slate-200 font-mono mt-0.5 font-bold text-cyan-400">{selectedAlert.command}</div>
          </div>
        </div>

        {/* Confidence */}
        <div>
          <span className="text-[9px] text-slate-500 uppercase tracking-wider">CONFIDENCE SCORE</span>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-2xl font-light text-slate-100 font-mono">{(selectedAlert.confidence * 100).toFixed(1)}%</span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${selectedAlert.confidence * 100}%`,
                  backgroundColor: selectedAlert.confidence > 0.9 ? '#10b981' : selectedAlert.confidence > 0.7 ? '#f59e0b' : '#ef4444',
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Timestamp */}
        <div className="flex items-start gap-2">
          <Clock size={12} className="text-emerald-500 mt-0.5 shrink-0" />
          <div>
            <span className="text-[9px] text-slate-500 uppercase tracking-wider">TIMESTAMP</span>
            <div className="text-xs text-emerald-400 font-mono mt-0.5">{new Date(selectedAlert.timestamp).toLocaleString()}</div>
          </div>
        </div>

        {/* Authority Notification List */}
        <div className="pt-2 border-t border-slate-800/50">
          <div className="flex items-center gap-1.5 mb-2">
            <Shield size={11} className="text-cyan-400" />
            <span className="text-[9px] text-cyan-400 uppercase tracking-wider font-bold">AUTHORITIES NOTIFIED</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {selectedAlert.notify.map((n, i) => (
              <span key={i} className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700">
                {n}
              </span>
            ))}
          </div>
        </div>

        {/* Escalation Path */}
        {selectedAlert.escalation.length > 0 && (
          <div className="pt-2 border-t border-slate-800/50">
            <div className="flex items-center gap-1.5 mb-2">
              <Route size={11} className="text-red-400" />
              <span className="text-[9px] text-red-400 uppercase tracking-wider font-bold">ESCALATION PATH</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {selectedAlert.escalation.map((e, i) => (
                <span key={i} className="text-[10px] bg-red-900/20 text-red-400 px-2 py-0.5 rounded border border-red-500/30">
                  {e}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
