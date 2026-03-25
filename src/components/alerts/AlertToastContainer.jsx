import React, { useEffect, useState } from 'react';
import { X, AlertTriangle, Users, Package, Eye, Ban, ShieldAlert } from 'lucide-react';
import useAlertStore from '../../store/useAlertStore';
import { ALERT_TYPES, SEVERITY_CONFIG } from '../../data/alerts';

const iconMap = {
  AlertTriangle, Users, Package, Eye, Ban, ShieldAlert,
};

/**
 * AlertToastContainer — Renders stacked toast notifications in top-right corner.
 */
export default function AlertToastContainer() {
  const { toasts, dismissToast } = useAlertStore();

  return (
    <div className="fixed top-20 right-4 z-50 space-y-3 w-80">
      {toasts.map((toast) => (
        <AlertToast key={toast.id} alert={toast} onDismiss={() => dismissToast(toast.id)} />
      ))}
    </div>
  );
}

function AlertToast({ alert, onDismiss }) {
  const [isVisible, setIsVisible] = useState(false);
  const alertType = ALERT_TYPES[alert.type] || ALERT_TYPES.SUSPICIOUS_BEHAVIOUR;
  const severity = SEVERITY_CONFIG[alertType.severity];
  const Icon = iconMap[alertType.icon] || AlertTriangle;

  useEffect(() => {
    // Animate in
    requestAnimationFrame(() => setIsVisible(true));
    // Auto-dismiss after 8s
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onDismiss, 300);
    }, 8000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className={`
        glass-heavy rounded-lg overflow-hidden transition-all duration-300
        ${isVisible ? 'animate-slide-in-right opacity-100' : 'opacity-0 translate-x-full'}
        ${alertType.severity === 'critical' ? 'animate-flash-critical' : ''}
      `}
      style={{ borderLeft: `3px solid ${severity.color}` }}
    >
      <div className="p-3">
        <div className="flex items-start gap-3">
          <div
            className="p-1.5 rounded-md flex-shrink-0 mt-0.5"
            style={{ backgroundColor: severity.bg }}
          >
            <Icon className="w-4 h-4" style={{ color: severity.color }} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-text-primary truncate">
                {alertType.label}
              </span>
              <button
                onClick={() => { setIsVisible(false); setTimeout(onDismiss, 300); }}
                className="p-0.5 rounded hover:bg-bg-hover transition-colors text-text-muted hover:text-text-primary flex-shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-text-secondary mt-0.5">{alert.location}</p>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[10px] font-mono text-text-muted">{alert.camera}</span>
              <span
                className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                style={{ color: severity.color, backgroundColor: severity.bg }}
              >
                AI {alert.aiConfidence}%
              </span>
            </div>
          </div>
        </div>
      </div>
      {/* Progress bar for auto-dismiss */}
      <div className="h-0.5 w-full" style={{ backgroundColor: `${severity.color}22` }}>
        <div
          className="h-full transition-all ease-linear"
          style={{
            backgroundColor: severity.color,
            animation: 'shrinkWidth 8s linear forwards',
          }}
        />
      </div>
      <style>{`
        @keyframes shrinkWidth {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  );
}
