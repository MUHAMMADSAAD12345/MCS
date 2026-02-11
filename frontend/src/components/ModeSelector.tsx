import { useChatStore } from '../stores/chatStore';
import type { ReasoningMode } from '../types';
import { Zap, Brain, Sparkles, Gauge } from 'lucide-react';

const MODES: { value: ReasoningMode; label: string; desc: string; icon: any }[] = [
  { value: 'auto', label: 'Auto', desc: 'Adapts to network', icon: Gauge },
  { value: 'fast', label: 'Fast', desc: '1 LLM call', icon: Zap },
  { value: 'standard', label: 'Standard', desc: '2-3 calls', icon: Brain },
  { value: 'deep', label: 'Deep', desc: '4-6 calls', icon: Sparkles },
];

export function ModeSelector() {
  const { selectedMode, setMode, activeMode } = useChatStore();

  return (
    <div className="flex gap-1">
      {MODES.map(({ value, label, desc, icon: Icon }) => {
        const isSelected = selectedMode === value;
        const isActive = activeMode === value;
        return (
          <button
            key={value}
            onClick={() => setMode(value)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
              ${isSelected
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}
              ${isActive && !isSelected ? 'ring-1 ring-blue-500/50' : ''}
            `}
            title={desc}
          >
            <Icon size={14} />
            {label}
          </button>
        );
      })}
    </div>
  );
}
