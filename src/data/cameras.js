// Mock camera data — 12 feeds across the station
export const cameras = [
  { id: 'CAM-001', name: 'Platform 1 - North', location: 'Platform 1', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 94, zone: 'high-risk' },
  { id: 'CAM-002', name: 'Platform 1 - South', location: 'Platform 1', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 91, zone: 'medium-risk' },
  { id: 'CAM-003', name: 'Platform 2 - Central', location: 'Platform 2', status: 'online', fps: 28, aiStatus: 'active', aiConfidence: 96, zone: 'low-risk' },
  { id: 'CAM-004', name: 'Entry Gate A', location: 'Entry Gate', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 89, zone: 'high-risk' },
  { id: 'CAM-005', name: 'Entry Gate B', location: 'Entry Gate', status: 'online', fps: 29, aiStatus: 'active', aiConfidence: 92, zone: 'medium-risk' },
  { id: 'CAM-006', name: 'Ticket Counter', location: 'Main Hall', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 88, zone: 'low-risk' },
  { id: 'CAM-007', name: 'Waiting Area', location: 'Main Hall', status: 'online', fps: 25, aiStatus: 'active', aiConfidence: 95, zone: 'medium-risk' },
  { id: 'CAM-008', name: 'Footbridge', location: 'Bridge', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 90, zone: 'high-risk' },
  { id: 'CAM-009', name: 'Parking Area', location: 'Exterior', status: 'offline', fps: 0, aiStatus: 'inactive', aiConfidence: 0, zone: 'low-risk' },
  { id: 'CAM-010', name: 'Platform 3 - East', location: 'Platform 3', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 93, zone: 'medium-risk' },
  { id: 'CAM-011', name: 'Track Section A', location: 'Track Zone', status: 'online', fps: 30, aiStatus: 'active', aiConfidence: 97, zone: 'high-risk' },
  { id: 'CAM-012', name: 'Emergency Exit', location: 'Exit', status: 'online', fps: 27, aiStatus: 'active', aiConfidence: 86, zone: 'low-risk' },
];

// Camera feed simulation colors (gradient backgrounds)
export const cameraFeedColors = [
  'from-slate-800 to-slate-900',
  'from-gray-800 to-gray-900',
  'from-zinc-800 to-zinc-900',
  'from-neutral-800 to-neutral-900',
];
