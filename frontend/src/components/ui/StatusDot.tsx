import { cn } from '@/lib/utils';

export type StatusType = 'scanning' | 'complete' | 'paused' | 'error';

interface StatusDotProps {
  status: StatusType;
  className?: string;
  withRadar?: boolean;
}

const statusConfig = {
  scanning: 'bg-[#00D4FF]',
  complete: 'bg-[#00FF88]',
  paused: 'bg-[#FFB800]',
  error: 'bg-[#FF2D55]',
};

export function StatusDot({ status, className, withRadar = false }: StatusDotProps) {
  return (
    <div className={cn("relative flex items-center justify-center w-3 h-3", className)}>
      {withRadar && status === 'scanning' && (
        <>
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#00D4FF] opacity-75 duration-1000"></span>
          <span className="absolute inline-flex h-6 w-6 animate-ping rounded-full bg-[#00D4FF] opacity-30" style={{ animationDuration: '2s' }}></span>
          <span className="absolute inline-flex h-9 w-9 animate-ping rounded-full border border-[#00D4FF] opacity-20" style={{ animationDuration: '3s' }}></span>
        </>
      )}
      
      {status === 'scanning' && !withRadar && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#00D4FF] opacity-75"></span>
      )}
      
      {status === 'error' && (
        <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-[#FF2D55] opacity-75 duration-500"></span>
      )}

      <span className={cn("relative inline-flex rounded-full h-2 w-2", statusConfig[status])}></span>
    </div>
  );
}

export function SonarPulse({ active = true, className }: { active?: boolean, className?: string }) {
  if (!active) return null;
  return (
    <div className={cn("relative w-4 h-4", className)}>
      <span className="absolute inset-0 rounded-full border border-[#00D4FF] opacity-0 animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite]"></span>
      <span className="absolute inset-0 rounded-full border border-[#00D4FF] opacity-0 animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite_1s]"></span>
      <span className="absolute inset-0 rounded-full border border-[#00D4FF] opacity-0 animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite_2s]"></span>
      <span className="absolute inset-[30%] rounded-full bg-[#00D4FF]"></span>
    </div>
  );
}
