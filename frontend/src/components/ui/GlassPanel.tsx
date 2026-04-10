import { cn } from '@/lib/utils';
import { motion, HTMLMotionProps } from 'framer-motion';

interface GlassPanelProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: React.ReactNode;
  animated?: boolean;
  delay?: number;
  highlightColor?: string;
}

export function GlassPanel({ children, className, animated = false, delay = 0, highlightColor, ...props }: GlassPanelProps) {
  const baseClasses = "glass-panel group transition-all duration-300 relative overflow-hidden";

  const Content = () => (
    <>
      {highlightColor && (
        <div 
          className="absolute top-0 left-0 w-full h-[1px] opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{ background: `linear-gradient(90deg, transparent, ${highlightColor}, transparent)` }}
        />
      )}
      <div className="relative z-10 w-full h-full">
        {children}
      </div>
    </>
  );

  if (animated) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay, ease: "easeOut" }}
        className={cn(baseClasses, className)}
        {...props}
      >
        <Content />
      </motion.div>
    );
  }

  return (
    <motion.div className={cn(baseClasses, className)} {...props}>
      <Content />
    </motion.div>
  );
}
