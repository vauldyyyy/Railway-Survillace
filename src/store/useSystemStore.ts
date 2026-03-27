import { create } from 'zustand';

// ── Types ──
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
  // Threat index
  threatLevel: ThreatLevel;
  threatScore: number; // 0–10

  // Cameras
  cameras: Record<string, CameraState>;

  // Model metrics
  modelMetrics: {
    coco: ModelMetrics;
    railfod: ModelMetrics;
    uav: ModelMetrics;
    lstm: ModelMetrics;
    tracker: ModelMetrics;
  };

  // Edge health
  edgeNodes: EdgeNodeHealth[];

  // System info
  systemUptime: number;
  lastSync: number;
  wsConnected: boolean;
  jwtToken: string | null;

  // Actions
  updateThreatScore: (score: number) => void;
  updateModelMetrics: (model: string, metrics: Partial<ModelMetrics>) => void;
  updateCamera: (id: string, update: Partial<CameraState>) => void;
  setEdgeNodes: (nodes: EdgeNodeHealth[]) => void;
  setWsConnected: (connected: boolean) => void;
  login: () => Promise<boolean>;
  connectWebSocket: () => void;
}

// ── Simulated initial metrics ──
const defaultModel = (name: string, fps: number, gpu: number): ModelMetrics => ({
  name,
  fps,
  latency_ms: Math.round(1000 / fps),
  gpu_util_pct: gpu,
  precision: 0.88 + Math.random() * 0.1,
  recall: 0.82 + Math.random() * 0.12,
  false_positive_rate: 0.02 + Math.random() * 0.05,
  drift_score: Math.random() * 0.15,
  status: 'active',
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
  { id: 'EDGE_01', station: 'Madgaon Junction', status: 'healthy', cpu_pct: 42, gpu_pct: 68, memory_pct: 55, uptime_hours: 342, models_loaded: 4, last_heartbeat: Date.now() },
  { id: 'EDGE_02', station: 'Thivim Station', status: 'healthy', cpu_pct: 38, gpu_pct: 52, memory_pct: 48, uptime_hours: 220, models_loaded: 4, last_heartbeat: Date.now() },
  { id: 'EDGE_03', station: 'Vasco da Gama', status: 'degraded', cpu_pct: 78, gpu_pct: 91, memory_pct: 82, uptime_hours: 18, models_loaded: 3, last_heartbeat: Date.now() - 30000 },
];

// ── Store ──
const useSystemStore = create<SystemState>((set, get) => ({
  threatLevel: 'HIGH',
  threatScore: 7.2,
  cameras: defaultCameras,
  modelMetrics: {
    coco: defaultModel('YOLOv8n COCO', 32.1, 45),
    railfod: defaultModel('RailFOD YOLOv8', 28.4, 12),
    uav: defaultModel('UAV YOLOv8', 26.8, 10),
    lstm: defaultModel('LSTM Crowd v2.4', 200, 0),
    tracker: { ...defaultModel('ByteTrack', 30, 0), gpu_util_pct: 0 },
  },
  edgeNodes: defaultEdgeNodes,
  systemUptime: 342 * 3600,
  lastSync: Date.now(),
  wsConnected: false,
  jwtToken: null,

  updateThreatScore: (score) => {
    let level: ThreatLevel = 'LOW';
    if (score >= 8) level = 'CRITICAL';
    else if (score >= 6) level = 'HIGH';
    else if (score >= 3) level = 'MEDIUM';
    set({ threatScore: score, threatLevel: level });
  },

  updateModelMetrics: (model, metrics) =>
    set((state) => ({
      modelMetrics: {
        ...state.modelMetrics,
        [model]: { ...state.modelMetrics[model as keyof typeof state.modelMetrics], ...metrics },
      },
    })),

  updateCamera: (id, update) =>
    set((state) => ({
      cameras: {
        ...state.cameras,
        [id]: { ...state.cameras[id], ...update },
      },
    })),

  setEdgeNodes: (nodes) => set({ edgeNodes: nodes }),
  setWsConnected: (connected) => set({ wsConnected: connected }),

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

  connectWebSocket: async () => {
    let token = get().jwtToken;
    if (!token) {
      const success = await get().login();
      if (!success) {
        console.warn('[WS] Authentication failed, retrying in 5s...');
        setTimeout(() => get().connectWebSocket(), 5000);
        return;
      }
      token = get().jwtToken;
    }

    const wsBase = 'ws://127.0.0.1:8001';
    const ws = new WebSocket(`${wsBase}/ws/alerts?token=${token}`);

    ws.onopen = () => {
      set({ wsConnected: true });
      console.log('[WS] Connected to RailGuard backend');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
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
      console.log('[WS] Disconnected, retrying in 5s...');
      setTimeout(() => get().connectWebSocket(), 5000);
    };
  },
}));

// ── Metric simulation (for demo when backend is offline) ──
export function startMetricsSimulation() {
  return setInterval(() => {
    const store = useSystemStore.getState();
    const jitter = (base: number, range: number) => Math.max(0, base + (Math.random() - 0.5) * range);

    store.updateModelMetrics('coco', {
      fps: jitter(32, 6),
      latency_ms: jitter(31, 8),
      gpu_util_pct: jitter(45, 10),
    });
    store.updateModelMetrics('railfod', {
      fps: jitter(28, 5),
      latency_ms: jitter(35, 6),
      gpu_util_pct: jitter(12, 4),
    });
    store.updateModelMetrics('uav', {
      fps: jitter(27, 4),
      latency_ms: jitter(37, 5),
      gpu_util_pct: jitter(10, 3),
    });
    store.updateModelMetrics('lstm', {
      fps: jitter(200, 40),
      latency_ms: jitter(5, 2),
    });
    store.updateModelMetrics('tracker', {
      fps: jitter(30, 4),
      latency_ms: jitter(33, 5),
    });

    // Slowly fluctuate threat score
    const newScore = Math.max(0, Math.min(10, store.threatScore + (Math.random() - 0.48) * 0.3));
    store.updateThreatScore(parseFloat(newScore.toFixed(1)));
  }, 1500);
}

export default useSystemStore;
