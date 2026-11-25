import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { QuestionInput } from './components/QuestionInput';
import { ActivityFeed } from './components/ActivityFeed';
import { FinalAnswer } from './components/FinalAnswer';
import type { AgentEvent, HealthStatus } from './types/agent';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [finalEvent, setFinalEvent] = useState<AgentEvent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Check health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data: HealthStatus = await res.json();
          setHealth(data);
        } else {
          setHealth({
            status: 'error',
            ollama_host: 'http://localhost:11434',
            ollama_model: 'llama3.2:latest',
            ollama_connected: false,
            model_available: false,
            error: 'Backend health check failed',
          });
        }
      } catch (err: any) {
        setHealth({
          status: 'error',
          ollama_host: 'http://localhost:11434',
          ollama_model: 'llama3.2:latest',
          ollama_connected: false,
          model_available: false,
          error: err.message,
        });
      }
    };

    checkHealth();
  }, []);

  const handleReset = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setQuestion('');
    setEvents([]);
    setFinalEvent(null);
    setCurrentStep(0);
    setGlobalError(null);
    setIsLoading(false);
  };

  const handleStartResearch = async () => {
    if (!question.trim()) return;

    // Reset previous run
    setEvents([]);
    setFinalEvent(null);
    setCurrentStep(0);
    setGlobalError(null);
    setIsLoading(true);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ question: question.trim() }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP request failed with status ${response.status}`
        );
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported on response body.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep uncompleted line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const jsonPayload = trimmed.replace(/^data:\s*/, '');
          try {
            const event: AgentEvent = JSON.parse(jsonPayload);
            event.clientTimestamp = Date.now();

            if (event.step > 0) {
              setCurrentStep(event.step);
            }

            setEvents((prev) => [...prev, event]);

            if (event.type === 'final') {
              setFinalEvent(event);
            } else if (event.type === 'error' && !event.step) {
              setGlobalError(event.error || event.message || 'Agent error occurred');
            }
          } catch (jsonErr) {
            console.error('Failed to parse SSE payload:', jsonPayload, jsonErr);
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Research request was aborted by user.');
      } else {
        setGlobalError(err.message || 'Failed to connect to research agent.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      <Header health={health} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Global Error Banner */}
        {globalError && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-sm flex items-start gap-3 shadow-lg">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-200">Execution Alert</p>
              <p className="text-xs text-rose-300/90 mt-0.5">{globalError}</p>
            </div>
          </div>
        )}

        {/* Input Panel */}
        <QuestionInput
          question={question}
          setQuestion={setQuestion}
          onSubmit={handleStartResearch}
          onReset={handleReset}
          isLoading={isLoading}
        />

        {/* Two-Column Display: Left Activity, Right Output */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <ActivityFeed
            events={events}
            isLoading={isLoading}
            currentStep={currentStep}
          />

          <FinalAnswer
            finalEvent={finalEvent}
            isLoading={isLoading}
          />
        </div>
      </main>

      <footer className="border-t border-slate-900 bg-slate-950/90 py-4 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>
            AI-Assisted Research Agent • Built with React, FastAPI & Ollama
          </div>
          <div className="flex items-center gap-4">
            <span>No LangChain / LangGraph</span>
            <span>•</span>
            <span>Manual ReAct Loop</span>
            <span>•</span>
            <span>Safe AST Math</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
