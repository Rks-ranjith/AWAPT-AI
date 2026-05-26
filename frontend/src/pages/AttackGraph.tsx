import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Share2, Maximize2, Minimize2, ZoomIn, ZoomOut,
  RotateCcw, Activity, ArrowLeft, X
} from 'lucide-react';
import axios from 'axios';
import { cn } from '@/lib/utils';
import { useScanStore } from '@/store/useScanStore';
import { useTargets } from '@/hooks/useTargets';
import { useScanMonitor } from '@/hooks/useScanMonitor';
import { useNavigate } from 'react-router-dom';
import CytoscapeComponent from 'react-cytoscapejs';

const API_URL = '/api/v1';

// ── Enhanced Cytoscape stylesheet for full-screen — larger nodes + labels ──
const CY_STYLE: any[] = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      color: '#E2E8F0',
      'font-family': 'JetBrains Mono, Fira Code, monospace',
      'font-size': 11,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 8,
      'background-color': '#0D1117',
      'border-width': 2,
      'border-color': '#4A5568',
      'text-wrap': 'ellipsis',
      'text-max-width': '120px',
      'text-background-color': '#0a0b0f',
      'text-background-opacity': 0.7,
      'text-background-padding': '2px',
      'text-background-shape': 'roundrectangle',
    },
  },
  // ── Domain (hexagon) ─────────────────────────────────────────────────
  {
    selector: 'node[type="target"]',
    style: {
      shape: 'hexagon',
      width: 64,
      height: 64,
      'border-color': '#00D4FF',
      'background-color': 'rgba(0,212,255,0.15)',
      'border-width': 4,
      'font-size': 14,
      'font-weight': 'bold',
      'text-valign': 'bottom',
      'text-max-width': '160px',
    },
  },
  // ── Crawled endpoint (ellipse) ───────────────────────────────────────
  {
    selector: 'node[type="endpoint"]',
    style: {
      shape: 'ellipse',
      width: 28,
      height: 28,
      'border-color': '#636366',
      'background-color': 'rgba(99,99,102,0.22)',
    },
  },
  // ── Vulnerability (diamond) ──────────────────────────────────────────
  {
    selector: 'node[type="vulnerability"]',
    style: {
      shape: 'diamond',
      width: 40,
      height: 40,
      'border-color': '#FFB800',
      'background-color': 'rgba(255,184,0,0.22)',
      'border-width': 3,
    },
  },
  // ── Severity overrides ───────────────────────────────────────────────
  {
    selector: 'node[severity="CRITICAL"]',
    style: { 'border-color': '#FF2D55', 'background-color': 'rgba(255,45,85,0.30)' },
  },
  {
    selector: 'node[severity="HIGH"]',
    style: { 'border-color': '#FF9F0A', 'background-color': 'rgba(255,159,10,0.25)' },
  },
  {
    selector: 'node[severity="MEDIUM"]',
    style: { 'border-color': '#FFD60A', 'background-color': 'rgba(255,214,10,0.22)' },
  },
  {
    selector: 'node[severity="LOW"]',
    style: { 'border-color': '#30D158', 'background-color': 'rgba(48,209,88,0.18)' },
  },
  // ── Highlighted node (on hover / select) ─────────────────────────────
  {
    selector: 'node:selected',
    style: {
      'border-width': 4,
      'border-color': '#818CF8',
      'background-color': 'rgba(129,140,248,0.15)',
      'text-background-opacity': 0.9,
    },
  },
  // ── Base edge ────────────────────────────────────────────────────────
  {
    selector: 'edge',
    style: {
      width: 1.5,
      'line-color': '#4A5568',
      'target-arrow-color': '#4A5568',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      opacity: 0.55,
    },
  },
  // ── Exploitation edge (dashed red) ───────────────────────────────────
  {
    selector: 'edge[type="exploitation"]',
    style: {
      'line-color': '#FF2D55',
      'target-arrow-color': '#FF2D55',
      'line-style': 'dashed',
      width: 2.5,
      opacity: 0.9,
    },
  },
];

const CY_LAYOUT = {
  name: 'cose',
  animate: true,
  animationDuration: 800,
  refresh: 10,
  fit: true,
  padding: 50,
  randomize: false,
  componentSpacing: 100,
  nodeRepulsion: () => 8000,
  idealEdgeLength: () => 80,
};


// ── Tooltip component for hovered nodes ─────────────────────────────────────
function NodeTooltip({ data, position }: { data: any; position: { x: number; y: number } }) {
  if (!data) return null;
  return (
    <div
      className="absolute z-[100] pointer-events-none px-4 py-3 rounded-xl bg-gray-900/95 border border-white/10 shadow-2xl backdrop-blur-lg"
      style={{ left: position.x + 14, top: position.y - 10, maxWidth: 280 }}
    >
      <div className="text-xs font-mono font-bold text-white mb-1 truncate">{data.label}</div>
      {data.type === 'endpoint' && data.method && (
        <div className="text-[10px] font-mono text-cyan-400">Method: {data.method}</div>
      )}
      {data.type === 'vulnerability' && (
        <>
          <div className="text-[10px] font-mono text-amber-400">Type: Vulnerability</div>
          {data.severity && (
            <div className={cn('text-[10px] font-black uppercase tracking-widest mt-1',
              data.severity === 'CRITICAL' ? 'text-red-500' :
              data.severity === 'HIGH' ? 'text-orange-400' :
              data.severity === 'MEDIUM' ? 'text-yellow-400' : 'text-green-400'
            )}>
              Severity: {data.severity}
            </div>
          )}
        </>
      )}
      {data.type === 'target' && (
        <div className="text-[10px] font-mono text-cyan-400">Root Domain</div>
      )}
    </div>
  );
}


export function AttackGraph() {
  const navigate = useNavigate();
  const { isScanning, activeTargetId, activeScanId, scanComplete, recoverScan } = useScanStore();
  const { targets } = useTargets();
  const { isConnected } = useScanMonitor(activeScanId);
  const activeTarget = targets.find((t: any) => String(t.id) === String(activeTargetId));

  const [elements, setElements] = useState<any[]>([]);
  const [graphStats, setGraphStats] = useState({ endpoints: 0, vulns: 0, critical: 0, high: 0, medium: 0, low: 0 });
  const cyRef = useRef<any>(null);
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Scan state recovery on mount
  useEffect(() => { recoverScan(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const isActive = isScanning || scanComplete;

  // ── Fullscreen toggle ─────────────────────────────────────────────────────
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  }, []);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  // ── Graph data polling — 3s while active ──────────────────────────────────
  useEffect(() => {
    if (!activeScanId) return;
    if (!isActive) return;

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

        // Domain root
        nodes.push({
          data: {
            id: 'target',
            label: activeTarget?.name || activeTarget?.domain || activeTarget?.base_url || 'Target',
            type: 'target',
          },
        });

        // Endpoint nodes
        endpoints.forEach((ep: any, idx: number) => {
          const nodeId = `ep_${idx}`;
          const shortLabel = (() => {
            try {
              const u = new URL(ep.url);
              return u.pathname.substring(0, 36) || '/';
            } catch { return ep.url?.substring(0, 36) || '/'; }
          })();

          if (!seenUrls.has(ep.url)) {
            seenUrls.add(ep.url);
            nodes.push({
              data: { id: nodeId, label: shortLabel, type: 'endpoint', method: ep.method },
            });
            edges.push({
              data: { id: `e_crawl_${idx}`, source: 'target', target: nodeId, type: 'crawl' },
            });
          }
        });

        // Vulnerability nodes
        let critical = 0, high = 0, medium = 0, low = 0;
        findings.forEach((f: any, idx: number) => {
          const vulnNodeId = `vuln_${idx}`;
          const shortLabel = f.vuln_class?.substring(0, 20) || 'VULN';
          const epIdx = endpoints.findIndex((ep: any) => f.url?.startsWith(ep.url) || ep.url?.startsWith(f.url));
          const epNodeId = epIdx >= 0 ? `ep_${epIdx}` : 'target';

          if (f.severity === 'CRITICAL') critical++;
          else if (f.severity === 'HIGH') high++;
          else if (f.severity === 'MEDIUM') medium++;
          else low++;

          nodes.push({
            data: { id: vulnNodeId, label: shortLabel, type: 'vulnerability', severity: f.severity },
          });
          edges.push({
            data: { id: `e_exploit_${idx}`, source: epNodeId, target: vulnNodeId, type: 'exploitation' },
          });
        });

        setElements([...nodes, ...edges]);
        setGraphStats({ endpoints: endpoints.length, vulns: findings.length, critical, high, medium, low });
      } catch (err) {
        console.error('[AttackGraph] Poll error:', err);
      }
    };

    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [isActive, activeScanId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cytoscape event handlers ──────────────────────────────────────────────
  const handleCyInit = useCallback((cy: any) => {
    cyRef.current = cy;

    cy.on('mouseover', 'node', (e: any) => {
      const node = e.target;
      const pos = node.renderedPosition();
      setHoveredNode(node.data());
      setTooltipPos({ x: pos.x, y: pos.y });
    });

    cy.on('mouseout', 'node', () => {
      setHoveredNode(null);
    });

    cy.on('layoutstop', () => cy.fit(undefined, 40));
  }, []);

  // Controls
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.3);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.3);
  const resetView = () => {
    cyRef.current?.fit(undefined, 40);
    cyRef.current?.center();
  };
  const relayout = () => {
    cyRef.current?.layout(CY_LAYOUT).run();
  };

  return (
    <div
      ref={containerRef}
      className="h-[calc(100vh-5rem)] flex flex-col relative z-10 overflow-hidden bg-[var(--bg-main)]"
    >
      {/* ── Header bar ─────────────────────────────────────────────────────── */}
      <header className="px-8 py-4 flex justify-between items-center flex-shrink-0 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/60 backdrop-blur-xl">
        <div className="flex items-center gap-5">
          {/* Back button */}
          <button
            onClick={() => navigate('/scans')}
            className="p-2.5 rounded-xl bg-[var(--bg-main)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all group"
            title="Back to Engine Console"
          >
            <ArrowLeft className="w-4 h-4 text-[var(--text-secondary)] group-hover:text-[var(--accent)]" />
          </button>

          <div className="flex items-center gap-3">
            <Share2 className="w-5 h-5 text-[var(--accent)]" />
            <div>
              <h1 className="text-xl font-display font-black tracking-tight">
                Attack Surface Graph
              </h1>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] font-black tracking-widest text-[var(--accent)] uppercase">
                  {activeTarget ? (activeTarget.name || activeTarget.domain || activeTarget.base_url) : 'NO_TARGET'}
                </span>
                {isScanning && (
                  <span className="flex items-center gap-1.5 text-[10px] font-black text-emerald-400 uppercase tracking-widest">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    LIVE
                  </span>
                )}
                {scanComplete && !isScanning && (
                  <span className="text-[10px] font-black text-cyan-400 uppercase tracking-widest">COMPLETE</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stats badges */}
        <div className="flex items-center gap-3">
          {graphStats.critical > 0 && (
            <span className="text-[10px] font-black px-2.5 py-1 rounded-lg bg-red-500/10 text-red-500 border border-red-500/20 uppercase tracking-widest">
              {graphStats.critical} Critical
            </span>
          )}
          {graphStats.high > 0 && (
            <span className="text-[10px] font-black px-2.5 py-1 rounded-lg bg-orange-500/10 text-orange-400 border border-orange-500/20 uppercase tracking-widest">
              {graphStats.high} High
            </span>
          )}
          {graphStats.medium > 0 && (
            <span className="text-[10px] font-black px-2.5 py-1 rounded-lg bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 uppercase tracking-widest">
              {graphStats.medium} Med
            </span>
          )}
          {graphStats.vulns > 0 && (
            <span className="text-[10px] font-black px-2.5 py-1 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 uppercase tracking-widest">
              {graphStats.vulns} Vulns
            </span>
          )}
          {graphStats.endpoints > 0 && (
            <span className="text-[10px] font-black px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase tracking-widest">
              {graphStats.endpoints} Endpoints
            </span>
          )}

          {/* Graph controls */}
          <div className="h-6 w-px bg-[var(--border-subtle)] mx-1" />

          <button onClick={zoomIn} className="p-2 rounded-lg bg-[var(--bg-main)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all" title="Zoom In">
            <ZoomIn className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
          <button onClick={zoomOut} className="p-2 rounded-lg bg-[var(--bg-main)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all" title="Zoom Out">
            <ZoomOut className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
          <button onClick={resetView} className="p-2 rounded-lg bg-[var(--bg-main)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all" title="Fit to View">
            <Minimize2 className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
          <button onClick={relayout} className="p-2 rounded-lg bg-[var(--bg-main)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all" title="Re-layout">
            <RotateCcw className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
          <button onClick={toggleFullscreen} className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 transition-all" title="Toggle Fullscreen">
            {isFullscreen ? <Minimize2 className="w-4 h-4 text-indigo-400" /> : <Maximize2 className="w-4 h-4 text-indigo-400" />}
          </button>
        </div>
      </header>

      {/* ── Full-screen graph canvas ───────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden bg-gray-950">
        {/* Graph legend — floating top-left */}
        <div className="absolute top-5 left-5 z-40 flex gap-4 px-4 py-2.5 rounded-xl bg-gray-900/80 border border-white/5 backdrop-blur-lg shadow-xl">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <div className="w-4 h-4 rounded border-2 border-cyan-400" style={{ clipPath: 'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)' }} />
            Domain
          </div>
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-500" />
            Endpoint
          </div>
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <div className="w-3.5 h-3.5 border-2 border-amber-400 rotate-45" />
            Vulnerability
          </div>
          <div className="h-4 w-px bg-white/10" />
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <div className="w-6 h-0.5 bg-slate-500" /> Crawl
          </div>
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
            <div className="w-6 h-0.5 border-t-2 border-dashed border-red-500" /> Exploit
          </div>
        </div>

        {/* Status indicator — floating top-right */}
        {isScanning && (
          <div className="absolute top-5 right-5 z-40 flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-lg">
            <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
            <span className="text-[10px] font-black tracking-widest text-emerald-400 uppercase">
              Live — Polling every 3s
            </span>
            {isConnected && (
              <span className="text-[9px] font-mono text-emerald-500/60">WS Connected</span>
            )}
          </div>
        )}

        {/* Tooltip */}
        <NodeTooltip data={hoveredNode} position={tooltipPos} />

        {/* Cytoscape graph */}
        {elements.length > 0 ? (
          <CytoscapeComponent
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            layout={CY_LAYOUT}
            stylesheet={CY_STYLE}
            cy={handleCyInit}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
            <Share2 className="w-16 h-16 text-white/5" />
            <div className="text-center">
              <div className="text-sm font-display font-black uppercase tracking-[0.3em] text-white/10 mb-2">
                {isScanning ? 'Awaiting Crawl Data...' : 'No Active Scan'}
              </div>
              <p className="text-xs text-white/5 font-body max-w-sm">
                {isScanning
                  ? 'The attack surface graph will populate as endpoints are discovered and vulnerabilities are identified.'
                  : 'Start a scan from the Targets page to see the attack surface graph in real-time.'}
              </p>
            </div>
            {!isActive && (
              <button
                onClick={() => navigate('/targets')}
                className="mt-4 px-6 py-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-black tracking-widest uppercase hover:bg-indigo-500/20 transition-all"
              >
                Go to Targets
              </button>
            )}
          </div>
        )}

        {/* Bottom-left stats overlay */}
        {elements.length > 0 && (
          <div className="absolute bottom-5 left-5 z-40 flex gap-3 px-4 py-2.5 rounded-xl bg-gray-900/80 border border-white/5 backdrop-blur-lg shadow-xl">
            <div className="text-[10px] font-mono text-slate-400">
              <span className="text-white font-bold">{graphStats.endpoints}</span> endpoints
            </div>
            <div className="h-4 w-px bg-white/10" />
            <div className="text-[10px] font-mono text-slate-400">
              <span className="text-white font-bold">{graphStats.vulns}</span> vulnerabilities
            </div>
            <div className="h-4 w-px bg-white/10" />
            <div className="text-[10px] font-mono text-slate-400">
              <span className="text-white font-bold">{elements.filter((e: any) => e.data?.id && !e.data?.source).length}</span> nodes
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
