import React from 'react';
import { Search, Loader2, Sparkles, RotateCcw } from 'lucide-react';

interface QuestionInputProps {
  question: string;
  setQuestion: (q: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  isLoading: boolean;
}

const SAMPLE_QUESTIONS = [
  {
    label: 'Test A (Calculator)',
    query: 'What is 25 multiplied by 4?',
    icon: '🧮',
  },
  {
    label: 'Test B (Web Search & Fetch)',
    query: 'What are the latest developments in AI coding agents?',
    icon: '🌐',
  },
  {
    label: 'Test C (Search + Arithmetic)',
    query: 'Find the height of Mount Everest in meters and calculate what 15% of that height is.',
    icon: '⛰️',
  },
  {
    label: 'Test D (Multi-source Research)',
    query: 'What are the key technical differences between Llama 3.2 and previous Llama models?',
    icon: '🔬',
  },
];

export const QuestionInput: React.FC<QuestionInputProps> = ({
  question,
  setQuestion,
  onSubmit,
  onReset,
  isLoading,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && question.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 shadow-xl shadow-black/20">
      <div className="flex flex-col gap-3">
        <label htmlFor="research-input" className="text-sm font-semibold text-slate-200 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Enter Research Question
          </span>
          <span className="text-xs text-slate-400 font-normal">
            Press <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-300 font-mono">Enter</kbd> to execute
          </span>
        </label>

        <div className="relative">
          <textarea
            id="research-input"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="e.g. What are the latest developments in AI coding agents? Or perform complex math..."
            className="w-full bg-slate-950/90 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg p-3 text-slate-100 placeholder-slate-500 resize-none text-sm leading-relaxed transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-slate-400 mr-1">Quick Demos:</span>
            {SAMPLE_QUESTIONS.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                disabled={isLoading}
                onClick={() => setQuestion(sample.query)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/50 transition-colors disabled:opacity-50"
              >
                <span>{sample.icon}</span>
                <span>{sample.label}</span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              onClick={onReset}
              disabled={isLoading || (!question && !isLoading)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
              title="Reset query and activity"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>

            <button
              type="button"
              onClick={onSubmit}
              disabled={isLoading || !question.trim()}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-indigo-600"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>Researching...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Start Research</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
