import { memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import type { Message } from '../types';
import { ReasoningSteps } from './ReasoningSteps';
import { User, Bot, Zap, Brain, Sparkles, Clock, Hash, Loader2, Volume2, Copy, Check } from 'lucide-react';
import { useState } from 'react';

/** Convert LaTeX delimiters \[...\] and \(...\) to $$...$$ and $...$ */
function normalizeMath(text: string): string {
  // Display math: \[ ... \]  →  $$ ... $$
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_m, inner) => `$$${inner}$$`);
  // Inline math: \( ... \)  →  $ ... $
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_m, inner) => `$${inner}$`);
  return text;
}

interface Props {
  message: Message;
  onSpeak?: (text: string) => void;
}

const MODE_ICONS: Record<string, { icon: any; color: string }> = {
  fast: { icon: Zap, color: 'text-yellow-400' },
  standard: { icon: Brain, color: 'text-blue-400' },
  deep: { icon: Sparkles, color: 'text-purple-400' },
};

export const MessageBubble = memo(function MessageBubble({ message, onSpeak }: Props) {
  const isUser = message.role === 'user';
  const meta = message.metadata;
  const [copied, setCopied] = useState(false);

  // Only re-run normalizeMath when content changes
  const normalizedContent = useMemo(
    () => (message.content ? normalizeMath(message.content) : ''),
    [message.content],
  );

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
          <Bot size={16} className="text-white" />
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'order-first' : ''}`}>
        {/* Reasoning steps */}
        {!isUser && message.reasoning_steps && message.reasoning_steps.length > 0 && (
          <ReasoningSteps steps={message.reasoning_steps} />
        )}

        {/* Message content */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-gray-100 border border-gray-700'
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none text-gray-100">
              {normalizedContent ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {normalizedContent}
                </ReactMarkdown>
              ) : message.isStreaming ? (
                <div className="flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-blue-400" />
                  <span className="text-gray-400 text-sm">Thinking</span>
                  <span className="loading-dots text-blue-400 text-sm" />
                </div>
              ) : null}
              {message.isStreaming && normalizedContent && (
                <span className="inline-block w-1.5 h-4 bg-blue-400 rounded-sm animate-cursor-blink ml-0.5 align-text-bottom" />
              )}
            </div>
          )}
        </div>

        {/* Metadata footer */}
        {!isUser && meta && !message.isStreaming && (
          <div className="flex flex-wrap items-center gap-3 mt-1.5 px-2">
            {meta.reasoning_mode && (
              <MetaBadge
                icon={MODE_ICONS[meta.reasoning_mode]?.icon || Brain}
                color={MODE_ICONS[meta.reasoning_mode]?.color || 'text-gray-400'}
                label={meta.reasoning_mode}
              />
            )}
            {meta.network_tier && (
              <span className="text-[10px] text-gray-500">
                Network: {meta.network_tier}
              </span>
            )}
            {meta.latency_ms != null && (
              <MetaBadge icon={Clock} color="text-gray-500" label={`${meta.latency_ms}ms`} />
            )}
            {meta.total_tokens != null && (
              <MetaBadge icon={Hash} color="text-gray-500" label={`${meta.total_tokens} tok`} />
            )}
            {meta.tools_used && meta.tools_used.length > 0 && (
              <span className="text-[10px] text-gray-500">
                Tools: {meta.tools_used.join(', ')}
              </span>
            )}

            {/* Action buttons */}
            <div className="ml-auto flex items-center gap-1">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(message.content);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
                title="Copy response"
              >
                {copied ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
              </button>
              {onSpeak && (
                <button
                  onClick={() => onSpeak(message.content)}
                  className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
                  title="Read aloud"
                >
                  <Volume2 size={11} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
          <User size={16} className="text-gray-300" />
        </div>
      )}
    </div>
  );
});

function MetaBadge({ icon: Icon, color, label }: { icon: any; color: string; label: string }) {
  return (
    <span className={`flex items-center gap-1 text-[10px] ${color}`}>
      <Icon size={10} />
      {label}
    </span>
  );
}
