import { create } from 'zustand';
import useAlertStore from './alertStore';   // ← fixed: was './useAlertStore'

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ModelMetrics {
  name: string;
  fps: number;
  latency_ms: number;
  gpu_util_pct: number;
  precision: number;
  recall: number;
  false_positive_rate: number;
  drift_score: number;
  status: 'active' | 'idle' | 'error' | 'loading';
}

export interface CameraState {
  id: string;
  label: string;
  status: 'online' | 'offline' | 'tampered';
  last_frame_ts: number;
  person_count: number;
  stream_url: string;
}

export interface EdgeNodeHealth {
  id: string;
  station: string;
  status: 'healthy' | 'degraded' | 'offline';
  cpu_pct: number;
  gpu_pct: number;
  memory_pct: number;
  uptime_hours: number;
  models_loaded: number;
  last_heartbeat: number;
}

export type ThreatLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

interface SystemState {
  threatLevel:      ThreatLevel;
  threatScore:      number;
  cameras:          Record<string, CameraState>;
  modelMetrics: {
    coco:    ModelMetrics;
    railfod: ModelMetrics;
    uav:     ModelMetrics;
    lstm:    ModelMetrics;
    tracker: ModelMetrics;
  };
  edgeNodes:        EdgeNodeHealth[];
  systemUptime:     number;
  lastSync:         number;
  wsConnected:      boolean;
  jwtToken:         string | null;
  globalConfidence: number;
  gpuBridge: {
    mode:             'local' | 'remote';
    connected:        boolean;
    latency_ms:       number;
    inference_source: 'local' | 'remote';
  };

  // Actions
  updateThreatScore: (score: number) => void;
  updateGlobalConfidence: (conf: number) => void;
  updateModelMetrics: (model: string, metrics: Partial<ModelMetrics>) => void;
  updateCamera: (id: string, update: Partial<CameraState>) => void;
  setEdgeNodes: (nodes: EdgeNodeHealth[]) => void;
  setWsConnected: (connected: boolean) => void;
  updateBridgeStatus: (status: { mode: string; connected: boolean; latency_ms: number; inference_source: string }) => void;
  toggleGpuBridge: () => Promise<void>;
  setVideoSource: (url: string) => Promise<boolean>;
  login: () => Promise<boolean>;
  connectWebSocket: () => void;
}

// ── Default data ───────────────────────────────────────────────────────────────

const defaultModel = (name: string, fps: number, gpu: number): ModelMetrics => ({
  name,
  fps,
  latency_ms:          Math.round(1000 / fps),
  gpu_util_pct:        gpu,
  precision:           0.88 + Math.random() * 0.1,
  recall:              0.82 + Math.random() * 0.12,
  false_positive_rate: 0.02 + Math.random() * 0.05,
  drift_score:         Math.random() * 0.15,
  status:              'active',
});

const defaultCameras: Record<string, CameraState> = {
  'CAM_01': { id: 'CAM_01', label: 'Platform 1 South', status: 'online', last_frame_ts: Date.now(), person_count: 42, stream_url: 'http://127.0.0.1:8001/stream/cam1' },
  'CAM_02': { id: 'CAM_02', label: 'Platform 1 North', status: 'online', last_frame_ts: Date.now(), person_count: 38, stream_url: 'http://127.0.0.1:8001/stream/cam2' },
  'CAM_03': { id: 'CAM_03', label: 'Platform 2 Central', status: 'online', last_frame_ts: Date.now(), person_count: 55, stream_url: 'http://127.0.0.1:8001/stream/cam3' },
  'CAM_04': { id: 'CAM_04', label: 'Entry Gate A', status: 'online', last_frame_ts: Date.now(), person_count: 21, stream_url: 'http://127.0.0.1:8001/stream/cam4' },
  'CAM_05': { id: 'CAM_05', label: 'Footbridge', status: 'online', last_frame_ts: Date.now(), person_count: 15, stream_url: 'http://127.0.0.1:8001/stream/cam5' },
  'CAM_06': { id: 'CAM_06', label: 'Track Section A', status: 'online', last_frame_ts: Date.now(), person_count: 3, stream_url: 'http://127.0.0.1:8001/stream/cam6' },
  'CAM_07': { id: 'CAM_07', label: 'Waiting Area', status: 'online', last_frame_ts: Date.now(), person_count: 67, stream_url: 'http://127.0.0.1:8001/stream/cam7' },
  'CAM_08': { id: 'CAM_08', label: 'Ticket Counter', status: 'online', last_frame_ts: Date.now(), person_count: 28, stream_url: 'http://127.0.0.1:8001/stream/cam8' },
  'CAM_09': { id: 'CAM_09', label: 'Entrance Hall', status: 'online', last_frame_ts: Date.now(), person_count: 34, stream_url: 'http://127.0.0.1:8001/stream/cam9' },
  'CAM_10': { id: 'CAM_10', label: 'Platform 3 East', status: 'online', last_frame_ts: Date.now(), person_count: 19, stream_url: 'http://127.0.0.1:8001/stream/cam10' },
  'CAM_11': { id: 'CAM_11', label: 'Platform 3 West', status: 'online', last_frame_ts: Date.now(), person_count: 22, stream_url: 'http://127.0.0.1:8001/stream/cam11' },
  'CAM_12': { id: 'CAM_12', label: 'Track Section B', status: 'online', last_frame_ts: Date.now(), person_count: 1, stream_url: 'http://127.0.0.1:8001/stream/cam12' },
  'CAM_13': { id: 'CAM_13', label: 'Parking Area', status: 'offline', last_frame_ts: Date.now() - 600000, person_count: 0, stream_url: '' },
  'CAM_14': { id: 'CAM_14', label: 'VIP Lounge', status: 'online', last_frame_ts: Date.now(), person_count: 5, stream_url: 'http://127.0.0.1:8001/stream/cam14' },
};

const defaultEdgeNodes: EdgeNodeHealth[] = [
  { id: 'EDGE_01', station: 'Madgaon Junction', status: 'healthy',  cpu_pct: 42, gpu_pct: 68, memory_pct: 55, uptime_hours: 342, models_loaded: 4, last_heartbeat: Date.now() },
  { id: 'EDGE_02', station: 'Thivim Station',   status: 'healthy',  cpu_pct: 38, gpu_pct: 52, memory_pct: 48, uptime_hours: 220, models_loaded: 4, last_heartbeat: Date.now() },
  { id: 'EDGE_03', station: 'Vasco da Gama',    status: 'degraded', cpu_pct: 78, gpu_pct: 91, memory_pct: 82, uptime_hours: 18,  models_loaded: 3, last_heartbeat: Date.now() - 30000 },
];

// ── Store ──────────────────────────────────────────────────────────────────────

const useSystemStore = create<SystemState>((set, get) => ({
  threatLevel:      'HIGH',
  threatScore:      7.2,
  cameras:          defaultCameras,
  modelMetrics: {
    coco:    defaultModel('YOLOv8n COCO',      32.1, 45),
    railfod: defaultModel('RailFOD YOLOv8',    28.4, 12),
    uav:     defaultModel('UAV YOLOv8',        26.8, 10),
    lstm:    defaultModel('LSTM Crowd v2.4',  200.0,  0),
    tracker: { ...defaultModel('ByteTrack', 30, 0), gpu_util_pct: 0 },
  },
  edgeNodes:        defaultEdgeNodes,
  systemUptime:     342 * 3600,
  lastSync:         Date.now(),
  wsConnected:      false,
  jwtToken:         null,
  globalConfidence: 94.2,
  gpuBridge: {
    mode:             'local',
    connected:        false,
    latency_ms:       0,
    inference_source: 'local',
  },

  // ── Actions ────────────────────────────────────────────────────────────────

  updateThreatScore: (score) => {
    let level: ThreatLevel = 'LOW';
    if      (score >= 8) level = 'CRITICAL';
    else if (score >= 6) level = 'HIGH';
    else if (score >= 3) level = 'MEDIUM';
    set({ threatScore: score, threatLevel: level });
  },

  updateGlobalConfidence: (conf) => set({ globalConfidence: conf }),

  updateModelMetrics: (model, metrics) =>
    set(state => ({
      modelMetrics: {
        ...state.modelMetrics,
        [model]: {
          ...state.modelMetrics[model as keyof typeof state.modelMetrics],
          ...metrics,
        },
      },
    })),

  updateCamera: (id, update) =>
    set(state => ({
      cameras: {
        ...state.cameras,
        [id]: { ...state.cameras[id], ...update },
      },
    })),

  setEdgeNodes:   (nodes)     => set({ edgeNodes: nodes }),
  setWsConnected: (connected) => set({ wsConnected: connected }),

  updateBridgeStatus: (status) => set({
    gpuBridge: {
      mode:             (status.mode as 'local' | 'remote') || 'local',
      connected:        status.connected  ?? false,
      latency_ms:       status.latency_ms ?? 0,
      inference_source: (status.inference_source as 'local' | 'remote') || 'local',
    },
  }),

  toggleGpuBridge: async () => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/bridge/toggle', { method: 'POST' });
      if (res.ok) {
        // Fetch new status instantly
        const statusRes = await fetch('http://127.0.0.1:8001/api/bridge-status');
        if (statusRes.ok) {
           useSystemStore.getState().updateBridgeStatus(await statusRes.json());
        }
      }
    } catch(e) {
      console.error('Failed to toggle GPU bridge', e);
    }
  },

  setVideoSource: async (url) => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/stream/source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: 'cam1', source: url }), // Explicitly target cam1
      });
      return res.ok;
    } catch (e) {
      console.error('Failed to update video source', e);
      return false;
    }
  },

  login: async () => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', 'admin');
      formData.append('password', 'railguard');
      const res = await fetch('http://127.0.0.1:8001/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        set({ jwtToken: data.access_token });
        return true;
      }
    } catch (e) {
      console.error('[Auth] Login failed:', e);
    }
    return false;
  },

  // ── WebSocket ──────────────────────────────────────────────────────────────
  connectWebSocket: async () => {
    const token = get().jwtToken || localStorage.getItem('railguard_token');
    if (!token) {
      console.warn('[WS] No token — retrying in 5s...');
      setTimeout(() => get().connectWebSocket(), 5000);
      return;
    }
    set({ jwtToken: token });

    const wsBase = 'ws://127.0.0.1:8001';
    const ws = new WebSocket(`${wsBase}/ws/alerts?token=${token}`);

    ws.onopen = () => {
      set({ wsConnected: true });
      console.log('[WS] Connected to RailGuard backend');
    };

    ws.onmessage = (event) => {
      try {
        const msg     = JSON.parse(event.data);
        const channel = msg.channel || 'alert';

        switch (channel) {

          case 'metrics':
            if (msg.payload?.model) {
              get().updateModelMetrics(msg.payload.model, msg.payload.metrics);
            }
            break;

          case 'camera':
            if (msg.payload?.camera_id) {
              get().updateCamera(msg.payload.camera_id, msg.payload);
            }
            break;

          case 'health':
            if (msg.payload?.edge_nodes) {
              get().setEdgeNodes(msg.payload.edge_nodes);
            }
            break;

          case 'threat':
            if (typeof msg.payload?.score === 'number') {
              get().updateThreatScore(msg.payload.score);
            }
            break;

          // ── FIXED: now pushes into alertStore (same store as ThreatAlerts) ──
          case 'alert':
            if (msg.payload) {
              const p = msg.payload;
              // Entity-State V4 format: entity_id, base_class, threat_type (was new_state)
              const cam = p.camera || p.camera_id || 'unknown';
              const type = p.threat_type || p.type || p.new_state || 'UNKNOWN';
              const level = p.threat_level || p.severity || 'info';
              const entityId = p.entity_id || '';
              const baseClass = p.base_class || '';

              useAlertStore.getState().addAlert({
                id: p.id || `${entityId || 'WS'}-${Date.now()}`,
                type: type,
                severity: (level.toLowerCase() as any),
                camera: cam,
                location: p.location || (cam.startsWith('CAM') ? `Platform ${cam.slice(-1)}` : 'Railway Perimeter'),
                timestamp: p.timestamp ? (typeof p.timestamp === 'string' ? p.timestamp : new Date(p.timestamp * 1000).toISOString()) : new Date().toISOString(),
                aiConfidence: Math.round((p.confidence || 0) * 100),
                acknowledged: false,
                description: p.description || `${type} — Entity ${entityId} (${baseClass}) on ${cam}`,
                transparency: {
                  model_used: 'RailGuard Entity-State V4.0',
                  confidence: p.confidence || 0,
                  reasoning: p.reasoning || [`${type} detected by Entity-State Engine on ${cam}`],
                  track_id_history: entityId ? [entityId] : [],
                  time_to_detection_ms: 0,
                  bbox: p.box || p.bbox,
                },
                imageUrl: p.image || p.imageUrl || '', 
                status: 'ACTIVE',
                cam: cam,
                ts: p.timestamp,
                entityId: entityId,
                baseClass: baseClass,
                command: p.command || '',
              } as any);
            }
            break;

          default:
            break;
        }
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    ws.onerror = () => set({ wsConnected: false });

    ws.onclose = () => {
      set({ wsConnected: false });
      console.log('[WS] Disconnected — retrying in 5s...');
      setTimeout(() => get().connectWebSocket(), 5000);
    };
  },
}));

// ── Real ML metric synchronisation (polls /api/stats every 2s) ───────────────

export function startMetricsSimulation() {
  return setInterval(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/stats');
      if (res.ok) {
        const data = await res.json();
        const store = useSystemStore.getState();
        if (data.avg_confidence) {
          store.updateGlobalConfidence(data.avg_confidence);
        }
        // Sync tracker active
        if (data.total_tracked !== undefined) {
             const tracker = store.modelMetrics.tracker;
             store.updateModelMetrics('tracker', { ...tracker, precision: data.avg_confidence ? data.avg_confidence / 100 : tracker.precision });
        }
        if (data.recent_alerts > 0) {
            // Adjust threat score dynamically based on active alerts
            const newScore = Math.min(10, data.recent_alerts * 1.5);
            store.updateThreatScore(newScore);
        } else {
            // Decay threat score slowly gracefully
            store.updateThreatScore(Math.max(0, store.threatScore - 0.5));
        }
      }
    } catch {
      // Backend offline — silent
    }
  }, 2000);
}

// ── GPU Bridge status polling (every 5s) ──────────────────────────────────────

export function startBridgePoller() {
  return setInterval(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/bridge-status');
      if (res.ok) {
        useSystemStore.getState().updateBridgeStatus(await res.json());
      }
    } catch {
      useSystemStore.getState().updateBridgeStatus({
        mode:             'local',
        connected:        false,
        latency_ms:       0,
        inference_source: 'local',
      });
    }
  }, 5000);
}

export default useSystemStore;