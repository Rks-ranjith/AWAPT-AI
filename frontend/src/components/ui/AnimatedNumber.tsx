import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  format?: (val: number) => string;
  className?: string;
}

export function AnimatedNumber({
  value,
  format = (val) => Math.floor(val).toLocaleString(),
  className
}: AnimatedNumberProps) {
  const [hasMounted, setHasMounted] = useState(false);
  const motionValue = useMotionValue(0);
  
  const springValue = useSpring(motionValue, {
    damping: 20,
    stiffness: 100,
    mass: 1,
  });

  const display = useTransform(springValue, (current) => format(current));

  useEffect(() => {
    setHasMounted(true);
    // Add small delay to allow actual mount sequence to finish
    const timer = setTimeout(() => {
      // In Framer Motion, useSpring animates towards motionValue changes
      // However, duration isn't direct in useSpring, so we simulate it by setting it
      // For precise duration, we can use requestAnimationFrame internally, but framer motion provides smoother springs.
      motionValue.set(value);
    }, 50);
    return () => clearTimeout(timer);
  }, [value, motionValue]);

  if (!hasMounted) {
    return <span className={className}>{format(0)}</span>;
  }

  return <motion.span className={className}>{display}</motion.span>;
}
