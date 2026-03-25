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
