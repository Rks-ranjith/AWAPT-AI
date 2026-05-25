import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  ShieldAlert, Download, Terminal,
  Bug, ExternalLink, BarChart3,
  Search, Fingerprint, Lock, TerminalSquare,
  Activity, ChevronDown, RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useScanStore } from '@/store/useScanStore';
import { useTargets } from '@/hooks/useTargets';
import { AttackerConsole } from '@/components/ui/AttackerConsole';
import { CvssGauge } from '@/components/ui/CvssGauge';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const API_URL = '/api/v1';

const SEVERITY_RANK: Record<string, number> = {
  CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4,
};

export function Findings() {
  const { isScanning, activeTargetId } = useScanStore();
  const { targets } = useTargets();

  const [findings, setFindings] = useState<any[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Target selector — defaults to the currently active scan target
  const [selectedTargetId, setSelectedTargetId] = useState<string>('ALL');

  // Pre-select active target whenever a scan is running
  useEffect(() => {
    if (activeTargetId) {
      setSelectedTargetId(String(activeTargetId));
    }
  }, [activeTargetId]);

  // ── Data fetch ────────────────────────────────────────────────────────────
  const fetchFindings = useCallback(async () => {
    try {
      let data: any[] = [];

      if (selectedTargetId !== 'ALL') {
        // Find the latest scan for this target
        const scansResp = await axios.get(`${API_URL}/scans`);
        const scansForTarget = (scansResp.data as any[])
          .filter((s: any) => String(s.target_id) === selectedTargetId)
          .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

        if (scansForTarget.length > 0) {
          const latestScanId = scansForTarget[0].id;
          const findingsResp = await axios.get(`${API_URL}/scans/${latestScanId}/findings`);
          data = findingsResp.data;
        }
      } else {
        const resp = await axios.get(`${API_URL}/findings`);
        data = resp.data;
      }

      // Sort by severity then date
      data.sort((a: any, b: any) => {
        const sr = (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99);
        if (sr !== 0) return sr;
        return new Date(b.discovered_at).getTime() - new Date(a.discovered_at).getTime();
      });

      setFindings(data);
      // Auto-select first if nothing is selected or selection no longer exists
      if (data.length > 0 && (!selectedFinding || !data.find((f: any) => f.id === selectedFinding?.id))) {
        setSelectedFinding(data[0]);
      }
    } catch (err) {
      console.error('Failed to fetch findings:', err);
    }
  }, [selectedTargetId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Initial load + re-fetch when target filter changes
  useEffect(() => {
    fetchFindings();
  }, [fetchFindings]);

  // ── 3-second live poll while scan is active ───────────────────────────────
  useEffect(() => {
    if (!isScanning) return;
    const interval = setInterval(() => {
      fetchFindings();
    }, 3000);
    return () => clearInterval(interval);
  }, [isScanning, fetchFindings]);

  // Manual refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchFindings();
    setIsRefreshing(false);
  };

  const filteredFindings = findings.filter((f: any) =>
    f.vuln_class?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (f.url || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const severityColor = (sev: string) => {
    switch (sev) {
      case 'CRITICAL': return 'bg-red-500/10 text-red-500 border border-red-500/20';
      case 'HIGH':     return 'bg-orange-500/10 text-orange-500 border border-orange-500/20';
      case 'MEDIUM':   return 'bg-amber-500/10 text-amber-500 border border-amber-500/20';
      case 'LOW':      return 'bg-blue-500/10 text-blue-500 border border-blue-500/20';
      default:         return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
    }
  };

  return (
    /* ── Root: locked to viewport height so inner columns scroll correctly ── */
    <div className="h-[calc(100vh-5rem)] flex flex-col relative z-10 overflow-hidden">

      {/* Header */}
      <header className="px-10 pt-8 pb-5 flex justify-between items-end flex-shrink-0">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Vulnerability Intelligence</h1>
          <p className="text-sm text-[var(--text-secondary)] font-body">
            Deep analysis of identified security weaknesses.
            {isScanning && (
              <span className="ml-2 inline-flex items-center gap-1 text-emerald-400 font-bold text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE — polling every 3s
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-3 items-center">
          {/* Manual refresh */}
          <button
            onClick={handleRefresh}
            className="p-2.5 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all group"
            title="Refresh findings"
          >
            <RefreshCw className={cn('w-4 h-4 text-[var(--text-secondary)]', isRefreshing && 'animate-spin text-[var(--accent)]')} />
          </button>

          {/* Export PDF */}
          <button
            onClick={async () => {
              if (selectedFinding?.scan_id) {
                try {
                  const { data } = await axios.get(`/api/v1/reports/${selectedFinding.scan_id}/pdf`, { responseType: 'blob' });
                  const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `AWAP_Report_${selectedFinding.scan_id}.pdf`;
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                  window.URL.revokeObjectURL(url);
                } catch {
                  alert('Failed to export PDF report.');
                }
              } else {
                alert('Scan ID not found for this finding.');
              }
            }}
            className="bg-[var(--bg-card)] border border-[var(--border-subtle)] px-4 py-2.5 rounded-2xl flex items-center gap-2 shadow-sm cursor-pointer hover:bg-[var(--bg-main)] transition-all group"
          >
            <Download className="w-4 h-4 text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]" />
            <span className="text-xs font-black tracking-widest uppercase">Export PDF</span>
          </button>
        </div>
      </header>

      {/* ── Target Selector Bar ── */}
      <div className="px-10 pb-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="relative">
            <ChevronDown className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] pointer-events-none" />
            <select
              value={selectedTargetId}
              onChange={(e) => {
                setSelectedTargetId(e.target.value);
                setSelectedFinding(null);
              }}
              className="appearance-none pl-4 pr-9 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] text-sm font-bold outline-none focus:ring-2 ring-indigo-500/20 transition-all cursor-pointer"
            >
              <option value="ALL">All Targets</option>
              {targets.map((t: any) => (
                <option key={t.id} value={String(t.id)}>
                  {t.name || t.domain}
                  {activeTargetId && String(t.id) === String(activeTargetId) ? ' 🔴 LIVE' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <span className="font-black">{filteredFindings.length}</span>
            <span>findings</span>
            {filteredFindings.filter((f: any) => f.severity === 'CRITICAL').length > 0 && (
              <span className="px-2 py-0.5 rounded-lg bg-red-500/10 text-red-500 font-black text-[9px] tracking-widest uppercase border border-red-500/20">
                {filteredFindings.filter((f: any) => f.severity === 'CRITICAL').length} CRITICAL
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Two-column panel ── */}
      <div className="flex-1 flex px-10 gap-8 pb-6 min-h-0 overflow-hidden">

        {/* ── Findings list column — scrolls independently ── */}
        <div className="w-[380px] flex flex-col gap-4 min-h-0">
          {/* Search */}
          <div className="relative flex-shrink-0">
            <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" />
            <input
              placeholder="Filter intelligence..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] text-sm font-body outline-none focus:ring-2 ring-indigo-500/20 shadow-sm"
            />
          </div>

          {/* Scrollable list */}
          <div className="flex-1 overflow-y-auto premium-card rounded-2xl min-h-0">
            {filteredFindings.length === 0 ? (
              <div className="p-10 text-center opacity-30 font-display text-sm italic">
                {isScanning ? 'Waiting for first finding...' : 'NO_FINDINGS_IN_VIEW'}
              </div>
            ) : (
              filteredFindings.map((finding: any) => (
                <div
                  key={finding.id}
                  onClick={() => setSelectedFinding(finding)}
                  className={cn(
                    'p-5 border-b border-[var(--border-subtle)] cursor-pointer transition-all relative group overflow-hidden',
                    selectedFinding?.id === finding.id ? 'bg-[var(--accent)]/[0.04]' : 'hover:bg-[var(--bg-main)]'
                  )}
                >
                  {selectedFinding?.id === finding.id && (
                    <motion.div layoutId="active-find-ring" className="absolute left-0 top-0 bottom-0 w-1 bg-[var(--accent)]" />
                  )}
                  <div className="flex justify-between items-start mb-2">
                    <span className={cn('text-[9px] font-black tracking-[0.2em] px-2 py-0.5 rounded-lg uppercase', severityColor(finding.severity))}>
                      {finding.severity}
                    </span>
                    <span className="text-[10px] text-[var(--text-secondary)] font-mono">
                      {new Date(finding.discovered_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="font-bold text-[var(--text-primary)] mb-1 group-hover:text-[var(--accent)] transition-colors text-sm">
                    {finding.vuln_class}
                  </div>
                  <div className="text-xs text-[var(--text-secondary)] font-mono truncate">{finding.url}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── Detail pane — scrolls independently ── */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <AnimatePresence mode="wait">
            {selectedFinding ? (
              <motion.div
                key={selectedFinding.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="h-full flex flex-col premium-card overflow-hidden bg-[var(--bg-card)]/50 backdrop-blur-xl"
              >
                {/* Sticky header */}
                <div className="p-8 border-b border-[var(--border-subtle)] bg-[var(--bg-main)]/30 space-y-5 flex-shrink-0">
                  <div className="flex justify-between items-start">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <Fingerprint className="w-5 h-5 text-[var(--accent)]" />
                        <span className="text-xs font-black tracking-widest uppercase text-[var(--text-secondary)]">Finding Signature</span>
                      </div>
                      <h2 className="text-3xl font-display font-black tracking-tight">{selectedFinding.vuln_class}</h2>
                    </div>
                    <div className="flex gap-3 flex-wrap justify-end">
                      <button
                        onClick={async () => {
                          try {
                            const { data } = await axios.get(`/api/v1/findings/${selectedFinding.id}/exploit`, { responseType: 'blob' });
                            const url = window.URL.createObjectURL(new Blob([data], { type: 'text/x-python' }));
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = `poc_${selectedFinding.id}.py`;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            window.URL.revokeObjectURL(url);
                          } catch {
                            alert('Failed to download standalone exploit.');
                          }
                        }}
                        className="px-5 py-2.5 rounded-2xl font-bold text-sm transition-all flex items-center gap-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20"
                      >
                        <Download className="w-4 h-4" />
                        Standalone Exploit
                      </button>
                      <button
                        onClick={() => setIsConsoleOpen(true)}
                        className="px-5 py-2.5 rounded-2xl font-bold text-sm transition-all flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/20"
                      >
                        <TerminalSquare className="w-4 h-4" />
                        Interactive Console
                      </button>
                      <button
                        onClick={async () => {
                          if (selectedFinding) {
                            await axios.patch(`/api/v1/findings/${selectedFinding.id}`, { status: 'ESCALATED' });
                            await fetchFindings();
                          }
                        }}
                        className={cn(
                          'px-5 py-2.5 rounded-2xl font-bold text-sm transition-all flex items-center gap-2',
                          selectedFinding.status === 'ESCALATED'
                            ? 'bg-red-500/20 text-red-500 border border-red-500/30'
                            : 'bg-red-500 hover:bg-red-600 text-white shadow-red-500/20'
                        )}
                      >
                        <Lock className="w-4 h-4" />
                        {selectedFinding.status === 'ESCALATED' ? 'Risk Escalated' : 'Escalate Risk'}
                      </button>
                    </div>
                  </div>

                  <div className="flex gap-10 flex-wrap">
                    <div className="space-y-1">
                      <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Resource Path</div>
                      <div className="text-sm font-mono text-[var(--accent)]">{selectedFinding.url}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Method</div>
                      <div className="text-sm font-mono text-[var(--text-primary)]">{selectedFinding.method}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Confidence</div>
                      <div className="text-sm font-mono text-emerald-500">{Math.round((selectedFinding.confidence || 0) * 100)}% Certain</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Severity</div>
                      <span className={cn('text-[9px] font-black tracking-[0.2em] px-2 py-0.5 rounded-lg uppercase', severityColor(selectedFinding.severity))}>
                        {selectedFinding.severity}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto p-8 space-y-10">
                  {/* Technical evidence */}
                  <section className="space-y-5">
                    <div className="flex items-center gap-3">
                      <Terminal className="w-5 h-5 text-[var(--accent)]" />
                      <h3 className="text-lg font-display font-black tracking-tight">Technical Evidence</h3>
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center px-1">
                          <span className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Reproduction Request</span>
                          <span className="text-[9px] font-mono text-emerald-500/60 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10">RAW_HTTP_v1.1</span>
                        </div>
                        <div className="rounded-2xl overflow-hidden border border-white/5 shadow-2xl">
                          <SyntaxHighlighter
                            language="http"
                            style={vscDarkPlus}
                            customStyle={{ margin: 0, padding: '20px', fontSize: '12px', backgroundColor: '#0D0E12' }}
                          >
                            {selectedFinding.request_raw || `GET /api/v1/resource HTTP/1.1\nHost: target.local\nUser-Agent: AWAP-AI/2.0`}
                          </SyntaxHighlighter>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex justify-between items-center px-1">
                          <span className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Target Response Reflection</span>
                          <span className="text-[9px] font-mono text-amber-500/60 bg-amber-500/5 px-2 py-0.5 rounded border border-amber-500/10">SINK_DETECTED</span>
                        </div>
                        <div className="rounded-2xl overflow-hidden border border-white/5 shadow-2xl">
                          <SyntaxHighlighter
                            language="javascript"
                            style={vscDarkPlus}
                            customStyle={{ margin: 0, padding: '20px', fontSize: '12px', backgroundColor: '#0D0E12' }}
                          >
                            {selectedFinding.response_raw ? selectedFinding.response_raw.substring(0, 600) : '// NO_RESPONSE_BODY_CAPTURED'}
                          </SyntaxHighlighter>
                        </div>
                      </div>
                    </div>

                    {/* AI Summary */}
                    {selectedFinding.ai_summary && (
                      <div className="p-8 rounded-[32px] bg-indigo-500/[0.03] border border-indigo-500/10 relative overflow-hidden group shadow-2xl shadow-indigo-500/5 mt-4">
                        <div className="absolute -right-10 -top-10 p-4 opacity-[0.03] group-hover:opacity-[0.07] transition-all duration-700">
                          <Activity className="w-56 h-56 text-indigo-400" />
                        </div>
                        <div className="relative z-10 space-y-4">
                          <div className="flex items-center gap-3">
                            <div className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse shadow-[0_0_10px_rgba(129,140,248,0.5)]" />
                            <span className="text-[10px] font-black tracking-[0.2em] uppercase text-indigo-400">Deep Neural Vulnerability Analysis</span>
                          </div>
                          <div className="text-base font-medium leading-relaxed font-body text-indigo-100/90 whitespace-pre-wrap">
                            {selectedFinding.ai_summary}
                          </div>
                        </div>
                      </div>
                    )}
                  </section>

                  {/* Vulnerability Blueprint */}
                  <section className="space-y-5">
                    <div className="flex items-center gap-3">
                      <Bug className="w-5 h-5 text-[var(--accent)]" />
                      <h3 className="text-lg font-display font-black tracking-tight">Vulnerability Blueprint</h3>
                    </div>
                    <div className="text-[var(--text-secondary)] font-body leading-relaxed max-w-2xl text-base">
                      The engine identified a <span className="text-[var(--text-primary)] font-bold">{selectedFinding.vuln_class}</span> vulnerability
                      within the <span className="text-[var(--text-primary)] font-bold">{selectedFinding.method}</span> handler.
                      This suggests a failure in <span className="text-[var(--text-primary)] font-bold">Input Validation</span> protocols.
                    </div>

                    <div className="grid grid-cols-2 gap-5 pt-2">
                      {/* CVSS Score */}
                      <div className="p-5 rounded-3xl bg-[var(--bg-main)]/50 border border-[var(--border-subtle)] flex items-center gap-5 group hover:border-[var(--accent)] transition-all overflow-hidden relative">
                        <div className="absolute right-[-20%] bottom-[-20%] opacity-5 group-hover:opacity-10 transition-opacity">
                          <BarChart3 className="w-40 h-40" />
                        </div>
                        <div className="z-10 bg-[var(--bg-main)] rounded-full p-1 shadow-lg shadow-black/50">
                          <CvssGauge score={selectedFinding.cvss_score || 0.0} />
                        </div>
                        <div className="z-10">
                          <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase mb-1">Risk Impact Vector</div>
                          <div className="text-xl font-display font-black tracking-tight mb-1">{selectedFinding.severity} Level</div>
                          <div className="text-[9px] font-mono text-[var(--text-muted)] border border-[var(--border-subtle)] px-2 py-0.5 rounded inline-block bg-black/20">
                            {selectedFinding.cvss_vector || 'VECTOR_PENDING'}
                          </div>
                        </div>
                      </div>

                      {/* Remediation */}
                      <div className="p-5 rounded-3xl bg-[var(--bg-main)]/50 border border-[var(--border-subtle)] flex flex-col justify-start gap-3 group hover:border-red-500/50 transition-all relative overflow-hidden">
                        <div className="absolute right-[-10%] top-[-10%] opacity-5 group-hover:opacity-10 transition-opacity">
                          <ShieldAlert className="w-36 h-36 text-red-500" />
                        </div>
                        <div className="z-10 flex items-center gap-3">
                          <ShieldAlert className="w-5 h-5 text-red-500" />
                          <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Remediation Guidance</div>
                        </div>
                        <div className="z-10 text-xs font-mono text-[var(--text-primary)] leading-relaxed overflow-y-auto pr-1 opacity-90" style={{ maxHeight: '120px' }}>
                          {selectedFinding.remediation || 'Apply standard input validation and context-aware output encoding to sanitize user parameters before rendering or execution. Ensure database drivers explicitly separate data payloads from query structures using prepared statements.'}
                        </div>
                      </div>
                    </div>
                  </section>

                  <div className="pt-4 flex justify-end">
                    <button className="flex items-center gap-2 text-sm font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
                      View in Raw Proxy <ExternalLink className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="h-full flex items-center justify-center premium-card opacity-30 font-display italic">
                SELECT_FINDING_TO_DECODE_INTELLIGENCE
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Interactive Terminal Modal */}
      {selectedFinding && (
        <AttackerConsole
          isOpen={isConsoleOpen}
          onClose={() => setIsConsoleOpen(false)}
          findingId={selectedFinding.id}
        />
      )}
    </div>
  );
}
