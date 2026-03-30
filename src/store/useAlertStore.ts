import { create } from 'zustand';

// ── Types ──
export type AlertSeverity = 'critical' | 'high' | 'warning' | 'info';

export interface AlertTransparency {
  model_used: string;
  confidence: number;
  reasoning: string[];
  track_id_history: string[];
  time_to_detection_ms: number;
  bbox?: [number, number, number, number];
}

export interface Alert {
  id?: string; // Optional for input, generated in store
  camera_id: string;
  threat_type: string;
  threat_level: string;
  command: string;
  notify: string[];
  escalation: string[];
  timestamp: string;
  confidence: number;
  acknowledged?: boolean;
}

export const ALERT_TYPES: Record<string, { label: string; severity: AlertSeverity; model: string }> = {
  PERSON_ON_TRACK:       { label: 'Person on Track',        severity: 'critical', model: 'YOLO-World + ZoneDetector' },
  PERSON_FALLEN_ON_TRACK: { label: 'Person Fallen on Track', severity: 'critical', model: 'YOLO-World + Posture Engine' },
  UNATTENDED_BAGGAGE:    { label: 'Unattended Baggage',     severity: 'critical', model: 'YOLO-World + BaggageTracker' },
  FIRE:                  { label: 'Fire Detected',           severity: 'critical', model: 'YOLO-World' },
  SMOKE:                 { label: 'Smoke Detected',          severity: 'critical', model: 'YOLO-World' },
  BAGGAGE:               { label: 'Baggage Detected',        severity: 'info',    model: 'YOLO-World' },
  FOREIGN_OBJECT:        { label: 'Foreign Object on Track', severity: 'high',    model: 'YOLO-World' },
  ANIMAL_ON_TRACK:       { label: 'Animal on Track',         severity: 'high',    model: 'YOLO-World' },
  CROWD_RISK:            { label: 'Crowd Surge Risk',        severity: 'high',    model: 'Density Counter' },
  PERSON_TRACKED:        { label: 'Person Tracked',          severity: 'info',    model: 'OSNet ReID' },
};

export const SEVERITY_CONFIG = {
  critical: { color: '#FF3B3B', bg: 'rgba(255, 59, 59, 0.15)', border: 'rgba(255, 59, 59, 0.4)', label: 'Critical' },
  high:     { color: '#FF6B00', bg: 'rgba(255, 107, 0, 0.15)', border: 'rgba(255, 107, 0, 0.4)', label: 'High' },
  warning:  { color: '#FFA500', bg: 'rgba(255, 165, 0, 0.15)', border: 'rgba(255, 165, 0, 0.3)', label: 'Warning' },
  info:     { color: '#00E0FF', bg: 'rgba(0, 224, 255, 0.1)',  border: 'rgba(0, 224, 255, 0.3)', label: 'Info' },
};

// ── Store (Real data only — no simulation) ──
interface AlertState {
  alerts: Alert[];
  toasts: Alert[];
  selectedAlert: Alert | null;

  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: string) => void;
  selectAlert: (alertId: string | null) => void;
  dismissToast: (alertId: string) => void;
  clearToasts: () => void;
  getUnacknowledgedCount: () => number;
}

const useAlertStore = create<AlertState>((set, get) => ({
  alerts: [],
  toasts: [],
  selectedAlert: null,

  addAlert: (alert) => {
    // Ensure ID exists for React keys
    const alertWithId: Alert & { id: string } = { 
      ...alert, 
      id: alert.id || `${alert.threat_type}_${alert.camera_id}_${alert.timestamp}` 
    };
    
    // Deduplication
    const existing = get().alerts;
    if (existing.some(a => (a as any).id === alertWithId.id)) return;

    set((state) => ({
      alerts: [alertWithId as any, ...state.alerts].slice(0, 100),
      toasts: [alertWithId as any, ...state.toasts].slice(0, 5),
    }));
  },

  acknowledgeAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a)),
    })),

  selectAlert: (alertId) =>
    set((state) => ({
      selectedAlert: alertId ? state.alerts.find((a) => a.id === alertId) || null : null,
    })),

  dismissToast: (alertId) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== alertId),
    })),

  clearToasts: () => set({ toasts: [] }),

  getUnacknowledgedCount: () => get().alerts.filter((a) => !a.acknowledged).length,
}));

export default useAlertStore;
