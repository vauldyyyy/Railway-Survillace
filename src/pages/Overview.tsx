import React from 'react';
import { Header } from '../components/Header';
import { Video, AlertTriangle, UserSearch, Users, Shield, MapPin, Bell, User } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const crowdData = [
  { time: '12:00', history: 120 },
  { time: '13:00', history: 150 },
  { time: 'LIVE', history: 247, predict: 247 },
  { time: '15:00', predict: 180 },
  { time: '16:00', predict: 120 },
];

export function Overview({ onNavigate }: { onNavigate?: (page: any) => void }) {
  return (
    <div className="flex flex-col h-full">
      <Header 
        title="STATION OVERVIEW — MADGAON JUNCTION" 
        subtitle="MINISTRY OF RAILWAYS | ISEA PHASE III INITIATIVE | IIT MADRAS × BITS GOA"
        rightContent={
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2 bg-slate-800/50 border border-slate-700 rounded-full px-4 py-1.5 text-slate-300 cursor-pointer hover:bg-slate-800 transition-colors">
              <MapPin size={14} className="text-slate-400" />
              <span>Madgaon Junction</span>
              <span className="text-slate-500 text-xs ml-2">▼</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400 font-mono text-xs">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              LIVE
              <span className="ml-2 border-l border-slate-700 pl-2">24 JAN 2026 | 14:42:08 UTC</span>
            </div>
          </div>
        }
      />

      <div className="p-8 space-y-6 flex-1 overflow-y-auto">
        {/* Stats Row */}
        <div className="grid grid-cols-5 gap-4">
          <StatCard 
            title="ACTIVE CAMERAS" 
            value="14" 
            subValue="/ 16 online" 
            icon={<Video size={16} className="text-cyan-400" />} 
            borderColor="border-cyan-500"
            onClick={() => onNavigate?.('live-feeds')}
          />
          <StatCard 
            title="THREATS DETECTED" 
            value="03" 
            subValue="ACTIVE" 
            subText="HIGH PRIORITY LEVEL"
            icon={<AlertTriangle size={16} className="text-red-400" />} 
            borderColor="border-red-500"
            valueColor="text-red-400"
            onClick={() => onNavigate?.('threat-alerts')}
          />
          <StatCard 
            title="PERSONS TRACKED" 
            value="247" 
            subValue="on platform" 
            subText="+12% VS LAST HR"
            icon={<UserSearch size={16} className="text-slate-400" />} 
            borderColor="border-slate-500"
            onClick={() => onNavigate?.('person-tracking')}
          />
          <div 
            className="bg-[#0B0F19] border-l-2 border-yellow-500 p-4 flex flex-col justify-between cursor-pointer hover:bg-slate-900/50 transition-colors"
            onClick={() => onNavigate?.('crowd-analytics')}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">CROWD RISK LEVEL</span>
              <Users size={16} className="text-yellow-400" />
            </div>
            <div>
              <div className="text-yellow-400 font-mono text-sm mb-2 border border-yellow-400/30 bg-yellow-400/10 inline-block px-2 py-0.5 rounded">HIGH</div>
              <div className="w-full h-1 bg-slate-800 flex">
                <div className="h-full bg-yellow-500 w-2/3"></div>
              </div>
            </div>
          </div>
          <div 
            className="bg-[#0B0F19] border-l-2 border-emerald-500 p-4 flex flex-col justify-between cursor-pointer hover:bg-slate-900/50 transition-colors"
            onClick={() => onNavigate?.('security-layer')}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">SYSTEM SECURITY</span>
              <Shield size={16} className="text-emerald-400" />
            </div>
            <div>
              <div className="text-emerald-400 font-mono text-sm mb-1 border border-emerald-400/30 bg-emerald-400/10 inline-block px-2 py-0.5 rounded">SECURE</div>
              <div className="text-[10px] text-emerald-500/70 font-mono mt-1">ENCRYPTED L-12</div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* Live Threat Feed */}
          <div className="col-span-2 space-y-4">
            <div className="flex justify-between items-end border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">LIVE THREAT FEED</h3>
              <div className="flex gap-4 text-xs text-slate-400 font-mono">
                <span className="text-slate-200 bg-slate-800 px-2 py-1 rounded cursor-pointer">GRID VIEW</span>
                <span className="px-2 py-1 cursor-pointer hover:text-slate-200 transition-colors">ANALYTICS</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <CameraFeed 
                id="CAM_01_SOUTH" 
                time="24.01.26 14:42:01" 
                threat="UNKNOWN_ID" 
                confidence={94.2} 
                image="https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&q=80&w=800"
              />
              <CameraFeed 
                id="CAM_04_NORTH" 
                time="24.01.26 14:42:02" 
                status="NOMINAL" 
                image="https://images.unsplash.com/photo-1584432810601-6c7f27d2362b?auto=format&fit=crop&q=80&w=800"
              />
              <CameraFeed 
                id="CAM_09_ENTRANCE" 
                time="24.01.26 14:42:02" 
                image="https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&q=80&w=800"
                dark
              />
              <CameraFeed 
                id="CAM_12_TRACKS" 
                time="24.01.26 14:42:03" 
                status="ENCODING STREAM..." 
                image="https://images.unsplash.com/photo-1584432810601-6c7f27d2362b?auto=format&fit=crop&q=80&w=800"
                dark
              />
            </div>
            
            {/* Heatmap */}
            <div className="pt-4">
              <div className="flex justify-between items-end border-b border-slate-800 pb-2 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">PLATFORM RISK HEATMAP — LIVE</h3>
                  <p className="text-[10px] text-slate-500 font-mono mt-1">MAPPING: MADGAON JN [MAO] — ALL PLATFORMS (1-4)</p>
                </div>
                <div className="flex gap-4 text-[10px] font-mono text-slate-400">
                  <div className="flex items-center gap-1"><span className="w-3 h-3 bg-red-400/80 rounded-sm"></span> HIGH RISK</div>
                  <div className="flex items-center gap-1"><span className="w-3 h-3 bg-yellow-400/80 rounded-sm"></span> MODERATE</div>
                  <div className="flex items-center gap-1"><span className="w-3 h-3 bg-slate-600/80 rounded-sm"></span> OPTIMAL</div>
                </div>
              </div>
              <div className="h-16 w-full flex gap-1">
                {Array.from({ length: 48 }).map((_, i) => {
                  const isHigh = i > 15 && i < 22;
                  const isMod = (i > 10 && i <= 15) || (i >= 22 && i < 28);
                  return (
                    <div 
                      key={i} 
                      className={`flex-1 rounded-sm ${isHigh ? 'bg-red-400/80' : isMod ? 'bg-yellow-400/80' : 'bg-slate-700/50'}`}
                    ></div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Active Alerts */}
            <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg p-5">
              <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-2">
                <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">ACTIVE ALERTS</h3>
                <span className="text-[10px] text-red-400 font-mono">3 EVENTS PENDING</span>
              </div>
              <div className="space-y-3">
                <AlertItem 
                  type="CRITICAL THREAT" 
                  time="14:40:12" 
                  desc="Unattended Package — Platform 2 North" 
                  actions={['DISPATCH', 'IGNORE']}
                  critical
                />
                <AlertItem 
                  type="CROWD WARNING" 
                  time="14:38:55" 
                  desc="Density Threshold Exceeded — Gate 4B" 
                  actions={['MONITOR']}
                  warning
                />
                <AlertItem 
                  type="SYSTEM INFO" 
                  time="14:35:00" 
                  desc="Routine scan of Express 12455 completed" 
                  info
                />
              </div>
            </div>

            {/* Crowd Prediction */}
            <div className="bg-[#0B0F19] border border-slate-800/50 rounded-lg p-5">
              <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-2">
                <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">CROWD PREDICTION</h3>
                <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                  <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                  LSTM MODEL V2.4
                </div>
              </div>
              <div className="h-48 w-full relative">
                <div className="absolute top-0 right-1/2 translate-x-1/2 bg-cyan-500/20 text-cyan-400 text-[10px] font-mono px-2 py-0.5 border border-cyan-500/30 rounded z-10">LIVE</div>
                <div className="absolute top-6 right-1/4 bg-yellow-500/20 text-yellow-400 text-[10px] font-mono px-2 py-0.5 border border-yellow-500/30 rounded z-10">PREDICT</div>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={crowdData} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', fontSize: '12px' }}
                      itemStyle={{ color: '#cbd5e1' }}
                      cursor={{fill: '#1e293b', opacity: 0.4}}
                    />
                    <ReferenceLine x="LIVE" stroke="#06b6d4" strokeDasharray="3 3" />
                    <Bar dataKey="history" fill="#475569" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="predict" fill="#b45309" radius={[2, 2, 0, 0]} opacity={0.8} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-2">
                  <span>T-4 HRS HISTORY</span>
                  <span>T+3 HRS FORECAST</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, subValue, subText, icon, borderColor = "border-slate-800", valueColor = "text-slate-100", onClick }: any) {
  return (
    <div 
      className={`bg-[#0B0F19] border-l-2 ${borderColor} p-4 flex flex-col justify-between relative overflow-hidden ${onClick ? 'cursor-pointer hover:bg-slate-900/50 transition-colors' : ''}`}
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs text-slate-400 uppercase tracking-wider z-10">{title}</span>
        <div className="z-10">{icon}</div>
      </div>
      <div className="z-10">
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-light ${valueColor}`}>{value}</span>
          {subValue && <span className="text-xs text-slate-500">{subValue}</span>}
        </div>
        {subText && <div className="text-[10px] text-slate-500 mt-1 font-mono">{subText}</div>}
      </div>
    </div>
  );
}

function CameraFeed({ id, time, threat, status, confidence, image, dark }: any) {
  return (
    <div className="relative overflow-hidden border border-slate-800 bg-slate-900 aspect-video group">
      <img 
        src={image} 
        alt={id} 
        className={`w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 ${dark ? 'opacity-40 grayscale' : 'opacity-70'}`}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[#05080F] via-transparent to-transparent opacity-90"></div>
      
      {/* Overlay UI */}
      <div className="absolute top-0 left-0 flex flex-col">
        <div className="bg-[#0B0F19]/90 text-[10px] text-cyan-400 font-mono px-2 py-1 border-l-2 border-cyan-500">
          {id}
        </div>
        <div className="bg-[#0B0F19]/80 text-[10px] text-slate-400 font-mono px-2 py-1">
          {time}
        </div>
      </div>

      {threat && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="border border-red-500/50 bg-red-500/10 w-32 h-48 relative">
            <div className="absolute -bottom-6 left-0 bg-red-500 text-white text-[10px] px-2 py-0.5 font-mono">{threat}</div>
          </div>
        </div>
      )}

      <div className="absolute bottom-2 right-2 left-2 flex justify-between items-end">
        <div></div>
        {confidence && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-300 font-mono">CONFIDENCE: {confidence}%</span>
            <div className="w-16 h-1 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-cyan-500" style={{ width: `${confidence}%` }}></div>
            </div>
          </div>
        )}
        {status && (
          <div className={`text-[10px] font-mono px-2 py-1 ${status === 'NOMINAL' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-slate-400'}`}>
            {status}
          </div>
        )}
      </div>
    </div>
  );
}

function AlertItem({ type, time, desc, actions, critical, warning, info }: any) {
  return (
    <div className={`border-l-2 p-4 bg-[#05080F] ${critical ? 'border-red-500' : warning ? 'border-yellow-500' : 'border-slate-600'}`}>
      <div className="flex justify-between items-start mb-2">
        <span className={`text-[10px] font-bold tracking-wider ${critical ? 'text-red-400' : warning ? 'text-yellow-400' : 'text-slate-400'}`}>{type}</span>
        <span className="text-[10px] text-slate-500 font-mono">{time}</span>
      </div>
      <p className="text-sm text-slate-200 mb-4">{desc}</p>
      {actions && (
        <div className="flex gap-2">
          {actions.map((action: string, i: number) => (
            <button 
              key={i}
              className={`text-[10px] px-4 py-1.5 font-mono tracking-wider transition-colors ${
                action === 'DISPATCH' 
                  ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30' 
                  : action === 'MONITOR'
                  ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 border border-yellow-500/30'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
              }`}
            >
              {action}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
