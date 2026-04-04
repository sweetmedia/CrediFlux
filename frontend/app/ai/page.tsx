'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { aiAPI, ChatMessage } from '@/lib/api/ai';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  Send,
  Bot,
  User,
  Sparkles,
  ArrowLeft,
  RotateCcw,
  Brain,
  MessageSquare,
  Zap,
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  { icon: '📊', text: 'Dame el resumen del dashboard' },
  { icon: '⚠️', text: '¿Quiénes están en mora?' },
  { icon: '🧮', text: 'Calcula un préstamo de RD$50,000 a 3.5% mensual por 12 meses' },
  { icon: '📅', text: 'Proyección de cobros para los próximos 7 días' },
];

export default function AIAssistantPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [selectedAgent, setSelectedAgent] = useState<'assistant' | 'analyst'>('assistant');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `❌ Error: ${error.response?.data?.error || error.message || 'Error de conexión'}`,
        timestamp: new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
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
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="border-b bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#163300] flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-[#FFE026]" />
              </div>
              <div>
                <h1 className="text-sm font-semibold">Asistente CrediFlux</h1>
                <p className="text-xs text-gray-500">Powered by djangosdk</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Agent selector */}
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              <button
                onClick={() => setSelectedAgent('assistant')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  selectedAgent === 'assistant'
                    ? 'bg-white text-[#163300] shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <MessageSquare className="h-3 w-3" />
                General
              </button>
              <button
                onClick={() => setSelectedAgent('analyst')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  selectedAgent === 'analyst'
                    ? 'bg-white text-[#163300] shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Brain className="h-3 w-3" />
                Analista
              </button>
            </div>
            <Button variant="ghost" size="sm" onClick={handleNewConversation} title="Nueva conversación">
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-full bg-[#163300]/10 flex items-center justify-center mb-4">
              <Bot className="h-8 w-8 text-[#163300]" />
            </div>
            <h2 className="text-lg font-semibold text-gray-800 mb-1">¡Hola! Soy tu asistente</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-md">
              Puedo buscar clientes, analizar riesgo crediticio, calcular préstamos
              y revisar la cartera de cobros.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => sendMessage(prompt.text)}
                  className="flex items-center gap-2 p-3 bg-white border border-gray-200 rounded-lg text-left text-sm hover:border-[#163300] hover:bg-[#163300]/5 transition-colors"
                >
                  <span>{prompt.icon}</span>
                  <span className="text-gray-700">{prompt.text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-[#163300] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot className="h-3.5 w-3.5 text-[#FFE026]" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-2.5 ${
                    msg.role === 'user'
                      ? 'bg-[#163300] text-white'
                      : 'bg-white border border-gray-200 text-gray-800'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                  <div className="flex items-center justify-between mt-1">
                    <span className={`text-[10px] ${msg.role === 'user' ? 'text-green-200' : 'text-gray-400'}`}>
                      {msg.timestamp}
                    </span>
                    {msg.usage && (
                      <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                        <Zap className="h-2.5 w-2.5" />
                        {msg.usage.total_tokens} tokens
                      </span>
                    )}
                  </div>
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-[#738566] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="h-3.5 w-3.5 text-white" />
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="w-7 h-7 rounded-full bg-[#163300] flex items-center justify-center flex-shrink-0">
                  <Bot className="h-3.5 w-3.5 text-[#FFE026]" />
                </div>
                <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Pensando...
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="border-t bg-white px-4 py-3">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={selectedAgent === 'analyst' ? 'Consultar al analista de crédito...' : 'Escribe tu consulta...'}
            disabled={isLoading}
            className="flex-1"
            autoFocus
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-[#163300] hover:bg-[#163300]/90"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
        <div className="flex items-center justify-between mt-2">
          <p className="text-[10px] text-gray-400">
            {selectedAgent === 'analyst' ? '🧠 Analista de Crédito' : '🤖 Asistente General'} · AI puede cometer errores
          </p>
          {conversationId && (
            <Badge variant="outline" className="text-[10px]">
              Sesión activa
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}
