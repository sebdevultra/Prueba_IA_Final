import React, { useState, useRef, useEffect } from 'react';
import { Bot, User, Send, Sparkles, Database, ShieldCheck, RefreshCw, Cpu } from 'lucide-react';
import { api, AgentQueryResponse } from '../api/client';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  dataPoints?: number;
}

export const AgentChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `¡Hola! Soy el **Agente de Inteligencia Artificial de SismoWatch**, conectado a la **Capa Curated (Gold)** mediante el modelo local de **Ollama (8B)**.\n\nPuedo responder cualquier consulta sobre la actividad sísmica global certificada, estadísticas, detección de anomalías o eventos críticos con estricta política de **cero alucinaciones**.\n\n*Selecciona una pregunta rápida o escribe tu consulta:*`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model: 'Ollama 8B (llama3:8b)',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const quickPrompts = [
    '¿Cuáles son los 5 sismos más fuertes registrados en la capa Gold?',
    '¿Cuántos eventos tuvieron alerta de tsunami activa?',
    '¿Qué actividad sísmica reciente hay en Chile, Japón o California?',
    '¿Cuál es la magnitud promedio y la ventana de fechas observada?',
  ];

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputValue.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setLoading(true);

    try {
      // Formato para historial
      const historyPayload = messages
        .filter((m) => m.id !== 'welcome')
        .map((m) => ({ role: m.role, content: m.content }));

      const res: AgentQueryResponse = await api.askGoldAgent(text, historyPayload);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        model: res.model,
        dataPoints: res.data_points_analyzed,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ **Error en consulta**: ${err.message || 'No se pudo conectar con el agente de IA.'}\n\n*Verifica que el servicio backend y Ollama estén en ejecución.*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div style={{ paddingBottom: '50px', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Header Panel */}
      <div
        className="glass-panel"
        style={{
          padding: '20px 24px',
          marginBottom: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #06B6D4 0%, #3B82F6 50%, #6366F1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--glow-cyan)',
            }}
          >
            <Bot size={26} color="#fff" />
          </div>
          <div>
            <h2 style={{ fontSize: '18px', color: '#fff', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Agente de Inteligencia Artificial (Capa Gold)</span>
              <span
                style={{
                  fontSize: '11px',
                  background: 'rgba(56, 189, 248, 0.15)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: 'var(--accent-cyan-bright)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontWeight: 600,
                }}
              >
                Ollama 8B Local
              </span>
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>
              Consultas analíticas en lenguaje natural validadas contra datos certificados de <code style={{ color: 'var(--accent-cyan-bright)' }}>curated.earthquake_events</code>.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              color: 'var(--accent-emerald)',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              padding: '5px 10px',
              borderRadius: '6px',
            }}
          >
            <ShieldCheck size={14} /> Cero Alucinaciones
          </span>
          <button
            className="btn btn-secondary"
            onClick={() => setMessages([messages[0]])}
            title="Reiniciar chat"
            style={{ padding: '6px 10px', fontSize: '12px' }}
          >
            <RefreshCw size={13} />
            <span>Limpiar</span>
          </button>
        </div>
      </div>

      {/* Suggested Quick Prompts */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
        {quickPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(prompt)}
            disabled={loading}
            style={{
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              fontSize: '12px',
              padding: '6px 12px',
              borderRadius: '20px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onMouseOver={(e) => (e.currentTarget.style.borderColor = 'var(--accent-cyan)')}
            onMouseOut={(e) => (e.currentTarget.style.borderColor = 'var(--border-color)')}
          >
            <Sparkles size={12} color="var(--accent-cyan-bright)" />
            <span>{prompt}</span>
          </button>
        ))}
      </div>

      {/* Chat Messages Container */}
      <div
        className="glass-panel"
        style={{
          minHeight: '440px',
          maxHeight: '520px',
          overflowY: 'auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          marginBottom: '16px',
        }}
      >
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                gap: '12px',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                flexDirection: isUser ? 'row-reverse' : 'row',
              }}
            >
              {/* Avatar */}
              <div
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '10px',
                  background: isUser
                    ? 'linear-gradient(135deg, #3B82F6, #6366F1)'
                    : 'linear-gradient(135deg, #06B6D4, #3B82F6)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  boxShadow: isUser ? '0 0 10px rgba(59, 130, 246, 0.4)' : '0 0 10px rgba(6, 182, 212, 0.4)',
                }}
              >
                {isUser ? <User size={18} color="#fff" /> : <Bot size={18} color="#fff" />}
              </div>

              {/* Message Bubble */}
              <div>
                <div
                  style={{
                    background: isUser ? 'rgba(59, 130, 246, 0.2)' : 'rgba(15, 23, 42, 0.85)',
                    border: `1px solid ${isUser ? 'rgba(59, 130, 246, 0.4)' : 'var(--border-color)'}`,
                    borderRadius: '12px',
                    padding: '14px 18px',
                    color: '#F8FAFC',
                    fontSize: '13.5px',
                    lineHeight: '1.6',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {msg.content}
                </div>

                {/* Metadata tag */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '10.5px',
                    color: 'var(--text-dim)',
                    marginTop: '4px',
                    justifyContent: isUser ? 'flex-end' : 'flex-start',
                  }}
                >
                  <span>{msg.timestamp}</span>
                  {msg.model && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Cpu size={10} color="var(--accent-cyan-bright)" />
                      {msg.model}
                    </span>
                  )}
                  {msg.dataPoints !== undefined && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Database size={10} color="var(--accent-emerald)" />
                      {msg.dataPoints.toLocaleString()} eventos auditados
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div style={{ display: 'flex', gap: '12px', alignSelf: 'flex-start' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #06B6D4, #3B82F6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--glow-cyan)',
              }}
            >
              <Bot size={18} color="#fff" />
            </div>
            <div
              className="glass-panel"
              style={{
                padding: '12px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: 'var(--accent-cyan-bright)',
                fontSize: '13px',
              }}
            >
              <RefreshCw size={14} className="spin" />
              <span>Consultando la capa Curated y ejecutando modelo Ollama 8B...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div
        className="glass-panel"
        style={{
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <textarea
          rows={1}
          className="input-field"
          style={{
            resize: 'none',
            minHeight: '44px',
            padding: '10px 14px',
            fontSize: '14px',
            flex: 1,
          }}
          placeholder="Haz una pregunta sobre los sismos certificados de la capa Gold..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />

        <button
          className="btn btn-primary"
          onClick={() => handleSendMessage()}
          disabled={loading || !inputValue.trim()}
          style={{ height: '44px', padding: '0 18px' }}
        >
          <Send size={16} />
          <span>Enviar</span>
        </button>
      </div>
    </div>
  );
};
