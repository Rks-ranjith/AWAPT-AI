import { create } from 'zustand';
import axios from 'axios';

const API_URL = '/api/v1';

interface Finding {
  id: string;
  vuln_class: string;
  severity: string;
  url: string;
  param?: string;
  payload?: string;
  confidence: number;
  discovered_at: string;
  cvss_score?: number;
  description?: string;
  false_positive: boolean;
}

interface FindingState {
  findings: Finding[];
  summary: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    active_scans: number;
    targets_count: number;
    vuln_distribution: Record<string, number>;
  };
  loading: boolean;
  fetchFindings: () => Promise<void>;
  fetchSummary: () => Promise<void>;
  updateFindingStatus: (id: string, updates: Record<string, unknown>) => Promise<void>;
}

export const useFindingStore = create<FindingState>((set, get) => ({
  findings: [],
  summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0, active_scans: 0, targets_count: 0, vuln_distribution: {} },
  loading: false,
  fetchFindings: async () => {
    set({ loading: true });
    try {
      const response = await axios.get(`${API_URL}/findings`);
      set({ findings: response.data, loading: false });
    } catch (err) {
      set({ loading: false });
    }
  },
  fetchSummary: async () => {
    try {
      const response = await axios.get(`${API_URL}/analytics/summary`);
      set({ summary: response.data });
    } catch (err) {}
  },
  updateFindingStatus: async (id, updates) => {
    try {
      await axios.patch(`${API_URL}/findings/${id}`, updates);
      await get().fetchFindings();
    } catch (err) {
      console.error("Failed to update finding status:", err);
    }
  }
}));
