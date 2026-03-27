import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { Bell, Info, AlertCircle, Search, Filter, ChevronDown } from 'lucide-react';

const NOTIFICATIONS = [
  {
    id: 1,
    type: 'WARNING',
    icon: <AlertCircle size={16} className="text-yellow-400" />,
    title: "High GPU Memory Usage",
    time: "10 mins ago",
    desc: "AI-INFERENCE-03 is operating at 95% VRAM capacity. Consider scaling up the cluster.",
    unread: true
  },
  {
    id: 2,
    type: 'INFO',
    icon: <Info size={16} className="text-cyan-400" />,
    title: "System Update Available",
    time: "1 hour ago",
    desc: "OSNET-V4.1 weights are available for download. Improves Re-ID accuracy by 2.4%.",
    unread: true
  },
  {
    id: 3,
    type: 'LOG',
    icon: <Bell size={16} className="text-slate-400" />,
    title: "Shift Change Completed",
    time: "4 hours ago",
    desc: "Operator RPF_GOA_01 logged in. Previous session terminated securely.",
    unread: false
  }
];

export function Notifications({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const filteredNotifications = useMemo(() => {
    return NOTIFICATIONS.filter(notif => {
      const matchesSearch = 
        notif.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        notif.desc.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesFilter = typeFilter === 'ALL' || 
                            (typeFilter === 'UNREAD' ? notif.unread : notif.type === typeFilter);
      
      return matchesSearch && matchesFilter;
    });
  }, [searchQuery, typeFilter]);

  return (
    <div className="flex flex-col h-full">
      <Header 
        title="NOTIFICATIONS" 
        subtitle="System Alerts & Logs"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search notifications..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#151C2C] border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 w-64"
            />
          </div>
          <div className="relative">
            <button 
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className="flex items-center gap-2 bg-[#151C2C] border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
            >
              <Filter size={14} /> {typeFilter === 'ALL' ? 'FILTER' : typeFilter} <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'UNREAD', 'WARNING', 'INFO', 'LOG'].map(type => (
                  <button
                    key={type}
                    onClick={() => { setTypeFilter(type); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-800 text-slate-300"
                  >
                    {type === 'ALL' ? 'All Notifications' : type}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </Header>
      <div className="p-6 flex-1 overflow-y-auto max-w-4xl">
        <div className="space-y-3">
          {filteredNotifications.map(notif => (
            <NotificationItem key={notif.id} {...notif} />
          ))}
          {filteredNotifications.length === 0 && (
            <div className="text-center text-slate-500 font-mono py-12 border border-dashed border-slate-800 rounded-lg">
              NO NOTIFICATIONS MATCHING CRITERIA
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function NotificationItem({ icon, title, time, desc, unread }: any) {
  return (
    <div className={`p-4 rounded-lg border ${unread ? 'bg-[#151C2C] border-cyan-500/30' : 'bg-[#151C2C]/50 border-slate-800'} flex gap-4`}>
      <div className="mt-1">{icon}</div>
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h4 className={`text-sm font-semibold ${unread ? 'text-slate-200' : 'text-slate-400'}`}>{title}</h4>
          <span className="text-[10px] text-slate-500 font-mono">{time}</span>
        </div>
        <p className="text-sm text-slate-400">{desc}</p>
      </div>
    </div>
  );
}
