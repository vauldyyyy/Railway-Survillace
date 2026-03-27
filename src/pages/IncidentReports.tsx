import React, { useState, useMemo } from 'react';
import { Header } from '../components/Header';
import { FileText, Download, Filter, Search, ChevronDown } from 'lucide-react';

const REPORTS = [
  { id: 'REP-2026-0142', date: '2026-01-24 10:15', type: 'Medical Emergency', loc: 'Platform 1', status: 'RESOLVED' },
  { id: 'REP-2026-0141', date: '2026-01-23 22:40', type: 'Trespassing', loc: 'South Yard', status: 'RESOLVED' },
  { id: 'REP-2026-0140', date: '2026-01-23 18:20', type: 'Suspicious Package', loc: 'Main Concourse', status: 'FALSE ALARM' },
  { id: 'REP-2026-0139', date: '2026-01-22 09:05', type: 'Crowd Crush Warning', loc: 'Gate 4', status: 'RESOLVED' },
  { id: 'REP-2026-0138', date: '2026-01-21 14:30', type: 'Unauthorized Access', loc: 'Control Room B', status: 'UNDER INVESTIGATION' },
  { id: 'REP-2026-0137', date: '2026-01-20 11:15', type: 'Fire Alarm', loc: 'Food Court', status: 'FALSE ALARM' },
  { id: 'REP-2026-0136', date: '2026-01-19 16:45', type: 'Theft Report', loc: 'Waiting Lounge', status: 'UNDER INVESTIGATION' },
];

export function IncidentReports({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  const filteredReports = useMemo(() => {
    return REPORTS.filter(report => {
      const matchesSearch = 
        report.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        report.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        report.loc.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesFilter = statusFilter === 'ALL' || report.status === statusFilter;
      
      return matchesSearch && matchesFilter;
    });
  }, [searchQuery, statusFilter]);

  return (
    <div className="flex flex-col h-full">
      <Header 
        title="INCIDENT REPORTS" 
        subtitle="Historical Logs & Documentation"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search reports..." 
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
              <Filter size={14} /> {statusFilter === 'ALL' ? 'FILTER' : statusFilter} <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'RESOLVED', 'FALSE ALARM', 'UNDER INVESTIGATION'].map(status => (
                  <button
                    key={status}
                    onClick={() => { setStatusFilter(status); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-800 text-slate-300"
                  >
                    {status === 'ALL' ? 'All Statuses' : status}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button className="flex items-center gap-2 bg-cyan-950/30 border border-cyan-500/30 rounded-md px-3 py-1.5 text-xs text-cyan-400 hover:bg-cyan-950/50">
            <Download size={14} /> EXPORT CSV
          </button>
        </div>
      </Header>
      <div className="p-6 flex-1 overflow-y-auto">
        <div className="bg-[#151C2C] border border-slate-800 rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/50 text-slate-400 font-mono text-xs">
              <tr>
                <th className="p-4 font-medium">REPORT ID</th>
                <th className="p-4 font-medium">DATE/TIME</th>
                <th className="p-4 font-medium">TYPE</th>
                <th className="p-4 font-medium">LOCATION</th>
                <th className="p-4 font-medium">STATUS</th>
                <th className="p-4 font-medium">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-slate-300">
              {filteredReports.map((row, i) => (
                <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                  <td className="p-4 font-mono text-cyan-400">{row.id}</td>
                  <td className="p-4 font-mono text-slate-400">{row.date}</td>
                  <td className="p-4">{row.type}</td>
                  <td className="p-4 text-slate-400">{row.loc}</td>
                  <td className="p-4">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                      row.status === 'RESOLVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      row.status === 'FALSE ALARM' ? 'bg-slate-500/10 text-slate-400 border border-slate-500/20' :
                      'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <button className="text-slate-400 hover:text-cyan-400 transition-colors">
                      <FileText size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {filteredReports.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500 font-mono">
                    NO REPORTS MATCHING CRITERIA
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
