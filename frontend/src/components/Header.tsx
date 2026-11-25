import React from 'react';
import { Cpu, Server, CheckCircle2, AlertCircle, ShieldCheck } from 'lucide-react';
import type { HealthStatus } from '../types/agent';

interface HeaderProps {
  health: HealthStatus | null;
}

export const Header: React.FC<HeaderProps> = ({ health }) => {
  const isHealthy = health?.status === 'ok';

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-gradient-to-tr from-indigo-600 to-violet-500 rounded-lg shadow-lg shadow-indigo-500/20 text-white">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Research Agent
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Custom ReAct Agent
                </span>
              </h1>
              <p className="text-xs text-slate-400 font-medium">
                Custom ReAct Loop • Local Llama • Live Tool Execution
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span>Ollama:</span>
            <span className="font-mono text-slate-100">{health?.ollama_model || 'llama3.2:latest'}</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Max Steps:</span>
            <span className="font-mono text-emerald-400 font-semibold">8</span>
          </div>

          <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border ${
            isHealthy 
              ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50' 
              : 'bg-amber-950/40 text-amber-400 border-amber-800/50'
          }`}>
            {isHealthy ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="font-medium">Ollama Ready</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5" />
                <span className="font-medium">Connecting...</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
