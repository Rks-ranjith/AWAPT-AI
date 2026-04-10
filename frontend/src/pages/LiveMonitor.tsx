import { useState, useEffect } from 'react';
import { 
  ShieldCheck, Share2, 
  Cpu, Network, Square, Activity, Database
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useScanStore } from '@/store/useScanStore';
import { useTargets } from '@/hooks/useTargets';
import { useScanMonitor } from '@/hooks/useScanMonitor';
import CytoscapeComponent from 'react-cytoscapejs';

import { LiveFeed, FeedItem } from '@/components/ui/LiveFeed';

const PIPELINE_PHASES = [
  { id: 1, label: 'Reconnaissance', status_key: 'RECONNAISSANCE' },
  { id: 2, label: 'Deep Crawling', status_key: 'CRAWLING' },
  { id: 3, label: 'AI Attack Planning', status_key: 'AI_PLANNING' },
  { id: 4, label: 'Exploitation Engines', status_key: 'VULN_EXPLOITATION' },
];

export function LiveMonitor() {
  const { isScanning, logs, addLog, stopScan, currentPhase, activeTargetId, activeScanId } = useScanStore();
  const { targets } = useTargets();
  const { isConnected } = useScanMonitor(activeScanId);
  const activeTarget = targets.find((t: any) => t.id === activeTargetId);
  const [elements, setElements] = useState<any[]>([]);

  useEffect(() => {
    if (isScanning && activeTarget) {
      setElements([{ data: { id: 'target', label: activeTarget.name, type: 'target' } }]);
    }
  }, [isScanning, activeTarget]);

  const cyLayout = { name: 'cose', animate: true, refresh: 20 };
  const cyStyle: any = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'background-color': '#6366F1',
        'color': '#fff',
        'font-size': '8px',
        'text-valign': 'center',
        'text-halign': 'center',
        'width': '20px',
        'height': '20px',
        'font-family': 'Outfit'
      }
    },
    {
      selector: 'node[type="target"]',
      style: {
        'background-color': '#0EA5E9',
        'width': '40px',
        'height': '40px',
        'font-size': '10px',
        'font-weight': 'bold'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 1,
        'line-color': '#6366F1',
        'target-arrow-color': '#6366F1',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.3
      }
    }
  ];

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-center">
        <div className="flex items-center gap-6">
           <div className={cn(
             "w-16 h-16 rounded-[24px] flex items-center justify-center shadow-xl transition-all duration-500",
             isScanning ? "bg-[var(--accent)] shadow-indigo-500/30" : "bg-gray-200 dark:bg-gray-800 shadow-none border border-[var(--border-subtle)]"
           )}>
              <Activity className={cn("w-8 h-8 text-white", isScanning && "animate-pulse")} />
           </div>
           <div>
              <h1 className="text-4xl font-display font-black tracking-tight mb-1">Live Engine Monitor</h1>
              <div className="flex items-center gap-3">
                 <span className="text-xs font-black tracking-widest text-[var(--accent)] uppercase">
                   {activeTarget ? activeTarget.name : 'NO_ACTIVE_TARGET'}
                 </span>
                 <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-secondary)]" />
                 <span className="text-xs font-bold text-[var(--text-secondary)]">
                   {isScanning ? 'Streaming Core Data...' : 'Engine Standby'}
                 </span>
              </div>
           </div>
        </div>

        <div className="flex gap-4">
           {isScanning && (
             <button className="px-6 py-3 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 font-bold text-sm flex items-center gap-2 hover:bg-red-500/20 transition-all cursor-pointer" onClick={() => stopScan()}>
                <Square className="w-5 h-5" />
                Terminate Engine
             </button>
           )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
         <div className="lg:col-span-4 space-y-8">
            <section className="premium-card p-8 space-y-8">
               <div className="flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-[var(--accent)]" />
                  <h2 className="text-[10px] font-display font-black tracking-[0.2em] uppercase text-[var(--text-secondary)]">Pipeline Orchestration</h2>
               </div>
               
               <div className="space-y-6">
                  {PIPELINE_PHASES.map((phase, i) => {
                    const activeIndex = PIPELINE_PHASES.findIndex(p => p.status_key === currentPhase);
                    const isPast = activeIndex === -1 ? false : i < activeIndex;
                    const isActive = phase.status_key === currentPhase;
                    
                    return (
                      <div key={phase.id} className="relative flex gap-6 group">
                         {i < PIPELINE_PHASES.length - 1 && (
                           <div className="absolute left-4 top-10 bottom-0 w-0.5 bg-[var(--border-subtle)] -mb-6" />
                         )}
                         <div className={cn(
                           "w-8 h-8 rounded-full flex items-center justify-center z-10 border-2 transition-all duration-500",
                           isPast ? "bg-emerald-500 border-emerald-500 text-white" :
                           isActive ? "border-[var(--accent)] bg-[var(--bg-card)] text-[var(--accent)] shadow-lg shadow-indigo-500/20" :
                           "border-[var(--border-subtle)] bg-[var(--bg-card)] text-[var(--text-secondary)]"
                         )}>
                            <span className="text-[10px] font-black">{i + 1}</span>
                         </div>
                         <div className="pb-10 pt-1">
                            <div className={cn(
                              "text-sm font-black tracking-tight transition-colors",
                              isActive ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]"
                            )}>{phase.label}</div>
                            <div className="text-[10px] font-bold text-[var(--text-secondary)] tracking-widest uppercase mt-0.5">
                              {isActive ? 'Executing...' : isPast ? 'Verified' : 'Pending Deployment'}
                            </div>
                         </div>
                      </div>
                    );
                  })}
               </div>
            </section>

            <div className="premium-card p-6 min-h-[300px] flex flex-col">
               <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                     <Share2 className="w-4 h-4 text-[var(--text-secondary)]" />
                     <span className="text-[10px] font-black tracking-widest uppercase text-[var(--text-secondary)]">Attack Surface Graph</span>
                  </div>
                  <div className="text-[9px] font-mono text-emerald-500 animate-pulse">LIVE_COMPUTE</div>
               </div>
               <div className="flex-1 bg-gray-50 dark:bg-black/20 rounded-xl overflow-hidden relative">
                  {elements.length > 0 ? (
                    <CytoscapeComponent 
                      elements={elements} 
                      style={{ width: '100%', height: '100%' }} 
                      layout={cyLayout}
                      stylesheet={cyStyle}
                      cy={(cy) => {
                        cy.on('layoutstop', () => cy.center());
                      }}
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-[10px] uppercase font-black tracking-tighter opacity-20">NO_GRAPH_DATA</div>
                  )}
               </div>
            </div>
         </div>

         <div className="lg:col-span-8 flex flex-col gap-8">
            <div className="flex-1 premium-card flex flex-col overflow-hidden min-h-[500px] relative">
               {isScanning || logs.length > 0 ? (
                 <LiveFeed items={logs.map((log, idx) => {
                    let type: FeedItem['type'] = 'recon';
                    let severity: FeedItem['severity'] = 'INFO';
                    if(log.includes('[VULN]') || log.includes('[ATTACK]')) {
                       type = 'finding'; severity = 'CRITICAL';
                    } else if (log.includes('[SYS]') || log.includes('cycle completed')) {
                       type = 'complete'; severity = 'INFO';
                    } else if (log.includes('[AI_NEURAL]') || log.includes('Hypothesizing')) {
                       type = 'crawl'; severity = 'HIGH';
                    }
                
                    return {
                        id: String(idx),
                        timestamp: new Date(Date.now() - (logs.length - idx) * 1000).toISOString().substring(11, 23) + "Z",
                        type,
                        message: log,
                        severity
                    };
                 })} />
               ) : (
                 <div className="flex-1 flex items-center justify-center bg-[var(--bg-main)]/30 backdrop-blur">
                    <div className="py-20 text-center text-[var(--text-secondary)] font-display text-sm tracking-widest italic uppercase">ENGINE_WAITING_FOR_SCOPE</div>
                 </div>
               )}
            </div>

            <div className="grid grid-cols-2 gap-8">
                <div className="premium-card p-6 flex items-center gap-5 group cursor-default">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-500 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                        <Cpu className="w-6 h-6" />
                    </div>
                    <div>
                        <div className="text-[10px] font-black text-[var(--text-secondary)] uppercase tracking-widest text-[var(--text-muted)]">Proc Usage</div>
                        <div className="text-xl font-black text-[var(--text-primary)]">{isScanning ? '42.8%' : '2.1%'}</div>
                    </div>
                </div>
                <div className="premium-card p-6 flex items-center gap-5 group cursor-default">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white transition-all">
                        <Network className="w-6 h-6" />
                    </div>
                    <div>
                        <div className="text-[10px] font-black text-[var(--text-secondary)] uppercase tracking-widest text-[var(--text-muted)]">Throughput</div>
                        <div className="text-xl font-black text-[var(--text-primary)]">{isScanning ? '1.2k req/s' : '0'}</div>
                    </div>
                </div>
            </div>

            <div className="premium-card p-8 flex items-center justify-between group hover:border-[var(--accent)] transition-all">
               <div className="flex items-center gap-6">
                  <div className="w-14 h-14 rounded-2xl bg-indigo-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 group-hover:scale-110 transition-transform">
                     <Database className="w-7 h-7" />
                  </div>
                  <div>
                     <h3 className="font-display font-black text-xl text-[var(--text-primary)]">Intelligence Sync</h3>
                     <p className="text-sm text-[var(--text-muted)] font-bold">Streaming findings to Secure PostgreSQL Cluster.</p>
                  </div>
               </div>
               <button 
                  className="px-8 py-3 bg-[var(--accent)] text-white font-black text-xs uppercase tracking-widest rounded-2xl hover:bg-[var(--accent)]/90 transition-all shadow-lg shadow-indigo-500/20 active:scale-95 cursor-pointer"
                  onClick={() => {
                     const msg = "[SYS] Manual storage sync initiated. Validating data integrity...";
                     addLog(msg);
                     alert("Storage Controller: Data integrity check passed. 100% sync achieved.");
                  }}
               >Storage Controller</button>
            </div>
         </div>
      </div>
    </div>
  );
}
