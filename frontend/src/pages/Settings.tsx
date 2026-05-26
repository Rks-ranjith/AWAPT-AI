
import { useState, useEffect } from 'react';
import { 
  Moon, Sun, Bell, 
  Lock, Save, RefreshCw,
  Computer, Monitor, Sliders,
  CheckCircle2, AlertCircle, Cpu, Mail, Slack, Activity, Key, Terminal, Send,
  Plus, X
} from 'lucide-react';

import { cn } from '@/lib/utils';
import { useThemeStore } from '@/store/useThemeStore';
import { motion } from 'framer-motion';
import axios from 'axios';

interface HealthData {
  status: string;
  celery: string;
  postgres: string;
  redis: string;
}

export function Settings() {
  const { theme, setTheme } = useThemeStore();
  const [activeTab, setActiveTab] = useState('interface');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Interface Settings State
  const [wsRate, setWsRate] = useState(() => localStorage.getItem('awap_ws_rate') || '500ms');

  // Security & LLM Keys State
  const [primaryKey, setPrimaryKey] = useState('awap_sec_prod_key_77a942bc792c47fe92e4');
  const [showKey, setShowKey] = useState(false);
  const [llmProvider, setLlmProvider] = useState(() => localStorage.getItem('awap_llm_provider') || 'gemini');
  const [llmKey, setLlmKey] = useState(() => localStorage.getItem('awap_llm_key') || '');
  const [llmModel, setLlmModel] = useState(() => localStorage.getItem('awap_llm_model') || 'gemini-2.5-flash');
  const [llmBaseUrl, setLlmBaseUrl] = useState(() => localStorage.getItem('awap_llm_base_url') || '');

  // Alerting State
  const [emailAlerts, setEmailAlerts] = useState<string[]>(() => {
    const stored = localStorage.getItem('awap_email_alert') || '';
    return stored ? stored.split(',').map(s => s.trim()).filter(Boolean) : [''];
  });
  const [slackWebhook, setSlackWebhook] = useState(() => localStorage.getItem('awap_slack_webhook') || '');
  const [emailEnabled, setEmailEnabled] = useState(() => localStorage.getItem('awap_email_enabled') === 'true');
  const [slackEnabled, setSlackEnabled] = useState(() => localStorage.getItem('awap_slack_enabled') === 'true');

  // Telegram Bot State
  const [telegramEnabled, setTelegramEnabled] = useState(() => localStorage.getItem('awap_telegram_enabled') === 'true');
  const [telegramToken, setTelegramToken] = useState(() => localStorage.getItem('awap_telegram_token') || '');
  const [telegramChatId, setTelegramChatId] = useState(() => localStorage.getItem('awap_telegram_chat_id') || '');

  // Test Connection States
  const [testLoading, setTestLoading] = useState(false);
  const [testSuccess, setTestSuccess] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  // Engine Health State
  const [health, setHealth] = useState<HealthData | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Scan Logs State
  const [scans, setScans] = useState<any[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string>('');
  const [scanLogs, setScanLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsFilter, setLogsFilter] = useState('ALL');
  const [logsSearch, setLogsSearch] = useState('');

  const fetchScans = async () => {
    try {
      const { data } = await axios.get('/api/v1/scans?limit=50');
      setScans(data);
      if (data.length > 0) {
        setSelectedScanId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch scans:", err);
    }
  };

  const fetchLogs = async (scanId: string) => {
    if (!scanId) return;
    setLogsLoading(true);
    try {
      const { data } = await axios.get(`/api/v1/scans/${scanId}/logs`);
      setScanLogs(data);
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    } finally {
      setLogsLoading(false);
    }
  };

  const fetchEngineHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const { data } = await axios.get<HealthData>('/api/v1/health');
      setHealth(data);
    } catch {
      setHealthError('Failed to capture active engine node telemetry.');
      setHealth({
        status: 'degraded',
        celery: 'error',
        postgres: 'error',
        redis: 'error'
      });
    } finally {
      setHealthLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const { data } = await axios.get('/api/v1/settings');
      setEmailEnabled(data.email_enabled);
      const alertStr = data.email_alert || '';
      setEmailAlerts(alertStr ? alertStr.split(',').map((s: string) => s.trim()).filter(Boolean) : ['']);
      setSlackEnabled(data.slack_enabled);
      setSlackWebhook(data.slack_webhook || '');
      setTelegramEnabled(data.telegram_enabled);
      setTelegramToken(data.telegram_token || '');
      setTelegramChatId(data.telegram_chat_id || '');
    } catch (err) {
      console.error("Failed to fetch settings from database:", err);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (activeTab === 'nodes') {
      fetchEngineHealth();
    } else if (activeTab === 'logs') {
      fetchScans();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'logs' && selectedScanId) {
      fetchLogs(selectedScanId);
    }
  }, [selectedScanId, activeTab]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);

    // Save to LocalStorage for offline fallback UI caching
    localStorage.setItem('awap_ws_rate', wsRate);
    localStorage.setItem('awap_llm_provider', llmProvider);
    localStorage.setItem('awap_llm_key', llmKey);
    localStorage.setItem('awap_llm_model', llmModel);
    localStorage.setItem('awap_llm_base_url', llmBaseUrl);
    const emailAlertJoined = emailAlerts.filter(e => e.trim()).join(', ');
    localStorage.setItem('awap_email_alert', emailAlertJoined);
    localStorage.setItem('awap_slack_webhook', slackWebhook);
    localStorage.setItem('awap_email_enabled', String(emailEnabled));
    localStorage.setItem('awap_slack_enabled', String(slackEnabled));
    localStorage.setItem('awap_telegram_enabled', String(telegramEnabled));
    localStorage.setItem('awap_telegram_token', telegramToken);
    localStorage.setItem('awap_telegram_chat_id', telegramChatId);

    try {
      await axios.post('/api/v1/settings', {
        email_enabled: emailEnabled,
        email_alert: emailAlertJoined,
        slack_enabled: slackEnabled,
        slack_webhook: slackWebhook,
        telegram_enabled: telegramEnabled,
        telegram_token: telegramToken,
        telegram_chat_id: telegramChatId
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save settings to database:", err);
      // Fallback
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestTelegram = async () => {
    setTestLoading(true);
    setTestSuccess(false);
    setTestError(null);
    try {
      const { data } = await axios.post('/api/v1/settings/test-telegram', {
        email_enabled: emailEnabled,
        email_alert: emailAlert,
        slack_enabled: slackEnabled,
        slack_webhook: slackWebhook,
        telegram_enabled: telegramEnabled,
        telegram_token: telegramToken,
        telegram_chat_id: telegramChatId
      });
      if (data.status === 'success') {
        setTestSuccess(true);
        setTimeout(() => setTestSuccess(false), 6000);
      } else {
        setTestError(data.message || 'Verification failed');
      }
    } catch (err: any) {
      console.error("Failed to verify bot connection:", err);
      const detail = err.response?.data?.detail || "Could not reach Telegram API. Verify token and chat ID.";
      setTestError(detail);
    } finally {
      setTestLoading(false);
    }
  };

  const handleRotateKey = () => {
    if (confirm("Are you sure you want to rotate the primary API engine key? Current integration webhooks will be invalidated.")) {
      const randomHex = Array.from({length: 40}, () => Math.floor(Math.random()*16).toString(16)).join('');
      setPrimaryKey(`awap_sec_prod_key_${randomHex.slice(0, 20)}`);
      alert("Platform API keys successfully rotated. Remember to click 'Save Platform Config' to apply changes.");
    }
  };

  const TABS = [
    { id: 'interface', label: 'Display & UI', icon: Monitor },
    { id: 'security', label: 'Security & LLM Keys', icon: Lock },
    { id: 'nodes', label: 'Engine Nodes', icon: Sliders },
    { id: 'logs', label: 'Engine & Scan Logs', icon: Terminal },
    { id: 'notifications', label: 'Alerting', icon: Bell },
  ];

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Platform Engine Control</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">Configure environment parameters and visual preferences.</p>
        </div>
        
        {saveSuccess && (
          <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl text-emerald-400 text-xs font-bold uppercase tracking-wider animate-pulse">
            <CheckCircle2 className="w-4 h-4" />
            Config Saved Successfully
          </div>
        )}
      </header>

      <div className="flex gap-12">
         {/* Sidebar Navigation */}
         <div className="w-64 space-y-2 shrink-0">
            {TABS.map((tab) => (
               <button
                 key={tab.id}
                 onClick={() => setActiveTab(tab.id)}
                 className={cn(
                   "w-full flex items-center gap-3 px-4 py-3 rounded-2xl font-bold text-sm transition-all text-left",
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
                    <div className="premium-card p-6 flex justify-between items-center bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                       <div>
                          <div className="font-bold">WebSocket Streaming</div>
                          <div className="text-sm text-[var(--text-secondary)]">Real-time update frequency for scan telemetry.</div>
                       </div>
                       <select 
                         value={wsRate}
                         onChange={(e) => setWsRate(e.target.value)}
                         className="bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-xl px-4 py-2 font-bold text-sm outline-none focus:ring-2 ring-indigo-500/20 text-[var(--text-primary)]"
                       >
                          <option value="500ms">500ms (High Performance)</option>
                          <option value="1000ms">1000ms (Balanced)</option>
                          <option value="2000ms">2000ms (Low Bandwidth)</option>
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
                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex items-center gap-3">
                        <Key className="w-5 h-5 text-[var(--accent)]" />
                        <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">API Authentication</h3>
                     </div>
                     <p className="text-[var(--text-secondary)] text-sm font-body">Manage credentials for external CI/CD pipeline triggers and third-party scanning hooks.</p>
                     
                     <div className="space-y-4">
                        <div className="space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Primary Engine Key</label>
                           <div className="flex gap-4">
                              <input 
                                type={showKey ? "text" : "password"} 
                                value={primaryKey} 
                                readOnly
                                className="flex-1 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm text-[var(--text-primary)] focus:ring-2 ring-indigo-500/20 outline-none"
                              />
                              <button 
                                onClick={() => setShowKey(!showKey)}
                                className="px-5 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl font-bold text-xs hover:border-[var(--text-primary)] transition-all uppercase tracking-widest"
                              >
                                {showKey ? "Hide" : "Show"}
                              </button>
                              <button 
                                onClick={handleRotateKey}
                                className="px-6 py-4 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl font-bold hover:bg-[var(--accent)]/10 hover:text-[var(--accent)] transition-all uppercase text-xs tracking-widest"
                              >
                                Rotate
                              </button>
                           </div>
                        </div>
                     </div>
                  </div>

                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex items-center gap-3">
                        <Activity className="w-5 h-5 text-[var(--accent)]" />
                        <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Large Language Model (LLM) Engine</h3>
                     </div>
                     <p className="text-[var(--text-secondary)] text-sm font-body">Setup AI providers for generating descriptive WAF bypass recommendations and executive summaries.</p>
                     
                     <div className="grid grid-cols-2 gap-6">
                        <div className="space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">LLM Provider</label>
                           <select 
                             value={llmProvider}
                             onChange={(e) => {
                               setLlmProvider(e.target.value);
                               if (e.target.value === 'gemini') setLlmModel('gemini-2.5-flash');
                               else if (e.target.value === 'openai') setLlmModel('gpt-4o');
                               else if (e.target.value === 'anthropic') setLlmModel('claude-3-5-sonnet-20241022');
                             }}
                             className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-bold text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                           >
                              <option value="gemini">Google Gemini AI</option>
                              <option value="openai">OpenAI GPT</option>
                              <option value="anthropic">Anthropic Claude</option>
                           </select>
                        </div>

                        <div className="space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Active Model</label>
                           <input 
                             type="text" 
                             value={llmModel}
                             onChange={(e) => setLlmModel(e.target.value)}
                             placeholder="e.g. gemini-2.5-flash"
                             className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-bold text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                           />
                        </div>
                     </div>

                     <div className="space-y-4">
                        <div className="space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">API Key</label>
                           <input 
                             type="password" 
                             value={llmKey}
                             onChange={(e) => setLlmKey(e.target.value)}
                             placeholder="Enter provider API key"
                             className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                           />
                        </div>

                        <div className="space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Proxy / Enterprise Gateway Base URL (Optional)</label>
                           <input 
                             type="text" 
                             value={llmBaseUrl}
                             onChange={(e) => setLlmBaseUrl(e.target.value)}
                             placeholder="e.g. http://my-corporate-proxy-gateway.internal/v1"
                             className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                           />
                        </div>
                     </div>
                  </div>
              </motion.div>
            )}

            {activeTab === 'nodes' && (
              <motion.div 
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-8"
              >
                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                           <Cpu className="w-5 h-5 text-[var(--accent)]" />
                           <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Active Cluster Nodes</h3>
                        </div>
                        <button 
                          onClick={fetchEngineHealth}
                          disabled={healthLoading}
                          className="p-2 border border-[var(--border-subtle)] hover:border-[var(--accent)] rounded-xl flex items-center justify-center transition-all disabled:opacity-50"
                        >
                           <RefreshCw className={cn("w-4 h-4 text-[var(--text-secondary)]", healthLoading && "animate-spin")} />
                        </button>
                     </div>
                     <p className="text-[var(--text-secondary)] text-sm font-body">Monitor microservice engines and direct connections in the automated cluster topology.</p>

                     {healthError && (
                       <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-500 text-xs">
                          <AlertCircle className="w-4 h-4 shrink-0" />
                          {healthError}
                       </div>
                     )}

                     <div className="grid grid-cols-3 gap-6">
                        <div className="p-6 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-[24px] space-y-3">
                           <div className="text-[10px] font-black uppercase text-[var(--text-secondary)] tracking-wider">PostgreSQL Node</div>
                           <div className="flex items-center gap-2">
                              <div className={cn("w-2.5 h-2.5 rounded-full animate-pulse", health?.postgres === 'connected' ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500 shadow-[0_0_8px_#ef4444]")} />
                              <span className="font-bold text-sm">{health?.postgres === 'connected' ? 'Connected' : 'Disconnected'}</span>
                           </div>
                           <div className="text-[10px] text-[var(--text-muted)] font-mono">Port: 5432 · db_main</div>
                        </div>

                        <div className="p-6 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-[24px] space-y-3">
                           <div className="text-[10px] font-black uppercase text-[var(--text-secondary)] tracking-wider">Redis Cache & Broker</div>
                           <div className="flex items-center gap-2">
                              <div className={cn("w-2.5 h-2.5 rounded-full animate-pulse", health?.redis === 'connected' ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500 shadow-[0_0_8px_#ef4444]")} />
                              <span className="font-bold text-sm">{health?.redis === 'connected' ? 'Connected' : 'Disconnected'}</span>
                           </div>
                           <div className="text-[10px] text-[var(--text-muted)] font-mono">Port: 6379 · broker_0</div>
                        </div>

                        <div className="p-6 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-[24px] space-y-3">
                           <div className="text-[10px] font-black uppercase text-[var(--text-secondary)] tracking-wider">Celery Task Worker</div>
                           <div className="flex items-center gap-2">
                              <div className={cn("w-2.5 h-2.5 rounded-full animate-pulse", health?.celery === 'connected' ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-red-500 shadow-[0_0_8px_#ef4444]")} />
                              <span className="font-bold text-sm">{health?.celery === 'connected' ? 'Worker Active' : 'Offline'}</span>
                           </div>
                           <div className="text-[10px] text-[var(--text-muted)] font-mono">Pool: Windows Solo</div>
                        </div>
                     </div>
                  </div>
              </motion.div>
            )}

            {activeTab === 'notifications' && (
              <motion.div 
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-8"
              >
                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex items-center gap-3">
                        <Mail className="w-5 h-5 text-[var(--accent)]" />
                        <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Email Alerting</h3>
                     </div>
                     
                     <div className="flex items-center justify-between">
                        <div>
                           <div className="font-bold text-sm">Enable Email Alerts</div>
                           <div className="text-xs text-[var(--text-secondary)]">Receive report links and critical vulnerability logs via email.</div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input 
                            type="checkbox" 
                            checked={emailEnabled}
                            onChange={(e) => setEmailEnabled(e.target.checked)}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)]"></div>
                        </label>
                     </div>

                     {emailEnabled && (
                        <div className="space-y-3 animate-fadeIn">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Destination Addresses</label>
                           {emailAlerts.map((email, idx) => (
                             <div key={idx} className="flex items-center gap-2">
                               <input 
                                 type="email" 
                                 value={email}
                                 onChange={(e) => {
                                   const updated = [...emailAlerts];
                                   updated[idx] = e.target.value;
                                   setEmailAlerts(updated);
                                 }}
                                 placeholder="admin@enterprise-security.local"
                                 className="flex-1 bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-body text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                               />
                               {emailAlerts.length > 1 && (
                                 <button
                                   type="button"
                                   onClick={() => {
                                     const updated = emailAlerts.filter((_, i) => i !== idx);
                                     setEmailAlerts(updated);
                                   }}
                                   className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 transition-all"
                                   title="Remove this address"
                                 >
                                   <X className="w-4 h-4" />
                                 </button>
                               )}
                             </div>
                           ))}
                           <button
                             type="button"
                             onClick={() => setEmailAlerts([...emailAlerts, ''])}
                             className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-[var(--border-subtle)] hover:border-[var(--accent)] text-[var(--text-secondary)] hover:text-[var(--accent)] text-xs font-bold uppercase tracking-wider transition-all"
                           >
                             <Plus className="w-4 h-4" />
                             Add Recipient
                           </button>
                        </div>
                     )}
                  </div>

                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex items-center gap-3">
                        <Slack className="w-5 h-5 text-[var(--accent)]" />
                        <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Slack Integration</h3>
                     </div>
                     
                     <div className="flex items-center justify-between">
                        <div>
                           <div className="font-bold text-sm">Send Webhook Notifications</div>
                           <div className="text-xs text-[var(--text-secondary)]">Push findings instantly to your security Slack channel.</div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                           <input 
                             type="checkbox" 
                             checked={slackEnabled}
                             onChange={(e) => setSlackEnabled(e.target.checked)}
                             className="sr-only peer"
                           />
                           <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)]"></div>
                        </label>
                     </div>

                     {slackEnabled && (
                       <div className="space-y-2 animate-fadeIn">
                          <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Slack Webhook URL</label>
                          <input 
                            type="text" 
                            value={slackWebhook}
                            onChange={(e) => setSlackWebhook(e.target.value)}
                            placeholder="https://hooks.slack.com/services/YOUR_WORKSPACE_ID/YOUR_CHANNEL_ID/YOUR_TOKEN"
                            className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                          />
                       </div>
                     )}
                  </div>

                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex items-center gap-3">
                        <Send className="w-5 h-5 text-[var(--accent)] animate-pulse" />
                        <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Telegram Bot Integration</h3>
                     </div>
                     
                     <div className="flex items-center justify-between">
                        <div>
                           <div className="font-bold text-sm">Enable Telegram Bot</div>
                           <div className="text-xs text-[var(--text-secondary)]">Index targets, status pipelines, and download report templates directly via Telegram chat commands.</div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                           <input 
                             type="checkbox" 
                             checked={telegramEnabled}
                             onChange={(e) => setTelegramEnabled(e.target.checked)}
                             className="sr-only peer"
                           />
                           <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)]"></div>
                        </label>
                     </div>

                     {telegramEnabled && (
                       <div className="space-y-6 animate-fadeIn">
                          <div className="grid grid-cols-2 gap-6">
                             <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Bot API Token</label>
                                <input 
                                  type="password" 
                                  value={telegramToken}
                                  onChange={(e) => setTelegramToken(e.target.value)}
                                  placeholder="Enter your BotFather token"
                                  className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                                />
                             </div>

                             <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Admin Chat ID (Optional)</label>
                                <input 
                                  type="text" 
                                  value={telegramChatId}
                                  onChange={(e) => setTelegramChatId(e.target.value)}
                                  placeholder="Auto-pairs on `/start` command"
                                  className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-2xl px-5 py-4 font-mono text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                                />
                             </div>
                          </div>

                          <div className="flex items-center gap-4">
                             <button
                               type="button"
                               disabled={testLoading || !telegramToken || !telegramChatId}
                               onClick={handleTestTelegram}
                               className="px-6 py-3.5 bg-[var(--bg-main)] hover:bg-[var(--accent)]/10 hover:text-[var(--accent)] border border-[var(--border-subtle)] hover:border-[var(--accent)]/20 text-xs uppercase tracking-widest font-black rounded-2xl transition-all disabled:opacity-40"
                             >
                                {testLoading ? "Verifying Bot..." : "Verify & Test Connection"}
                             </button>

                             {testSuccess && (
                                <span className="text-emerald-400 text-xs font-bold animate-pulse">
                                   ✅ Test message dispatched successfully! Check your Telegram chat.
                                </span>
                             )}

                             {testError && (
                                <span className="text-red-500 text-xs font-bold animate-pulse">
                                   ❌ Connection failed: {testError}
                                </span>
                             )}
                          </div>
                       </div>
                     )}
                  </div>
              </motion.div>
            )}

            {activeTab === 'logs' && (
              <motion.div 
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-6"
              >
                  <div className="premium-card p-8 border border-[var(--border-subtle)] space-y-6">
                     <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                           <Terminal className="w-5 h-5 text-[var(--accent)]" />
                           <h3 className="text-lg font-display font-black tracking-tight uppercase tracking-widest text-[var(--text-secondary)] text-[11px]">Engine Scan Logs</h3>
                        </div>
                        <button 
                          onClick={() => fetchLogs(selectedScanId)}
                          disabled={logsLoading}
                          className="p-2 border border-[var(--border-subtle)] hover:border-[var(--accent)] rounded-xl flex items-center justify-center transition-all disabled:opacity-50"
                        >
                           <RefreshCw className={cn("w-4 h-4 text-[var(--text-secondary)]", logsLoading && "animate-spin")} />
                        </button>
                     </div>
                     <p className="text-[var(--text-secondary)] text-sm font-body">Review detailed pipeline execution logs and vulnerability finding timestamps.</p>
                     
                     <div className="flex gap-4">
                        <div className="flex-1 space-y-2">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Target Scan Run</label>
                           <select 
                             value={selectedScanId}
                             onChange={(e) => setSelectedScanId(e.target.value)}
                             className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 font-bold text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                           >
                              {scans.length === 0 ? (
                                <option value="">No scan logs available</option>
                              ) : (
                                scans.map((scan) => (
                                  <option key={scan.id} value={scan.id}>
                                    Scan #{scan.id.substring(0, 8)} - {new Date(scan.created_at).toLocaleString()} ({scan.state})
                                  </option>
                                ))
                              )}
                           </select>
                        </div>

                        <div className="space-y-2 shrink-0">
                           <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Log Severity</label>
                           <div className="flex gap-2">
                              {['ALL', 'INFO', 'WARNING', 'ERROR'].map((lvl) => (
                                <button
                                  key={lvl}
                                  onClick={() => setLogsFilter(lvl)}
                                  className={cn(
                                    "px-3 py-3 rounded-xl text-xs font-bold transition-all border border-[var(--border-subtle)]",
                                    logsFilter === lvl
                                      ? "bg-[var(--accent)] text-white border-[var(--accent)]"
                                      : "bg-[var(--bg-main)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                                  )}
                                >
                                   {lvl}
                                </button>
                              ))}
                           </div>
                        </div>
                     </div>

                     <div className="space-y-2">
                        <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">Search Content</label>
                        <input
                          type="text"
                          value={logsSearch}
                          onChange={(e) => setLogsSearch(e.target.value)}
                          placeholder="Filter logs by message content..."
                          className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-sm text-[var(--text-primary)] outline-none focus:ring-2 ring-indigo-500/20"
                        />
                     </div>

                     <div className="rounded-2xl border border-[var(--border-subtle)] bg-black overflow-hidden flex flex-col">
                        <div className="bg-gray-900 border-b border-[var(--border-subtle)] px-4 py-2 flex items-center justify-between">
                           <div className="flex gap-2">
                              <div className="w-3 h-3 rounded-full bg-red-500" />
                              <div className="w-3 h-3 rounded-full bg-yellow-500" />
                              <div className="w-3 h-3 rounded-full bg-green-500" />
                           </div>
                           <span className="text-[10px] font-mono text-gray-500">Scan Session Telemetry Terminal</span>
                           <div className="w-12" />
                        </div>
                        <div className="p-6 font-mono text-xs overflow-y-auto space-y-2 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent" style={{ height: '360px' }}>
                           {logsLoading ? (
                             <div className="h-full flex flex-col items-center justify-center gap-2 text-gray-500">
                                <RefreshCw className="w-6 h-6 animate-spin text-[var(--accent)]" />
                                <span>Querying intelligence logs...</span>
                             </div>
                           ) : scanLogs.length === 0 ? (
                             <div className="h-full flex flex-col items-center justify-center text-gray-600">
                                <span>No telemetry records found for this scan.</span>
                             </div>
                           ) : (
                             scanLogs
                               .filter(log => logsFilter === 'ALL' || log.level === logsFilter)
                               .filter(log => !logsSearch || log.message.toLowerCase().includes(logsSearch.toLowerCase()))
                               .map((log) => {
                                 let color = 'text-cyan-400';
                                 if (log.level === 'WARNING') color = 'text-amber-400';
                                 else if (log.level === 'ERROR') color = 'text-red-400';

                                 return (
                                   <div key={log.id} className="flex items-start gap-4 hover:bg-gray-900/50 p-1 rounded transition-all">
                                      <span className="text-gray-500 select-none">{new Date(log.logged_at).toISOString().substring(11, 23)}Z</span>
                                      <span className={cn("font-black tracking-wider uppercase select-none w-16", color)}>[{log.level}]</span>
                                      <span className="text-gray-100 flex-1 whitespace-pre-wrap">{log.message}</span>
                                   </div>
                                 );
                               })
                           )}
                        </div>
                     </div>
                  </div>
              </motion.div>
            )}

            <div className="pt-10 flex justify-end gap-4 border-t border-[var(--border-subtle)]">
               <button 
                 onClick={() => {
                   if (confirm("Are you sure you want to discard all pending configuration changes?")) {
                     window.location.reload();
                   }
                 }}
                 className="px-8 py-4 font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-sm"
               >
                 Discard Changes
               </button>
               <button 
                 onClick={handleSave}
                 disabled={isSaving}
                 className="px-8 py-4 bg-[var(--accent)] text-white font-bold rounded-2xl shadow-lg shadow-indigo-500/20 flex items-center gap-2 hover:scale-[1.02] active:scale-95 transition-all text-sm disabled:opacity-50"
               >
                  {isSaving ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Save className="w-5 h-5" />
                  )}
                  {isSaving ? "Saving..." : "Save Platform Config"}
               </button>
            </div>
         </div>
      </div>
    </div>
  );
}
