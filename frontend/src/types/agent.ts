export type AgentEventType =
  | 'step'
  | 'tool_call'
  | 'tool_result'
  | 'error'
  | 'final'
  | 'done';

export interface AgentEvent {
  type: AgentEventType;
  step: number;
  message?: string;
  tool?: string;
  arguments?: Record<string, any>;
  result_summary?: string;
  raw_result?: any;
  error?: string;
  final_answer?: string;
  citations?: string[];
  fetched_urls?: string[];
  discovered_urls?: string[];
  token_usage?: {
    prompt_tokens: number;
    eval_tokens: number;
    total_tokens: number;
  };
  clientTimestamp?: number;
}

export interface HealthStatus {
  status: string;
  ollama_host: string;
  ollama_model: string;
  ollama_connected: boolean;
  model_available: boolean;
  error?: string | null;
}
