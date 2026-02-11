import { useCallback, useRef, useEffect } from 'react';
import { useChatStore } from '../stores/chatStore';
import type { WSMessage } from '../types';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const {
    auth,
    sessionId,
    setSessionId,
    selectedMode,
    addMessage,
    appendToken,
    addReasoningStep,
    completeLastReasoningStep,
    updateLastAssistant,
    setProcessing,
    setNetwork,
    setActiveMode,
  } = useChatStore();

  // Poll network status
  useEffect(() => {
    if (!auth.token) return;
    const poll = async () => {
      try {
        const res = await fetch('/api/network/status', {
          headers: { Authorization: `Bearer ${auth.token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setNetwork(data.tier, data.avg_latency_ms);
        }
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, [auth.token]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!auth.token) return;

      // Add user message
      addMessage({
        id: crypto.randomUUID(),
        role: 'user',
        content,
      });

      // Add placeholder assistant message
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        isStreaming: true,
        reasoning_steps: [],
      });

      setProcessing(true);

      // Try WebSocket first
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/chat/ws?token=${auth.token}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          const payload: any = {
            type: 'chat_message',
            content: content,
            mode_override: selectedMode === 'auto' ? null : selectedMode,
          };
          if (sessionId) payload.session_id = sessionId;
          ws.send(JSON.stringify(payload));
        };

        ws.onmessage = (event) => {
          const msg: WSMessage = JSON.parse(event.data);

          switch (msg.type) {
            case 'token':
              appendToken(msg.content || '');
              break;

            case 'reasoning_step':
              addReasoningStep({
                step_name: msg.step_name || '',
                step_number: msg.step_number || 0,
                total_steps: msg.total_steps || 0,
                description: msg.description || '',
                status: 'active',
              });
              break;

            case 'tool_call':
              addReasoningStep({
                step_name: `Tool: ${msg.tool}`,
                step_number: 0,
                total_steps: 0,
                description: msg.description || `Using ${msg.tool}`,
                status: 'active',
              });
              break;

            case 'done':
              // Mark final reasoning step as complete
              completeLastReasoningStep();
              if (msg.metadata) {
                updateLastAssistant({
                  isStreaming: false,
                  metadata: msg.metadata,
                });
                if (msg.metadata.session_id) {
                  setSessionId(msg.metadata.session_id);
                }
                if (msg.metadata.reasoning_mode) {
                  setActiveMode(msg.metadata.reasoning_mode);
                }
              } else {
                updateLastAssistant({ isStreaming: false });
              }
              setProcessing(false);
              ws.close();
              break;

            case 'error':
              updateLastAssistant({
                content: msg.content || 'An error occurred.',
                isStreaming: false,
              });
              setProcessing(false);
              ws.close();
              break;
          }
        };

        ws.onerror = () => {
          // Fallback to REST
          ws.close();
          sendREST(content);
        };

        ws.onclose = () => {
          wsRef.current = null;
        };
      } catch {
        sendREST(content);
      }
    },
    [auth.token, sessionId, selectedMode],
  );

  const sendREST = useCallback(
    async (content: string) => {
      try {
        const body: any = {
          content: content,
          mode_override: selectedMode === 'auto' ? null : selectedMode,
        };
        if (sessionId) body.session_id = sessionId;

        const res = await fetch('/api/chat/send', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${auth.token}`,
          },
          body: JSON.stringify(body),
        });

        if (res.ok) {
          const data = await res.json();
          updateLastAssistant({
            content: data.content,
            isStreaming: false,
            metadata: data.metadata,
          });
          if (data.session_id) setSessionId(data.session_id);
          if (data.metadata?.reasoning_mode) setActiveMode(data.metadata.reasoning_mode);
        } else {
          updateLastAssistant({
            content: 'Failed to get a response. Please try again.',
            isStreaming: false,
          });
        }
      } catch {
        updateLastAssistant({
          content: 'Connection failed. Please check your network.',
          isStreaming: false,
        });
      } finally {
        setProcessing(false);
      }
    },
    [auth.token, sessionId, selectedMode],
  );

  return { sendMessage };
}
