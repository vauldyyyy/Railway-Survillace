import React, { useState, useEffect, useMemo } from 'react';
import { FileText, Filter, Calendar, MapPin, AlertTriangle, Clock, ChevronDown, ExternalLink } from 'lucide-react';
import SearchInput from '../components/ui/SearchInput';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingSkeleton from '../components/ui/LoadingSkeleton';
import { incidents, incidentTypes, incidentLocations, severityLevels } from '../data/incidents';

/**
 * Incidents — Historical incident log with filters and search.
 */
export default function Incidents() {
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');
  const [expandedRow, setExpandedRow] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(timer);
  }, []);

  // Filter logic
  const filtered = useMemo(() => {
    return incidents.filter(inc => {
      const matchSearch =
        search === '' ||
        inc.type.toLowerCase().includes(search.toLowerCase()) ||
        inc.location.toLowerCase().includes(search.toLowerCase()) ||
        inc.id.toLowerCase().includes(search.toLowerCase()) ||
        inc.description.toLowerCase().includes(search.toLowerCase());
      const matchSeverity = severityFilter === 'all' || inc.severity === severityFilter;
      const matchLocation = locationFilter === 'all' || inc.location === locationFilter;
      return matchSearch && matchSeverity && matchLocation;
    });
  }, [search, severityFilter, locationFilter]);

  const severityCount = {
    critical: incidents.filter(i => i.severity === 'critical').length,
    warning: incidents.filter(i => i.severity === 'warning').length,
    info: incidents.filter(i => i.severity === 'info').length,
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <FileText className="w-6 h-6 text-cyber" />
            Incident History
          </h1>
          <p className="text-sm text-text-secondary mt-1">{incidents.length} total incidents recorded</p>
        </div>
        {/* Severity counts */}
        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-lg glass flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-danger" />
            <span className="text-xs text-text-secondary">Critical: <strong className="text-danger">{severityCount.critical}</strong></span>
          </div>
          <div className="px-3 py-1.5 rounded-lg glass flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-warning" />
            <span className="text-xs text-text-secondary">Warning: <strong className="text-warning">{severityCount.warning}</strong></span>
          </div>
          <div className="px-3 py-1.5 rounded-lg glass flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyber" />
            <span className="text-xs text-text-secondary">Info: <strong className="text-cyber">{severityCount.info}</strong></span>
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="glass-card p-4 flex flex-wrap items-center gap-4">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search incidents..."
          className="flex-1 min-w-[200px]"
        />
        <SelectFilter
          icon={AlertTriangle}
          label="Severity"
          value={severityFilter}
          onChange={setSeverityFilter}
          options={[
            { value: 'all', label: 'All Severities' },
            ...severityLevels.map(s => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1) })),
          ]}
        />
        <SelectFilter
          icon={MapPin}
          label="Location"
          value={locationFilter}
          onChange={setLocationFilter}
          options={[
            { value: 'all', label: 'All Locations' },
            ...incidentLocations.map(l => ({ value: l, label: l })),
          ]}
        />
        <div className="text-xs text-text-muted">
          Showing {filtered.length} of {incidents.length}
        </div>
      </div>

      {/* Incidents Table */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <LoadingSkeleton key={i} lines={1} />
          ))}
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-border-subtle text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
            <span className="col-span-1">ID</span>
            <span className="col-span-2">Type</span>
            <span className="col-span-2">Location</span>
            <span className="col-span-1">Severity</span>
            <span className="col-span-2">Timestamp</span>
            <span className="col-span-1">Camera</span>
            <span className="col-span-1">Response</span>
            <span className="col-span-1">Status</span>
            <span className="col-span-1"></span>
          </div>

          {/* Table rows */}
          <div className="divide-y divide-border-subtle/50">
            {filtered.map((inc) => (
              <React.Fragment key={inc.id}>
                <div
                  className={`grid grid-cols-12 gap-2 px-4 py-3 text-sm hover:bg-bg-hover/50 transition-colors cursor-pointer
                    ${inc.severity === 'critical' ? 'border-l-2 border-l-danger' : 'border-l-2 border-l-transparent'}`}
                  onClick={() => setExpandedRow(expandedRow === inc.id ? null : inc.id)}
                >
                  <span className="col-span-1 text-xs font-mono text-text-muted">{inc.id}</span>
                  <span className="col-span-2 text-text-primary font-medium truncate">{inc.type}</span>
                  <span className="col-span-2 text-text-secondary text-xs truncate flex items-center gap-1">
                    <MapPin className="w-3 h-3 flex-shrink-0" />
                    {inc.location}
                  </span>
                  <span className="col-span-1">
                    <StatusBadge severity={inc.severity} size="sm" />
                  </span>
                  <span className="col-span-2 text-xs text-text-secondary flex items-center gap-1">
                    <Clock className="w-3 h-3 flex-shrink-0" />
                    {new Date(inc.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className="col-span-1 text-xs font-mono text-text-muted">{inc.camera}</span>
                  <span className="col-span-1 text-xs font-mono text-cyber">{inc.responseTime}</span>
                  <span className="col-span-1">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                      inc.status === 'resolved' ? 'bg-success/15 text-success' : 'bg-warning/15 text-warning'
                    }`}>
                      {inc.status.toUpperCase()}
                    </span>
                  </span>
                  <span className="col-span-1 flex justify-end">
                    <ChevronDown className={`w-4 h-4 text-text-muted transition-transform ${expandedRow === inc.id ? 'rotate-180' : ''}`} />
                  </span>
                </div>

                {/* Expanded row */}
                {expandedRow === inc.id && (
                  <div className="px-6 py-4 bg-bg-hover/30 border-l-2 border-l-cyber/30 animate-slide-in-up">
                    <p className="text-sm text-text-secondary">{inc.description}</p>
                    <div className="flex items-center gap-4 mt-3">
                      <span className="text-[11px] text-text-muted">Camera: <strong className="text-text-primary">{inc.camera}</strong></span>
                      <span className="text-[11px] text-text-muted">Response Time: <strong className="text-cyber">{inc.responseTime}</strong></span>
                      <span className="text-[11px] text-text-muted">Status: <strong className={inc.status === 'resolved' ? 'text-success' : 'text-warning'}>{inc.status}</strong></span>
                    </div>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="px-4 py-12 text-center text-text-muted text-sm">
              No incidents match your filters.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SelectFilter({ icon: Icon, label, value, onChange, options }) {
  return (
    <div className="relative">
      <div className="flex items-center gap-1.5 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
        <Icon className="w-3.5 h-3.5 text-text-muted" />
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-8 pr-8 py-2.5 bg-bg-secondary/50 border border-border-subtle rounded-lg
          text-sm text-text-primary appearance-none cursor-pointer
          focus:outline-none focus:border-cyber/40 focus:shadow-glow-cyan
          transition-all duration-200"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <ChevronDown className="w-3.5 h-3.5 text-text-muted absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
    </div>
  );
}
