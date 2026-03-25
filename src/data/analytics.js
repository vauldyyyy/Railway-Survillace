// Crowd density per platform (hourly data)
export const crowdDensityData = [
  { time: '06:00', platform1: 20, platform2: 15, platform3: 10 },
  { time: '07:00', platform1: 55, platform2: 40, platform3: 25 },
  { time: '08:00', platform1: 85, platform2: 72, platform3: 45 },
  { time: '09:00', platform1: 92, platform2: 80, platform3: 60 },
  { time: '10:00', platform1: 70, platform2: 55, platform3: 40 },
  { time: '11:00', platform1: 50, platform2: 42, platform3: 30 },
  { time: '12:00', platform1: 65, platform2: 58, platform3: 35 },
  { time: '13:00', platform1: 60, platform2: 50, platform3: 32 },
  { time: '14:00', platform1: 55, platform2: 45, platform3: 28 },
  { time: '15:00', platform1: 62, platform2: 52, platform3: 38 },
  { time: '16:00', platform1: 78, platform2: 65, platform3: 48 },
  { time: '17:00', platform1: 90, platform2: 78, platform3: 55 },
  { time: '18:00', platform1: 88, platform2: 75, platform3: 52 },
  { time: '19:00', platform1: 65, platform2: 55, platform3: 35 },
  { time: '20:00', platform1: 40, platform2: 30, platform3: 20 },
  { time: '21:00', platform1: 25, platform2: 18, platform3: 12 },
];

// Threat distribution
export const threatDistribution = [
  { name: 'Person on Track', value: 28, color: '#FF3B3B' },
  { name: 'Overcrowding', value: 35, color: '#FFA500' },
  { name: 'Unattended Baggage', value: 18, color: '#FFDD57' },
  { name: 'Suspicious Behaviour', value: 12, color: '#00E0FF' },
  { name: 'Track Obstruction', value: 5, color: '#FF6B6B' },
  { name: 'Unauthorized Access', value: 2, color: '#A78BFA' },
];

// Hourly alert trend (last 24 hours)
export const alertTrendData = [
  { hour: '00:00', alerts: 2, critical: 0 },
  { hour: '01:00', alerts: 1, critical: 0 },
  { hour: '02:00', alerts: 0, critical: 0 },
  { hour: '03:00', alerts: 1, critical: 1 },
  { hour: '04:00', alerts: 0, critical: 0 },
  { hour: '05:00', alerts: 3, critical: 1 },
  { hour: '06:00', alerts: 5, critical: 2 },
  { hour: '07:00', alerts: 8, critical: 3 },
  { hour: '08:00', alerts: 12, critical: 4 },
  { hour: '09:00', alerts: 15, critical: 5 },
  { hour: '10:00', alerts: 9, critical: 2 },
  { hour: '11:00', alerts: 7, critical: 1 },
  { hour: '12:00', alerts: 10, critical: 3 },
  { hour: '13:00', alerts: 8, critical: 2 },
  { hour: '14:00', alerts: 6, critical: 1 },
  { hour: '15:00', alerts: 9, critical: 3 },
  { hour: '16:00', alerts: 11, critical: 4 },
  { hour: '17:00', alerts: 14, critical: 5 },
  { hour: '18:00', alerts: 13, critical: 4 },
  { hour: '19:00', alerts: 8, critical: 2 },
  { hour: '20:00', alerts: 5, critical: 1 },
  { hour: '21:00', alerts: 3, critical: 1 },
  { hour: '22:00', alerts: 2, critical: 0 },
  { hour: '23:00', alerts: 1, critical: 0 },
];

// Platform risk levels (real-time)
export const platformRisks = [
  { platform: 'Platform 1', risk: 78, level: 'high', crowd: 92, cameras: 2 },
  { platform: 'Platform 2', risk: 45, level: 'medium', crowd: 58, cameras: 1 },
  { platform: 'Platform 3', risk: 32, level: 'low', crowd: 40, cameras: 1 },
  { platform: 'Entry Gates', risk: 62, level: 'medium', crowd: 75, cameras: 2 },
  { platform: 'Main Hall', risk: 38, level: 'low', crowd: 50, cameras: 2 },
  { platform: 'Track Zone', risk: 85, level: 'high', crowd: 5, cameras: 1 },
];

// KPI summary
export const kpiData = {
  totalAlerts: 147,
  criticalAlerts: 23,
  highRiskZones: 3,
  predictionConfidence: 94.2,
  activeCameras: 11,
  totalCameras: 12,
  systemUptime: 99.7,
  avgResponseTime: '1m 42s',
};

// Heatmap data — station zones with intensity
export const heatmapZones = [
  { id: 'z1', name: 'Platform 1 North', x: 10, y: 20, w: 25, h: 15, intensity: 0.9 },
  { id: 'z2', name: 'Platform 1 South', x: 10, y: 40, w: 25, h: 15, intensity: 0.6 },
  { id: 'z3', name: 'Platform 2', x: 40, y: 20, w: 20, h: 30, intensity: 0.7 },
  { id: 'z4', name: 'Platform 3', x: 65, y: 20, w: 25, h: 15, intensity: 0.4 },
  { id: 'z5', name: 'Entry Gate A', x: 10, y: 65, w: 15, h: 20, intensity: 0.8 },
  { id: 'z6', name: 'Entry Gate B', x: 30, y: 65, w: 15, h: 20, intensity: 0.5 },
  { id: 'z7', name: 'Main Hall', x: 50, y: 60, w: 25, h: 25, intensity: 0.55 },
  { id: 'z8', name: 'Track Zone', x: 5, y: 5, w: 85, h: 10, intensity: 0.3 },
  { id: 'z9', name: 'Footbridge', x: 38, y: 52, w: 10, h: 8, intensity: 0.65 },
];

// Tracking data — simulated person journey
export const trackingData = {
  trackId: 'TRK-0042',
  subject: 'Person of Interest',
  confidence: 91,
  status: 'active',
  path: [
    { camera: 'CAM-004', location: 'Entry Gate A', timestamp: '2026-03-25T14:02:00', event: 'First detected', snapshot: 'Entered through Gate A' },
    { camera: 'CAM-006', location: 'Ticket Counter', timestamp: '2026-03-25T14:05:30', event: 'Purchased ticket', snapshot: 'Counter 2 interaction' },
    { camera: 'CAM-007', location: 'Waiting Area', timestamp: '2026-03-25T14:12:00', event: 'Waiting', snapshot: 'Seated in Zone B for 8 minutes' },
    { camera: 'CAM-008', location: 'Footbridge', timestamp: '2026-03-25T14:22:00', event: 'Moving to platform', snapshot: 'Crossing footbridge eastward' },
    { camera: 'CAM-001', location: 'Platform 1 - North', timestamp: '2026-03-25T14:25:00', event: 'On platform', snapshot: 'Standing near edge — flagged' },
    { camera: 'CAM-011', location: 'Track Section A', timestamp: '2026-03-25T14:28:00', event: '⚠ Near track', snapshot: 'Alert: Proximity warning triggered' },
  ],
};
