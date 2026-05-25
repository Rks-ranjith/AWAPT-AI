import { create } from 'zustand';
import axios from 'axios';

const API_URL = '/api/v1';

interface Target {
  id: number;
  name: string;
  base_url: string;
  status: string;
  created_at: string;
}

interface TargetState {
  targets: Target[];
  loading: boolean;
  error: string | null;
  fetchTargets: () => Promise<void>;
  addTarget: (name: string, url: string) => Promise<void>;
  deleteTarget: (id: number) => Promise<void>;
}

export const useTargetStore = create<TargetState>((set, get) => ({
  targets: [],
  loading: false,
  error: null,
  fetchTargets: async () => {
    set({ loading: true });
    try {
      const response = await axios.get(`${API_URL}/targets/`);
      set({ targets: response.data, loading: false });
    } catch (err) {
      set({ error: 'Failed to fetch targets', loading: false });
    }
  },
  addTarget: async (name, url) => {
    try {
      // Backend expects 'base_url' as per schema, but if my routes use schemas.TargetCreate, it might be different.
      // Let's check schemas/targets.py or schemas.py
      await axios.post(`${API_URL}/targets/`, { name, base_url: url });
      await get().fetchTargets();
    } catch (err) {
      set({ error: 'Failed to add target' });
    }
  },
  deleteTarget: async (id) => {
    try {
      await axios.delete(`${API_URL}/targets/${id}`);
      await get().fetchTargets();
    } catch (err) {
      set({ error: 'Failed to delete target' });
    }
  },
}));
