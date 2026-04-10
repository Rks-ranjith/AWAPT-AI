import { create } from 'zustand';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

interface Finding {
  id: number;
  vuln_class: string;
  severity: string;
  endpoint_url: string;
  method: string;
  payload?: string;
  confidence: number;
  discovered_at: string;
  status: string;
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
  };
  loading: boolean;
  fetchFindings: () => Promise<void>;
  fetchSummary: () => Promise<void>;
  updateFindingStatus: (id: number, status: string) => Promise<void>;
}

export const useFindingStore = create<FindingState>((set, get) => ({
  findings: [],
  summary: { total: 0, critical: 0, high: 0, medium: 0, low: 0, active_scans: 0, targets_count: 0 },
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
  updateFindingStatus: async (id, status) => {
    try {
      await axios.patch(`${API_URL}/findings/${id}`, { status });
      await get().fetchFindings();
    } catch (err) {
      console.error("Failed to update finding status:", err);
    }
  }
}));
