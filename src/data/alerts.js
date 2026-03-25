// Alert type definitions
export const ALERT_TYPES = {
  PERSON_ON_TRACK: { label: 'Person on Track', severity: 'critical', icon: 'AlertTriangle' },
  OVERCROWDING: { label: 'Overcrowding', severity: 'warning', icon: 'Users' },
  UNATTENDED_BAGGAGE: { label: 'Unattended Baggage', severity: 'warning', icon: 'Package' },
  SUSPICIOUS_BEHAVIOUR: { label: 'Suspicious Behaviour', severity: 'info', icon: 'Eye' },
  TRACK_OBSTRUCTION: { label: 'Track Obstruction', severity: 'critical', icon: 'Ban' },
  UNAUTHORIZED_ACCESS: { label: 'Unauthorized Access', severity: 'warning', icon: 'ShieldAlert' },
};

// Severity levels
export const SEVERITY_CONFIG = {
  critical: { color: '#FF3B3B', bg: 'rgba(255, 59, 59, 0.15)', border: 'rgba(255, 59, 59, 0.4)', label: 'Critical' },
  warning: { color: '#FFA500', bg: 'rgba(255, 165, 0, 0.15)', border: 'rgba(255, 165, 0, 0.3)', label: 'Warning' },
  info: { color: '#00E0FF', bg: 'rgba(0, 224, 255, 0.1)', border: 'rgba(0, 224, 255, 0.3)', label: 'Info' },
};

// Sample alerts
export const sampleAlerts = [
  { id: 'ALR-001', type: 'PERSON_ON_TRACK', camera: 'CAM-011', location: 'Track Section A', timestamp: Date.now() - 30000, aiConfidence: 97, acknowledged: false },
  { id: 'ALR-002', type: 'OVERCROWDING', camera: 'CAM-001', location: 'Platform 1 - North', timestamp: Date.now() - 120000, aiConfidence: 89, acknowledged: false },
  { id: 'ALR-003', type: 'UNATTENDED_BAGGAGE', camera: 'CAM-007', location: 'Waiting Area', timestamp: Date.now() - 300000, aiConfidence: 82, acknowledged: true },
  { id: 'ALR-004', type: 'SUSPICIOUS_BEHAVIOUR', camera: 'CAM-004', location: 'Entry Gate A', timestamp: Date.now() - 600000, aiConfidence: 74, acknowledged: true },
  { id: 'ALR-005', type: 'OVERCROWDING', camera: 'CAM-003', location: 'Platform 2 - Central', timestamp: Date.now() - 900000, aiConfidence: 91, acknowledged: false },
  { id: 'ALR-006', type: 'PERSON_ON_TRACK', camera: 'CAM-008', location: 'Footbridge', timestamp: Date.now() - 1800000, aiConfidence: 95, acknowledged: true },
];

// Text generator for random alerts
const locations = ['Platform 1 - North', 'Platform 2 - Central', 'Entry Gate A', 'Waiting Area', 'Track Section A', 'Footbridge', 'Ticket Counter', 'Entry Gate B'];
const alertTypes = Object.keys(ALERT_TYPES);

export function generateRandomAlert() {
  const type = alertTypes[Math.floor(Math.random() * alertTypes.length)];
  const location = locations[Math.floor(Math.random() * locations.length)];
  return {
    id: `ALR-${Date.now().toString(36).toUpperCase()}`,
    type,
    camera: `CAM-${String(Math.floor(Math.random() * 12) + 1).padStart(3, '0')}`,
    location,
    timestamp: Date.now(),
    aiConfidence: Math.floor(Math.random() * 25) + 75,
    acknowledged: false,
  };
}
