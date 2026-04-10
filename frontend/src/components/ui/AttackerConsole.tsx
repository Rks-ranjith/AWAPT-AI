import { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { Loader2, Terminal as TerminalIcon, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import '@xterm/xterm/css/xterm.css';

interface AttackerConsoleProps {
  findingId: number;
  isOpen: boolean;
  onClose: () => void;
}

export function AttackerConsole({ findingId, isOpen, onClose }: AttackerConsoleProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!isOpen || !terminalRef.current) return;

    // Initialize Xterm
    const term = new Terminal({
      theme: {
        background: '#0f172a', // slate-900
        foreground: '#10b981', // emerald-500
        cursor: '#10b981',
      },
      fontFamily: '"Fira Code", "Cascadia Code", Consolas, monospace',
      fontSize: 14,
      cursorBlink: true,
      disableStdin: false,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();
    xtermRef.current = term;

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/console/${findingId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
      term.write('\r\n\x1b[31m[!] Connection Error.\x1b[0m\r\n');
    };

    ws.onclose = () => {
      setIsConnected(false);
      term.write('\r\n\x1b[33m[*] Connection Closed.\x1b[0m\r\n');
    };

    // Handle user input
    let currentInput = '';
    term.onData((data) => {
      // Basic input handling
      if (data === '\r') {
        // Enter pressed
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(currentInput);
        }
        currentInput = '';
      } else if (data === '\u007F' || data === '\b') {
        // Backspace
        if (currentInput.length > 0) {
          currentInput = currentInput.slice(0, -1);
          term.write('\b \b');
        }
      } else {
        currentInput += data;
        term.write(data);
      }
    });

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => fitAddon.fit());
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
      resizeObserver.disconnect();
      ws.close();
      term.dispose();
    };
  }, [isOpen, findingId]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        >
          <div className="w-full max-w-5xl bg-slate-900 border border-slate-700/50 rounded-xl shadow-2xl overflow-hidden flex flex-col">
            {/* Terminal Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-800/80 border-b border-slate-700/50">
              <div className="flex items-center space-x-3">
                <TerminalIcon className="w-5 h-5 text-emerald-500" />
                <h3 className="text-white font-medium flex items-center gap-2">
                  Interactive Attacker Console 
                  <span className="text-slate-400 text-xs">| Finding ID: {findingId}</span>
                </h3>
                {isConnected ? (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                ) : (
                  <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
                )}
              </div>
              
              <button 
                onClick={onClose}
                className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded-md transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Terminal Body */}
            <div 
              ref={terminalRef} 
              className="h-[60vh] p-4 bg-[#0f172a]" 
              style={{ overflow: 'hidden' }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
