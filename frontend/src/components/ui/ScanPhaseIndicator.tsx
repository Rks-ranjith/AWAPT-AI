import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

export interface ScanPhase {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'complete' | 'error';
}

interface ScanPhaseIndicatorProps {
  phases: ScanPhase[];
}

export function ScanPhaseIndicator({ phases }: ScanPhaseIndicatorProps) {
  return (
    <div className="flex items-center justify-between w-full font-mono text-xs overflow-x-auto pb-4">
      {phases.map((phase, i) => {
        const isComplete = phase.status === 'complete';
        const isActive = phase.status === 'active';
        
        return (
          <div key={phase.id} className="contents">
            <div className="flex flex-col items-center flex-shrink-0 relative">
              <div 
                className={cn(
                  "w-8 h-8 rounded-full flex flex-col items-center justify-center border-2 mb-2 transition-colors duration-300 z-10 bg-[#0D1117]",
                  isComplete ? "border-[#00FF88] text-[#00FF88]" : 
                  isActive ? "border-[#00D4FF] text-[#00D4FF]" : 
                  "border-[#4A5568] text-[#4A5568]"
                )}
              >
                {isComplete ? (
                  <Check className="w-4 h-4" />
                ) : isActive ? (
                  <div className="w-3 h-3 rounded-full bg-[#00D4FF] animate-pulse" />
                ) : (
                  <span>{i + 1}</span>
                )}

                {isActive && (
                  <span className="absolute inset-0 rounded-full border border-[#00D4FF] animate-ping opacity-60"></span>
                )}
              </div>
              <span 
                className={cn(
                  "whitespace-nowrap font-medium",
                  isComplete ? "text-[#00FF88]" : 
                  isActive ? "text-[#00D4FF]" : 
                  "text-[#4A5568]"
                )}
              >
                {phase.label}
              </span>
            </div>
            {i < phases.length - 1 && (
              <div className="flex-1 min-w-[32px] max-w-[120px] h-[2px] mx-2 -mt-6 bg-[#111827] relative overflow-hidden">
                {(isComplete || (isActive && phases[i+1]?.status === 'active')) && (
                  <div className="absolute inset-0 bg-[#00FF88] animate-[fillRight_0.5s_ease-out_forwards]" />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
