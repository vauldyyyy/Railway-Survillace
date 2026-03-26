import { create } from 'zustand';
import { sampleAlerts, generateRandomAlert } from '../data/alerts';

/**
 * Alert Store — manages real-time alerts with WebSocket-ready architecture.
 * Uses Zustand for global state management.
 */
const useAlertStore = create((set, get) => ({
  // Alert state
  alerts: [...sampleAlerts],
  toasts: [],
  
  // Add a new alert (called by WebSocket handler or simulation)
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, 50), // Keep last 50
    toasts: [alert, ...state.toasts].slice(0, 5),  // Keep last 5 toasts
  })),

  // Acknowledge an alert
  acknowledgeAlert: (alertId) => set((state) => ({
    alerts: state.alerts.map(a => 
      a.id === alertId ? { ...a, acknowledged: true } : a
    ),
  })),

  // Dismiss a toast notification
  dismissToast: (alertId) => set((state) => ({
    toasts: state.toasts.filter(t => t.id !== alertId),
  })),

  // Clear all toasts
  clearToasts: () => set({ toasts: [] }),

  // Connect WebSocket for real-time alerts
  connectWebSocket: () => {
    import('../config.js').then(({ WS_BASE }) => {
      const ws = new WebSocket(`${WS_BASE}/ws/alerts`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type && data.type !== 'connected') {
            get().addAlert({ ...data, id: Date.now().toString(), acknowledged: false });
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };
      ws.onerror = (e) => console.error("WebSocket error", e);
      ws.onclose = () => {
        console.log("WebSocket closed, retrying in 5s...");
        setTimeout(() => get().connectWebSocket(), 5000);
      };
    });
  },

  // Simulate incoming alerts (replaces WebSocket in demo)
  startSimulation: () => {
    const interval = setInterval(() => {
      const newAlert = generateRandomAlert();
      get().addAlert(newAlert);
    }, 12000); // New alert every 12 seconds
    return interval;
  },

  // Get unacknowledged count
  getUnacknowledgedCount: () => {
    return get().alerts.filter(a => !a.acknowledged).length;
  },
}));

export default useAlertStore;
