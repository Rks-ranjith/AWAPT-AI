import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

const API_URL = '/api/v1';

interface ScanState {
  isScanning: boolean;
  activeTargetId: string | null;
  activeScanId: string | null;
  logs: string[];
  currentPhase: string;
  scanComplete: boolean;
  startScan: (targetId: string | number) => Promise<boolean>;
  stopScan: () => void;
  addLog: (log: string) => void;
  setPhase: (phase: string) => void;
  setScanComplete: () => void;
  recoverScan: () => Promise<void>;
}

export const useScanStore = create<ScanState>()(
  persist(
    (set, get) => ({
      isScanning: false,
      activeTargetId: null,
      activeScanId: null,
      logs: [],
      currentPhase: 'INITIALIZING',
      scanComplete: false,

      startScan: async (targetId) => {
        try {
          const response = await axios.post(`${API_URL}/scans`, { target_id: targetId });
          set({
            isScanning: true,
            activeTargetId: String(targetId),
            activeScanId: String(response.data.id),
            logs: [
              `[SYS] Scan #${response.data.id} Initialized.`,
              '[NET] Establishing handshake with target...',
            ],
            currentPhase: 'RECONNAISSANCE',
            scanComplete: false,
          });
          return true;
        } catch (err) {
          console.error("Failed to start scan:", err);
          return false;
        }
      },

      stopScan: () =>
        set({
          isScanning: false,
          activeTargetId: null,
          activeScanId: null,
          scanComplete: false,
          currentPhase: 'INITIALIZING',
        }),

      addLog: (log) =>
        set((state) => ({ logs: [...state.logs.slice(-100), log] })),

      setPhase: (phase) => set({ currentPhase: phase }),

      setScanComplete: () =>
        set({
          isScanning: false,
          scanComplete: true,
          currentPhase: 'VULN_EXPLOITATION',
        }),

      // Recover scan state after page refresh
      recoverScan: async () => {
        const { activeScanId, isScanning } = get();
        if (!activeScanId) return;

        try {
          const resp = await axios.get(`${API_URL}/scans/${activeScanId}`);
          const scan = resp.data;

          const terminalStates = ['COMPLETE', 'FAILED', 'ABORTED'];
          if (terminalStates.includes(scan.state)) {
            set({
              isScanning: false,
              scanComplete: scan.state === 'COMPLETE',
              currentPhase: 'VULN_EXPLOITATION',
            });
          } else if (scan.state) {
            // Scan is still running — reconnect
            const phaseMap: Record<string, string> = {
              'CREATED': 'RECONNAISSANCE',
              'SCOPE_VERIFIED': 'RECONNAISSANCE',
              'RECON': 'RECONNAISSANCE',
              'CRAWL': 'CRAWLING',
              'MAPPING': 'CRAWLING',
              'ATTACK': 'AI_PLANNING',
              'ANALYSIS': 'AI_PLANNING',
              'REPORTING': 'VULN_EXPLOITATION',
            };
            set({
              isScanning: true,
              currentPhase: phaseMap[scan.state] || 'RECONNAISSANCE',
            });
          }
        } catch {
          // Scan not found — clear state
          set({
            isScanning: false,
            activeScanId: null,
            activeTargetId: null,
          });
        }
      },
    }),
    {
      name: 'awap-scan-state',
      // Only persist IDs and flags, not transient data like logs
      partialize: (state) => ({
        activeTargetId: state.activeTargetId,
        activeScanId: state.activeScanId,
        isScanning: state.isScanning,
        scanComplete: state.scanComplete,
      }),
    }
  )
);
