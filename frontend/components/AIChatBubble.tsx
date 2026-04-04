'use client';

import { useState, useRef, useEffect } from 'react';
import { aiAPI, ChatMessage } from '@/lib/api/ai';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  Send,
  Bot,
  User,
  Sparkles,
  X,
  Zap,
  Brain,
  MessageSquare,
  RotateCcw,
  Minimize2,
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  { icon: '📊', text: 'Resumen del dashboard' },
  { icon: '⚠️', text: '¿Quiénes están en mora?' },
  { icon: '🧮', text: 'Calcula un préstamo de RD$50,000' },
  { icon: '📅', text: 'Proyección de cobros 7 días' },
];

export function AIChatBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [selectedAgent, setSelectedAgent] = useState<'lite' | 'assistant' | 'analyst'>('lite');
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const sendMessage = async (prompt: string) => {
    if (!prompt.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: prompt,
      timestamp: new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await aiAPI.chat(prompt, conversationId, selectedAgent);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.text,
        timestamp: new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' }),
        thinking: response.thinking || undefined,
        usage: response.usage || undefined,
      };

      setMessages(prev => [...prev, assistantMessage]);
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      if (!isOpen) setUnreadCount(prev => prev + 1);
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.error || error.message || 'Error de conexión'}`,
        timestamp: new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    inputRef.current?.focus();
  };

  return (
    <>
      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 sm:right-6 z-50 w-[360px] sm:w-[400px] h-[520px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 fade-in duration-200">
          {/* Header */}
          <div className="bg-[#163300] px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-[#FFE026]" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Asistente CrediFlux</h3>
                <p className="text-[10px] text-white/60">
                  {selectedAgent === 'analyst' ? 'Analista de crédito' : selectedAgent === 'assistant' ? 'Acceso completo' : 'Respuesta rápida'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleNewConversation}
                className="p-1.5 rounded-md text-white/60 hover:text-white hover:bg-white/10 transition-colors"
                title="Nueva conversación"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-md text-white/60 hover:text-white hover:bg-white/10 transition-colors"
                title="Minimizar"
              >
                <Minimize2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Agent Selector */}
          <div className="px-3 py-2 border-b bg-gray-50 flex-shrink-0">
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              <button
                onClick={() => setSelectedAgent('lite')}
                className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  selectedAgent === 'lite'
                    ? 'bg-white text-[#163300] shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Zap className="h-3 w-3" />
                Rápido
              </button>
              <button
                onClick={() => setSelectedAgent('assistant')}
                className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  selectedAgent === 'assistant'
                    ? 'bg-white text-[#163300] shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <MessageSquare className="h-3 w-3" />
                Completo
              </button>
              <button
                onClick={() => setSelectedAgent('analyst')}
                className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  selectedAgent === 'analyst'
                    ? 'bg-white text-[#163300] shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Brain className="h-3 w-3" />
                Analista
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 bg-gray-50/50">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-2">
                <div className="w-12 h-12 rounded-full bg-[#163300]/10 flex items-center justify-center mb-3">
                  <Bot className="h-6 w-6 text-[#163300]" />
                </div>
                <p className="text-xs text-gray-500 mb-4">
                  Busca clientes, analiza riesgos, calcula préstamos y más.
                </p>
                <div className="grid grid-cols-1 gap-1.5 w-full">
                  {SUGGESTED_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => sendMessage(prompt.text)}
                      className="flex items-center gap-2 p-2 bg-white border border-gray-200 rounded-lg text-left text-xs hover:border-[#163300]/40 hover:bg-[#163300]/5 transition-colors"
                    >
                      <span>{prompt.icon}</span>
                      <span className="text-gray-600">{prompt.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-6 h-6 rounded-full bg-[#163300] flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Bot className="h-3 w-3 text-[#FFE026]" />
                      </div>
                    )}
                    <div
                      className={`max-w-[85%] rounded-xl px-3 py-2 ${
                        msg.role === 'user'
                          ? 'bg-[#163300] text-white'
                          : 'bg-white border border-gray-200 text-gray-800'
                      }`}
                    >
                      <div className="text-xs whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                      <div className="flex items-center justify-between mt-1">
                        <span className={`text-[9px] ${msg.role === 'user' ? 'text-green-200' : 'text-gray-400'}`}>
                          {msg.timestamp}
                        </span>
                        {msg.usage && (
                          <span className="text-[9px] text-gray-400 flex items-center gap-0.5">
                            <Zap className="h-2 w-2" />
                            {msg.usage.total_tokens}
                          </span>
                        )}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <div className="w-6 h-6 rounded-full bg-[#738566] flex items-center justify-center flex-shrink-0 mt-0.5">
                        <User className="h-3 w-3 text-white" />
                      </div>
                    )}
                  </div>
                ))}
                {isLoading && (
                  <div className="flex gap-2 justify-start">
                    <div className="w-6 h-6 rounded-full bg-[#163300] flex items-center justify-center flex-shrink-0">
                      <Bot className="h-3 w-3 text-[#FFE026]" />
                    </div>
                    <div className="bg-white border border-gray-200 rounded-xl px-3 py-2">
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Pensando...
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input */}
          <div className="border-t bg-white px-3 py-2.5 flex-shrink-0">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Escribe tu pregunta..."
                disabled={isLoading}
                className="flex-1 h-9 text-xs"
              />
              <Button
                type="submit"
                size="sm"
                disabled={!input.trim() || isLoading}
                className="bg-[#163300] hover:bg-[#0f2400] h-9 px-3"
              >
                <Send className="h-3.5 w-3.5" />
              </Button>
            </form>
          </div>
        </div>
      )}

      {/* Floating Bubble */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-4 right-4 sm:right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-200 hover:scale-110 active:scale-95 ${
          isOpen
            ? 'bg-gray-600 hover:bg-gray-700'
            : 'bg-[#163300] hover:bg-[#0f2400]'
        }`}
        title={isOpen ? 'Cerrar asistente' : 'Abrir asistente AI'}
      >
        {isOpen ? (
          <X className="h-6 w-6 text-white" />
        ) : (
          <>
            <Sparkles className="h-6 w-6 text-[#FFE026]" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-[#FF7503] text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </>
        )}
      </button>
    </>
  );
}
