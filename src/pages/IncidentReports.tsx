import React, { useState, useMemo, useEffect } from 'react';
import { Header } from '../components/Header';
import { FileText, Filter, Search, ChevronDown, Download } from 'lucide-react';
import useAlertStore, { AlertStatus, Alert } from '../store/alertStore';
import { format } from 'date-fns';
import { jsPDF } from 'jspdf';

export function IncidentReports({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [searchQuery,    setSearchQuery]    = useState('');
  const [statusFilter,   setStatusFilter]   = useState('ALL');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  // ΓöÇΓöÇ Same store as ThreatAlerts ΓÇö perfectly synced ΓöÇΓöÇ
  const alerts       = useAlertStore(s => s.alerts);
  const startPolling = useAlertStore(s => s.startPolling);

  // Start polling on mount (safe to call multiple times ΓÇö store deduplicates)
  useEffect(() => {
    const stop = startPolling();
    return stop;
  }, [startPolling]);

  // ΓöÇΓöÇ PDF Generation Logic ΓöÇΓöÇ
  const generateIncidentReport = async (incident: Alert) => {
    try {
      const doc = new jsPDF();
      
      // 1. Watermark
      doc.setTextColor(240, 240, 240);
      doc.setFontSize(55);
      doc.setFont('helvetica', 'bold');
      doc.text('KONKAN RAILWAY', 25, 180, { angle: 45 });

      // 2. Header
      doc.setTextColor(30, 30, 30);
      doc.setFontSize(16);
      doc.text('RAILGUARD AUTOMATED SECURITY REPORT', 20, 20);
      doc.setLineWidth(0.5);
      doc.line(20, 25, 190, 25);

      // 3. Extract Time/Date
      let rDate = 'Unknown Date';
      let rTime = 'Unknown Time';
      try {
        const d = new Date(incident.timestamp);
        rDate = format(d, 'yyyy-MM-dd');
        rTime = format(d, 'HH:mm:ss');
      } catch {}

      // 4. Body Text
      doc.setFontSize(11);
      doc.setFont('helvetica', 'normal');
      doc.text(`1. Date and Time: ${rDate} | ${rTime}`, 20, 40);
      doc.text(`2. Camera Source: ${incident.location}`, 20, 50);
      doc.text(`3. Incident Summary:`, 20, 60);

      const summaryText = `A ${incident.severity} priority "${incident.type.replace(/_/g, ' ')}" was automatically detected by the RailGuard AI on ${incident.location} on ${rDate} at ${rTime}.`;
      const splitSummary = doc.splitTextToSize(summaryText, 170);
      doc.text(splitSummary, 20, 70);

      let vOffset = 70 + (splitSummary.length * 8);

      // 5. Embed Alert Image
      // Only attempt to load if it's not the generic SVG placeholder
      if (incident.imageUrl && !incident.imageUrl.startsWith('data:image/svg')) {
        const loadImg = new Promise<HTMLImageElement>((resolve, reject) => {
          const img = new Image();
          img.crossOrigin = 'anonymous';
          img.onload = () => resolve(img);
          img.onerror = reject;
          img.src = incident.imageUrl;
        });

        try {
          const imgElem = await loadImg;
          const maxWidth = 120;
          const ratio = imgElem.width / imgElem.height;
          const height = maxWidth / ratio;
          
          doc.text(`4. Incident Snapshot:`, 20, vOffset + 5);
          doc.addImage(imgElem, 'JPEG', 20, vOffset + 12, maxWidth, height);
          vOffset += 12 + height;
        } catch {
          doc.setTextColor(150, 150, 150);
          doc.text(`4. Incident Snapshot: [Image failed to load]`, 20, vOffset + 5);
          doc.setTextColor(30, 30, 30);
        }
      } else {
        doc.setTextColor(150, 150, 150);
        doc.text(`4. Incident Snapshot: [Generic Placeholder]`, 20, vOffset + 5);
        doc.setTextColor(30, 30, 30);
      }

      // 6. Footer
      doc.setLineWidth(0.5);
      doc.line(20, 280, 190, 280);
      doc.setFontSize(10);
      doc.setFont('helvetica', 'italic');
      doc.text('Issued by: Platform Security Officer', 20, 288);

      // 7. Save to disk natively
      doc.save(`RailGuard_Report_${incident.id}.pdf`);
    } catch (e) {
      console.error('PDF Generation failed:', e);
      alert('Failed to generate PDF report. Check console logs.');
    }
  };

  // ΓöÇΓöÇ Filtered list ΓöÇΓöÇ
  const filteredReports = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return alerts.filter(r => {
      const matchSearch =
        r.id.toLowerCase().includes(q) ||
        r.type.toLowerCase().includes(q) ||
        r.location.toLowerCase().includes(q);
      const matchFilter =
        statusFilter === 'ALL' || r.status === statusFilter;
      return matchSearch && matchFilter;
    });
  }, [searchQuery, statusFilter, alerts]);

  // ΓöÇΓöÇ Summary counts for header badge ΓöÇΓöÇ
  const activeCount   = useMemo(() => alerts.filter(a => a.status === 'ACTIVE').length,   [alerts]);
  const resolvedCount = useMemo(() => alerts.filter(a => a.status === 'RESOLVED').length, [alerts]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="INCIDENT REPORTS"
        subtitle="Historical Logs & Documentation"
        onNavigate={onNavigate}
      >
        <div className="flex gap-4 items-center">
          {/* Summary pill */}
          <div className="text-[10px] font-mono text-slate-500 bg-[#151C2C] border border-slate-700 rounded px-3 py-1.5">
            <span className="text-red-400">{activeCount} ACTIVE</span>
            <span className="mx-2 text-slate-700">|</span>
            <span className="text-emerald-400">{resolvedCount} RESOLVED</span>
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search by ID, type, location..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="bg-[#151C2C] border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 w-64"
            />
          </div>

          {/* Filter */}
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(v => !v)}
              className="flex items-center gap-2 bg-[#151C2C] border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
            >
              <Filter size={14} />
              {statusFilter === 'ALL' ? 'FILTER' : statusFilter.replace('_', ' ')}
              <ChevronDown size={12} />
            </button>
            {showFilterMenu && (
              <div className="absolute top-full right-0 mt-1 w-48 bg-[#151C2C] border border-slate-700 rounded-md shadow-xl z-50 py-1">
                {['ALL', 'ACTIVE', 'RESOLVED', 'FALSE_ALARM'].map(s => (
                  <button
                    key={s}
                    onClick={() => { setStatusFilter(s); setShowFilterMenu(false); }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-800 text-slate-300"
                  >
                    {s === 'ALL' ? 'All Statuses' : s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            )}
          </div>
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
                <th className="p-4 font-medium">SEVERITY</th>
                <th className="p-4 font-medium">STATUS</th>
                <th className="p-4 font-medium">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-slate-300">
              {filteredReports.map(row => (
                <tr key={row.id} className="hover:bg-slate-800/30 transition-colors">

                  {/* ID */}
                  <td className="p-4 font-mono text-cyan-400 text-xs">{row.id}</td>

                  {/* Timestamp */}
                  <td className="p-4 font-mono text-slate-400 text-xs">
                    {(() => {
                      try {
                        return format(new Date(row.timestamp), 'yyyy-MM-dd HH:mm:ss');
                      } catch {
                        return 'ΓÇö';
                      }
                    })()}
                  </td>

                  {/* Type */}
                  <td className="p-4 text-xs font-mono text-slate-200">
                    {row.type.replace(/_/g, ' ')}
                  </td>

                  {/* Location */}
                  <td className="p-4 text-slate-400 text-xs">{row.location}</td>

                  {/* Severity */}
                  <td className="p-4">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                      row.severity === 'CRITICAL' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                      row.severity === 'HIGH'     ? 'bg-orange-500/10 text-orange-400 border border-orange-500/20' :
                      row.severity === 'WARNING'  ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                                                    'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {row.severity}
                    </span>
                  </td>

                  {/* Status ΓÇö reflects real-time changes from ThreatAlerts page */}
                  <td className="p-4">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                      row.status === 'RESOLVED'    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      row.status === 'FALSE_ALARM' ? 'bg-slate-500/10 text-slate-400 border border-slate-500/20' :
                                                     'bg-red-500/10 text-red-500 border border-red-500/20'
                    }`}>
                      {row.status.replace('_', ' ')}
                    </span>
                  </td>

                  {/* Action */}
                  <td className="p-4">
                    <button
                      onClick={() => generateIncidentReport(row)}
                      className="flex items-center gap-1.5 bg-slate-800 hover:bg-cyan-500/20 text-slate-300 hover:text-cyan-400 border border-slate-700 hover:border-cyan-500/40 px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider transition-colors shadow-sm"
                      title={`Download PDF Report for ${row.id}`}
                    >
                      <Download size={14} /> DOWNLOAD
                    </button>
                  </td>
                </tr>
              ))}

              {filteredReports.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500 font-mono text-xs">
                    {alerts.length === 0
                      ? 'NO INCIDENTS YET ΓÇö Backend alerts will appear here'
                      : 'NO REPORTS MATCHING CRITERIA'
                    }
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer summary */}
        {alerts.length > 0 && (
          <div className="mt-4 flex items-center gap-6 text-[10px] font-mono text-slate-600">
            <span>TOTAL INCIDENTS: {alerts.length}</span>
            <span className="text-red-500/70">ACTIVE: {activeCount}</span>
            <span className="text-emerald-500/70">RESOLVED: {resolvedCount}</span>
            <span className="text-slate-500/70">
              FALSE ALARMS: {alerts.filter(a => a.status === 'FALSE_ALARM').length}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
