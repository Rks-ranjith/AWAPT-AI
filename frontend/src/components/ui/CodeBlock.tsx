import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language?: string;
  copyable?: boolean;
  className?: string;
  maxHeight?: string;
  highlightLine?: number;
}

export function CodeBlock({ 
  code, 
  language = 'json', 
  copyable = true, 
  className,
  maxHeight = '400px',
  highlightLine
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("relative group border border-[#111827] rounded bg-[#0D1117] font-mono", className)}>
      <div className="absolute top-0 left-0 right-0 h-8 bg-[#111827] flex items-center justify-between px-3 border-b border-[#252D45]">
        <span className="text-[#4A5568] text-xs uppercase">{language}</span>
        {copyable && (
          <button 
            onClick={handleCopy}
            className="text-[#4A5568] hover:text-[#00D4FF] focus:outline-none transition-colors"
            title="Copy code"
            type="button"
          >
            {copied ? <Check className="w-4 h-4 text-[#00FF88]" /> : <Copy className="w-4 h-4" />}
          </button>
        )}
      </div>
      <div className="overflow-auto mt-8 p-1 scrollbar-thin scrollbar-thumb-[#252D45]" style={{ maxHeight }}>
        <SyntaxHighlighter
          language={language}
          style={tomorrow as any}
          customStyle={{
            background: 'transparent',
            margin: 0,
            padding: '1rem',
            fontSize: '13px',
            lineHeight: '1.5',
          }}
          wrapLines={true}
          lineProps={(lineNumber) => {
            const style: any = { display: 'block' };
            if (lineNumber === highlightLine) {
              style.backgroundColor = 'rgba(255, 45, 85, 0.1)';
              style.borderLeft = '2px solid #FF2D55';
            }
            return { style };
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
