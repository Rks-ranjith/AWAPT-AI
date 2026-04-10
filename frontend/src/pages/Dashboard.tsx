import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { 
  Shield, Target, Activity, 
  ArrowUpRight, CheckCircle2, ShieldAlert
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { 
  LineChart, Line, ResponsiveContainer
} from 'recharts';
import { cn } from '@/lib/utils';
import { useFindingStore } from '@/store/useFindingStore';
import { useScanStore } from '@/store/useScanStore';
import { OASTActivity } from '@/components/ui/OASTActivity';

const MOCK_CHART_DATA = [
  { name: '00:00', value: 30 },
  { name: '04:00', value: 45 },
  { name: '08:00', value: 35 },
  { name: '12:00', value: 65 },
  { name: '16:00', value: 50 },
  { name: '20:00', value: 80 },
  { name: '24:00', value: 75 },
];

export function Dashboard() {
  const navigate = useNavigate();
  const { summary, fetchSummary, findings, fetchFindings } = useFindingStore();
  const { isScanning } = useScanStore();
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([fetchSummary(), fetchFindings()]);
      } catch (err) {
        console.error("Dashboard init error:", err);
      } finally {
        setIsLoaded(true);
      }
    };
    init();
    const interval = setInterval(init, 5000);
    return () => clearInterval(interval);
  }, [fetchSummary, fetchFindings]);

  const STATS = [
    { label: 'Active Scans', value: isScanning ? '1' : '0', change: isScanning ? '+1' : '0', icon: Activity, color: 'text-blue-500', data: MOCK_CHART_DATA.map(d => ({ ...d, value: Math.random() * 100 })) },
    { label: 'Total Assets', value: summary?.targets_count?.toString() || '0', change: 'Live', icon: Target, color: 'text-indigo-500', data: MOCK_CHART_DATA },
    { label: 'Critical Findings', value: summary?.critical?.toString() || '0', change: (summary?.critical || 0) > 0 ? '+'+summary.critical : '0', icon: Shield, color: 'text-red-500', data: MOCK_CHART_DATA.map(d => ({ ...d, value: Math.random() * 50 })) },
    { label: 'System Health', value: '98%', change: 'Stable', icon: CheckCircle2, color: 'text-emerald-500', data: MOCK_CHART_DATA.map(d => ({ ...d, value: 90 + Math.random() * 10 })) },
  ];

  if (!isLoaded) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
          <div className="text-[10px] font-display font-black tracking-widest uppercase text-[var(--text-secondary)]">Initializing_System_Core</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Command Overview</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">Global security posture and active autonomous operations.</p>
        </div>
        <div className="px-4 py-2 bg-[var(--accent)]/10 text-[var(--accent)] rounded-2xl border border-[var(--accent)]/20 font-bold text-sm">
           Live Intelligence Enabled
        </div>
      </header>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        {STATS.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="premium-card p-6 group cursor-default overflow-hidden flex flex-col"
          >
            <div className="flex justify-between items-start mb-4">
              <div className={cn("p-3 rounded-2xl bg-gray-100 dark:bg-gray-800 transition-colors", stat.color)}>
                <stat.icon className="w-6 h-6" />
              </div>
              <span className={cn(
                "text-xs font-bold font-display px-2 py-1 rounded-lg",
                stat.change.startsWith('+') ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-500"
              )}>
                {stat.change}
              </span>
            </div>
            <div className="mb-4">
              <div className="text-[var(--text-secondary)] text-[10px] font-black uppercase tracking-[0.2em] mb-1">
                {stat.label}
              </div>
              <div className="text-4xl font-display font-black tracking-tight">{stat.value}</div>
            </div>
            
            {/* Sparkline */}
            <div className="h-12 w-full mt-auto -mb-2 -mx-2 opacity-50 group-hover:opacity-100 transition-opacity">
               <ResponsiveContainer width="110%" height="100%">
                  <LineChart data={stat.data}>
                     <Line 
                       type="monotone" 
                       dataKey="value" 
                       stroke="currentColor" 
                       strokeWidth={2} 
                       dot={false} 
                       className={stat.color}
                     />
                  </LineChart>
               </ResponsiveContainer>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
         {/* Live Activity */}
         <div className="lg:col-span-8 space-y-6">
            <div className="flex justify-between items-center px-2">
               <h2 className="text-xl font-display font-bold tracking-tight">System Telemetry</h2>
               <button className="text-sm font-bold text-[var(--accent)] hover:underline flex items-center gap-1">
                  View Full Logs <ArrowUpRight className="w-3 h-3" />
               </button>
            </div>
            
            <div className="premium-card overflow-hidden">
               <div className="p-6 bg-[var(--bg-main)]/30 border-b border-[var(--border-subtle)] flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-bold tracking-[0.2em] uppercase text-[var(--text-secondary)]">Active Stream</span>
               </div>
               <div className="p-0 max-h-[400px] overflow-y-auto no-scrollbar">
                  {!findings || findings.length === 0 ? (
                    <div className="p-20 text-center text-[var(--text-secondary)] font-display text-sm tracking-widest italic uppercase">NO_ACTIVE_FINDINGS_IN_STREAM</div>
                  ) : (
                    findings.map((find: any) => (
                      <div key={find.id} className="flex items-start gap-4 p-6 border-b border-[var(--border-subtle)] hover:bg-[var(--accent)]/[0.04] transition-colors last:border-0 group cursor-pointer" onClick={() => navigate('/findings')}>
                        <div className={cn(
                          "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-lg",
                          find.severity === 'CRITICAL' ? "bg-red-500 text-white shadow-red-500/20" : "bg-amber-500 text-white shadow-amber-500/20"
                        )}>
                           <ShieldAlert className="w-5 h-5" />
                        </div>
                        <div className="flex-1 space-y-1">
                           <div className="flex justify-between items-center">
                              <span className="text-[10px] font-black text-[var(--text-primary)] uppercase tracking-widest">{find.vuln_class}</span>
                              <span className="text-[10px] font-bold text-[var(--text-muted)]">{new Date(find.discovered_at).toLocaleTimeString()}</span>
                           </div>
                           <div className="text-sm font-black tracking-tight text-[var(--text-primary)]">{find.endpoint_url}</div>
                           <div className="text-[10px] font-bold text-[var(--text-muted)] italic">Module: {find.module_id}</div>
                        </div>
                      </div>
                    ))
                  )}
               </div>
            </div>
         </div>

         {/* Vulnerability Summary */}
         <div className="lg:col-span-4 space-y-6">
            <h2 className="text-xl font-display font-bold tracking-tight px-2">Findings Intelligence</h2>
            <div className="space-y-4">
               {findings && findings.slice(0, 3).map((find: any) => (
                 <div key={find.id} className="premium-card p-5 group flex items-center justify-between">
                    <div className="flex items-center gap-4">
                       <div className={cn(
                         "w-2 h-10 rounded-full",
                         find.severity === 'CRITICAL' ? "bg-red-500" : find.severity === 'HIGH' ? "bg-orange-500" : "bg-yellow-500"
                        )} />
                       <div>
                          <div className="text-sm font-black tracking-tight">{find.vuln_class}</div>
                          <div className="text-[10px] font-bold text-[var(--text-secondary)] tracking-widest uppercase">{find.severity}</div>
                       </div>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                       <ArrowUpRight className="w-5 h-5 text-[var(--text-secondary)]" />
                    </div>
                 </div>
               ))}
               {(!findings || findings.length === 0) && (
                 <div className="p-8 premium-card text-center text-[10px] text-[var(--text-secondary)] font-display font-black tracking-[0.2em] uppercase">No_Recent_Incidents</div>
               )}
            </div>

            <OASTActivity />
         </div>
      </div>
    </div>
  );
}
