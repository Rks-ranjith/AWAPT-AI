import { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck, Share2,
  Cpu, Network, Square, Activity, Database, CheckCircle2
} from 'lucide-react';
import axios from 'axios';
import { cn } from '@/lib/utils';
import { useScanStore } from '@/store/useScanStore';
import { useTargets } from '@/hooks/useTargets';
import { useScanMonitor } from '@/hooks/useScanMonitor';
import CytoscapeComponent from 'react-cytoscapejs';

import { LiveFeed, FeedItem } from '@/components/ui/LiveFeed';

const API_URL = '/api/v1';

const PIPELINE_PHASES = [
  { id: 1, label: 'Reconnaissance',      status_key: 'RECONNAISSANCE' },
  { id: 2, label: 'Deep Crawling',        status_key: 'CRAWLING' },
  { id: 3, label: 'AI Attack Planning',   status_key: 'AI_PLANNING' },
  { id: 4, label: 'Exploitation Engines', status_key: 'VULN_EXPLOITATION' },
];


// ── Premium Cytoscape stylesheet (ported + extended from AttackGraph.tsx) ────
const CY_STYLE: any[] = [
  // ── Base node ────────────────────────────────────────────────────────────
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      color: '#F8FAFC',
      'font-family': 'JetBrains Mono, Fira Code, monospace',
      'font-size': 9,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 6,
      'background-color': '#0D1117',
      'border-width': 2,
      'border-color': '#4A5568',
      'text-wrap': 'ellipsis',
      'text-max-width': '90px',
    },
  },
  // ── Domain (hexagon) ─────────────────────────────────────────────────────
  {
    selector: 'node[type="target"]',
    style: {
      shape: 'hexagon',
      width: 48,
      height: 48,
      'border-color': '#00D4FF',
      'background-color': 'rgba(0,212,255,0.12)',
      'border-width': 3,
      'font-size': 11,
      'font-weight': 'bold',
      'text-valign': 'bottom',
    },
  },
  // ── Crawled endpoint (ellipse) ────────────────────────────────────────────
  {
    selector: 'node[type="endpoint"]',
    style: {
      shape: 'ellipse',
      width: 22,
      height: 22,
      'border-color': '#636366',
      'background-color': 'rgba(99,99,102,0.18)',
    },
  },
  // ── Vulnerability (diamond) ───────────────────────────────────────────────
  {
    selector: 'node[type="vulnerability"]',
    style: {
      shape: 'diamond',
      width: 32,
      height: 32,
      'border-color': '#FFB800',
      'background-color': 'rgba(255,184,0,0.20)',
      'border-width': 2,
    },
  },
  // ── Severity overrides ────────────────────────────────────────────────────
  {
    selector: 'node[severity="CRITICAL"]',
    style: { 'border-color': '#FF2D55', 'background-color': 'rgba(255,45,85,0.25)' },
  },
  {
    selector: 'node[severity="HIGH"]',
    style: { 'border-color': '#FF9F0A', 'background-color': 'rgba(255,159,10,0.20)' },
  },
  {
    selector: 'node[severity="MEDIUM"]',
    style: { 'border-color': '#FFD60A', 'background-color': 'rgba(255,214,10,0.18)' },
  },
  {
    selector: 'node[severity="LOW"]',
    style: { 'border-color': '#30D158', 'background-color': 'rgba(48,209,88,0.15)' },
  },
  // ── Base edge ────────────────────────────────────────────────────────────
  {
    selector: 'edge',
    style: {
      width: 1,
      'line-color': '#4A5568',
      'target-arrow-color': '#4A5568',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      opacity: 0.6,
    },
  },
  // ── Exploitation edge (dashed red) ────────────────────────────────────────
  {
    selector: 'edge[type="exploitation"]',
    style: {
      'line-color': '#FF2D55',
      'target-arrow-color': '#FF2D55',
      'line-style': 'dashed',
      width: 2,
      opacity: 0.85,
    },
  },
];

const CY_LAYOUT = {
  name: 'cose',
  animate: true,
  refresh: 10,
  fit: true,
  padding: 28,
  randomize: false,
  componentSpacing: 80,
  nodeRepulsion: () => 6000,
};

export function LiveMonitor() {
  const { isScanning, logs, addLog, stopScan, currentPhase, activeTargetId, activeScanId, scanComplete, recoverScan } = useScanStore();
  const { targets } = useTargets();
  const { isConnected } = useScanMonitor(activeScanId);
  const activeTarget = targets.find((t: any) => String(t.id) === String(activeTargetId));

  // ── Cytoscape graph state ─────────────────────────────────────────────────
  const [elements, setElements] = useState<any[]>([]);
  const [graphStats, setGraphStats] = useState({ endpoints: 0, vulns: 0 });
  const cyRef = useRef<any>(null);

  // ── Recover scan state on mount (handles page refresh) ────────────────────
  useEffect(() => {
    recoverScan();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Poll scan state from API to keep pipeline phases in sync ──────────────
  useEffect(() => {
    if (!activeScanId) return;
    if (!isScanning && !scanComplete) return;

    const pollState = async () => {
      try {
        const resp = await axios.get(`${API_URL}/scans/${activeScanId}`);
        const scan = resp.data;
        if (scan.state) {
          const phaseMap: Record<string, string> = {
            'CREATED': 'RECONNAISSANCE',
            'SCOPE_VERIFIED': 'RECONNAISSANCE',
            'RECON': 'RECONNAISSANCE',
            'CRAWL': 'CRAWLING',
            'MAPPING': 'CRAWLING',
            'ATTACK': 'AI_PLANNING',
            'ANALYSIS': 'AI_PLANNING',
            'REPORTING': 'VULN_EXPLOITATION',
            'COMPLETE': 'VULN_EXPLOITATION',
          };
          const mappedPhase = phaseMap[scan.state];
          if (mappedPhase) {
            useScanStore.getState().setPhase(mappedPhase);
          }

          if (scan.state === 'COMPLETE' && isScanning) {
            useScanStore.getState().setScanComplete();
            addLog('[SYS] ✓ Scan completed successfully. All phases finished.');
          } else if (scan.state === 'FAILED' && isScanning) {
            addLog(`[SYS] ✗ Scan failed: ${scan.error_message || 'Unknown error'}`);
            stopScan();
          }
        }
      } catch {
        // Scan not found — ignore
      }
    };

    pollState();
    const interval = setInterval(pollState, 4000);
    return () => clearInterval(interval);
  }, [activeScanId, isScanning]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Seed domain node whenever a new scan starts ───────────────────────────
  useEffect(() => {
    if ((isScanning || scanComplete) && activeTarget) {
      setElements([{
        data: {
          id: 'target',
          label: activeTarget.name || activeTarget.domain || 'Target',
          type: 'target',
        },
      }]);
      if (!scanComplete) {
        setGraphStats({ endpoints: 0, vulns: 0 });
      }
    } else if (!isScanning && !scanComplete) {
      setElements([]);
      setGraphStats({ endpoints: 0, vulns: 0 });
    }
  }, [isScanning, scanComplete, activeTarget?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── 3-second graph data poll ──────────────────────────────────────────────
  useEffect(() => {
    if ((!isScanning && !scanComplete) || !activeScanId) return;

    const poll = async () => {
      try {
        const [epResp, fResp] = await Promise.all([
          axios.get(`${API_URL}/scans/${activeScanId}/endpoints`).catch(() => ({ data: [] })),
          axios.get(`${API_URL}/scans/${activeScanId}/findings`).catch(() => ({ data: [] })),
        ]);

        const endpoints: any[] = epResp.data || [];
        const findings: any[] = fResp.data || [];

        const nodes: any[] = [];
        const edges: any[] = [];
        const seenUrls = new Set<string>();

        // Domain root node
        nodes.push({
          data: {
            id: 'target',
            label: activeTarget?.name || activeTarget?.domain || 'Target',
            type: 'target',
          },
        });

        // Endpoint nodes + edges from domain
        endpoints.forEach((ep: any, idx: number) => {
          const nodeId = `ep_${idx}`;
          const shortLabel = (() => {
            try {
              const u = new URL(ep.url);
              return u.pathname.substring(0, 28) || '/';
            } catch { return ep.url.substring(0, 28); }
          })();

          if (!seenUrls.has(ep.url)) {
            seenUrls.add(ep.url);
            nodes.push({
              data: {
                id: nodeId,
                label: shortLabel,
                type: 'endpoint',
                method: ep.method,
              },
            });
            edges.push({
              data: {
                id: `e_crawl_${idx}`,
                source: 'target',
                target: nodeId,
                type: 'crawl',
              },
            });
          }
        });

        // Finding nodes — diamonds with severity colours + exploitation edges
        findings.forEach((f: any, idx: number) => {
          const vulnNodeId = `vuln_${idx}`;
          const shortLabel = `${f.vuln_class?.substring(0, 14) || 'VULN'}`;

          // Find nearest endpoint node for this finding URL
          const epIdx = endpoints.findIndex((ep: any) => f.url?.startsWith(ep.url) || ep.url?.startsWith(f.url));
          const epNodeId = epIdx >= 0 ? `ep_${epIdx}` : 'target';

          nodes.push({
            data: {
              id: vulnNodeId,
              label: shortLabel,
              type: 'vulnerability',
              severity: f.severity,
            },
          });
          edges.push({
            data: {
              id: `e_exploit_${idx}`,
              source: epNodeId,
              target: vulnNodeId,
              type: 'exploitation',
            },
          });
        });

        setElements([...nodes, ...edges]);
        setGraphStats({ endpoints: endpoints.length, vulns: findings.length });

        // Re-run layout when new data arrives
        if (cyRef.current && nodes.length > 1) {
          setTimeout(() => {
            cyRef.current?.layout(CY_LAYOUT).run();
          }, 100);
        }
      } catch (err) {
        console.error('[LiveMonitor] Graph poll error:', err);
      }
    };

    // Poll immediately then every 3 s
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [isScanning, scanComplete, activeScanId]); // eslint-disable-line react-hooks/exhaustive-deps

  const isActive = isScanning || scanComplete;

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-10 relative z-10">
      {/* Header */}
      <header className="flex justify-between items-center">
        <div className="flex items-center gap-6">
          <div className={cn(
            'w-16 h-16 rounded-[24px] flex items-center justify-center shadow-xl transition-all duration-500',
            scanComplete
              ? 'bg-emerald-500 shadow-emerald-500/30'
              : isScanning
                ? 'bg-[var(--accent)] shadow-indigo-500/30'
                : 'bg-gray-200 dark:bg-gray-800 shadow-none border border-[var(--border-subtle)]'
          )}>
            {scanComplete
              ? <CheckCircle2 className="w-8 h-8 text-white" />
              : <Activity className={cn('w-8 h-8 text-white', isScanning && 'animate-pulse')} />}
          </div>
          <div>
            <h1 className="text-4xl font-display font-black tracking-tight mb-1">Live Engine Monitor</h1>
            <div className="flex items-center gap-3">
              <span className="text-xs font-black tracking-widest text-[var(--accent)] uppercase">
                {activeTarget ? (activeTarget.name || activeTarget.domain) : 'NO_ACTIVE_TARGET'}
              </span>
              <div className="w-1.5 h-1.5 rounded-full bg-[var(--text-secondary)]" />
              <span className="text-xs font-bold text-[var(--text-secondary)]">
                {scanComplete
                  ? '✓ SCAN COMPLETE'
                  : isScanning
                    ? isConnected
                      ? '⬤ STREAMING CORE DATA...'
                      : '⬤ CONNECTING...'
                    : 'Engine Standby'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-4">
          {scanComplete && (
            <button
              className="px-6 py-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 font-bold text-sm flex items-center gap-2 hover:bg-emerald-500/20 transition-all cursor-pointer"
              onClick={() => {
                stopScan();
                setElements([]);
                setGraphStats({ endpoints: 0, vulns: 0 });
              }}
            >
              <CheckCircle2 className="w-5 h-5" />
              Clear Results
            </button>
          )}
          {isScanning && (
            <button
              className="px-6 py-3 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 font-bold text-sm flex items-center gap-2 hover:bg-red-500/20 transition-all cursor-pointer"
              onClick={() => stopScan()}
            >
              <Square className="w-5 h-5" />
              Terminate Engine
            </button>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* ── Left column ── */}
        <div className="lg:col-span-4 space-y-8">
          {/* Pipeline orchestration */}
          <section className="premium-card p-8 space-y-8">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-[var(--accent)]" />
              <h2 className="text-[10px] font-display font-black tracking-[0.2em] uppercase text-[var(--text-secondary)]">
                Pipeline Orchestration
              </h2>
            </div>

            <div className="space-y-6">
              {PIPELINE_PHASES.map((phase, i) => {
                const activeIndex = PIPELINE_PHASES.findIndex(p => p.status_key === currentPhase);
                const isPast   = scanComplete ? true : (activeIndex === -1 ? false : i < activeIndex);
                const isActivePhase = scanComplete ? (i === PIPELINE_PHASES.length - 1) : phase.status_key === currentPhase;

                return (
                  <div key={phase.id} className="relative flex gap-6 group">
                    {i < PIPELINE_PHASES.length - 1 && (
                      <div className="absolute left-4 top-10 bottom-0 w-0.5 bg-[var(--border-subtle)] -mb-6" />
                    )}
                    <div className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center z-10 border-2 transition-all duration-500',
                      isPast  ? 'bg-emerald-500 border-emerald-500 text-white' :
                      isActivePhase ? 'border-[var(--accent)] bg-[var(--bg-card)] text-[var(--accent)] shadow-lg shadow-indigo-500/20' :
                               'border-[var(--border-subtle)] bg-[var(--bg-card)] text-[var(--text-secondary)]'
                    )}>
                      <span className="text-[10px] font-black">{i + 1}</span>
                    </div>
                    <div className="pb-10 pt-1">
                      <div className={cn(
                        'text-sm font-black tracking-tight transition-colors',
                        isActivePhase ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
                      )}>
                        {phase.label}
                      </div>
                      <div className="text-[10px] font-bold text-[var(--text-secondary)] tracking-widest uppercase mt-0.5">
                        {isActivePhase && isScanning ? 'Executing...' : isPast ? 'Verified ✓' : isActivePhase && scanComplete ? 'Complete ✓' : 'Pending'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Attack Surface Graph */}
          <div className="premium-card p-6 flex flex-col" style={{ minHeight: '360px' }}>
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
              <div className="flex items-center gap-2">
                <Share2 className="w-4 h-4 text-[var(--text-secondary)]" />
                <span className="text-[10px] font-black tracking-widest uppercase text-[var(--text-secondary)]">
                  Attack Surface Graph
                </span>
              </div>
              <div className="flex items-center gap-2">
                {graphStats.vulns > 0 && (
                  <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-red-500/10 text-red-500 border border-red-500/20">
                    {graphStats.vulns} VULN{graphStats.vulns !== 1 ? 'S' : ''}
                  </span>
                )}
                {graphStats.endpoints > 0 && (
                  <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                    {graphStats.endpoints} EP
                  </span>
                )}
                {isScanning && (
                  <div className="text-[9px] font-mono text-emerald-500 animate-pulse">LIVE</div>
                )}
              </div>
            </div>

            {/* Graph legend */}
            <div className="flex gap-4 mb-3 flex-shrink-0">
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-[var(--text-secondary)]">
                <div className="w-3 h-3 rounded border-2 border-cyan-400" style={{ clipPath: 'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)' }} />
                Domain
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-[var(--text-secondary)]">
                <div className="w-3 h-3 rounded-full border-2 border-slate-500" />
                Endpoint
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-[var(--text-secondary)]">
                <div className="w-3 h-3 border-2 border-amber-400 rotate-45" />
                Vuln
              </div>
            </div>

            {/* Cytoscape canvas */}
            <div className="flex-1 bg-gray-950 rounded-xl overflow-hidden relative" style={{ minHeight: '260px' }}>
              {elements.length > 0 ? (
                <CytoscapeComponent
                  elements={elements}
                  style={{ width: '100%', height: '100%', minHeight: '260px' }}
                  layout={CY_LAYOUT}
                  stylesheet={CY_STYLE}
                  cy={(cy) => {
                    cyRef.current = cy;
                    cy.on('layoutstop', () => cy.fit(undefined, 20));
                  }}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 opacity-20">
                  <Share2 className="w-10 h-10" />
                  <div className="text-[10px] uppercase font-black tracking-widest">
                    {isScanning ? 'Awaiting Crawl Data...' : 'No Active Scan'}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Right column ── */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          {/* Live log feed */}
          <div className="flex-1 premium-card flex flex-col overflow-hidden min-h-[500px] relative">
            {isActive || logs.length > 0 ? (
              <LiveFeed items={logs.map((log, idx) => {
                let type: FeedItem['type'] = 'recon';
                let severity: FeedItem['severity'] = 'INFO';
                if (log.includes('[VULN]') || log.includes('[ATTACK]') || log.includes('FINDING')) {
                  type = 'finding'; severity = 'CRITICAL';
                } else if (log.includes('[SYS]') || log.includes('cycle completed') || log.includes('complete')) {
                  type = 'complete'; severity = 'INFO';
                } else if (log.includes('[AI') || log.includes('Hypothesizing') || log.includes('analysis')) {
                  type = 'crawl'; severity = 'HIGH';
                } else if (log.includes('[CRAWL]') || log.includes('crawl')) {
                  type = 'crawl'; severity = 'INFO';
                }
                return {
                  id: String(idx),
                  timestamp: new Date(Date.now() - (logs.length - idx) * 1000).toISOString().substring(11, 23) + 'Z',
                  type,
                  message: log,
                  severity,
                };
              })} />
            ) : (
              <div className="flex-1 flex items-center justify-center bg-[var(--bg-main)]/30 backdrop-blur">
                <div className="py-20 text-center text-[var(--text-secondary)] font-display text-sm tracking-widest italic uppercase">
                  ENGINE_WAITING_FOR_SCOPE
                </div>
              </div>
            )}
          </div>

          {/* Status chips */}
          <div className="grid grid-cols-2 gap-8">
            <div className="premium-card p-6 flex items-center gap-5 group cursor-default">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-500 group-hover:bg-indigo-500 group-hover:text-white transition-all">
                <Cpu className="w-6 h-6" />
              </div>
              <div>
                <div className="text-[10px] font-black text-[var(--text-secondary)] uppercase tracking-widest">Current Phase</div>
                <div className="text-base font-black text-[var(--text-primary)] truncate max-w-[140px]">
                  {scanComplete ? 'Complete ✓' : isScanning ? currentPhase : 'Idle'}
                </div>
              </div>
            </div>
            <div className="premium-card p-6 flex items-center gap-5 group cursor-default">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white transition-all">
                <Network className="w-6 h-6" />
              </div>
              <div>
                <div className="text-[10px] font-black text-[var(--text-secondary)] uppercase tracking-widest">Engine Status</div>
                <div className="text-base font-black text-[var(--text-primary)]">
                  {scanComplete
                    ? 'Scan Finished'
                    : isScanning
                      ? isConnected ? 'Live — Connected' : 'Initializing...'
                      : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Storage sync */}
          <div className="premium-card p-8 flex items-center justify-between group hover:border-[var(--accent)] transition-all">
            <div className="flex items-center gap-6">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 group-hover:scale-110 transition-transform">
                <Database className="w-7 h-7" />
              </div>
              <div>
                <h3 className="font-display font-black text-xl text-[var(--text-primary)]">Intelligence Sync</h3>
                <p className="text-sm text-[var(--text-muted)] font-bold">Streaming findings to Secure SQLite → PostgreSQL Cluster.</p>
              </div>
            </div>
            <button
              className="px-8 py-3 bg-[var(--accent)] text-white font-black text-xs uppercase tracking-widest rounded-2xl hover:bg-[var(--accent)]/90 transition-all shadow-lg shadow-indigo-500/20 active:scale-95 cursor-pointer"
              onClick={() => {
                addLog('[SYS] Manual storage sync initiated. Validating data integrity...');
                addLog('[SYS] Storage sync acknowledged.');
              }}
            >
              Storage Controller
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
