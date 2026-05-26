import {
  BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import {
  AlertTriangle,
  ShieldAlert, Activity, History, Shield, RefreshCw
} from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { cn } from '@/lib/utils';

const COLORS = ['#6366F1', '#0EA5E9', '#F59E0B', '#EF4444'];

interface Scan {
  id: string;
  target_id: string;
  state: string;
  profile: string;
  progress: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

interface Target {
  id: string;
  domain: string;
  name: string;
  base_url: string;
}

interface Finding {
  id: string;
  vuln_class: string;
  severity: string;
  url: string;
  discovered_at: string;
}

export function Analytics() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string>('');
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [scansRes, targetsRes] = await Promise.all([
        axios.get('/api/v1/scans?limit=100'),
        axios.get('/api/v1/targets?limit=100')
      ]);
      setScans(scansRes.data);
      setTargets(targetsRes.data);
      if (scansRes.data.length > 0) {
        const currentStillExists = scansRes.data.some((s: Scan) => s.id === selectedScanId);
        if (!selectedScanId || !currentStillExists) {
          // Select the most recent completed scan, fallback to index 0
          const completedScan = scansRes.data.find((s: Scan) => s.state === 'COMPLETE');
          setSelectedScanId(completedScan ? completedScan.id : scansRes.data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load analytics details:", err);
    } finally {
      setIsLoaded(true);
      if (isRefresh) setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedScanId) return;
    const fetchSelectedFindings = async () => {
      setLoadingFindings(true);
      try {
        const { data } = await axios.get(`/api/v1/scans/${selectedScanId}/findings`);
        setFindings(data);
      } catch (err) {
        console.error("Failed to fetch scan findings:", err);
      } finally {
        setLoadingFindings(false);
      }
    };
    fetchSelectedFindings();
  }, [selectedScanId]);

  const VULN_DIST = useMemo(() => {
    const counts: Record<string, number> = {};
    findings.forEach(f => {
      counts[f.vuln_class] = (counts[f.vuln_class] || 0) + 1;
    });
    return Object.entries(counts).map(([key, val]) => {
      const readableName = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      return { name: readableName, value: val };
    });
  }, [findings]);

  const SEVERITY_DATA = useMemo(() => {
    const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
    findings.forEach(f => {
      if (f.severity === 'CRITICAL') counts.Critical++;
      else if (f.severity === 'HIGH') counts.High++;
      else if (f.severity === 'MEDIUM') counts.Medium++;
      else if (f.severity === 'LOW') counts.Low++;
    });
    return [
      { name: 'Critical', value: counts.Critical, color: '#EF4444' },
      { name: 'High', value: counts.High, color: '#F59E0B' },
      { name: 'Medium', value: counts.Medium, color: '#0EA5E9' },
      { name: 'Low', value: counts.Low, color: '#6366F1' },
    ];
  }, [findings]);

  const velocityData = useMemo(() => {
    if (!findings || findings.length === 0) {
      return [
        { name: '09:00', val: 0 },
        { name: '10:00', val: 0 },
        { name: '11:00', val: 0 },
        { name: '12:00', val: 0 },
      ];
    }
    const counts: Record<string, number> = {};
    findings.forEach(f => {
      const d = new Date(f.discovered_at);
      const hour = `${d.getHours().toString().padStart(2, '0')}:00`;
      counts[hour] = (counts[hour] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([name, val]) => ({ name, val }));
  }, [findings]);

  const activeScan = useMemo(() => {
    return scans.find(s => s.id === selectedScanId);
  }, [scans, selectedScanId]);

  const activeTarget = useMemo(() => {
    if (!activeScan) return null;
    return targets.find(t => t.id === activeScan.target_id);
  }, [targets, activeScan]);

  if (!isLoaded) {
    return <div className="h-full flex items-center justify-center opacity-40">CALCULATING_ANALYTICS...</div>;
  }

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Security Analytics</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">Deep intelligence insights and vulnerability distribution metrics.</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="p-3 border border-[var(--border-subtle)] hover:border-[var(--accent)] hover:bg-[var(--accent)]/5 rounded-2xl flex items-center justify-center transition-all disabled:opacity-50"
            title="Refresh Scan Data"
          >
             <RefreshCw className={cn("w-5 h-5 text-[var(--text-secondary)]", refreshing && "animate-spin")} />
          </button>
          {activeTarget && (
            <div className="bg-[var(--accent)]/10 border border-[var(--accent)]/20 px-5 py-3 rounded-2xl flex items-center gap-3">
               <Shield className="w-5 h-5 text-[var(--accent)] animate-pulse" />
               <div>
                  <div className="text-[10px] font-black uppercase text-[var(--text-secondary)] tracking-widest">Active Scan Focus</div>
                  <div className="text-sm font-black text-[var(--text-primary)]">{activeTarget.name}</div>
               </div>
            </div>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
         {/* Vulnerability Distribution */}
         <div className="premium-card p-8 flex flex-col gap-6 relative">
            {loadingFindings && (
               <div className="absolute inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center rounded-[32px] z-20">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 animate-pulse">Updating...</span>
               </div>
            )}
            <div className="flex items-center gap-3">
               <AlertTriangle className="w-5 h-5 text-amber-500" />
               <h2 className="text-sm font-black tracking-widest uppercase text-[var(--text-secondary)]">Vulnerability Distribution</h2>
            </div>
            <div className="h-64 flex flex-col justify-center items-center">
               {VULN_DIST.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                     <PieChart>
                        <Pie
                          data={VULN_DIST}
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
                        </Pie>
                        <Tooltip />
                        <Legend />
                     </PieChart>
                  </ResponsiveContainer>
               ) : (
                  <div className="text-center py-10 opacity-40">
                     <Shield className="w-12 h-12 text-emerald-500 mx-auto mb-2 opacity-50" />
                     <p className="text-xs font-bold uppercase tracking-wider">No Vulnerabilities Discovered</p>
                  </div>
               )}
            </div>
         </div>

         {/* Severity Breakdown */}
         <div className="premium-card p-8 flex flex-col gap-6 relative">
            {loadingFindings && (
               <div className="absolute inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center rounded-[32px] z-20">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 animate-pulse">Updating...</span>
               </div>
            )}
            <div className="flex items-center gap-3">
               <ShieldAlert className="w-5 h-5 text-red-500" />
               <h2 className="text-sm font-black tracking-widest uppercase text-[var(--text-secondary)]">Severity Breakdown</h2>
            </div>
            <div className="h-64 flex flex-col justify-center items-center">
               {findings.length > 0 ? (
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
               ) : (
                  <div className="text-center py-10 opacity-40">
                     <Shield className="w-12 h-12 text-emerald-500 mx-auto mb-2 opacity-50" />
                     <p className="text-xs font-bold uppercase tracking-wider">No Vulnerabilities Discovered</p>
                  </div>
               )}
            </div>
         </div>

         {/* Attack Surface Metrics */}
         <div className="premium-card p-8 lg:col-span-2 space-y-8 relative">
            {loadingFindings && (
               <div className="absolute inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center rounded-[32px] z-20">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 animate-pulse">Updating...</span>
               </div>
            )}
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
            <div className="h-64 flex flex-col justify-center items-center">
               {findings.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                     <LineChart data={velocityData}>
                         <XAxis dataKey="name" fontSize={10} hide />
                         <Tooltip />
                         <Line type="monotone" dataKey="val" stroke="#6366F1" strokeWidth={3} dot={false} />
                     </LineChart>
                  </ResponsiveContainer>
               ) : (
                  <div className="text-center py-10 opacity-40">
                     <Activity className="w-12 h-12 text-emerald-500 mx-auto mb-2 opacity-50" />
                     <p className="text-xs font-bold uppercase tracking-wider">No Probe Velocity Data</p>
                  </div>
               )}
            </div>
         </div>
      </div>

      {/* Scan History Section */}
      <section className="space-y-6">
         <div className="flex items-center gap-3 px-2">
            <History className="w-5 h-5 text-indigo-400" />
            <h2 className="text-xl font-display font-black tracking-tight">Scan Run History</h2>
         </div>
         <div className="premium-card overflow-hidden">
            <div className="overflow-y-auto max-h-96 divide-y divide-[var(--border-subtle)] scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
               {scans.map((scan) => {
                  const target = targets.find(t => t.id === scan.target_id);
                  const isSelected = selectedScanId === scan.id;
                  return (
                     <div 
                        key={scan.id}
                        onClick={() => setSelectedScanId(scan.id)}
                        className={cn(
                           "flex justify-between items-center p-6 cursor-pointer transition-all hover:bg-[var(--accent)]/[0.03]",
                           isSelected && "bg-[var(--accent)]/[0.08] border-l-4 border-[var(--accent)]"
                        )}
                     >
                        <div className="space-y-1">
                           <div className="font-bold text-sm text-[var(--text-primary)]">
                              {target ? target.name : 'Unknown Target'}
                           </div>
                           <div className="text-xs text-[var(--text-secondary)] font-mono">
                              Scan ID: {scan.id} · {new Date(scan.created_at).toLocaleString()}
                           </div>
                        </div>
                        <div className="flex items-center gap-6">
                           <span className={cn(
                             "px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase",
                             scan.state === 'COMPLETE' ? "bg-emerald-500/10 text-emerald-500" :
                             scan.state === 'FAILED' ? "bg-red-500/10 text-red-500" : "bg-blue-500/10 text-blue-500"
                           )}>
                              {scan.state}
                           </span>
                           <span className="text-xs font-mono font-bold text-[var(--text-secondary)] w-12 text-right">
                              {scan.progress}%
                           </span>
                        </div>
                     </div>
                  );
               })}
               {scans.length === 0 && (
                  <div className="p-12 text-center opacity-40 font-bold">No scan sessions recorded.</div>
               )}
            </div>
         </div>
      </section>
    </div>
  );
}
