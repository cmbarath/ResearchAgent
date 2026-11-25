import React from 'react';
import {
  BookOpen,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  FileCheck2,
  Coins,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { AgentEvent } from '../types/agent';

interface FinalAnswerProps {
  finalEvent: AgentEvent | null;
  isLoading: boolean;
}

export const FinalAnswer: React.FC<FinalAnswerProps> = ({
  finalEvent,
  isLoading,
}) => {
  if (!finalEvent && !isLoading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl h-[600px] flex flex-col items-center justify-center text-center p-8 shadow-xl shadow-black/20 text-slate-500">
        <BookOpen className="w-10 h-10 mb-3 text-slate-600 stroke-[1.5]" />
        <h3 className="text-base font-semibold text-slate-300">Final Research Output</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm">
          The synthesized final research answer and verified citations will be compiled here once the ReAct agent finishes its investigation.
        </p>
      </div>
    );
  }

  if (isLoading && !finalEvent) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl h-[600px] flex flex-col items-center justify-center text-center p-8 shadow-xl shadow-black/20">
        <div className="relative mb-4">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
          <Sparkles className="w-5 h-5 text-indigo-400 absolute inset-0 m-auto" />
        </div>
        <h3 className="text-base font-semibold text-slate-200">Conducting Investigation...</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-sm">
          The agent is actively searching the web, fetching authoritative pages, and evaluating evidence. Watch the Live Activity panel for step-by-step progress.
        </p>
      </div>
    );
  }

  const citations = finalEvent?.citations || [];
  const fetchedUrls = finalEvent?.fetched_urls || [];
  const tokenUsage = finalEvent?.token_usage;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col h-[600px] shadow-xl shadow-black/20 overflow-hidden">
      {/* Top Header */}
      <div className="px-5 py-3 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold text-slate-100">Research Report</h2>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            <CheckCircle2 className="w-3 h-3" />
            Verified Complete
          </span>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="px-5 py-2.5 bg-slate-950/70 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span>Steps:</span>
            <span className="font-semibold text-slate-200 font-mono">{finalEvent?.step || 0}</span>
          </div>

          <div className="flex items-center gap-1.5">
            <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Fetched Pages:</span>
            <span className="font-semibold text-emerald-300 font-mono">{fetchedUrls.length}</span>
          </div>

          {tokenUsage && (
            <div className="flex items-center gap-1.5">
              <Coins className="w-3.5 h-3.5 text-amber-400" />
              <span>Token Usage:</span>
              <span className="font-semibold text-slate-200 font-mono">{tokenUsage.total_tokens}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1 text-[11px] text-slate-500">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>Strict Citation Policy Enforced</span>
        </div>
      </div>

      {/* Scrollable Answer Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 text-sm text-slate-200 leading-relaxed font-sans">
        {/* Final Synthesized Text */}
        <div className="whitespace-pre-wrap selection:bg-indigo-500/30 font-sans text-slate-200 leading-relaxed space-y-3">
          {finalEvent?.final_answer || 'No answer generated.'}
        </div>

        {/* Verified Citations Panel */}
        {citations.length > 0 && (
          <div className="pt-4 border-t border-slate-800/80">
            <div className="flex items-center gap-2 mb-2.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Strictly Verified Sources ({citations.length})
              </h4>
            </div>
            <p className="text-[11px] text-slate-400 mb-2">
              Only URLs successfully retrieved via <code className="text-indigo-400">fetch_page</code> are eligible for citation:
            </p>
            <ul className="space-y-1.5">
              {citations.map((url, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs bg-slate-950/80 border border-slate-800/90 rounded-lg p-2 hover:border-slate-700 transition-colors"
                >
                  <span className="font-mono text-emerald-400 font-bold shrink-0">[{i + 1}]</span>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 break-all flex items-center gap-1"
                  >
                    <span>{url}</span>
                    <ExternalLink className="w-3 h-3 inline-block shrink-0" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Successfully Fetched URLs Drawer (if distinct or all fetched pages) */}
        {fetchedUrls.length > 0 && (
          <div className="pt-3 border-t border-slate-800/60">
            <div className="text-[11px] text-slate-500 flex items-center justify-between">
              <span>All Webpages Retrieved by Agent:</span>
              <span className="font-mono">{fetchedUrls.length} pages</span>
            </div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {fetchedUrls.map((fUrl, idx) => {
                let domain = fUrl;
                try {
                  domain = new URL(fUrl).hostname;
                } catch {}
                return (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                    title={fUrl}
                  >
                    <FileCheck2 className="w-2.5 h-2.5 text-emerald-400" />
                    {domain}
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
