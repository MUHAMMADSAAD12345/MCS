export type NetworkTier = 'EXCELLENT' | 'GOOD' | 'FAIR' | 'POOR';
export type ReasoningMode = 'fast' | 'standard' | 'deep' | 'auto';
export type WSMessageType = 'chat_message' | 'token' | 'reasoning_step' | 'tool_call' | 'done' | 'error';

export interface WSMessage {
  type: WSMessageType;
  content?: string;
  metadata?: Record<string, any>;
  step_name?: string;
  step_number?: number;
  total_steps?: number;
  description?: string;
  tool?: string;
  status?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    reasoning_mode?: string;
    network_tier?: string;
    tools_used?: string[];
    llm_calls?: number;
    total_tokens?: number;
    latency_ms?: number;
    query_complexity?: string;
    complexity_score?: number;
  };
  reasoning_steps?: ReasoningStep[];
  isStreaming?: boolean;
}

export interface ReasoningStep {
  step_name: string;
  step_number: number;
  total_steps: number;
  description: string;
  status: 'active' | 'done';
}

export interface UploadedDocument {
  id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
}

export interface AuthState {
  token: string | null;
  user: { id: string; username: string } | null;
}
