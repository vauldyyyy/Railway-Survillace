import React from 'react';
import useSystemStore from '../store/useSystemStore';
import type { ModelMetrics } from '../store/useSystemStore';

function MetricCard({ model, accent }: { model: ModelMetrics; accent: string }) {
  const fpsColor = model.fps > 25 ? 'text-emerald-400' : model.fps > 15 ? 'text-yellow-400' : 'text-red-400';
  const gpuColor = model.gpu_util_pct > 80 ? 'text-red-400' : model.gpu_util_pct > 50 ? 'text-yellow-400' : 'text-emerald-400';

  return (
    <div className={`flex items-center gap-3 bg-[#0B0F19] border border-slate-800/50 rounded px-3 py-2 min-w-[200px]`}>
      <div className={`w-1.5 h-8 rounded-full ${accent}`}></div>
      <div className="flex-1 min-w-0">
        <div className="text-[9px] text-slate-500 uppercase tracking-wider truncate font-mono">{model.name}</div>
        <div className="flex items-baseline gap-3 mt-0.5">
          <div className="flex items-baseline gap-1">
            <span className={`text-sm font-bold font-mono ${fpsColor}`}>{model.fps.toFixed(0)}</span>
            <span className="text-[8px] text-slate-600">FPS</span>
          </div>
          {model.gpu_util_pct > 0 && (
            <div className="flex items-baseline gap-1">
              <span className={`text-xs font-mono ${gpuColor}`}>{model.gpu_util_pct.toFixed(0)}%</span>
              <span className="text-[8px] text-slate-600">GPU</span>
            </div>
          )}
          <div className="flex items-baseline gap-1">
            <span className="text-xs font-mono text-slate-400">{model.latency_ms.toFixed(0)}</span>
            <span className="text-[8px] text-slate-600">ms</span>
          </div>
        </div>
      </div>
      <div className={`w-2 h-2 rounded-full ${model.status === 'active' ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]' : model.status === 'error' ? 'bg-red-500 animate-pulse' : 'bg-slate-600'}`}></div>
    </div>
  );
}

export function ModelPerformanceStrip() {
  const metrics = useSystemStore((s) => s.modelMetrics);

  const accents = {
    coco: 'bg-cyan-500',
    railfod: 'bg-purple-500',
    uav: 'bg-amber-500',
    lstm: 'bg-emerald-500',
    tracker: 'bg-blue-500',
  };

  return (
    <div className="border-t border-slate-800/60 bg-[#05080F]/80 backdrop-blur-sm px-6 py-2.5">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 mr-3 shrink-0">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-mono">MODEL INFERENCE</span>
        </div>
        <div className="flex gap-2 overflow-x-auto scrollbar-none flex-1">
          {Object.entries(metrics).map(([key, model]) => (
            <MetricCard key={key} model={model} accent={accents[key as keyof typeof accents]} />
          ))}
        </div>
      </div>
    </div>
  );
}
