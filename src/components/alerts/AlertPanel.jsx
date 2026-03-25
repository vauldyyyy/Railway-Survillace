import React from 'react';
import { AlertTriangle, Users, Package, Eye, Ban, ShieldAlert, Clock, CheckCircle2, Camera } from 'lucide-react';
import useAlertStore from '../../store/useAlertStore';
import { ALERT_TYPES, SEVERITY_CONFIG } from '../../data/alerts';
import StatusBadge from '../ui/StatusBadge';

const iconMap = {
  AlertTriangle, Users, Package, Eye, Ban, ShieldAlert,
};

/**
 * AlertPanel — Real-time alerts feed for the Dashboard right sidebar.
 */
export default function AlertPanel() {
  const { alerts, acknowledgeAlert } = useAlertStore();

  const formatTime = (ts) => {
    const diff = Date.now() - ts;
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return `${Math.floor(diff / 3600000)}h ago`;
  };

  return (
    <div className="glass-card p-0 overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-danger animate-pulse-glow" />
          <h3 className="text-sm font-semibold text-text-primary">Live Alerts</h3>
        </div>
        <span className="text-[10px] font-mono text-text-muted">
          {alerts.filter(a => !a.acknowledged).length} UNREAD
        </span>
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto divide-y divide-border-subtle/50">
        {alerts.slice(0, 15).map((alert) => {
          const alertType = ALERT_TYPES[alert.type] || ALERT_TYPES.SUSPICIOUS_BEHAVIOUR;
          const severity = SEVERITY_CONFIG[alertType.severity];
          const Icon = iconMap[alertType.icon] || AlertTriangle;

          return (
            <div
              key={alert.id}
              className={`
                px-4 py-3 hover:bg-bg-hover/50 transition-colors cursor-pointer
                ${!alert.acknowledged ? 'border-l-2' : 'border-l-2 border-l-transparent opacity-70'}
                ${alertType.severity === 'critical' && !alert.acknowledged ? 'bg-danger/5' : ''}
              `}
              style={{ borderLeftColor: !alert.acknowledged ? severity.color : 'transparent' }}
              onClick={() => acknowledgeAlert(alert.id)}
            >
              <div className="flex items-start gap-3">
                <div
                  className="p-1.5 rounded-md flex-shrink-0 mt-0.5"
                  style={{ backgroundColor: severity.bg }}
                >
                  <Icon className="w-3.5 h-3.5" style={{ color: severity.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-text-primary truncate">
                      {alertType.label}
                    </span>
                    <StatusBadge severity={alertType.severity} size="sm" />
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-text-secondary">
                    <Camera className="w-3 h-3" />
                    <span>{alert.camera}</span>
                    <span className="text-text-muted">•</span>
                    <span className="truncate">{alert.location}</span>
                  </div>
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] font-mono text-text-muted flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(alert.timestamp)}
                    </span>
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{ color: severity.color, backgroundColor: severity.bg }}
                    >
                      AI {alert.aiConfidence}%
                    </span>
                  </div>
                </div>
                {alert.acknowledged && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-success flex-shrink-0 mt-1" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
