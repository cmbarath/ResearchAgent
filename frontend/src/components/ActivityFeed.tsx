import React, { useRef, useEffect, useState } from 'react';
import {
  Activity,
  Wrench,
  CheckCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Globe,
  Calculator,
  FileText,
  Clock,
  Sparkles,
} from 'lucide-react';
import type { AgentEvent } from '../types/agent';

interface ActivityFeedProps {
  events: AgentEvent[];
  isLoading: boolean;
  currentStep: number;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  events,
  isLoading,
  currentStep,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedItems, setExpandedItems] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const toggleExpand = (index: number) => {
    setExpandedItems((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const getToolIcon = (toolName?: string) => {
    switch (toolName) {
      case 'web_search':
        return <Globe className="w-3.5 h-3.5 text-sky-400" />;
      case 'fetch_page':
        return <FileText className="w-3.5 h-3.5 text-emerald-400" />;
      case 'calculator':
        return <Calculator className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Wrench className="w-3.5 h-3.5 text-indigo-400" />;
    }
  };

  const getEventBadge = (event: AgentEvent) => {
    switch (event.type) {
      case 'step':
        return {
          bg: 'bg-indigo-950/60 border-indigo-800/40 text-indigo-300',
          label: 'Reasoning Action',
          icon: <Activity className="w-3.5 h-3.5 text-indigo-400" />,
        };
      case 'tool_call':
        return {
          bg: 'bg-amber-950/50 border-amber-800/40 text-amber-300',
          label: `Tool: ${event.tool}`,
          icon: getToolIcon(event.tool),
        };
      case 'tool_result':
        return {
          bg: 'bg-emerald-950/50 border-emerald-800/40 text-emerald-300',
          label: `Result: ${event.tool}`,
          icon: <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />,
        };
      case 'error':
        return {
          bg: 'bg-rose-950/50 border-rose-800/40 text-rose-300',
          label: 'Warning / Error',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />,
        };
      case 'final':
      case 'done':
        return {
          bg: 'bg-violet-950/60 border-violet-800/40 text-violet-300',
          label: 'Synthesis Complete',
          icon: <Sparkles className="w-3.5 h-3.5 text-violet-400" />,
        };
      default:
        return {
          bg: 'bg-slate-800 border-slate-700 text-slate-300',
          label: 'Event',
          icon: <Activity className="w-3.5 h-3.5" />,
        };
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col h-[600px] shadow-xl shadow-black/20 overflow-hidden">
      {/* Header bar */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-200">Live Agent Activity</h2>
          {events.length > 0 && (
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              {events.length} events
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {isLoading && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-950/80 border border-indigo-700/50 text-indigo-300 text-xs">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
              <span>Step {currentStep || 1} / 8</span>
            </div>
          )}

          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-indigo-500 focus:ring-0 w-3.5 h-3.5"
            />
            Auto-scroll
          </label>
        </div>
      </div>

      {/* Progress tracker bar */}
      <div className="px-4 py-2 bg-slate-950/60 border-b border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
        <div className="flex items-center gap-1">
          <span>ReAct Iteration Budget:</span>
          <span className="text-slate-200 font-semibold">{currentStep || 0}</span>
          <span>/</span>
          <span>8 max</span>
        </div>
        <div className="w-32 bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, ((currentStep || 0) / 8) * 100)}%` }}
          />
        </div>
      </div>

      {/* Scrollable event list */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 font-sans text-xs"
      >
        {events.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 p-6">
            <Clock className="w-8 h-8 mb-2 text-slate-600 stroke-[1.5]" />
            <p className="font-medium text-slate-400">Waiting for research inquiry...</p>
            <p className="text-xs text-slate-600 mt-1 max-w-sm">
              Enter a query above to observe the LLM ReAct loop: reasoning, tool calls, and evidence collection.
            </p>
          </div>
        ) : (
          events.map((event, idx) => {
            const badge = getEventBadge(event);
            const isExpanded = !!expandedItems[idx];
            const hasRawData = !!(event.arguments || event.raw_result || event.error);

            return (
              <div
                key={idx}
                className="group border border-slate-800 hover:border-slate-700/80 bg-slate-950/60 rounded-lg p-3 transition-all duration-150"
              >
                {/* Event header row */}
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border ${badge.bg}`}
                    >
                      {badge.icon}
                      <span>{badge.label}</span>
                    </span>

                    {event.step > 0 && (
                      <span className="text-[11px] font-mono text-slate-500">
                        Step {event.step}/8
                      </span>
                    )}
                  </div>

                  {hasRawData && (
                    <button
                      type="button"
                      onClick={() => toggleExpand(idx)}
                      className="text-slate-500 hover:text-slate-300 flex items-center gap-1 text-[11px] font-mono transition-colors"
                    >
                      {isExpanded ? (
                        <>
                          Hide JSON <ChevronDown className="w-3 h-3" />
                        </>
                      ) : (
                        <>
                          Details <ChevronRight className="w-3 h-3" />
                        </>
                      )}
                    </button>
                  )}
                </div>

                {/* Event primary message */}
                <div className="text-slate-200 text-xs leading-relaxed font-sans pl-1">
                  {event.message || event.result_summary || 'Agent event received.'}
                </div>

                {/* Arguments Preview for Tool Call */}
                {event.type === 'tool_call' && event.arguments && (
                  <div className="mt-2 pl-2 border-l-2 border-amber-500/40 bg-slate-900/60 p-2 rounded text-slate-300 font-mono text-[11px] space-y-1">
                    {Object.entries(event.arguments).map(([key, val]) => (
                      <div key={key} className="truncate">
                        <span className="text-amber-400">{key}:</span>{' '}
                        <span className="text-slate-200 font-sans">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tool Result Summary Preview */}
                {event.type === 'tool_result' && (
                  <div className="mt-2 pl-2 border-l-2 border-emerald-500/40 bg-slate-900/60 p-2 rounded text-slate-300 text-[11px]">
                    <div className="font-medium text-emerald-300">
                      {event.result_summary}
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {event.type === 'error' && (
                  <div className="mt-2 p-2 rounded bg-rose-950/40 border border-rose-800/40 text-rose-300 text-[11px]">
                    {event.error || event.message}
                  </div>
                )}

                {/* Collapsible raw json inspector */}
                {isExpanded && hasRawData && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800/80">
                    <pre className="p-2.5 bg-slate-900/95 border border-slate-800 rounded font-mono text-[10px] text-slate-400 overflow-x-auto max-h-48 leading-snug">
                      {JSON.stringify(
                        {
                          arguments: event.arguments,
                          raw_result: event.raw_result,
                          error: event.error,
                        },
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
