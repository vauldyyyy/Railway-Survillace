import React from 'react';
import { Header } from '../components/Header';
import { User, Mail, Phone, MapPin, Shield, Key, Clock, Activity } from 'lucide-react';

export function Profile({ onNavigate }: { onNavigate?: (page: any) => void }) {
  return (
    <div className="flex flex-col h-full">
      <Header 
        title="OPERATOR PROFILE" 
        subtitle="Manage your account settings and security preferences"
        onNavigate={onNavigate}
      />

      <div className="p-8 flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto grid grid-cols-3 gap-8">
          {/* Left Column - Profile Info */}
          <div className="col-span-1 space-y-6">
            <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6 flex flex-col items-center text-center">
              <div className="w-32 h-32 rounded-full border-4 border-slate-800 overflow-hidden mb-4 relative group">
                <img 
                  src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=200" 
                  alt="Profile" 
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                  <span className="text-xs text-white font-semibold">CHANGE</span>
                </div>
              </div>
              <h2 className="text-xl font-bold text-slate-100">RPF_GOA_01</h2>
              <p className="text-sm text-cyan-400 font-mono mt-1">Senior Security Analyst</p>
              
              <div className="mt-6 w-full space-y-3">
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <Mail size={16} />
                  <span>rpf.goa.01@railguard.gov.in</span>
                </div>
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <Phone size={16} />
                  <span>+91 98765 43210</span>
                </div>
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <MapPin size={16} />
                  <span>Madgaon Junction, Zone A</span>
                </div>
              </div>
              
              <button className="mt-8 w-full py-2 bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded hover:bg-cyan-500/20 transition-colors text-sm font-semibold tracking-wider">
                EDIT PROFILE
              </button>
            </div>

            <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6">
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">Security Clearance</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <Shield size={16} className="text-emerald-400" />
                    <span>Access Level</span>
                  </div>
                  <span className="text-sm font-mono text-slate-200">LEVEL 4 (HIGH)</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <Key size={16} className="text-cyan-400" />
                    <span>2FA Status</span>
                  </div>
                  <span className="text-sm font-mono text-emerald-400">ENABLED</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <Clock size={16} className="text-slate-500" />
                    <span>Last Login</span>
                  </div>
                  <span className="text-xs font-mono text-slate-400">Today, 08:42 UTC</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Activity & Settings */}
          <div className="col-span-2 space-y-6">
            <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6">
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Activity size={18} className="text-cyan-400" />
                Recent Activity
              </h3>
              <div className="space-y-4">
                {[
                  { action: 'Acknowledged Threat Alert', target: 'CAM-04: PLATFORM 2 WEST', time: '10 mins ago', type: 'alert' },
                  { action: 'Changed Camera Layout', target: 'Live Feeds', time: '1 hour ago', type: 'system' },
                  { action: 'Exported Incident Report', target: 'INC-2026-0042', time: '3 hours ago', type: 'report' },
                  { action: 'System Login', target: 'Terminal A2', time: '6 hours ago', type: 'auth' },
                ].map((log, i) => (
                  <div key={i} className="flex items-start gap-4 p-3 rounded-md hover:bg-slate-800/50 transition-colors border-l-2 border-transparent hover:border-cyan-500">
                    <div className={`w-2 h-2 rounded-full mt-1.5 ${
                      log.type === 'alert' ? 'bg-red-500' : 
                      log.type === 'system' ? 'bg-cyan-500' : 
                      log.type === 'report' ? 'bg-yellow-500' : 'bg-emerald-500'
                    }`} />
                    <div className="flex-1">
                      <p className="text-sm text-slate-200">{log.action}</p>
                      <p className="text-xs text-slate-500 font-mono mt-1">{log.target}</p>
                    </div>
                    <span className="text-xs text-slate-500">{log.time}</span>
                  </div>
                ))}
              </div>
              <button className="mt-4 text-xs text-cyan-400 hover:text-cyan-300 uppercase tracking-wider font-semibold">
                View Full Log →
              </button>
            </div>

            <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6">
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">Preferences</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-slate-800/20 rounded border border-slate-800">
                  <div>
                    <h4 className="text-sm text-slate-200">Email Notifications</h4>
                    <p className="text-xs text-slate-500 mt-1">Receive daily summary reports and critical alerts.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-800/20 rounded border border-slate-800">
                  <div>
                    <h4 className="text-sm text-slate-200">SMS Alerts</h4>
                    <p className="text-xs text-slate-500 mt-1">Immediate text messages for HIGH priority threats.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-800/20 rounded border border-slate-800">
                  <div>
                    <h4 className="text-sm text-slate-200">Dark Mode</h4>
                    <p className="text-xs text-slate-500 mt-1">System-wide dark theme appearance.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked disabled />
                    <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500 opacity-50"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
