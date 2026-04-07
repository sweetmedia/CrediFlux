import { apiClient } from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  thinking?: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface ChatResponse {
  text: string;
  conversation_id: string | null;
  thinking: string | null;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
}

export interface AIAgent {
  id: string;
  name: string;
  description: string;
  model: string;
  tools: string[];
}

export const aiAPI = {
  async chat(prompt: string, conversationId?: string, agent: string = 'assistant'): Promise<ChatResponse> {
    return apiClient.post<ChatResponse>('/api/ai/chat/', {
      prompt,
      conversation_id: conversationId,
      agent,
    });
  },

  async getAgents(): Promise<{ agents: AIAgent[] }> {
    return apiClient.get<{ agents: AIAgent[] }>('/api/ai/agents/');
  },
};
