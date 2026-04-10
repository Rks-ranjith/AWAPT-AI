import { create } from 'zustand';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

interface ScanState {
  isScanning: boolean;
  activeTargetId: number | null;
  activeScanId: number | null;
  logs: string[];
  currentPhase: string;
  startScan: (targetId: number) => Promise<void>;
  stopScan: () => void;
  addLog: (log: string) => void;
  setPhase: (phase: string) => void;
}

export const useScanStore = create<ScanState>((set) => ({
  isScanning: false,
  activeTargetId: null,
  activeScanId: null,
  logs: [],
  currentPhase: 'INITIALIZING',
  startScan: async (targetId) => {
    try {
      const response = await axios.post(`${API_URL}/scans`, { target_id: targetId });
      set({ 
        isScanning: true, 
        activeTargetId: targetId, 
        activeScanId: response.data.id,
        logs: [`[SYS] Scan #${response.data.id} Initialized.`, '[NET] Establishing handshake with target...'], 
        currentPhase: 'RECONNAISSANCE' 
      });
    } catch (err) {
      console.error("Failed to start scan:", err);
    }
  },
  stopScan: () => set({ isScanning: false, activeTargetId: null, activeScanId: null }),
  addLog: (log) => set((state) => ({ logs: [...state.logs.slice(-50), log] })),
  setPhase: (phase) => set({ currentPhase: phase }),
}));
