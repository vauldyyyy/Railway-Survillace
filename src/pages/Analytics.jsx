import React, { useState, useEffect } from 'react';
import {
  BarChart3, AlertTriangle, MapPin, Cpu, TrendingUp, Shield, Gauge,
  ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart, Legend
} from 'recharts';
import GlassCard from '../components/ui/GlassCard';
import KPICard from '../components/ui/KPICard';
import LoadingSkeleton from '../components/ui/LoadingSkeleton';
import {
  crowdDensityData, threatDistribution, alertTrendData,
  platformRisks, kpiData
} from '../data/analytics';

/**
 * Analytics — Charts, KPIs, predictive analytics, and reports.
 */
export default function Analytics() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 700);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <LoadingSkeleton key={i} type="card" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LoadingSkeleton type="chart" />
          <LoadingSkeleton type="chart" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
          <BarChart3 className="w-6 h-6 text-cyber" />
          Analytics & Reports
        </h1>
        <p className="text-sm text-text-secondary mt-1">Predictive analytics and operational intelligence</p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard icon={AlertTriangle} label="Total Alerts Today" value={kpiData.totalAlerts} color="red" trend="up" trendValue="+12%" />
        <KPICard icon={MapPin} label="High-Risk Zones" value={kpiData.highRiskZones} color="orange" trend="up" trendValue="+1" />
        <KPICard icon={Cpu} label="AI Confidence" value={`${kpiData.predictionConfidence}%`} color="cyan" trend="up" trendValue="+2.1%" />
        <KPICard icon={Shield} label="Avg Response Time" value={kpiData.avgResponseTime} color="green" trend="down" trendValue="-8s" />
      </div>

      {/* Predictive Risk Gauge */}
      <GlassCard hoverable={false} className="p-5" glowColor="cyan">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <Gauge className="w-4 h-4 text-cyber" />
            Predictive Risk Analysis — Next 10 Minutes
          </h3>
          <span className="text-[10px] font-mono text-text-muted">UPDATED 30s AGO</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {platformRisks.slice(0, 6).map((pr) => (
            <div key={pr.platform} className="glass p-3 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-text-primary">{pr.platform}</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                  pr.level === 'high' ? 'bg-danger/15 text-danger' :
                  pr.level === 'medium' ? 'bg-warning/15 text-warning' :
                  'bg-success/15 text-success'
                }`}>
                  {pr.level.toUpperCase()}
                </span>
              </div>
              {/* Risk bar */}
              <div className="w-full h-2 bg-bg-primary rounded-full overflow-hidden mb-2">
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: `${pr.risk}%`,
                    background: pr.risk > 70
                      ? 'linear-gradient(90deg, #FF3B3B, #FF6B6B)'
                      : pr.risk > 50
                      ? 'linear-gradient(90deg, #FFA500, #FFDD57)'
                      : 'linear-gradient(90deg, #00FF88, #00E0FF)',
                  }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-text-muted">
                <span>Risk: {pr.risk}%</span>
                <span>Crowd: {pr.crowd}%</span>
                <span>{pr.cameras} cam{pr.cameras > 1 ? 's' : ''}</span>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alert Trend */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyber" />
            Alert Trend (24h)
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={alertTrendData}>
              <defs>
                <linearGradient id="alertGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00E0FF" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00E0FF" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="critGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF3B3B" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#FF3B3B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2D4A" />
              <XAxis dataKey="hour" tick={{ fill: '#8892A5', fontSize: 10 }} axisLine={{ stroke: '#1E2D4A' }} interval={3} />
              <YAxis tick={{ fill: '#8892A5', fontSize: 10 }} axisLine={{ stroke: '#1E2D4A' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0F1A2E', border: '1px solid #1E2D4A',
                  borderRadius: '8px', fontSize: '12px', color: '#E8EDF5',
                }}
              />
              <Area type="monotone" dataKey="alerts" stroke="#00E0FF" fill="url(#alertGrad)" strokeWidth={2} name="Total Alerts" />
              <Area type="monotone" dataKey="critical" stroke="#FF3B3B" fill="url(#critGrad)" strokeWidth={2} name="Critical" />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Threat Distribution */}
        <GlassCard hoverable={false} className="p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-cyber" />
            Threat Distribution
          </h3>
          <div className="flex items-center gap-6">
            <ResponsiveContainer width={180} height={180}>
              <PieChart>
                <Pie
                  data={threatDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {threatDistribution.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0F1A2E', border: '1px solid #1E2D4A',
                    borderRadius: '8px', fontSize: '12px', color: '#E8EDF5',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2">
              {threatDistribution.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: item.color }} />
                    <span className="text-xs text-text-secondary">{item.name}</span>
                  </div>
                  <span className="text-xs font-semibold text-text-primary">{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Charts Row 2 — Crowd Density */}
      <GlassCard hoverable={false} className="p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyber" />
          Crowd Density Over Time (All Platforms)
        </h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={crowdDensityData} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E2D4A" />
            <XAxis dataKey="time" tick={{ fill: '#8892A5', fontSize: 11 }} axisLine={{ stroke: '#1E2D4A' }} />
            <YAxis tick={{ fill: '#8892A5', fontSize: 11 }} axisLine={{ stroke: '#1E2D4A' }} domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0F1A2E', border: '1px solid #1E2D4A',
                borderRadius: '8px', fontSize: '12px', color: '#E8EDF5',
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: '#8892A5' }} />
            <Bar dataKey="platform1" name="Platform 1" fill="#00E0FF" radius={[3, 3, 0, 0]} />
            <Bar dataKey="platform2" name="Platform 2" fill="#FFA500" radius={[3, 3, 0, 0]} />
            <Bar dataKey="platform3" name="Platform 3" fill="#A78BFA" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </GlassCard>
    </div>
  );
}
