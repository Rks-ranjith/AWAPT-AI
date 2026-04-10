import { Outlet, NavLink } from 'react-router-dom';
import { 
  BarChart2, Shield, Activity, Target, Settings, 
  Bell, Search, Hexagon, 
  Menu, X, ChevronRight, Sun, Moon, FileText
} from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useThemeStore } from '@/store/useThemeStore';

const NAV_GROUPS = [
  {
    title: 'Monitor',
    items: [
      { id: 'dashboard', label: 'Overview', icon: BarChart2, path: '/dashboard' },
      { id: 'scans', label: 'Engine Console', icon: Activity, path: '/scans' },
      { id: 'analytics', label: 'Security Analytics', icon: BarChart2, path: '/analytics' },
    ]
  },
  {
    title: 'Operation',
    items: [
      { id: 'targets', label: 'Attack Surface', icon: Target, path: '/targets' },
      { id: 'findings', label: 'Intelligence', icon: Shield, path: '/findings' },
      { id: 'reports', label: 'Report Builder', icon: FileText, path: '/reports' },
    ]
  },
  {
    title: 'Platform',
    items: [
      { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
    ]
  }
];

export function DashboardLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const { theme, toggleTheme } = useThemeStore();

  return (
    <div className="flex h-screen w-full bg-[var(--bg-main)] overflow-hidden transition-colors duration-500">
      {/* Background Decor */}
      <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-[var(--accent)]/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-1/3 h-1/3 bg-[var(--accent)]/5 rounded-full blur-[100px] pointer-events-none" />

      {/* Sidebar - Modern Premium */}
      <motion.aside
        animate={{ width: isSidebarOpen ? 260 : 80 }}
        className="relative z-50 flex-shrink-0 bg-[var(--bg-card)] border-r border-[var(--border-subtle)] backdrop-blur-xl flex flex-col shadow-xl"
      >
        {/* Sidebar Header */}
        <div className="h-20 flex items-center px-6 gap-3 border-b border-[var(--border-subtle)]">
          <div className="w-10 h-10 rounded-xl bg-[var(--accent)] flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Hexagon className="w-6 h-6 text-white" />
          </div>
          <AnimatePresence>
            {isSidebarOpen && (
              <motion.span 
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="font-display font-black text-xl tracking-tight text-[var(--text-primary)]"
              >
                AWAP<span className="text-[var(--accent)]">.AI</span>
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation Content */}
        <nav className="flex-1 overflow-y-auto py-8 px-4 space-y-8 scrollbar-hide">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="space-y-2">
              <AnimatePresence mode="wait">
                {isSidebarOpen && (
                  <motion.h3 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="px-3 text-[11px] font-display font-bold text-[var(--text-secondary)] uppercase tracking-[0.2em]"
                  >
                    {group.title}
                  </motion.h3>
                )}
              </AnimatePresence>
              
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    className={({ isActive }) => cn(
                      "flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group relative",
                      isActive 
                        ? "bg-[var(--accent)] text-white shadow-lg shadow-indigo-500/20" 
                        : "text-[var(--text-secondary)] hover:bg-[var(--accent)]/5 hover:text-[var(--accent)]"
                    )}
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon className={cn("w-5 h-5 flex-shrink-0 transition-transform group-hover:scale-110")} />
                        {isSidebarOpen && (
                          <span className="font-body font-semibold text-sm tracking-wide">{item.label}</span>
                        )}
                        {isActive && isSidebarOpen && (
                          <motion.div 
                            layoutId="nav-indicator"
                            className="ml-auto"
                          >
                             <ChevronRight className="w-4 h-4 opacity-50" />
                          </motion.div>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-[var(--border-subtle)] space-y-4">
           {isSidebarOpen && (
             <div className="p-4 rounded-2xl bg-[var(--bg-main)]/50 border border-[var(--border-subtle)] space-y-3">
                <div className="flex justify-between items-center text-[10px] font-bold tracking-widest text-[var(--text-secondary)]">
                   <span>RESOURCE LOAD</span>
                   <span className="text-[var(--accent)]">12.4%</span>
                </div>
                <div className="h-1.5 w-full bg-[var(--border-subtle)] rounded-full overflow-hidden">
                   <motion.div 
                     initial={{ width: 0 }}
                     animate={{ width: '12.4%' }}
                     className="h-full bg-[var(--accent)]"
                   />
                </div>
             </div>
           )}
           <button 
             onClick={() => setIsSidebarOpen(!isSidebarOpen)}
             className="w-full flex items-center justify-center p-2 text-[var(--text-secondary)] hover:text-[var(--accent)] transition-colors"
           >
              {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
           </button>
        </div>
      </motion.aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        {/* Minimal Header */}
        <header className="h-20 flex-shrink-0 flex items-center justify-between px-10 relative z-40 bg-[var(--bg-main)]/50 backdrop-blur-md">
           <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-xs font-display font-bold text-[var(--text-secondary)] tracking-widest uppercase">
                 <span>PROJECTS</span>
                 <ChevronRight className="w-3 h-3" />
                 <span className="text-[var(--text-primary)] tracking-normal normal-case font-black text-sm">Main Alpha-01</span>
              </div>
           </div>

           <div className="flex items-center gap-6">
              {/* Modern Search */}
              <div className="hidden md:flex items-center gap-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] px-4 py-2.5 rounded-2xl focus-within:ring-2 ring-[var(--accent)]/20 transition-all shadow-sm">
                 <Search className="w-4 h-4 text-[var(--text-secondary)]" />
                 <input 
                   type="text" 
                   placeholder="Search commands..." 
                   className="bg-transparent border-none outline-none text-sm font-body w-48 placeholder:text-[var(--text-secondary)]/50"
                 />
                 <div className="flex gap-1">
                    <kbd className="px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[10px] text-[var(--text-secondary)]">⌘</kbd>
                    <kbd className="px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--bg-main)] text-[10px] text-[var(--text-secondary)]">K</kbd>
                 </div>
              </div>

              <div className="flex items-center gap-3">
                 <button 
                    onClick={toggleTheme}
                    className="p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all group"
                 >
                    {theme === 'dark' ? (
                      <Sun className="w-5 h-5 text-[var(--text-secondary)] group-hover:text-orange-400" />
                    ) : (
                      <Moon className="w-5 h-5 text-[var(--text-secondary)] group-hover:text-indigo-500" />
                    )}
                 </button>
                 <button className="relative p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/50 transition-all group">
                    <Bell className="w-5 h-5 text-[var(--text-secondary)] group-hover:text-[var(--accent)]" />
                    <span className="absolute top-3 right-3 w-2.5 h-2.5 bg-red-500 border-2 border-[var(--bg-card)] rounded-full animate-pulse" />
                 </button>
                 <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 border-2 border-white/10 shadow-lg cursor-pointer hover:scale-105 transition-transform" />
              </div>
           </div>
        </header>

        {/* Dynamic Page Content */}
        <main className="flex-1 overflow-y-auto relative no-scrollbar pb-20">
           <Outlet />
        </main>
      </div>
    </div>
  );
}
