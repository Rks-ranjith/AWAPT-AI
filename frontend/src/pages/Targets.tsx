import { useState } from 'react';
import { 
  Plus, Globe, Shield, Target, Play, ExternalLink, Trash2,
  Filter, Search
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useTargets } from '@/hooks/useTargets';
import { useScanStore } from '@/store/useScanStore';
import { useNavigate } from 'react-router-dom';

export function Targets() {
  const { targets, createTarget, deleteTarget } = useTargets();
  const { startScan } = useScanStore();
  const navigate = useNavigate();
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTarget, setNewTarget] = useState({ name: '', url: '' });

  const handleCreate = async () => {
    if (!newTarget.name || !newTarget.url) return;
    try {
      await createTarget({ name: newTarget.name, base_url: newTarget.url });
      setShowAddModal(false);
      setNewTarget({ name: '', url: '' });
    } catch (err) {
      console.error("Failed to add target:", err);
    }
  };

  const activeCountSize = targets.filter((t: any) => t.status === 'ACTIVE').length;

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Attack Surface</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">Manage assets and scoping for automated security audits.</p>
        </div>
        
        <button 
          onClick={() => setShowAddModal(true)}
          className="bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white font-bold text-sm px-6 py-3 rounded-2xl shadow-lg shadow-indigo-500/20 transition-all active:scale-95 flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Add Target
        </button>
      </header>

      {/* Target Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
         <div className="premium-card p-6 flex items-center gap-6">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-500">
               <Globe className="w-7 h-7" />
            </div>
            <div>
               <div className="text-[10px] font-display font-black text-[var(--text-secondary)] tracking-[0.2em] uppercase mb-1">Total Assets</div>
               <div className="text-3xl font-display font-black">{targets.length}</div>
            </div>
         </div>
         <div className="premium-card p-6 flex items-center gap-6">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500">
               <Shield className="w-7 h-7" />
            </div>
            <div>
               <div className="text-[10px] font-display font-black text-[var(--text-secondary)] tracking-[0.2em] uppercase mb-1">Verified Up</div>
               <div className="text-3xl font-display font-black">{activeCountSize}</div>
            </div>
         </div>
         <div className="premium-card p-6 flex items-center gap-6">
            <div className="w-14 h-14 rounded-2xl bg-red-500/10 flex items-center justify-center text-red-500">
               <Target className="w-7 h-7" />
            </div>
            <div>
               <div className="text-[10px] font-display font-black text-[var(--text-secondary)] tracking-[0.2em] uppercase mb-1">In Queue</div>
               <div className="text-3xl font-display font-black">{targets.length - activeCountSize}</div>
            </div>
         </div>
      </div>

      {/* Inventory List */}
      <section className="space-y-6">
         <div className="flex justify-between items-center px-2">
            <div className="flex gap-4">
               <div className="flex items-center gap-2 bg-[var(--bg-card)] border border-[var(--border-subtle)] px-4 py-2 rounded-xl text-sm font-bold shadow-sm">
                  <Filter className="w-4 h-4 text-[var(--text-secondary)]" />
                  Filter
               </div>
               <div className="relative">
                  <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" />
                  <input placeholder="Search assets..." className="pl-11 pr-4 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] text-sm font-body outline-none focus:ring-2 ring-indigo-500/20 shadow-sm w-64" />
               </div>
            </div>
         </div>

         <div className="premium-card overflow-hidden">
            <table className="w-full text-left border-collapse">
               <thead>
                  <tr className="bg-[var(--bg-main)]/50 border-b border-[var(--border-subtle)]">
                     <th className="px-8 py-4 text-[11px] font-display font-black text-[var(--text-secondary)] tracking-widest uppercase">Target Details</th>
                     <th className="px-8 py-4 text-[11px] font-display font-black text-[var(--text-secondary)] tracking-widest uppercase text-center">Status</th>
                     <th className="px-8 py-4 text-[11px] font-display font-black text-[var(--text-secondary)] tracking-widest uppercase">Last Activity</th>
                     <th className="px-8 py-4 text-right"></th>
                  </tr>
               </thead>
               <tbody className="divide-y divide-[var(--border-subtle)] text-sm">
                  {targets.map((target: any) => (
                    <tr key={target.id} className="hover:bg-[var(--accent)]/[0.02] transition-colors group">
                       <td className="px-8 py-6">
                          <div className="flex items-center gap-4">
                             <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-[var(--text-secondary)] group-hover:bg-[var(--accent)] group-hover:text-white transition-all">
                                <Globe className="w-5 h-5" />
                             </div>
                             <div>
                                <div className="font-bold text-[var(--text-primary)]">{target.name}</div>
                                <div className="text-xs text-[var(--text-secondary)] font-mono">{target.base_url}</div>
                             </div>
                          </div>
                       </td>
                       <td className="px-8 py-6 text-center">
                          <span className={cn(
                            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase",
                            target.status === 'ACTIVE' ? "bg-emerald-500/10 text-emerald-500" : "bg-orange-500/10 text-orange-500"
                          )}>
                             <div className={cn("w-1.5 h-1.5 rounded-full", target.status === 'ACTIVE' ? "bg-emerald-500" : "bg-orange-500")} />
                             {target.status}
                          </span>
                       </td>
                       <td className="px-8 py-6 text-xs text-[var(--text-secondary)] font-mono">
                          {new Date(target.created_at).toLocaleDateString()}
                       </td>
                       <td className="px-8 py-6 text-right">
                          <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                             <button 
                                onClick={async () => { await startScan(target.id); navigate('/monitor'); }}
                                className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-[var(--text-secondary)]"
                             >
                                <Play className="w-4 h-4" />
                             </button>
                             <button className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-[var(--text-secondary)]"><ExternalLink className="w-4 h-4" /></button>
                             <button 
                                onClick={() => deleteTarget(target.id)}
                                className="p-2 rounded-lg hover:bg-red-500/10 text-red-500"
                             >
                                <Trash2 className="w-4 h-4" />
                             </button>
                          </div>
                       </td>
                    </tr>
                  ))}
                  {targets.length === 0 && (
                    <tr><td colSpan={4} className="p-20 text-center opacity-30 font-display">NO_TARGETS_IN_SCOPE</td></tr>
                  )}
               </tbody>
            </table>
         </div>
      </section>

      {/* Modern Add Modal */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
             <motion.div 
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               onClick={() => setShowAddModal(false)}
               className="absolute inset-0 bg-black/60 backdrop-blur-sm"
             />
             <motion.div
               initial={{ opacity: 0, scale: 0.95, y: 20 }}
               animate={{ opacity: 1, scale: 1, y: 0 }}
               exit={{ opacity: 0, scale: 0.95, y: 20 }}
               className="w-full max-w-lg relative"
             >
                <div className="bg-[var(--bg-card)] rounded-[32px] p-10 shadow-2xl border border-[var(--border-subtle)] space-y-8">
                   <div className="space-y-2">
                      <h2 className="text-3xl font-display font-black tracking-tight">Scope Asset</h2>
                      <p className="text-[var(--text-secondary)] font-body">Define a new technical boundary for scanning.</p>
                   </div>
                   
                   <div className="space-y-6">
                      <div className="space-y-2">
                         <label className="text-[10px] font-display font-black text-[var(--text-secondary)] tracking-widest uppercase px-1">Friendly Name</label>
                         <input 
                           type="text" 
                           placeholder="Gateway API"
                           value={newTarget.name}
                           onChange={(e) => setNewTarget({ ...newTarget, name: e.target.value })}
                           className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-body outline-none focus:ring-2 ring-indigo-500/20 transition-all font-bold"
                         />
                      </div>
                      <div className="space-y-2">
                         <label className="text-[10px] font-display font-black text-[var(--text-secondary)] tracking-widest uppercase px-1">Endpoint URL</label>
                         <input 
                           type="text" 
                           placeholder="https://..."
                           value={newTarget.url}
                           onChange={(e) => setNewTarget({ ...newTarget, url: e.target.value })}
                           className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-body outline-none focus:ring-2 ring-indigo-500/20 transition-all font-mono"
                         />
                      </div>
                   </div>

                   <div className="flex gap-4">
                      <button 
                        onClick={() => setShowAddModal(false)}
                        className="flex-1 py-4 font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                      >
                         Cancel
                      </button>
                      <button 
                        onClick={handleCreate}
                        disabled={!newTarget.name || !newTarget.url}
                        className="flex-1 py-4 bg-[var(--accent)] text-white font-bold rounded-2xl shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50"
                      >
                         Index Target
                      </button>
                   </div>
                </div>
             </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
