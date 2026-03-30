/**
 * alertStore.ts
 * Global Zustand store for all threat alerts.
 *
 * PORT NOTE:
 *   Your backend runs on port 8000 (uvicorn default).
 *   Run it with:  uvicorn main:app --reload --port 8000
 *   If you run it on 8001, change API below to match.
 */

import { create } from 'zustand';

// ─── SINGLE SOURCE OF TRUTH FOR PORT ─────────────────────────────────────────
// Change this ONE constant if your backend port changes.
const API = 'http://127.0.0.1:8001';

// ─── Types ────────────────────────────────────────────────────────────────────

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'WARNING' | 'LOW' | 'INFO';
export type AlertStatus   = 'ACTIVE' | 'RESOLVED' | 'FALSE_ALARM';

export interface Alert {
  id:          string;
  timestamp:   string;
  type:        string;
  severity:    AlertSeverity;
  location:    string;
  description: string;
  imageUrl:    string;
  status:      AlertStatus;
  cam?:        string;
  ts?:         number;
}

// ─── Severity + description helpers ──────────────────────────────────────────

function severityFromType(type: string): AlertSeverity {
  const t = type.toUpperCase();
  if (t === 'TRACK_INTRUSION' || t === 'FIRE')         return 'CRITICAL';
  if (t === 'UNATTENDED_BAGGAGE' || t === 'SMOKE')     return 'HIGH';
  if (t === 'OVERCROWDING')                            return 'WARNING';
  return 'LOW';
}

function descFromType(type: string, cam: string): string {
  const t = type.toUpperCase();
  if (t === 'TRACK_INTRUSION')    return `Person detected in restricted track zone at ${cam}.`;
  if (t === 'FIRE')               return `Fire signature detected by HSV analysis at ${cam}.`;
  if (t === 'SMOKE')              return `Smoke pattern detected — low saturation + blur at ${cam}.`;
  if (t === 'UNATTENDED_BAGGAGE') return `Stationary baggage item exceeded ${6}s threshold at ${cam}.`;
  if (t === 'OVERCROWDING')       return `Crowd density threshold exceeded at ${cam}.`;
  return `Anomaly detected at ${cam}.`;
}

// ─── Map cam label → stream URL for snapshot ────────────────────────────────

function streamForCam(cam: string): string {
  if (cam.includes('CAM-01')) return `${API}/video/cam1`;
  if (cam.includes('CAM-02')) return `${API}/video/cam2`;
  if (cam.includes('CAM-03')) return `${API}/video/cam3`;
  if (cam.includes('CAM-04')) return `${API}/video/cam4`;
  if (cam.includes('CAM-05')) return `${API}/video/cam5`;
  if (cam.includes('CAM-06')) return `${API}/video/cam6`;
  return `${API}/video/cam1`;
}

// ─── Snapshot: grab one JPEG frame from the MJPEG stream ─────────────────────

let _canvas: HTMLCanvasElement | null = null;

async function captureSnapshot(streamUrl: string): Promise<string> {
  return new Promise(resolve => {
    try {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      const timer = setTimeout(() => { img.src = ''; resolve(''); }, 3000);

      img.onload = () => {
        clearTimeout(timer);
        try {
          if (!_canvas) _canvas = document.createElement('canvas');
          _canvas.width  = img.naturalWidth  || 320;
          _canvas.height = img.naturalHeight || 180;
          const ctx = _canvas.getContext('2d');
          if (!ctx) { resolve(''); return; }
          ctx.drawImage(img, 0, 0);
          resolve(_canvas.toDataURL('image/jpeg', 0.75));
        } catch { resolve(''); }
      };
      img.onerror = () => { clearTimeout(timer); resolve(''); };
      img.src = `${streamUrl}?snap=${Date.now()}`;
    } catch { resolve(''); }
  });
}

// ─── SVG placeholder shown before snapshot loads ─────────────────────────────

const PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' " +
  "height='180' viewBox='0 0 320 180'%3E%3Crect width='320' height='180' " +
  "fill='%230B0F19'/%3E%3Ctext x='160' y='95' text-anchor='middle' " +
  "font-family='monospace' font-size='11' fill='%23475569'%3ECAM SNAPSHOT%3C/text%3E%3C/svg%3E";

// ─── Store ────────────────────────────────────────────────────────────────────

interface AlertStoreState {
  alerts:          Alert[];
  loading:         boolean;
  backendOk:       boolean;
  lastFetch:       number;
  fetchAlerts:     () => Promise<void>;
  markAsResolved:  (id: string) => void;
  markAsFalseAlarm:(id: string) => void;
  addAlert:        (alert: Alert) => void;
  startPolling:    () => () => void;
}

const _seenIds = new Set<string>();

const useAlertStore = create<AlertStoreState>((set, get) => ({
  alerts:    [],
  loading:   true,
  backendOk: true,
  lastFetch: 0,

  // ── Fetch /api/alerts from FastAPI ──────────────────────────────────────
  fetchAlerts: async () => {
    try {
      const res = await fetch(`${API}/api/alerts`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const raw: Array<{
        id: string; cam: string; type: string; desc: string; ts: number; image?: string;
      }> = await res.json();

      set(state => {
        const existingMap = new Map(state.alerts.map(a => [a.id, a]));
        const updated: Alert[] = [];

        for (const r of raw) {
          const alertId = `INC-${r.id}`;

          // Already in store — keep (preserves user's resolved/false-alarm status)
          if (existingMap.has(alertId)) {
            updated.push(existingMap.get(alertId)!);
            continue;
          }

          // New alert
          const alert: Alert = {
            id:          alertId,
            timestamp:   new Date(r.ts * 1000).toISOString(),
            type:        r.type,
            severity:    severityFromType(r.type),
            location:    r.cam,
            description: descFromType(r.type, r.cam),
            imageUrl:    r.image || PLACEHOLDER,
            status:      'ACTIVE',
            cam:         r.cam,
            ts:          r.ts,
          };
          updated.push(alert);
        }

        return {
          alerts:    updated,
          backendOk: true,
          loading:   false,
          lastFetch: Date.now(),
        };
      });
    } catch (err) {
      console.warn('[AlertStore] fetch failed:', err);
      set({ backendOk: false, loading: false });
    }
  },

  // ── Optimistic status mutations ─────────────────────────────────────────
  markAsResolved: (id) =>
    set(s => ({
      alerts: s.alerts.map(a => a.id === id ? { ...a, status: 'RESOLVED' } : a),
    })),

  markAsFalseAlarm: (id) =>
    set(s => ({
      alerts: s.alerts.map(a => a.id === id ? { ...a, status: 'FALSE_ALARM' } : a),
    })),

  // ── addAlert — called from useSystemStore WebSocket handler ─────────────
  addAlert: (alert) =>
    set(s => {
      if (s.alerts.find(a => a.id === alert.id)) return s;
      return { alerts: [alert, ...s.alerts] };
    }),

  // ── Start polling — returns cleanup fn, safe to call multiple times ─────
  startPolling: () => {
    get().fetchAlerts();
    const timer = setInterval(() => get().fetchAlerts(), 3000);
    return () => clearInterval(timer);
  },
}));

export { useAlertStore };
export default useAlertStore;