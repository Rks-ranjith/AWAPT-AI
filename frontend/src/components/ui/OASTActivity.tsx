import { useState, useEffect } from 'react';
import { Activity, Globe, ShieldAlert, Clock, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Interaction {
  token: string;
  client_ip: string;
  method: string;
  headers: Record<string, string>;
  query_params: Record<string, string>;
  body: string | null;
  timestamp: string;
}

export function OASTActivity() {
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(true);

  // Poll for global OAST activity (in a real app, this would be a WebSocket)
  useEffect(() => {
    const fetchOAST = async () => {
      try {
        const res = await fetch('/api/v1/oast/all'); 
        const data = await res.json();
        setInteractions(data);
      } catch (err) {
        console.error("OAST Fetch Error", err);
      } finally {
        setLoading(false);
      }
    };

    fetchOAST();
    const interval = setInterval(fetchOAST, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="premium-card bg-[var(--bg-card)]/50 backdrop-blur-xl border border-[var(--border-subtle)] rounded-[32px] p-8 h-full flex flex-col">
       <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
             <div className="p-2 bg-indigo-500/10 rounded-xl">
                <Activity className="w-5 h-5 text-indigo-400" />
             </div>
             <div>
                <h3 className="font-display font-black text-lg tracking-tight uppercase italic">OAST Interaction Stream</h3>
                <p className="text-[10px] text-[var(--text-secondary)] font-mono tracking-widest uppercase">Live Out-of-Band Callbacks</p>
             </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 rounded-full border border-emerald-500/20">
             <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
             <span className="text-[10px] font-black text-emerald-500 uppercase tracking-tighter">Listener Active</span>
          </div>
       </div>

       <div className="flex-1 overflow-y-auto space-y-4 no-scrollbar">
          {interactions.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center opacity-30 italic text-sm space-y-4">
               <Globe className="w-10 h-10 animate-spin-slow" />
               <p className="font-display">Awaiting Asynchronous Callbacks...</p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
               {interactions.map((item, idx) => (
                 <motion.div 
                   key={idx}
                   initial={{ opacity: 0, x: -20 }}
                   animate={{ opacity: 1, x: 0 }}
                   className="p-5 rounded-2xl bg-[var(--bg-main)]/50 border border-[var(--border-subtle)] group hover:border-indigo-500/30 transition-all flex items-center justify-between"
                 >
                    <div className="flex items-center gap-4">
                       <div className="p-2.5 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                          <ShieldAlert className="w-4 h-4 text-indigo-400" />
                       </div>
                       <div>
                          <div className="flex items-center gap-2">
                             <span className="text-xs font-black font-mono text-indigo-400">{item.token}</span>
                             <span className="text-[9px] bg-indigo-500/10 px-1.5 rounded text-indigo-300 font-bold uppercase">{item.method}</span>
                          </div>
                          <div className="text-[10px] text-[var(--text-secondary)] font-mono">{item.client_ip}</div>
                       </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                       <div className="flex items-center gap-1 text-[9px] text-[var(--text-secondary)] font-mono">
                          <Clock className="w-3 h-3" />
                          {new Date(item.timestamp).toLocaleTimeString()}
                       </div>
                       <ChevronRight className="w-4 h-4 text-[var(--text-secondary)] opacity-0 group-hover:opacity-100 transition-all" />
                    </div>
                 </motion.div>
               ))}
            </AnimatePresence>
          )}
       </div>
    </div>
  );
}
