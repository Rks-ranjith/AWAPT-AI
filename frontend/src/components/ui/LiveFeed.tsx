import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { GlassPanel } from './GlassPanel';
import { ShieldAlert, Crosshair, Terminal, Activity, FileSearch } from 'lucide-react';

export type FeedEventType = 'recon' | 'crawl' | 'finding' | 'complete';

export interface FeedItem {
  id: string;
  timestamp: string;
  type: FeedEventType;
  message: string;
  severity?: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

interface LiveFeedProps {
  items: FeedItem[];
  maxItems?: number;
}

const typeConfig = {
  recon: { icon: FileSearch, color: 'text-[#00D4FF]', bg: 'bg-[#00D4FF]/10', border: 'border-[#00D4FF]' },
  crawl: { icon: Crosshair, color: 'text-[#FFB800]', bg: 'bg-[#FFB800]/10', border: 'border-[#FFB800]' },
  finding: { icon: ShieldAlert, color: 'text-[#FF2D55]', bg: 'bg-[#FF2D55]/10', border: 'border-[#FF2D55]' },
  complete: { icon: Activity, color: 'text-[#00FF88]', bg: 'bg-[#00FF88]/10', border: 'border-[#00FF88]' }
};

export function LiveFeed({ items, maxItems = 50 }: LiveFeedProps) {
  const [isPaused, setIsPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const displayItems = items.slice(-maxItems);

  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [items, isPaused]);

  return (
    <GlassPanel className="flex flex-col h-full absolute inset-0 font-body text-sm overflow-hidden" highlightColor="#00D4FF">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#00D4FF]/20 bg-[#0D1117] z-10 font-display">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#00D4FF] drop-shadow-[0_0_8px_rgba(0,212,255,0.8)]" />
          <span className="text-[#00D4FF] text-xs font-bold tracking-[0.2em] shadow-[#00D4FF] drop-shadow-sm">LIVE ACTIVITY STREAM</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[#4A5568] text-[9px] tracking-[0.2em]">
            {isPaused ? "[PAUSED]" : "[STREAMING]"}
          </span>
          <div className={cn("w-1.5 h-1.5 rounded-none", isPaused ? "bg-amber-500" : "bg-[#00D4FF] animate-pulse shadow-[0_0_8px_rgba(0,212,255,1)]")} />
        </div>
      </div>
      
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 space-y-[4px] scroll-smooth scrollbar-hide bg-[#080B14]/80"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        <AnimatePresence initial={false}>
          {displayItems.map((item) => {
            const Config = typeConfig[item.type];
            const Icon = Config.icon;
            void Icon; // used in JSX below via Config.icon
            
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -10, y: 10 }}
                animate={{ opacity: 1, x: 0, y: 0 }}
                exit={{ opacity: 0, transition: { duration: 0.1 } }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className={cn(
                  "flex items-start gap-3 p-2 border-l-2 bg-gradient-to-r from-[#0D1117] to-transparent",
                  Config.border
                )}
              >
                <div className="flex-shrink-0 w-16 text-[10px] text-[#4A5568] pt-[2px] font-data tracking-wide">
                  [{item.timestamp}]
                </div>

                <div className="flex-1 flex flex-col">
                   <div className="flex items-center gap-2 mb-1 uppercase font-display">
                      <span className={cn("text-[9px] font-bold tracking-widest px-1 py-0.5 rounded-sm shadow-sm", Config.bg, Config.color)}>
                        {item.type}
                      </span>
                      {item.severity && item.severity !== 'INFO' && (
                        <span className="text-[9px] px-1 py-0.5 rounded-sm font-bold bg-[#FF2D55]/20 text-[#FF2D55] border border-[#FF2D55]/30 drop-shadow-[0_0_5px_rgba(255,45,85,0.5)] tracking-widest">
                          {item.severity}
                        </span>
                      )}
                    </div>
                  <span className="text-[12px] text-[var(--text-primary)] font-data break-all opacity-90">{item.message}</span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </GlassPanel>
  );
}
