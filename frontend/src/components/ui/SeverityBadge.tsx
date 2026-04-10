import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

export type SeverityType = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

interface SeverityBadgeProps {
  severity: SeverityType;
  glow?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const severityConfig = {
  CRITICAL: {
    bg: 'bg-[#FF2D55]/15',
    text: 'text-[#FF2D55]',
    border: 'border-[#FF2D55]/50',
    glowColor: 'rgba(255, 45, 85, 0.8)',
  },
  HIGH: {
    bg: 'bg-[#FFB800]/15',
    text: 'text-[#FFB800]',
    border: 'border-[#FFB800]/50',
    glowColor: 'rgba(255, 184, 0, 0.6)',
  },
  MEDIUM: {
    bg: 'bg-[#EAB308]/15',
    text: 'text-[#EAB308]',
    border: 'border-[#EAB308]/50',
    glowColor: 'rgba(234, 179, 8, 0.4)',
  },
  LOW: {
    bg: 'bg-[#3B82F6]/15',
    text: 'text-[#3B82F6]',
    border: 'border-[#3B82F6]/50',
    glowColor: 'rgba(59, 130, 246, 0.4)',
  },
  INFO: {
    bg: 'bg-[#4A5568]/20',
    text: 'text-[#8F9CAE]',
    border: 'border-[#4A5568]/50',
    glowColor: 'rgba(143, 156, 174, 0.3)',
  }
};

const sizeConfig = {
  sm: 'px-1.5 py-0.5 text-[9px]',
  md: 'px-2 py-1 text-[10px]',
  lg: 'px-3 py-1.5 text-[12px]',
}

export function SeverityBadge({ severity, glow = false, className, size = 'sm' }: SeverityBadgeProps) {
  const config = severityConfig[severity];
  const isCritical = severity === 'CRITICAL';

  const Box = isCritical && glow ? motion.div : 'div';
  
  const animationProps = isCritical && glow ? {
    animate: {
      boxShadow: [
        `0 0 2px ${config.glowColor}`,
        `0 0 15px ${config.glowColor}`,
        `0 0 2px ${config.glowColor}`
      ]
    },
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: "easeInOut"
    }
  } : {};

  return (
    <Box
      {...(animationProps as any)}
      className={cn(
        "inline-flex items-center rounded-sm font-display font-bold tracking-[0.1em] border uppercase drop-shadow-sm",
        config.bg,
        config.text,
        config.border,
        sizeConfig[size],
        className
      )}
      style={glow && !isCritical ? { boxShadow: `0 0 8px ${config.glowColor}` } : {}}
    >
      {severity}
    </Box>
  );
}
