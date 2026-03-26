import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Bell, Shield, Monitor, Cpu, Database, Clock, Wifi, Box } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import useAppStore from '../store/useAppStore';
import { API_BASE } from '../config';

/**
 * Settings — System configuration and preferences.
 */
export default function Settings() {
  const { systemStatus } = useAppStore();
  const [modelStatus, setModelStatus] = useState(null);

  useEffect(() => {
    const fetchStatus = () => {
      fetch(`${API_BASE}/api/model-status`)
        .then(r => r.json())
        .then(data => setModelStatus(data))
        .catch(() => setModelStatus(null));
    };
    fetchStatus();
    const iv = setInterval(fetchStatus, 5000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
          <SettingsIcon className="w-6 h-6 text-cyber" />
          System Settings
        </h1>
        <p className="text-sm text-text-secondary mt-1">Configuration and system information</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notification Preferences */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Bell className="w-4 h-4 text-cyber" />
            Notification Preferences
          </h3>
          <div className="space-y-3">
            <ToggleSetting label="Critical Alert Notifications" description="Receive notifications for critical threats" defaultChecked={true} />
            <ToggleSetting label="Warning Notifications" description="Receive notifications for warnings" defaultChecked={true} />
            <ToggleSetting label="Info Notifications" description="Receive notifications for informational alerts" defaultChecked={false} />
            <ToggleSetting label="Sound Alerts" description="Play audio for critical alerts" defaultChecked={true} />
            <ToggleSetting label="Desktop Notifications" description="Push notifications to desktop" defaultChecked={false} />
          </div>
        </GlassCard>

        {/* Security Settings */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-cyber" />
            Security
          </h3>
          <div className="space-y-3">
            <ToggleSetting label="Secure Mode" description="Enable enhanced security protocols" defaultChecked={systemStatus.secureMode} />
            <ToggleSetting label="Auto-Lock Timeout" description="Lock dashboard after 15 min of inactivity" defaultChecked={true} />
            <ToggleSetting label="Audit Logging" description="Log all operator actions" defaultChecked={true} />
            <ToggleSetting label="Two-Factor Authentication" description="Require 2FA for login" defaultChecked={true} />
          </div>
        </GlassCard>

        {/* Display Settings */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Monitor className="w-4 h-4 text-cyber" />
            Display
          </h3>
          <div className="space-y-3">
            <ToggleSetting label="Dark Theme" description="Use dark UI theme (recommended for SOC)" defaultChecked={true} />
            <ToggleSetting label="Animation Effects" description="Enable scan lines and glow effects" defaultChecked={true} />
            <ToggleSetting label="Auto-Refresh Dashboard" description="Refresh data every 10 seconds" defaultChecked={true} />
            <ToggleSetting label="Compact Mode" description="Reduce spacing for more data density" defaultChecked={false} />
          </div>
        </GlassCard>

        {/* System Information */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyber" />
            System Information
          </h3>
          <div className="space-y-3">
            <InfoRow icon={Cpu} label="AI Engine" value="RailGuard AI v3.2.1" status="active" />
            <InfoRow icon={Database} label="Database" value="PostgreSQL 16.1" status="active" />
            <InfoRow icon={Wifi} label="Network Latency" value={`${systemStatus.networkLatency}ms`} status="active" />
            <InfoRow icon={Clock} label="System Uptime" value={systemStatus.uptime} status="active" />
            <InfoRow icon={Shield} label="System Health" value={`${systemStatus.systemHealth}%`} status="active" />
            <InfoRow icon={Monitor} label="Active Cameras" value="11 / 12" status="warning" />
          </div>
        </GlassCard>

        {/* AI Model Status */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Box className="w-4 h-4 text-cyber" />
            AI Model Status
          </h3>
          <div className="space-y-3">
            {modelStatus ? (
              Object.entries(modelStatus).map(([name, info]) => (
                <div key={name} className="flex items-center justify-between py-2 border-b border-border-subtle/30 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary uppercase">{name}</span>
                    {info.loaded ? (
                      <span className="text-[10px] bg-success/20 text-success border border-success/30 px-1.5 py-0.5 rounded font-bold">LOADED</span>
                    ) : (
                      <span className="text-[10px] bg-danger/20 text-danger border border-danger/30 px-1.5 py-0.5 rounded font-bold">OFFLINE</span>
                    )}
                  </div>
                  <span className="text-xs font-mono text-text-muted">{info.inference_ms} ms</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-text-muted italic">Connecting to model service...</p>
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

function ToggleSetting({ label, description, defaultChecked }) {
  const [checked, setChecked] = React.useState(defaultChecked);

  return (
    <div className="flex items-center justify-between py-2 border-b border-border-subtle/30 last:border-0">
      <div>
        <p className="text-sm text-text-primary">{label}</p>
        <p className="text-[11px] text-text-muted mt-0.5">{description}</p>
      </div>
      <button
        onClick={() => setChecked(!checked)}
        className={`
          relative w-11 h-6 rounded-full transition-colors duration-200 flex-shrink-0
          ${checked ? 'bg-cyber/30' : 'bg-bg-primary'}
          border ${checked ? 'border-cyber/40' : 'border-border-subtle'}
        `}
      >
        <div className={`
          absolute top-0.5 w-5 h-5 rounded-full transition-all duration-200
          ${checked ? 'left-[22px] bg-cyber shadow-glow-cyan' : 'left-0.5 bg-text-muted'}
        `} />
      </button>
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, status }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border-subtle/30 last:border-0">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-text-muted" />
        <span className="text-sm text-text-secondary">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono text-text-primary">{value}</span>
        <div className={`status-dot ${status === 'active' ? 'online' : status === 'warning' ? 'warning' : 'offline'}`} />
      </div>
    </div>
  );
}
