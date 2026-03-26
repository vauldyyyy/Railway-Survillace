import { create } from 'zustand';

// ── Types ──
export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface AlertTransparency {
  model_used: string;
  confidence: number;
  reasoning: string[];
  track_id_history: string[];
  time_to_detection_ms: number;
  bbox?: [number, number, number, number];
}

export interface Alert {
  id: string;
  type: string;
  severity: AlertSeverity;
  camera: string;
  location: string;
  timestamp: number;
  aiConfidence: number;
  acknowledged: boolean;
  transparency?: AlertTransparency;
}

export const ALERT_TYPES: Record<string, { label: string; severity: AlertSeverity; model: string }> = {
  PERSON_ON_TRACK: { label: 'Person on Track', severity: 'critical', model: 'YOLOv8n COCO + ByteTrack' },
  FOREIGN_OBJECT: { label: 'Foreign Object on Track', severity: 'critical', model: 'RailFOD YOLOv8' },
  UNATTENDED_BAGGAGE: { label: 'Unattended Baggage', severity: 'critical', model: 'YOLOv8n COCO + DeepSORT' },
  CROWD_SURGE: { label: 'Crowd Surge Predicted', severity: 'warning', model: 'LSTM Crowd v2.4' },
  OVERCROWDING: { label: 'Overcrowding', severity: 'warning', model: 'YOLOv8n COCO' },
  CAMERA_TAMPER: { label: 'Camera Tamper Detected', severity: 'critical', model: 'SSIM Analyzer' },
  TRACK_INTRUSION: { label: 'Track Intrusion', severity: 'critical', model: 'Zone Intrusion Detector' },
  UAV_OBSTACLE: { label: 'UAV / Aerial Obstacle', severity: 'warning', model: 'UAV YOLOv8' },
  SUSPICIOUS_BEHAVIOUR: { label: 'Suspicious Behaviour', severity: 'info', model: 'Anomaly Detector' },
};

export const SEVERITY_CONFIG = {
  critical: { color: '#FF3B3B', bg: 'rgba(255, 59, 59, 0.15)', border: 'rgba(255, 59, 59, 0.4)', label: 'Critical' },
  warning: { color: '#FFA500', bg: 'rgba(255, 165, 0, 0.15)', border: 'rgba(255, 165, 0, 0.3)', label: 'Warning' },
  info: { color: '#00E0FF', bg: 'rgba(0, 224, 255, 0.1)', border: 'rgba(0, 224, 255, 0.3)', label: 'Info' },
};

// ── Reasoning generators ──
const reasoningMap: Record<string, string[]> = {
  PERSON_ON_TRACK: ['Person bounding box detected inside restricted track zone polygon', 'Track zone intersection area > 60% of person bbox', 'Confirmed via 3 consecutive frames (temporal smoothing)'],
  FOREIGN_OBJECT: ['RailFOD model detected debris/object on track surface', 'Object does not match rolling stock signature', 'Confidence exceeds FOD threshold (0.4)'],
  UNATTENDED_BAGGAGE: ['Baggage tracked for > 15 seconds without associated person', 'DeepSORT embedding distance to nearest person > threshold', 'No person within 2m radius for extended duration'],
  CROWD_SURGE: ['LSTM predicted crowd count exceeds capacity threshold (85)', '20-timestep sequence shows accelerating density trend', 'Time-of-day and day-of-week features indicate peak period'],
  OVERCROWDING: ['Person count exceeds platform capacity threshold', 'Real-time density > 2.5 persons/sq.meter', 'Adjacent zones also showing elevated counts'],
  CAMERA_TAMPER: ['SSIM score dropped below 0.3 between consecutive frames', 'Sudden drastic change in frame structure detected', 'Not correlated with scene-wide lighting change'],
  TRACK_INTRUSION: ['Tracked person entered defined restricted zone polygon', 'Zone intersection confirmed for > 2 seconds', 'Alert escalated due to proximity to active track'],
  UAV_OBSTACLE: ['Aerial object detected in restricted airspace above tracks', 'Object trajectory inconsistent with bird flight patterns', 'Size and velocity match UAV/drone profile'],
  SUSPICIOUS_BEHAVIOUR: ['Anomaly score exceeds self-supervised threshold', 'Behavioral pattern diverges from normal station activity', 'Loitering duration exceeds 5-minute threshold'],
};

const locations = ['Platform 1 North', 'Platform 2 Central', 'Entry Gate A', 'Waiting Area', 'Track Section A', 'Footbridge', 'Ticket Counter', 'Entry Gate B', 'Platform 3 East', 'Parking Area'];
const alertTypes = Object.keys(ALERT_TYPES);

function generateRandomAlert(): Alert {
  const type = alertTypes[Math.floor(Math.random() * alertTypes.length)];
  const typeConfig = ALERT_TYPES[type];
  const confidence = Math.floor(Math.random() * 25) + 75;
  const camNum = Math.floor(Math.random() * 12) + 1;

  return {
    id: `ALR-${Date.now().toString(36).toUpperCase()}`,
    type,
    severity: typeConfig.severity,
    camera: `CAM_${String(camNum).padStart(2, '0')}`,
    location: locations[Math.floor(Math.random() * locations.length)],
    timestamp: Date.now(),
    aiConfidence: confidence,
    acknowledged: false,
    transparency: {
      model_used: typeConfig.model,
      confidence: confidence / 100,
      reasoning: reasoningMap[type] || ['Detection triggered by model inference'],
      track_id_history: Array.from({ length: Math.floor(Math.random() * 4) + 1 }, (_, i) => `T-${1000 + i}`),
      time_to_detection_ms: Math.floor(Math.random() * 150) + 20,
      bbox: [
        Math.floor(Math.random() * 200) + 50,
        Math.floor(Math.random() * 150) + 50,
        Math.floor(Math.random() * 200) + 300,
        Math.floor(Math.random() * 150) + 250,
      ],
    },
  };
}

// ── Initial alerts ──
const initialAlerts: Alert[] = [
  generateRandomAlert(),
  generateRandomAlert(),
  generateRandomAlert(),
  { ...generateRandomAlert(), acknowledged: true },
  { ...generateRandomAlert(), acknowledged: true },
];

// ── Store ──
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
  startSimulation: () => ReturnType<typeof setInterval>;
}

const useAlertStore = create<AlertState>((set, get) => ({
  alerts: initialAlerts,
  toasts: [],
  selectedAlert: null,

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 100),
      toasts: [alert, ...state.toasts].slice(0, 5),
    })),

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

  startSimulation: () => {
    return setInterval(() => {
      get().addAlert(generateRandomAlert());
    }, 10000);
  },
}));

export default useAlertStore;
