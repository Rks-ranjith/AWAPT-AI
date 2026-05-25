import { useState, useEffect, useRef } from 'react';
import { useScanStore } from '@/store/useScanStore';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/scan`;

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
          if (data.state) {
            const phaseMap: Record<string, string> = {
              'RECON': 'RECONNAISSANCE',
              'CRAWL': 'CRAWLING',
              'MAPPING': 'CRAWLING',
              'ATTACK': 'AI_PLANNING',
              'ANALYSIS': 'AI_PLANNING',
              'REPORTING': 'VULN_EXPLOITATION',
              'COMPLETE': 'VULN_EXPLOITATION'
            };
            if (phaseMap[data.state]) setPhase(phaseMap[data.state]);
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
