import { useState, useEffect, useRef, useCallback } from 'react';
import { useScanStore } from '@/store/useScanStore';

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/scan`;

export function useScanMonitor(scanId: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const retryCount = useRef(0);
  const isMounted = useRef(true);

  // Use refs for store actions to avoid triggering useEffect re-runs
  const addLogRef = useRef(useScanStore.getState().addLog);
  const setPhaseRef = useRef(useScanStore.getState().setPhase);

  // Keep refs in sync with latest store actions
  useEffect(() => {
    const unsub = useScanStore.subscribe((state) => {
      addLogRef.current = state.addLog;
      setPhaseRef.current = state.setPhase;
    });
    return unsub;
  }, []);

  const cleanup = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (pingTimer.current) {
      clearInterval(pingTimer.current);
      pingTimer.current = null;
    }
    if (ws.current) {
      ws.current.onopen = null;
      ws.current.onmessage = null;
      ws.current.onclose = null;
      ws.current.onerror = null;
      if (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING) {
        ws.current.close();
      }
      ws.current = null;
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;

    if (!scanId) {
      cleanup();
      setIsConnected(false);
      return;
    }

    const connect = () => {
      if (!isMounted.current) return;

      // Clean up any existing connection before creating a new one
      cleanup();

      const url = `${WS_BASE}/${scanId}`;
      const socket = new WebSocket(url);
      ws.current = socket;

      socket.onopen = () => {
        if (!isMounted.current) return;
        retryCount.current = 0;
        setIsConnected(true);
        addLogRef.current(`[SYS] WebSocket established for scan session ${scanId}`);

        // Send periodic pings to keep connection alive
        pingTimer.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            try {
              socket.send('ping');
            } catch {
              // Socket may have closed between check and send
            }
          }
        }, 15000);
      };

      socket.onmessage = (event) => {
        if (!isMounted.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.message) {
            addLogRef.current(data.message);
          }
          if (data.state) {
            const phaseMap: Record<string, string> = {
              'SCOPE_VERIFIED': 'RECONNAISSANCE',
              'RECON': 'RECONNAISSANCE',
              'CRAWL': 'CRAWLING',
              'MAPPING': 'CRAWLING',
              'ATTACK': 'AI_PLANNING',
              'ANALYSIS': 'AI_PLANNING',
              'REPORTING': 'VULN_EXPLOITATION',
              'COMPLETE': 'VULN_EXPLOITATION',
              'FAILED': 'FAILED',
            };
            if (phaseMap[data.state]) {
              setPhaseRef.current(phaseMap[data.state]);
            }

            // Handle scan completion
            if (data.state === 'COMPLETE') {
              addLogRef.current('[SYS] ✓ Scan completed successfully. All phases finished.');
              useScanStore.getState().setScanComplete();
            } else if (data.state === 'FAILED') {
              addLogRef.current(`[SYS] ✗ Scan failed: ${data.message || 'Unknown error'}`);
            }
          }
        } catch {
          // If not JSON, treat as raw log string
          if (event.data && event.data !== 'pong') {
            addLogRef.current(event.data);
          }
        }
      };

      socket.onclose = () => {
        if (!isMounted.current) return;
        setIsConnected(false);
        if (pingTimer.current) {
          clearInterval(pingTimer.current);
          pingTimer.current = null;
        }

        // Auto-reconnect with exponential backoff (max 30s)
        const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
        retryCount.current += 1;
        reconnectTimer.current = setTimeout(() => {
          if (isMounted.current && scanId) {
            connect();
          }
        }, delay);
      };

      socket.onerror = () => {
        // onclose will fire after onerror, reconnect happens there
      };
    };

    connect();

    return () => {
      isMounted.current = false;
      cleanup();
      setIsConnected(false);
    };
  }, [scanId, cleanup]); // Only depends on scanId — NOT on store actions

  return { isConnected };
}
