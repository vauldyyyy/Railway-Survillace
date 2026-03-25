import { create } from 'zustand';

/**
 * App Store — global application state (system health, sidebar, theme).
 */
const useAppStore = create((set) => ({
  // Sidebar state
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // System status
  systemStatus: {
    aiActive: true,
    secureMode: true,
    systemHealth: 98.5,
    uptime: '14d 6h 32m',
    lastSync: Date.now(),
    networkLatency: 12,
  },

  // Update system status
  updateSystemStatus: (updates) => set((state) => ({
    systemStatus: { ...state.systemStatus, ...updates },
  })),

  // Current time (updated by interval)
  currentTime: new Date(),
  updateTime: () => set({ currentTime: new Date() }),
}));

export default useAppStore;
