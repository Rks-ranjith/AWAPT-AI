import {
  BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import {
  AlertTriangle,
  ShieldAlert, Activity
} from 'lucide-react';
import { useFindingStore } from '@/store/useFindingStore';
import { useState, useEffect } from 'react';

const COLORS = ['#6366F1', '#0EA5E9', '#F59E0B', '#EF4444'];

export function Analytics() {
  const { summary, fetchSummary, findings, fetchFindings } = useFindingStore();
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([fetchSummary(), fetchFindings()]);
        setIsLoaded(true);
      } catch (err) {}
    };
    init();
  }, [fetchSummary, fetchFindings]);

  const VULN_DIST = [
    { name: 'SQL Injection', value: findings.filter(f => f.vuln_class === 'SQL_INJECTION').length },
    { name: 'XSS', value: findings.filter(f => f.vuln_class.includes('XSS')).length },
    { name: 'CSRF', value: findings.filter(f => f.vuln_class === 'CSRF').length },
    { name: 'Other', value: findings.filter(f => !['SQL_INJECTION', 'XSS', 'CSRF'].includes(f.vuln_class)).length },
  ].filter(d => d.value > 0);

  const SEVERITY_DATA = [
    { name: 'Critical', value: summary?.critical || 0, color: '#EF4444' },
    { name: 'High', value: summary?.high || 0, color: '#F59E0B' },
    { name: 'Medium', value: summary?.medium || 0, color: '#0EA5E9' },
    { name: 'Low', value: summary?.low || 0, color: '#6366F1' },
  ];

  if (!isLoaded) {
    return <div className="h-full flex items-center justify-center opacity-40">CALCULATING_ANALYTICS...</div>;
  }

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header>
        <h1 className="text-4xl font-display font-black tracking-tight mb-2">Security Analytics</h1>
        <p className="text-lg text-[var(--text-secondary)] font-body">Deep intelligence insights and vulnerability distribution metrics.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
         {/* Vulnerability Distribution */}
         <div className="premium-card p-8 flex flex-col gap-6">
            <div className="flex items-center gap-3">
               <AlertTriangle className="w-5 h-5 text-amber-500" />
               <h2 className="text-sm font-black tracking-widest uppercase text-[var(--text-secondary)]">Vulnerability Distribution</h2>
            </div>
            <div className="h-64">
               <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                     <Pie
                       data={VULN_DIST.length > 0 ? VULN_DIST : [{name: 'Empty', value: 1}]}
                       cx="50%"
                       cy="50%"
                       innerRadius={60}
                       outerRadius={80}
                       paddingAngle={5}
                       dataKey="value"
                     >
                       {VULN_DIST.map((_, index) => (
                         <Cell key={index} fill={COLORS[index % COLORS.length]} />
                       ))}
                       {VULN_DIST.length === 0 && <Cell fill="#ccc" opacity={0.1} />}
                     </Pie>
                     <Tooltip />
                     <Legend />
                  </PieChart>
               </ResponsiveContainer>
            </div>
         </div>

         {/* Severity Breakdown */}
         <div className="premium-card p-8 flex flex-col gap-6">
            <div className="flex items-center gap-3">
               <ShieldAlert className="w-5 h-5 text-red-500" />
               <h2 className="text-sm font-black tracking-widest uppercase text-[var(--text-secondary)]">Severity Breakdown</h2>
            </div>
            <div className="h-64">
               <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={SEVERITY_DATA}>
                     <XAxis dataKey="name" fontSize={10} axisLine={false} tickLine={false} />
                     <YAxis fontSize={10} axisLine={false} tickLine={false} />
                     <Tooltip />
                     <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {SEVERITY_DATA.map((entry, index) => (
                          <Cell key={index} fill={entry.color} />
                        ))}
                     </Bar>
                  </BarChart>
               </ResponsiveContainer>
            </div>
         </div>

         {/* Attack Surface Metrics */}
         <div className="premium-card p-8 lg:col-span-2 space-y-8">
            <div className="flex items-center justify-between">
               <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-emerald-500" />
                  <h2 className="text-sm font-black tracking-widest uppercase text-[var(--text-secondary)]">Platform Velocity</h2>
               </div>
               <div className="flex gap-4">
                  <div className="flex items-center gap-2">
                     <div className="w-3 h-3 rounded-full bg-indigo-500 shadow-glow shadow-indigo-500/50" />
                     <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-secondary)]">Active_Probes</span>
                  </div>
               </div>
            </div>
            <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={[
                      { name: '10:00', val: 30 },
                      { name: '11:00', val: 55 },
                      { name: '12:00', val: 45 },
                      { name: '13:00', val: 80 },
                      { name: '14:00', val: 120 },
                      { name: '15:00', val: 110 },
                    ]}>
                        <XAxis dataKey="name" fontSize={10} hide />
                        <Tooltip />
                        <Line type="monotone" dataKey="val" stroke="#6366F1" strokeWidth={3} dot={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
         </div>
      </div>
    </div>
  );
}
