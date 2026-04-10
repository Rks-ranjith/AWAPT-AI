import { useState } from 'react';
import { 
  Moon, Sun, Bell, 
  Lock, Save, RefreshCw,
  Computer, Monitor, Sliders
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useThemeStore } from '@/store/useThemeStore';
import { motion } from 'framer-motion';

export function Settings() {
  const { theme, setTheme } = useThemeStore();
  const [activeTab, setActiveTab] = useState('interface');

  const TABS = [
    { id: 'interface', label: 'Display & UI', icon: Monitor },
    { id: 'security', label: 'Security Keys', icon: Lock },
    { id: 'nodes', label: 'Engine Nodes', icon: Sliders },
    { id: 'notifications', label: 'Alerting', icon: Bell },
  ];

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-12 relative z-10">
      <header>
        <h1 className="text-4xl font-display font-black tracking-tight mb-2">Platform Engine Control</h1>
        <p className="text-lg text-[var(--text-secondary)] font-body">Configure environment parameters and visual preferences.</p>
      </header>

      <div className="flex gap-12">
         {/* Sidebar Navigation */}
         <div className="w-64 space-y-2">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-2xl font-bold text-sm transition-all",
                  activeTab === tab.id 
                    ? "bg-[var(--accent)] text-white shadow-lg shadow-indigo-500/20" 
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-card)] hover:text-[var(--text-primary)]"
                )}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
         </div>

         {/* Content Area */}
         <div className="flex-1 space-y-10">
            {activeTab === 'interface' && (
              <motion.div 
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-10"
              >
                 <section className="space-y-6">
                    <div className="flex items-center gap-3">
                       <Computer className="w-5 h-5 text-[var(--accent)]" />
                       <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Visual Core Theme</h3>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-6">
                       <button 
                         onClick={() => setTheme('light')}
                         className={cn(
                           "flex flex-col items-center gap-4 p-8 rounded-[32px] border-2 transition-all",
                           theme === 'light' ? "border-[var(--accent)] bg-white shadow-xl" : "border-[var(--border-subtle)] bg-gray-50/50 opacity-60"
                         )}
                       >
                          <div className="w-16 h-16 rounded-full bg-orange-100 flex items-center justify-center text-orange-500">
                             <Sun className="w-8 h-8" />
                          </div>
                          <div className="text-center">
                             <div className="font-black text-black">Light Mode</div>
                              <div className="text-xs text-[var(--text-muted)] font-bold">Optimal for daylight</div>
                          </div>
                       </button>

                       <button 
                         onClick={() => setTheme('dark')}
                         className={cn(
                           "flex flex-col items-center gap-4 p-8 rounded-[32px] border-2 transition-all",
                           theme === 'dark' ? "border-[var(--accent)] bg-gray-900 shadow-xl" : "border-[var(--border-subtle)] bg-gray-800/20 opacity-60"
                         )}
                       >
                          <div className="w-16 h-16 rounded-full bg-indigo-900/50 flex items-center justify-center text-indigo-400">
                             <Moon className="w-8 h-8" />
                          </div>
                          <div className="text-center">
                             <div className="font-black text-white">Dark Mode</div>
                             <div className="text-xs text-indigo-300 font-bold">Maximum immersion</div>
                          </div>
                       </button>
                    </div>
                 </section>

                 <section className="space-y-6">
                    <div className="flex items-center gap-3">
                       <RefreshCw className="w-5 h-5 text-[var(--accent)]" />
                       <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Interface Refresh Rate</h3>
                    </div>
                    <div className="premium-card p-6 flex justify-between items-center">
                       <div>
                          <div className="font-bold">WebSocket Streaming</div>
                          <div className="text-sm text-[var(--text-secondary)]">Real-time update frequency for scan telemetry.</div>
                       </div>
                       <select className="bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-xl px-4 py-2 font-bold text-sm outline-none focus:ring-2 ring-indigo-500/20">
                          <option>500ms (High Performance)</option>
                          <option>1000ms (Balanced)</option>
                          <option>2000ms (Low Bandwidth)</option>
                       </select>
                    </div>
                 </section>
              </motion.div>
            )}

            {activeTab === 'security' && (
              <motion.div 
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-8"
              >
                  <div className="premium-card p-10 space-y-8">
                     <div className="space-y-2">
                        <h3 className="text-2xl font-display font-black">API Authentication</h3>
                        <p className="text-[var(--text-secondary)] font-body">Manage credentials for external engine hooks.</p>
                     </div>
                     
                     <div className="space-y-4">
                        <div className="space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Primary Engine Key</label>
                           <div className="flex gap-4">
                              <input 
                                type="password" 
                                value="********************************" 
                                readOnly
                                className="flex-1 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm"
                              />
                              <button className="px-6 py-4 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl font-bold hover:bg-[var(--accent)]/10 hover:text-[var(--accent)] transition-all">Rotate</button>
                           </div>
                        </div>
                     </div>
                  </div>
              </motion.div>
            )}

            <div className="pt-10 flex justify-end gap-4">
               <button className="px-8 py-4 font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">Discard Changes</button>
               <button className="px-8 py-4 bg-[var(--accent)] text-white font-bold rounded-2xl shadow-lg shadow-indigo-500/20 flex items-center gap-2 hover:scale-[1.02] active:scale-95 transition-all">
                  <Save className="w-5 h-5" />
                  Save Platform Config
               </button>
            </div>
         </div>
      </div>
    </div>
  );
}
