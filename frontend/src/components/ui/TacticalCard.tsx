import { cn } from '@/lib/utils';
import { GlassPanel } from './GlassPanel';
import { HTMLMotionProps } from 'framer-motion';

interface TacticalCardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: React.ReactNode;
  animated?: boolean;
  delay?: number;
  highlightColor?: string;
}

export function TacticalCard({ children, className, animated = false, delay = 0, highlightColor, ...props }: TacticalCardProps) {
  return (
    <GlassPanel
      animated={animated}
      delay={delay}
      className={cn(
        "group transition-all duration-150 ease-in-out hover:-translate-y-[2px]",
        className
      )}
      style={highlightColor ? { borderLeft: `2px solid ${highlightColor}` } : {}}
      {...props}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      {highlightColor && (
        <div 
          className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 pointer-events-none"
          style={{ background: `linear-gradient(90deg, ${highlightColor} 0%, transparent 100%)` }}
        />
      )}
      
      <div className="relative z-10 w-full h-full p-4">
        {children}
      </div>
    </GlassPanel>
  );
}
