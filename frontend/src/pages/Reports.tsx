import { 
  FileText, Download, 
  Settings2, Layout, 
  CheckCircle2, Clock,
  FileSearch, Printer
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react'; // Added missing import for useState

const TEMPLATES = [
  { id: 'exec', name: 'Executive Summary', desc: 'High-level business risk overview for C-suite.', icon: Layout },
  { id: 'tech', name: 'Technical Deep-Dive', desc: 'Full finding blueprints with code-level PoCs.', icon: FileSearch },
  { id: 'compliance', name: 'PCI-DSS Compliance', desc: 'Standard mapping for regulatory audits.', icon: CheckCircle2 },
  { id: 'bounty', name: 'Bug Bounty Export', desc: 'VDP/HackerOne/Bugcrowd compatible format.', icon: Clock },
];

export function Reports() {
  const [selectedTemplate, setSelectedTemplate] = useState('tech');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      alert("Report Compiled Successfully! Check your downloads folder.");
    }, 2000);
  };

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Intelligence Reporting</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">Synthesize scan results into professional security documentation.</p>
        </div>
        <div className="flex gap-4">
           <button className="p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl hover:border-[var(--accent)] group transition-all">
              <Printer className="w-5 h-5 text-[var(--text-secondary)] group-hover:text-[var(--accent)]" />
           </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
         {/* Left: Template Selection */}
         <div className="lg:col-span-4 space-y-6">
            <div className="flex items-center gap-3 px-2">
               <Settings2 className="w-4 h-4 text-[var(--text-secondary)]" />
               <span className="text-[10px] font-black tracking-[0.2em] uppercase text-[var(--text-secondary)]">Report Configuration</span>
            </div>
            
            <div className="space-y-4">
               {TEMPLATES.map((tpl) => (
                 <div 
                   key={tpl.id}
                   onClick={() => setSelectedTemplate(tpl.id)}
                   className={cn(
                     "premium-card p-6 cursor-pointer flex gap-5 group transition-all",
                     selectedTemplate === tpl.id ? "border-[var(--accent)] bg-[var(--accent)]/[0.02] shadow-[var(--accent)]/10" : "hover:border-[var(--text-secondary)]/30"
                   )}
                 >
                    <div className={cn(
                      "w-12 h-12 rounded-xl flex items-center justify-center transition-all",
                      selectedTemplate === tpl.id ? "bg-[var(--accent)] text-white" : "bg-gray-100 dark:bg-gray-800 text-[var(--text-secondary)]"
                    )}>
                       <tpl.icon className="w-6 h-6" />
                    </div>
                    <div>
                       <div className="font-display font-black text-sm">{tpl.name}</div>
                       <div className="text-[10px] font-bold text-[var(--text-secondary)] mt-1">{tpl.desc}</div>
                    </div>
                 </div>
               ))}
            </div>
         </div>

         {/* Right: Live Preview */}
         <div className="lg:col-span-8 flex flex-col gap-8">
            <div className="flex-1 premium-card bg-white dark:bg-gray-950 shadow-2xl relative overflow-hidden min-h-[600px] flex flex-col">
               <div className="p-8 border-b border-gray-100 dark:border-gray-900 flex justify-between items-center">
                  <div className="text-[var(--accent)] font-display font-black text-2xl">AWAP<span className="opacity-50 text-[var(--text-primary)]">_REP_ALPHA</span></div>
                  <div className="text-[10px] font-mono opacity-40">GEN_ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}</div>
               </div>
               
               <div className="flex-1 p-12 space-y-12">
                  <div className="space-y-4">
                     <div className="h-10 w-2/3 bg-gray-100 dark:bg-gray-900 rounded-lg animate-pulse" />
                     <div className="h-6 w-1/2 bg-gray-50 dark:bg-gray-900/50 rounded-lg animate-pulse" />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-6">
                     {[1,2,3].map(i => <div key={i} className="h-24 bg-gray-50 dark:bg-gray-900/50 rounded-2xl animate-pulse" />)}
                  </div>

                  <div className="space-y-2">
                     <div className="h-4 w-full bg-gray-100 dark:bg-gray-900 rounded animate-pulse" />
                     <div className="h-4 w-full bg-gray-100 dark:bg-gray-900 rounded animate-pulse" />
                     <div className="h-4 w-5/6 bg-gray-100 dark:bg-gray-900 rounded animate-pulse" />
                  </div>
               </div>

               <div className="p-8 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-900 flex justify-between items-center">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-[var(--text-secondary)] uppercase">
                     <FileText className="w-4 h-4" />
                     Estimated Size: 4.2 MB
                  </div>
                  <button 
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="bg-[var(--accent)] text-white px-8 py-3 rounded-2xl font-black text-sm tracking-widest uppercase shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50"
                  >
                     <Download className={cn("w-4 h-4", isGenerating && "animate-bounce")} />
                     {isGenerating ? 'Compiling Engine...' : 'Generate Intelligence Report'}
                  </button>
               </div>
            </div>
         </div>
      </div>
    </div>
  );
}
