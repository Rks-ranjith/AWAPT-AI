import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface CvssGaugeProps {
  score: number;
  animated?: boolean;
}

export function CvssGauge({ score, animated = true }: CvssGaugeProps) {
  const [mounted, setMounted] = useState(!animated);
  const size = 120;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = mounted ? circumference - (score / 10) * circumference : circumference;

  useEffect(() => {
    if (animated) {
      setTimeout(() => setMounted(true), 100);
    }
  }, [animated]);

  let color = '#3B82F6'; // LOW
  if (score >= 9.0) color = '#FF2D55'; // CRITICAL
  else if (score >= 7.0) color = '#FFB800'; // HIGH
  else if (score >= 4.0) color = '#EAB308'; // MEDIUM

  return (
    <div className="relative inline-flex items-center justify-center font-mono" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#111827"
          strokeWidth={strokeWidth}
        />
        {/* Animated fill */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
          style={{
            filter: score >= 7.0 ? `drop-shadow(0 0 6px ${color}80)` : 'none'
          }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center text-center">
        <span className="text-3xl font-bold leading-none" style={{ color }}>
          {mounted ? score.toFixed(1) : "0.0"}
        </span>
        <span className="text-[10px] text-[#4A5568] tracking-widest mt-1">CVSS</span>
      </div>
    </div>
  );
}
