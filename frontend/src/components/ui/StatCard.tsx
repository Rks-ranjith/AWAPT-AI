import { cn } from '@/lib/utils';
import { GlassPanel } from './GlassPanel';
import { AnimatedNumber } from './AnimatedNumber';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface StatCardProps {
  label: string;
  value: number;
  trend?: number; 
  sparkline?: number[];
  accentColor?: string;
  prefix?: string;
  suffix?: string;
  animated?: boolean;
  delay?: number;
}

export function StatCard({ 
  label, 
  value, 
  trend, 
  sparkline = [], 
  accentColor = '#00D4FF',
  prefix,
  suffix,
  animated = true,
  delay = 0
}: StatCardProps) {
  const isCritical = label.toUpperCase().includes('CRITICAL') && value > 0;
  const actualAccent = isCritical ? '#FF2D55' : accentColor;
  
  // Transform sparkline array into objects for recharts
  const chartData = sparkline.map((val, i) => ({ value: val, index: i }));

  return (
    <GlassPanel 
      animated={animated} 
      delay={delay} 
      highlightColor={actualAccent}
      className={cn(
        "flex flex-col h-[110px] p-4",
        isCritical && "animate-[pulse_2s_infinite]"
      )}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-[#4A5568] text-[11px] font-display font-bold tracking-[0.1em] drop-shadow-sm">
          {label}
        </span>
        
        {trend !== undefined && (
          <span 
            className={cn(
              "text-[10px] font-data bg-[#111827] px-1.5 py-0.5 border",
              trend > 0 ? "text-[#FF2D55] border-[#FF2D55]/30 drop-shadow-[0_0_5px_rgba(255,45,85,0.4)]" : trend < 0 ? "text-[#00FF88] border-[#00FF88]/30 drop-shadow-[0_0_5px_rgba(0,255,136,0.4)]" : "text-[#4A5568] border-[#4A5568]/30"
            )}
          >
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      
      <div className="mt-auto flex items-end justify-between relative h-full">
        <div className="flex items-baseline gap-[2px] relative z-10 w-1/2">
          {prefix && <span className="text-xl text-[#00D4FF] font-data">{prefix}</span>}
          <AnimatedNumber 
            value={value} 
            className="text-[32px] font-data text-white leading-none tracking-tight drop-shadow-[0_0_8px_rgba(255,255,255,0.3)]"
          />
          {suffix && <span className="text-[10px] text-[#4A5568] font-display ml-1 tracking-widest">{suffix}</span>}
        </div>
        
        {/* Awesome React Recharts Sparkline */}
        {chartData.length > 0 && (
          <div className="absolute right-0 bottom-0 w-[55%] h-[40px] opacity-80 pointer-events-none">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={`color-${label}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={actualAccent} stopOpacity={0.4}/>
                    <stop offset="95%" stopColor={actualAccent} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke={actualAccent} 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill={`url(#color-${label})`} 
                  isAnimationActive={true}
                  animationDuration={1500}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </GlassPanel>
  );
}
