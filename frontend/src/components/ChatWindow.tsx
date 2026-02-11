import { useState, useRef, useEffect, useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { useVoice } from '../hooks/useVoice';
import { MessageBubble } from './MessageBubble';
import { NetworkIndicator } from './NetworkIndicator';
import { ModeSelector } from './ModeSelector';
import { DocumentSidebar } from './DocumentSidebar';
import { VoiceInput } from './VoiceInput';
import { Send, LogOut, Brain, Trash2, Clock, PanelLeftOpen, PanelLeftClose, Plus } from 'lucide-react';

interface SessionInfo {
  id: string;
  created_at: string;
  preview: string | null;
  message_count: number;
}

export function ChatWindow() {
  const { messages, isProcessing, auth, logout, clearMessages, setSessionId, sessionId, addMessage } = useChatStore();
  const { sendMessage } = useWebSocket();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const userScrolledUpRef = useRef(false);

  // Chat history sidebar
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  const { isListening, startListening, stopListening, isSpeaking, speak, stopSpeaking } = useVoice((transcript) => {
    setInput((prev) => (prev ? prev + ' ' + transcript : transcript));
  });

  // Track if user has scrolled away from bottom
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    userScrolledUpRef.current = distFromBottom > 120;
  }, []);

  // Smart auto-scroll: only scroll if user is near the bottom
  useEffect(() => {
    if (!userScrolledUpRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  // Load session list
  const loadSessions = useCallback(async () => {
    if (!auth.token) return;
    setLoadingSessions(true);
    try {
      const res = await fetch('/api/chat/sessions', {
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch {} finally {
      setLoadingSessions(false);
    }
  }, [auth.token]);

  // Load a specific session's messages
  const loadSession = useCallback(async (sid: string) => {
    if (!auth.token) return;
    clearMessages();
    setSessionId(sid);
    try {
      const res = await fetch(`/api/chat/sessions/${sid}/messages`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (res.ok) {
        const data = await res.json();
        for (const msg of data.messages || []) {
          addMessage({
            id: crypto.randomUUID(),
            role: msg.role,
            content: msg.content,
            metadata: msg.metadata || undefined,
          });
        }
      }
    } catch {}
    setHistoryOpen(false);
  }, [auth.token]);

  const handleHistoryOpen = () => {
    setHistoryOpen(true);
    loadSessions();
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isProcessing) return;
    sendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleNewChat = () => {
    clearMessages();
    setSessionId(crypto.randomUUID());
  };

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Chat history sidebar */}
      {historyOpen && (
        <aside className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col animate-fade-in">
          <div className="flex items-center justify-between px-3 py-3 border-b border-gray-800">
            <span className="text-xs font-semibold text-gray-300">Chat History</span>
            <button onClick={() => setHistoryOpen(false)} className="text-gray-500 hover:text-white transition-colors">
              <PanelLeftClose size={16} />
            </button>
          </div>
          <button
            onClick={handleNewChat}
            className="mx-3 mt-3 flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs text-white font-medium transition-colors"
          >
            <Plus size={14} /> New Chat
          </button>
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
            {loadingSessions ? (
              <p className="text-xs text-gray-500 text-center mt-6">Loading...</p>
            ) : sessions.length === 0 ? (
              <p className="text-xs text-gray-500 text-center mt-6">No previous chats</p>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => loadSession(s.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors group ${
                    sessionId === s.id
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`}
                >
                  <p className="truncate font-medium">{s.preview || 'Empty chat'}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5 flex items-center gap-1">
                    <Clock size={9} />
                    {new Date(s.created_at).toLocaleDateString()} · {s.message_count} msgs
                  </p>
                </button>
              ))
            )}
          </div>
        </aside>
      )}

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <button
            onClick={historyOpen ? () => setHistoryOpen(false) : handleHistoryOpen}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white transition-colors"
            title="Chat history"
          >
            {historyOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
          </button>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <Brain size={18} className="text-white" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-sm font-semibold text-white">Adaptive Reasoning Agent</h1>
            <p className="text-[10px] text-gray-500">Powered by Mistral AI</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden md:block"><NetworkIndicator /></div>
          <div className="hidden sm:flex"><ModeSelector /></div>
          <DocumentSidebar />
          <button
            onClick={handleNewChat}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white transition-colors"
            title="New chat"
          >
            <Trash2 size={16} />
          </button>
          <div className="flex items-center gap-2 pl-2 border-l border-gray-700">
            <span className="text-xs text-gray-500 hidden sm:inline">{auth.user?.username}</span>
            <button
              onClick={logout}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-red-400 transition-colors"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scroll-smooth"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-800/30 flex items-center justify-center mb-4">
              <Brain size={32} className="text-blue-400" />
            </div>
            <h2 className="text-lg font-semibold text-gray-300 mb-2">
              How can I help you today?
            </h2>
            <p className="text-sm text-gray-500 max-w-md">
              Ask anything. I'll automatically adapt my reasoning depth based on your network
              conditions for the best experience.
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-6">
              {[
                'Explain quantum computing',
                'What time is it?',
                'Compare React vs Vue in depth',
                'Search the web for latest AI news',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-full text-xs text-gray-400 hover:text-gray-200 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onSpeak={speak} />
        ))}

        {/* Scroll-to-bottom button when user scrolled up during streaming */}
        {userScrolledUpRef.current && isProcessing && (
          <button
            onClick={() => {
              userScrolledUpRef.current = false;
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="sticky bottom-2 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-blue-600/90 hover:bg-blue-500 text-white text-xs rounded-full shadow-lg backdrop-blur transition-all z-10"
          >
            ↓ Scroll to bottom
          </button>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input */}
      <div className="px-4 py-3 bg-gray-900 border-t border-gray-800">
        <form onSubmit={handleSubmit} className="flex items-end gap-2 max-w-4xl mx-auto">
          <VoiceInput
            isListening={isListening}
            isSpeaking={isSpeaking}
            onStart={startListening}
            onStop={stopListening}
            onStopSpeaking={stopSpeaking}
          />
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-200 resize-none focus:outline-none focus:border-blue-500 placeholder-gray-500"
              placeholder={isProcessing ? 'Processing...' : 'Type your message... (Shift+Enter for new line)'}
              disabled={isProcessing}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl text-white transition-colors"
          >
            <Send size={18} />
          </button>
        </form>

        {/* Mobile-only: mode selector below input */}
        <div className="flex sm:hidden justify-center mt-2">
          <ModeSelector />
        </div>
      </div>
      </div>{/* end main chat area */}
    </div>
  );
}
