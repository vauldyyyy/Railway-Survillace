import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Header } from '../components/Header';
import { Users, Activity, TrendingUp, RefreshCw, WifiOff } from 'lucide-react';
import useSystemStore from '../store/useSystemStore';

const API = 'http://localhost:8001';
const GRID_COLS = 20;
const GRID_ROWS = 20;

// ── Heatmap Canvas Renderer ─────────────────────────────────────────────────

function HeatmapCanvas({ grid }: { grid: number[][] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const cellW = W / GRID_COLS;
    const cellH = H / GRID_ROWS;

    // Find max for normalization
    let maxVal = 0;
    for (const row of grid) for (const v of row) if (v > maxVal) maxVal = v;
    if (maxVal === 0) maxVal = 1;

    ctx.clearRect(0, 0, W, H);

    // Draw grid cells with colour based on density
    for (let r = 0; r < GRID_ROWS; r++) {
      for (let c = 0; c < GRID_COLS; c++) {
        const norm = grid[r]?.[c] ? grid[r][c] / maxVal : 0;

        // Colour: cool-blue → amber → red
        let red = 0, green = 0, blue = 0;
        if (norm < 0.5) {
          // 0→0.5: blue to yellow
          const t = norm / 0.5;
          red   = Math.round(t * 255);
          green = Math.round(t * 180);
          blue  = Math.round((1 - t) * 220 + 6);
        } else {
          // 0.5→1: yellow to red
          const t = (norm - 0.5) / 0.5;
          red   = 255;
          green = Math.round((1 - t) * 180);
          blue  = Math.round(6 * (1 - t));
        }

        const alpha = 0.15 + norm * 0.75;
        ctx.fillStyle = `rgba(${red},${green},${blue},${alpha})`;
        ctx.fillRect(c * cellW, r * cellH, cellW, cellH);

        // Hot glow on high-density cells
        if (norm > 0.7) {
          const grad = ctx.createRadialGradient(
            c * cellW + cellW / 2, r * cellH + cellH / 2, 0,
            c * cellW + cellW / 2, r * cellH + cellH / 2, cellH * 1.5
          );
          grad.addColorStop(0, `rgba(255,${Math.round(green)},0,${norm * 0.5})`);
          grad.addColorStop(1, 'rgba(255,0,0,0)');
          ctx.fillStyle = grad;
          ctx.fillRect(
            (c - 1) * cellW, (r - 1) * cellH,
            cellW * 3, cellH * 3
          );
        }
      }
    }

    // Grid lines
    ctx.strokeStyle = 'rgba(30,41,59,0.5)';
    ctx.lineWidth = 0.5;
    for (let x = 0; x <= GRID_COLS; x++) {
      ctx.beginPath();
      ctx.moveTo(x * cellW, 0);
      ctx.lineTo(x * cellW, H);
      ctx.stroke();
    }
    for (let y = 0; y <= GRID_ROWS; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * cellH);
      ctx.lineTo(W, y * cellH);
      ctx.stroke();
    }

    // Concourse zone outline
    ctx.strokeStyle = 'rgba(6,182,212,0.3)';
    ctx.lineWidth = 1;
    ctx.strokeRect(cellW * 4, cellH * 4, cellW * 12, cellH * 12);
    ctx.fillStyle = 'rgba(6,182,212,0.06)';
    ctx.fillRect(cellW * 4, cellH * 4, cellW * 12, cellH * 12);

    // Labels
    ctx.fillStyle = 'rgba(100,116,139,0.8)';
    ctx.font = '9px monospace';
    ctx.fillText('PLATFORM 1 ▶', cellW * 0.3, cellH * 2);
    ctx.fillText('PLATFORM 2 ▶', cellW * 0.3, cellH * 10);
    ctx.fillText('EXIT ▲', cellW * 16, cellH * 19.2);
    ctx.fillText('ENTRY ▲', cellW * 8, cellH * 19.2);

  }, [grid]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={400}
      className="w-full h-full rounded"
      style={{ imageRendering: 'pixelated' }}
    />
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

export function CrowdAnalytics({ onNavigate }: { onNavigate?: (page: any) => void }) {
  const [grid, setGrid] = useState<number[][]>(Array.from({ length: GRID_ROWS }, () => Array(GRID_COLS).fill(0)));
  const [totalPersons, setTotalPersons] = useState(0);
  const [peakCell, setPeakCell] = useState({ row: 0, col: 0, val: 0 });
  const [backendOk, setBackendOk] = useState(true);
  const [loading, setLoading] = useState(true);
  const globalConfidence = useSystemStore(state => state.globalConfidence);

  const ZONE_LABELS: Record<string, string> = {
    '4-8,4-8':   'Platform 1 North',
    '8-12,4-8':  'Platform 1 South',
    '4-8,12-16': 'Platform 2 North',
    '8-12,12-16':'Concourse Central',
  };

  const fetchHeatmap = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/heatmap`);
      if (!res.ok) throw new Error('heatmap fetch failed');
      const data = await res.json();
      const g: number[][] = data.grid;
      setGrid(g);
      setBackendOk(true);
      setLoading(false);

      // Compute total persons and peak cell
      let total = 0;
      let peak = { row: 0, col: 0, val: 0 };
      for (let r = 0; r < g.length; r++) {
        for (let c = 0; c < (g[r]?.length ?? 0); c++) {
          total += g[r][c];
          if (g[r][c] > peak.val) peak = { row: r, col: c, val: g[r][c] };
        }
      }
      setTotalPersons(Math.round(total));
      setPeakCell(peak);
    } catch {
      setBackendOk(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHeatmap();
    const t = setInterval(fetchHeatmap, 2000);
    return () => clearInterval(t);
  }, [fetchHeatmap]);

  // Determine peak zone label
  const peakZoneLabel = (() => {
    const r = peakCell.row;
    const c = peakCell.col;
    for (const [key, label] of Object.entries(ZONE_LABELS)) {
      const [rRange, cRange] = key.split(',');
      const [r0, r1] = rRange.split('-').map(Number);
      const [c0, c1] = cRange.split('-').map(Number);
      if (r >= r0 && r < r1 && c >= c0 && c < c1) return label;
    }
    return `Grid [${peakCell.row},${peakCell.col}]`;
  })();

  // Density per m² (approx: 1 cell ≈ 2m x 2m = 4m²)
  const densityPerM2 = peakCell.val > 0 ? (peakCell.val / 4).toFixed(1) : '0.0';

  return (
    <div className="flex flex-col h-full">
      <Header
        title="CROWD ANALYTICS"
        subtitle="Live Density Heatmap — YOLO-World Person Detection Feed"
        onNavigate={onNavigate}
      >
        <div className={`flex items-center gap-2 text-[10px] font-mono px-3 py-1 rounded-full border ${
          backendOk
            ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
            : 'border-red-500/40 text-red-400 bg-red-500/10'
        }`}>
          {backendOk
            ? <><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />ML ENGINE LIVE</>
            : <><WifiOff size={10} /> BACKEND OFFLINE</>
          }
        </div>
        <button
          onClick={fetchHeatmap}
          className="p-2 bg-[#151C2C] border border-slate-700 rounded-md text-slate-400 hover:text-cyan-400 transition-colors"
          title="Refresh heatmap"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </Header>

      <div className="p-6 flex-1 overflow-y-auto">

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Persons Detected</span>
              <Users size={16} className="text-cyan-400" />
            </div>
            <div className="text-3xl font-light text-slate-200 font-mono">{totalPersons}</div>
            <div className="text-[10px] text-cyan-500 mt-1 font-mono">Live • YOLO-World Count</div>
          </div>
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Peak Density Zone</span>
              <Activity size={16} className="text-yellow-400" />
            </div>
            <div className="text-base font-bold text-slate-200 mt-1 truncate">{peakZoneLabel}</div>
            <div className="text-xs text-yellow-400 mt-1 font-mono">{densityPerM2} persons/m²</div>
          </div>
          <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Model Confidence</span>
              <TrendingUp size={16} className="text-emerald-400" />
            </div>
            <div className="text-3xl font-light font-mono text-emerald-400">{globalConfidence.toFixed(1)}%</div>
            <div className="text-[10px] text-slate-500 mt-1 font-mono">Rolling Average (50-frame)</div>
          </div>
        </div>

        {/* Heatmap Panel */}
        <div className="bg-[#151C2C] border border-slate-800 rounded-lg p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
                Live Density Heatmap — Station Concourse
              </h3>
              <p className="text-[10px] text-slate-500 font-mono mt-1">
                20×20 Grid • 2500ms refresh • YOLO-World Centroid Mapping
              </p>
            </div>
            <div className="flex gap-4 text-[10px] font-mono text-slate-400">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-cyan-500/80 border border-cyan-400/40" />
                LOW
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-amber-500/80 border border-amber-400/40" />
                MEDIUM
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-red-500/80 border border-red-400/40" />
                HIGH
              </div>
            </div>
          </div>

          <div className="relative rounded border border-slate-800 overflow-hidden bg-[#060a12]" style={{ minHeight: '340px' }}>
            {!backendOk && (
              <div className="absolute inset-0 flex items-center justify-center z-10">
                <div className="text-slate-600 font-mono text-xs text-center">
                  <WifiOff size={20} className="mx-auto mb-2 opacity-40" />
                  BACKEND OFFLINE — Start backend to see live density
                </div>
              </div>
            )}
            <HeatmapCanvas grid={grid} />
            {/* Scan line effect */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)',
              }}
            />
            {/* Corner labels */}
            <div className="absolute top-2 left-2 text-[9px] font-mono text-slate-600">N ↑</div>
            <div className="absolute bottom-2 right-2 text-[9px] font-mono text-slate-600">
              {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
