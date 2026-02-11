import type { ReasoningStep } from '../types';
import { CheckCircle, Loader2 } from 'lucide-react';

interface Props {
  steps: ReasoningStep[];
}

export function ReasoningSteps({ steps }: Props) {
  if (!steps.length) return null;

  return (
    <div className="mb-2 space-y-1">
      {steps.map((step, i) => (
        <div
          key={i}
          className={`flex items-start gap-2 text-xs px-3 py-1.5 rounded-md transition-all
            ${step.status === 'active'
              ? 'bg-blue-900/30 text-blue-300 border border-blue-800/40'
              : 'bg-gray-800/50 text-gray-500'}
          `}
        >
          {step.status === 'active' ? (
            <Loader2 size={12} className="mt-0.5 animate-spin flex-shrink-0" />
          ) : (
            <CheckCircle size={12} className="mt-0.5 text-green-500 flex-shrink-0" />
          )}
          <div>
            <span className="font-medium">{step.step_name}</span>
            {step.description && (
              <span className="ml-1 text-gray-500">— {step.description}</span>
            )}
          </div>
          {step.total_steps > 0 && (
            <span className="ml-auto text-gray-600 flex-shrink-0">
              {step.step_number}/{step.total_steps}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
