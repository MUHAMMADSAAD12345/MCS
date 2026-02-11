import { create } from 'zustand';
import type { AuthState, Message, NetworkTier, ReasoningMode, ReasoningStep, UploadedDocument } from '../types';

interface ChatStore {
  // Messages
  messages: Message[];
  addMessage: (msg: Message) => void;
  updateLastAssistant: (updates: Partial<Message>) => void;
  appendToken: (token: string) => void;
  addReasoningStep: (step: ReasoningStep) => void;
  completeLastReasoningStep: () => void;
  clearMessages: () => void;

  // Session
  sessionId: string | null;
  setSessionId: (id: string) => void;

  // Network
  networkTier: NetworkTier;
  networkLatency: number;
  setNetwork: (tier: NetworkTier, latency: number) => void;

  // Mode
  selectedMode: ReasoningMode;
  setMode: (mode: ReasoningMode) => void;
  activeMode: string | null; // The actual mode used (after auto selection)
  setActiveMode: (mode: string) => void;

  // Documents
  documents: UploadedDocument[];
  setDocuments: (docs: UploadedDocument[]) => void;
  addDocument: (doc: UploadedDocument) => void;
  removeDocument: (id: string) => void;

  // Loading
  isProcessing: boolean;
  setProcessing: (v: boolean) => void;

  // Auth
  auth: AuthState;
  setAuth: (auth: AuthState) => void;
  logout: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAssistant: (updates) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          msgs[i] = { ...msgs[i], ...updates };
          break;
        }
      }
      return { messages: msgs };
    }),
  appendToken: (token) =>
    set((s) => {
      const msgs = s.messages;
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          // Mutate in place and create new array reference only at top level
          // for minimal React re-render cost during high-frequency streaming
          const updated = [...msgs];
          updated[i] = { ...msgs[i], content: msgs[i].content + token };
          return { messages: updated };
        }
      }
      return { messages: msgs };
    }),
  addReasoningStep: (step) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          const steps = [...(msgs[i].reasoning_steps || [])];
          // Mark previous steps as done
          for (const st of steps) st.status = 'done';
          steps.push(step);
          msgs[i] = { ...msgs[i], reasoning_steps: steps };
          break;
        }
      }
      return { messages: msgs };
    }),
  completeLastReasoningStep: () =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          const steps = [...(msgs[i].reasoning_steps || [])];
          // Mark all steps as done
          for (const st of steps) st.status = 'done';
          msgs[i] = { ...msgs[i], reasoning_steps: steps };
          break;
        }
      }
      return { messages: msgs };
    }),
  clearMessages: () => set({ messages: [] }),

  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  networkTier: 'GOOD',
  networkLatency: 0,
  setNetwork: (tier, latency) => set({ networkTier: tier, networkLatency: latency }),

  selectedMode: 'auto',
  setMode: (mode) => set({ selectedMode: mode }),
  activeMode: null,
  setActiveMode: (mode) => set({ activeMode: mode }),

  documents: [],
  setDocuments: (docs) => set({ documents: docs }),
  addDocument: (doc) => set((s) => ({ documents: [doc, ...s.documents] })),
  removeDocument: (id) => set((s) => ({ documents: s.documents.filter((d) => d.id !== id) })),

  isProcessing: false,
  setProcessing: (v) => set({ isProcessing: v }),

  auth: {
    token: localStorage.getItem('token'),
    user: localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')!) : null,
  },
  setAuth: (auth) => {
    if (auth.token) localStorage.setItem('token', auth.token);
    if (auth.user) localStorage.setItem('user', JSON.stringify(auth.user));
    set({ auth });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({
      auth: { token: null, user: null },
      messages: [],
      sessionId: null,
      documents: [],
    });
  },
}));
