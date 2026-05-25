import {
  FileText, Download, Settings2, Layout,
  CheckCircle2, Clock, FileSearch, AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = '/api/v1';

const TEMPLATES = [
  { id: 'exec', name: 'Executive Summary', desc: 'Business risk overview for leadership.', icon: Layout },
  { id: 'tech', name: 'Technical Deep-Dive', desc: 'Full findings with PoC, curl, and remediation.', icon: FileSearch },
  { id: 'compliance', name: 'PCI-DSS Compliance', desc: 'Control mappings for regulatory audits.', icon: CheckCircle2 },
  { id: 'bounty', name: 'Bug Bounty Export', desc: 'HackerOne/Bugcrowd-ready submissions.', icon: Clock },
] as const;

type TemplateId = (typeof TEMPLATES)[number]['id'];

interface ScanRow {
  id: string;
  state: string;
  target_id: string;
  created_at: string;
}

interface PreviewData {
  scan_id: string;
  target: string;
  scan_state: string;
  generated_at: string;
  severity_counts: Record<string, number>;
  finding_count: number;
  top_findings: Array<{
    title?: string;
    vuln_class: string;
    severity: string;
    cvss_score?: number;
    url: string;
  }>;
}

export function Reports() {
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId>('bounty');
  const [scans, setScans] = useState<ScanRow[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string>('latest');
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadScans = useCallback(async () => {
    try {
      const { data } = await axios.get<ScanRow[]>(`${API}/scans?limit=20`);
      setScans(data);
    } catch {
      setError('Could not load scans. Ensure the API is running.');
    }
  }, []);

  const loadPreview = useCallback(async () => {
    if (!selectedScanId) return;
    try {
      const { data } = await axios.get<PreviewData>(
        `${API}/reports/${selectedScanId}/preview`,
        { params: { template: selectedTemplate } }
      );
      setPreview(data);
      setError(null);
    } catch {
      setPreview(null);
    }
  }, [selectedScanId, selectedTemplate]);

  useEffect(() => {
    loadScans();
  }, [loadScans]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      await axios.post(`${API}/reports/${selectedScanId}/generate`, null, {
        params: { template: selectedTemplate },
      });
      const { data: blob } = await axios.get(
        `${API}/reports/${selectedScanId}/pdf`,
        { params: { template: selectedTemplate }, responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `AWAPT_${selectedTemplate}_${preview?.scan_id || selectedScanId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      await loadPreview();
    } catch {
      setError('Report generation failed. Complete a scan first or check API logs.');
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadFormat = async (format: 'markdown' | 'bounty' | 'csv' | 'json') => {
    setError(null);
    const scan = selectedScanId;
    const urls: Record<string, string> = {
      markdown: `${API}/reports/${scan}/markdown`,
      bounty: `${API}/reports/${scan}/bounty`,
      csv: `${API}/reports/${scan}/csv`,
      json: `${API}/reports/${scan}/json`,
    };
    try {
      if (format === 'json') {
        const { data } = await axios.get(urls.json);
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AWAPT_findings_${preview?.scan_id || scan}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        return;
      }

      await axios.post(`${API}/reports/${scan}/generate`, null, {
        params: { template: selectedTemplate },
      });

      let mimeType = 'text/plain';
      let extension = 'txt';
      let params: Record<string, string> = {};

      if (format === 'markdown') {
        mimeType = 'text/markdown';
        extension = 'md';
        params = { template: selectedTemplate };
      } else if (format === 'bounty') {
        mimeType = 'application/json';
        extension = 'json';
      } else if (format === 'csv') {
        mimeType = 'text/csv';
        extension = 'csv';
      }

      const { data } = await axios.get(urls[format], {
        params,
        responseType: 'blob',
      });

      const blob = new Blob([data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AWAPT_${format === 'bounty' ? 'bounty_submissions' : format}_${preview?.scan_id || scan}.${extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch {
      setError(`Failed to download ${format} export.`);
    }
  };

  const counts = preview?.severity_counts || {};

  return (
    <div className="p-10 max-w-7xl mx-auto space-y-12 relative z-10">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight mb-2">Intelligence Reporting</h1>
          <p className="text-lg text-[var(--text-secondary)] font-body">
            Export scan results for executives, auditors, or bug bounty programs.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => downloadFormat('csv')}
            className="p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl hover:border-[var(--accent)] text-xs font-bold uppercase tracking-widest"
          >
            CSV
          </button>
          <button
            type="button"
            onClick={() => downloadFormat('bounty')}
            className="p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl hover:border-[var(--accent)] text-xs font-bold uppercase tracking-widest"
          >
            H1 JSON
          </button>
        </div>
      </header>

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-600 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-4 space-y-6">
          <div className="flex items-center gap-3 px-2">
            <Settings2 className="w-4 h-4 text-[var(--text-secondary)]" />
            <span className="text-[10px] font-black tracking-[0.2em] uppercase text-[var(--text-secondary)]">
              Report Configuration
            </span>
          </div>

          <div className="premium-card p-4 space-y-2">
            <label className="text-[10px] font-black uppercase tracking-widest text-[var(--text-secondary)]">
              Scan
            </label>
            <select
              value={selectedScanId}
              onChange={(e) => setSelectedScanId(e.target.value)}
              className="w-full bg-[var(--bg-main)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-sm font-bold"
            >
              <option value="latest">Latest completed scan</option>
              {scans.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id.slice(0, 8)}… — {s.state}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-4">
            {TEMPLATES.map((tpl) => (
              <div
                key={tpl.id}
                onClick={() => setSelectedTemplate(tpl.id)}
                className={cn(
                  'premium-card p-6 cursor-pointer flex gap-5 group transition-all',
                  selectedTemplate === tpl.id
                    ? 'border-[var(--accent)] bg-[var(--accent)]/[0.02] shadow-[var(--accent)]/10'
                    : 'hover:border-[var(--text-secondary)]/30'
                )}
              >
                <div
                  className={cn(
                    'w-12 h-12 rounded-xl flex items-center justify-center transition-all',
                    selectedTemplate === tpl.id
                      ? 'bg-[var(--accent)] text-white'
                      : 'bg-gray-100 dark:bg-gray-800 text-[var(--text-secondary)]'
                  )}
                >
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

        <div className="lg:col-span-8 flex flex-col gap-8">
          <div className="flex-1 premium-card bg-white dark:bg-gray-950 shadow-2xl relative overflow-hidden min-h-[600px] flex flex-col">
            <div className="p-8 border-b border-gray-100 dark:border-gray-900 flex justify-between items-center">
              <div className="text-[var(--accent)] font-display font-black text-2xl">
                AWAPT<span className="opacity-50 text-[var(--text-primary)]">_REPORT</span>
              </div>
              <div className="text-[10px] font-mono opacity-60 text-right">
                {preview ? (
                  <>
                    <div>SCAN: {preview.scan_id.slice(0, 8)}…</div>
                    <div>{preview.target}</div>
                  </>
                ) : (
                  'No preview'
                )}
              </div>
            </div>

            <div className="flex-1 p-12 space-y-8 overflow-y-auto">
              {preview ? (
                <>
                  <div>
                    <h2 className="text-2xl font-display font-black tracking-tight">
                      {preview.target}
                    </h2>
                    <p className="text-sm text-[var(--text-secondary)] mt-1">
                      State: {preview.scan_state} · {preview.finding_count} findings
                    </p>
                  </div>

                  <div className="grid grid-cols-4 gap-4">
                    {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((sev) => (
                      <div
                        key={sev}
                        className="p-4 rounded-2xl bg-gray-50 dark:bg-gray-900/50 text-center"
                      >
                        <div className="text-2xl font-black">{counts[sev] ?? 0}</div>
                        <div className="text-[10px] font-bold uppercase tracking-widest opacity-60">
                          {sev}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-xs font-black uppercase tracking-widest text-[var(--text-secondary)]">
                      Top findings
                    </h3>
                    {preview.top_findings.length === 0 ? (
                      <p className="text-sm text-[var(--text-secondary)] italic">
                        No findings yet. Run a scan against an authorized target.
                      </p>
                    ) : (
                      preview.top_findings.map((f, i) => (
                        <div
                          key={i}
                          className="p-4 rounded-xl border border-[var(--border-subtle)] text-sm"
                        >
                          <div className="flex justify-between font-bold">
                            <span>{f.title || f.vuln_class}</span>
                            <span className="text-[var(--accent)]">{f.severity}</span>
                          </div>
                          <div className="text-[10px] text-[var(--text-secondary)] mt-1 truncate">
                            {f.url}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-[var(--text-secondary)]">
                  <FileText className="w-12 h-12 mb-4 opacity-30" />
                  <p className="text-sm">Run a scan to preview report content.</p>
                </div>
              )}
            </div>

            <div className="p-8 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-900 flex flex-wrap justify-between items-center gap-4">
              <div className="flex items-center gap-2 text-[10px] font-bold text-[var(--text-secondary)] uppercase">
                <FileText className="w-4 h-4" />
                Template: {selectedTemplate}
              </div>
              <div className="flex gap-3 flex-wrap">
                <button
                  type="button"
                  onClick={() => downloadFormat('markdown')}
                  className="px-4 py-2 rounded-xl border border-[var(--border-subtle)] text-xs font-bold uppercase"
                >
                  Markdown
                </button>
                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="bg-[var(--accent)] text-white px-8 py-3 rounded-2xl font-black text-sm tracking-widest uppercase shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50"
                >
                  <Download className={cn('w-4 h-4', isGenerating && 'animate-bounce')} />
                  {isGenerating ? 'Generating…' : 'Download PDF'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
