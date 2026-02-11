import { useChatStore } from '../stores/chatStore';
import type { NetworkTier } from '../types';

const TIER_CONFIG: Record<NetworkTier, { color: string; bg: string; label: string; icon: string }> = {
  EXCELLENT: { color: 'text-green-400', bg: 'bg-green-400', label: 'Excellent', icon: '●●●●' },
  GOOD: { color: 'text-blue-400', bg: 'bg-blue-400', label: 'Good', icon: '●●●○' },
  FAIR: { color: 'text-yellow-400', bg: 'bg-yellow-400', label: 'Fair', icon: '●●○○' },
  POOR: { color: 'text-red-400', bg: 'bg-red-400', label: 'Poor', icon: '●○○○' },
};

export function NetworkIndicator() {
  const { networkTier, networkLatency } = useChatStore();
  const cfg = TIER_CONFIG[networkTier];

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 rounded-lg border border-gray-700">
      <div className="relative flex items-center">
        <div className={`w-2 h-2 rounded-full ${cfg.bg} animate-pulse`} />
      </div>
      <div className="flex flex-col">
        <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
        <span className="text-[10px] text-gray-500">{networkLatency.toFixed(0)}ms</span>
      </div>
      <span className={`text-xs tracking-wider ${cfg.color}`}>{cfg.icon}</span>
    </div>
  );
}
