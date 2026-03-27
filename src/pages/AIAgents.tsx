import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { Cpu, Network, Database, Search, Filter, ChevronDown } from 'lucide-react';

const AGENTS = [
  {
    name: "Vision Node Alpha",
    type: "Object Detection (YOLOv9)",
    status: "ACTIVE",
    load: "84%",
    tasks: ['Weapon Detection', 'Unattended Baggage'],
    icon: <Cpu size={20} className="text-cyan-400" />,
    category: 'Vision'
  },
  {
    name: "Behavioral Engine",
    type: "LSTM Sequence Analysis",
    status: "ACTIVE",
    load: "62%",
    tasks: ['Loitering Detection', 'Aggression Scoring'],
    icon: <Network size={20} className="text-purple-400" />,
    category: 'Behavior'
  },
  {
    name: "Re-ID Cluster",
    type: "OSNET Embeddings",
    status: "HIGH LOAD",
    load: "95%",
    tasks: ['Cross-camera Tracking', 'Feature Extraction'],
    icon: <Database size={20} className="text-yellow-400" />,
    warning: true,
    category: 'Tracking'
  },
  {
    name: "Crowd Density Analyzer",
    type: "CNN Density Map",
    status: "ACTIVE",
    load: "45%",
    tasks: ['Occupancy Counting', 'Flow Rate Estimation'],
    icon: <Users size={20} className="text-emerald-400" />,
    category: 'Vision'
  },
  {
    name: "Anomaly Detection Core",
    type: "Autoencoder",
    status: "IDLE",
    load: "12%",
    tasks: ['Unusual Pattern Detection'],
    icon: <Cpu size={20} className="text-slate-400" />,
    category: 'Behavior'
  }
];

// Need to import Users for the new agent
import { Users } from 'lucide-react';

export function AIAgents({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const filteredAgents = useMemo(() => {
    return AGENTS.filter(agent => {
      const matchesSearch = 
        agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.tasks.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesFilter = categoryFilter === 'ALL' || agent.category === categoryFilter;
      
      return matchesSearch && matchesFilter;
    });
  }, [searchQuery, categoryFilter]);

  return (
    <div className="flex flex-col h-full">
      <Header 
        title="AI AGENTS" 
        subtitle="Autonomous Security & Inference Nodes"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search agents or tasks..." 
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
              <Filter size={14} /> {categoryFilter === 'ALL' ? 'FILTER' : categoryFilter} <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'Vision', 'Behavior', 'Tracking'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => { setCategoryFilter(cat); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-800 text-slate-300"
                  >
                    {cat === 'ALL' ? 'All Categories' : cat}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </Header>
      <div className="p-6 flex-1 overflow-y-auto">
        <div className="grid grid-cols-3 gap-6">
          {filteredAgents.map((agent, i) => (
            <AgentCard key={i} {...agent} />
          ))}
          {filteredAgents.length === 0 && (
            <div className="col-span-full flex items-center justify-center text-slate-500 font-mono py-12">
              NO AI AGENTS MATCHING CRITERIA
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AgentCard({ name, type, status, load, tasks, icon, warning }: any) {
  return (
    <div className={`bg-[#151C2C] border ${warning ? 'border-yellow-500/50' : 'border-slate-800'} rounded-lg p-5`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-800 rounded-md">
            {icon}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-200">{name}</h3>
            <div className="text-xs text-slate-500 font-mono">{type}</div>
          </div>
        </div>
      </div>
      
      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">System Load</span>
            <span className={warning ? 'text-yellow-400 font-mono' : 'text-cyan-400 font-mono'}>{load}</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div className={`h-full ${warning ? 'bg-yellow-500' : 'bg-cyan-500'}`} style={{ width: load }}></div>
          </div>
        </div>
        
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 block">Active Tasks</span>
          <div className="flex flex-wrap gap-2">
            {tasks.map((task: string, i: number) => (
              <span key={i} className="text-[10px] bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-700">
                {task}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
