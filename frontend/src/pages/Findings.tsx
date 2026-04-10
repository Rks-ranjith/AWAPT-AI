import { useState, useEffect } from 'react';
import { 
  ShieldAlert, Download, Terminal, 
  Bug, ExternalLink, BarChart3,
  Search, Fingerprint, Lock, TerminalSquare,
  Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useFindingStore } from '@/store/useFindingStore';
import { AttackerConsole } from '@/components/ui/AttackerConsole';
import { CvssGauge } from '@/components/ui/CvssGauge';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export function Findings() {
  const { findings, fetchFindings, updateFindingStatus } = useFindingStore();
  const [selectedFinding, setSelectedFinding] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);

  useEffect(() => {
    const init = async () => {
      await fetchFindings();
    };
    init();
  }, [fetchFindings]);

  useEffect(() => {
    if (findings.length > 0 && !selectedFinding) {
      setSelectedFinding(findings[0]);
    }
  }, [findings, selectedFinding]);

  const filteredFindings = findings.filter(f => 
    f.vuln_class.toLowerCase().includes(searchTerm.toLowerCase()) ||
    f.endpoint_url.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col relative z-10 overflow-hidden">
      <header className="p-10 pb-6 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Vulnerability Intelligence</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">Deep analysis of identified security weaknesses.</p>
        </div>
        <div className="flex gap-3">
            <button 
              onClick={() => {
                if (selectedFinding?.scan_id) {
                  window.open(`/api/v1/scans/${selectedFinding.scan_id}/report`, '_blank');
                } else {
                  alert("Scan ID not found for this finding.");
                }
              }}
              className="bg-[var(--bg-card)] border border-[var(--border-subtle)] px-4 py-2.5 rounded-2xl flex items-center gap-2 shadow-sm cursor-pointer hover:bg-[var(--bg-main)] transition-all group"
            >
               <Download className="w-4 h-4 text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]" />
               <span className="text-xs font-black tracking-widest uppercase">Export PDF Report</span>
            </button>
        </div>
      </header>

      <div className="flex-1 flex px-10 gap-10 pb-10 min-h-0">
         {/* List */}
         <div className="w-[380px] flex flex-col gap-6 overflow-hidden">
            <div className="relative">
               <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" />
               <input 
                 placeholder="Filter intelligence..." 
                 value={searchTerm}
                 onChange={(e) => setSearchTerm(e.target.value)}
                 className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] text-sm font-body outline-none focus:ring-2 ring-indigo-500/20 shadow-sm" 
               />
            </div>
            
            <div className="flex-1 overflow-y-auto premium-card no-scrollbar">
               {filteredFindings.length === 0 ? (
                 <div className="p-10 text-center opacity-30 font-display text-sm italic">NO_FINDINGS_IN_VIEW</div>
               ) : (
                 filteredFindings.map((finding) => (
                   <div 
                     key={finding.id}
                     onClick={() => setSelectedFinding(finding)}
                     className={cn(
                       "p-6 border-b border-[var(--border-subtle)] cursor-pointer transition-all relative group overflow-hidden",
                       selectedFinding?.id === finding.id ? "bg-[var(--accent)]/[0.04]" : "hover:bg-[var(--bg-main)]"
                     )}
                   >
                      {selectedFinding?.id === finding.id && (
                        <motion.div layoutId="active-find-ring" className="absolute left-0 top-0 bottom-0 w-1 bg-[var(--accent)]" />
                      )}
                      <div className="flex justify-between items-start mb-2">
                         <span className={cn(
                           "text-[9px] font-black tracking-[0.2em] px-2 py-0.5 rounded-lg uppercase",
                           finding.severity === 'CRITICAL' ? "bg-red-500/10 text-red-500" : 
                           finding.severity === 'HIGH' ? "bg-orange-500/10 text-orange-500" :
                           "bg-blue-500/10 text-blue-500"
                         )}>
                            {finding.severity}
                         </span>
                         <span className="text-[10px] text-[var(--text-secondary)] font-mono">{new Date(finding.discovered_at).toLocaleTimeString()}</span>
                      </div>
                      <div className="font-bold text-[var(--text-primary)] mb-1 group-hover:text-[var(--accent)] transition-colors">{finding.vuln_class}</div>
                      <div className="text-xs text-[var(--text-secondary)] font-mono truncate">{finding.endpoint_url}</div>
                   </div>
                 ))
               )}
            </div>
         </div>

         {/* Detailing View */}
         <div className="flex-1 overflow-hidden">
            <AnimatePresence mode="wait">
               {selectedFinding ? (
                 <motion.div 
                   key={selectedFinding.id}
                   initial={{ opacity: 0, x: 20 }}
                   animate={{ opacity: 1, x: 0 }}
                   exit={{ opacity: 0, x: -20 }}
                   className="h-full flex flex-col premium-card overflow-hidden bg-[var(--bg-card)]/50 backdrop-blur-xl"
                 >
                    <div className="p-8 border-b border-[var(--border-subtle)] bg-[var(--bg-main)]/30 space-y-6">
                       <div className="flex justify-between items-start">
                          <div className="space-y-2">
                             <div className="flex items-center gap-3">
                                <Fingerprint className="w-5 h-5 text-[var(--accent)]" />
                                <span className="text-xs font-black tracking-widest uppercase text-[var(--text-secondary)]">Finding Signature</span>
                             </div>
                             <h2 className="text-3xl font-display font-black tracking-tight">{selectedFinding.vuln_class}</h2>
                          </div>
                          <div className="flex gap-3">
                             <button 
                               onClick={() => window.open(`/api/v1/findings/${selectedFinding.id}/exploit`, '_blank')}
                               className="px-5 py-2.5 rounded-2xl font-bold text-sm shadow-lg transition-all flex items-center gap-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 shadow-indigo-500/10"
                             >
                                <Download className="w-4 h-4" />
                                Standalone Exploit
                             </button>
                             <button 
                               onClick={() => setIsConsoleOpen(true)}
                               className="px-5 py-2.5 rounded-2xl font-bold text-sm shadow-lg transition-all flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/20 shadow-emerald-500/10"
                             >
                                <TerminalSquare className="w-4 h-4" />
                                Interactive Console
                             </button>
                             <button 
                               onClick={async () => {
                                 if (selectedFinding) {
                                   await updateFindingStatus(selectedFinding.id, 'ESCALATED');
                                   alert("Vulnerability Escalated to Security Council.");
                                 }
                               }}
                               className={cn(
                                 "px-5 py-2.5 rounded-2xl font-bold text-sm shadow-lg transition-all flex items-center gap-2",
                                 selectedFinding.status === 'ESCALATED' ? "bg-red-500/20 text-red-500 border border-red-500/30" : "bg-red-500 hover:bg-red-600 text-white shadow-red-500/20"
                               )}>
                                <Lock className="w-4 h-4" />
                                {selectedFinding.status === 'ESCALATED' ? 'Risk Escalated' : 'Escalate Risk'}
                             </button>
                          </div>
                       </div>

                       <div className="flex gap-10">
                          <div className="space-y-1">
                             <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Resource Path</div>
                             <div className="text-sm font-mono text-[var(--accent)]">{selectedFinding.endpoint_url}</div>
                          </div>
                          <div className="space-y-1">
                             <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Method</div>
                             <div className="text-sm font-mono text-[var(--text-primary)]">{selectedFinding.method}</div>
                          </div>
                          <div className="space-y-1">
                             <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Confidence</div>
                             <div className="text-sm font-mono text-emerald-500">{selectedFinding.confidence}% Certain</div>
                          </div>
                       </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-10 space-y-12 no-scrollbar">
                       <section className="space-y-6">
                          <div className="flex items-center gap-3">
                             <Terminal className="w-5 h-5 text-[var(--accent)]" />
                             <h3 className="text-lg font-display font-black tracking-tight">Technical Evidence</h3>
                          </div>
                          
                          <div className="grid grid-cols-1 gap-6">
                             <div className="space-y-3">
                                <div className="flex justify-between items-center px-1">
                                   <span className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Reproduction Request</span>
                                   <span className="text-[9px] font-mono text-emerald-500/60 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10">RAW_HTTP_v1.1</span>
                                </div>
                                <div className="rounded-2xl overflow-hidden border border-white/5 shadow-2xl">
                                   <SyntaxHighlighter 
                                      language="http" 
                                      style={vscDarkPlus} 
                                      customStyle={{ margin: 0, padding: '24px', fontSize: '13px', backgroundColor: '#0D0E12' }}
                                   >
                                      {selectedFinding.request_raw || "GET /api/v1/resource HTTP/1.1\nHost: target.local\nUser-Agent: AWAP-AI/2.0"}
                                   </SyntaxHighlighter>
                                </div>
                             </div>

                             <div className="space-y-3">
                                <div className="flex justify-between items-center px-1">
                                   <span className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Target Response Reflection</span>
                                   <span className="text-[9px] font-mono text-amber-500/60 bg-amber-500/5 px-2 py-0.5 rounded border border-amber-500/10">SINK_DETECTED</span>
                                </div>
                                <div className="rounded-2xl overflow-hidden border border-white/5 shadow-2xl">
                                   <SyntaxHighlighter 
                                      language="javascript" 
                                      style={vscDarkPlus} 
                                      customStyle={{ margin: 0, padding: '24px', fontSize: '12px', backgroundColor: '#0D0E12' }}
                                   >
                                      {selectedFinding.response_raw ? selectedFinding.response_raw.substring(0, 500) : "// NO_RESPONSE_BODY_CAPTURED"}
                                   </SyntaxHighlighter>
                                </div>
                             </div>
                          </div>
                            
                           {selectedFinding.ai_summary && (
                             <div className="p-10 rounded-[40px] bg-indigo-500/[0.03] border border-indigo-500/10 relative overflow-hidden group shadow-2xl shadow-indigo-500/5 mt-8">
                                <div className="absolute -right-12 -top-12 p-4 opacity-[0.03] group-hover:opacity-[0.08] transition-all duration-700">
                                   <Activity className="w-64 h-64 text-indigo-400" />
                                </div>
                                <div className="relative z-10 space-y-6">
                                   <div className="flex items-center gap-3">
                                      <div className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse shadow-[0_0_10px_rgba(129,140,248,0.5)]" />
                                      <span className="text-[10px] font-black tracking-[0.2em] uppercase text-indigo-400">Deep Neural Vulnerability Analysis</span>
                                   </div>
                                   <div className="text-lg font-medium leading-relaxed font-body text-indigo-100/90 whitespace-pre-wrap">
                                      {selectedFinding.ai_summary}
                                   </div>
                                </div>
                             </div>
                           )}
                        </section>

                       <section className="space-y-6">
                          <div className="flex items-center gap-3">
                             <Bug className="w-5 h-5 text-[var(--accent)]" />
                             <h3 className="text-lg font-display font-black tracking-tight">Vulnerability Blueprint</h3>
                          </div>
                          <div className="text-[var(--text-secondary)] font-body leading-relaxed max-w-2xl text-lg">
                             The engine identified a <span className="text-[var(--text-primary)] font-bold">{selectedFinding.vuln_class}</span> vulnerability 
                             within the <span className="text-[var(--text-primary)] font-bold">{selectedFinding.method}</span> handler. 
                             This suggests a failure in <span className="text-[var(--text-primary)] font-bold">Input Validation</span> protocols.
                          </div>
                          
                          <div className="grid grid-cols-2 gap-6 pt-4">
                             <div className="p-6 rounded-3xl bg-[var(--bg-main)]/50 border border-[var(--border-subtle)] flex items-center gap-6 group hover:border-[var(--accent)] transition-all overflow-hidden relative">
                                <div className="absolute right-[-20%] bottom-[-20%] opacity-5 group-hover:opacity-10 transition-opacity">
                                    <BarChart3 className="w-48 h-48" />
                                </div>
                                <div className="z-10 bg-[var(--bg-main)] rounded-full p-1 shadow-lg shadow-black/50">
                                  <CvssGauge score={selectedFinding.cvss_score || 0.0} />
                                </div>
                                <div className="z-10">
                                   <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase mb-1">Risk Impact Vector</div>
                                   <div className="text-2xl font-display font-black tracking-tight mb-2">{selectedFinding.severity} Level</div>
                                   {selectedFinding.cvss_vector ? (
                                      <div className="text-[9px] font-mono mt-1 text-[var(--text-muted)] border border-[var(--border-subtle)] px-2 py-1 rounded inline-block bg-black/20">
                                         {selectedFinding.cvss_vector}
                                      </div>
                                   ) : (
                                      <div className="text-[9px] font-mono mt-1 text-[var(--text-muted)] border border-[var(--border-subtle)] px-2 py-1 rounded inline-block bg-black/20">
                                         VECTOR_PENDING_CALCULATION
                                      </div>
                                   )}
                                </div>
                             </div>
                             <div className="p-6 rounded-3xl bg-[var(--bg-main)]/50 border border-[var(--border-subtle)] flex flex-col justify-start gap-3 group hover:border-red-500/50 transition-all relative overflow-hidden">
                                <div className="absolute right-[-10%] top-[-10%] opacity-5 group-hover:opacity-10 transition-opacity">
                                    <ShieldAlert className="w-40 h-40 text-red-500" />
                                </div>
                                <div className="z-10 flex items-center gap-3 mb-2">
                                   <ShieldAlert className="w-5 h-5 text-red-500" />
                                   <div className="text-[10px] font-black text-[var(--text-secondary)] tracking-widest uppercase">Remediation Guidance</div>
                                </div>
                                <div className="z-10 text-xs font-mono text-[var(--text-primary)] leading-relaxed h-[100px] overflow-y-auto no-scrollbar pr-2 opacity-90">
                                   {selectedFinding.remediation || "Apply standard input validation and context-aware output encoding to sanitize user parameters before rendering or execution. Ensure database drivers explicitly separate data payloads from query structures using prepared statements."}
                                </div>
                             </div>
                          </div>
                       </section>

                       <div className="pt-10 flex justify-end">
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
