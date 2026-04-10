import { useState, useEffect, useRef } from 'react';
import { useScanStore } from '@/store/useScanStore';

const WS_URL = 'ws://localhost:8000/ws/monitor';

export function useScanMonitor(scanId: number | null) {
  const { addLog, setPhase } = useScanStore();
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!scanId) return;

    const connect = () => {
      const socket = new WebSocket(`${WS_URL}/${scanId}`);
      ws.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        addLog(`[SYS] WebSocket established for scan session ${scanId}`);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.message) {
            addLog(data.message);
          }
          if (data.phase) {
            const phaseMap: Record<string, number> = {
              'RECON': 1,
              'CRAWL': 2,
              'PARAM_FUZZ': 2,
              'AI_REASONING': 3,
              'ATTACK': 3,
              'ANALYSIS': 4,
              'COMPLETED': 4
            };
            if (phaseMap[data.phase]) setPhase(phaseMap[data.phase]);
          }
        } catch (e) {
          // If it's not JSON, it might be a raw log string
          addLog(event.data);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        // Retry logic could go here for "industry grade"
      };

      socket.onerror = (err) => {
        console.error("WS Error:", err);
      };
    };

    connect();

    return () => {
      ws.current?.close();
    };
  }, [scanId, addLog, setPhase]);

  return { isConnected };
}
