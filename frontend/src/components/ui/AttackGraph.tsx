import { useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
// @ts-ignore
import cola from 'cytoscape-cola';


cytoscape.use(cola);

export interface GraphNode {
  id: string;
  label: string;
  type: 'domain' | 'endpoint' | 'vulnerability';
  severity?: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface GraphEdge {
  source: string;
  target: string;
  type: 'crawl' | 'exploitation';
}

interface AttackGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function AttackGraph({ nodes, edges }: AttackGraphProps) {
  const [cy, setCy] = useState<cytoscape.Core | null>(null);

  const elements = [
    ...nodes.map(n => ({
      data: { 
        id: n.id, 
        label: n.label, 
        type: n.type,
        severity: n.severity
      }
    })),
    ...edges.map((e, i) => ({
      data: { 
        id: `e${i}`, 
        source: e.source, 
        target: e.target,
        type: e.type
      }
    }))
  ];

  const layout = {
    name: 'cola',
    animate: true,
    refresh: 1,
    maxSimulationTime: 1500,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 100,
  };

  const style: any[] = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'color': '#fff',
        'font-family': 'Space Mono',
        'font-size': 10,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 5,
        'background-color': '#0D1117',
        'border-width': 2,
        'border-color': '#4A5568',
      }
    },
    {
      selector: 'node[type="domain"]',
      style: {
        'shape': 'hexagon',
        'width': 40,
        'height': 40,
        'border-color': '#00D4FF',
        'background-color': 'rgba(0, 212, 255, 0.1)',
      }
    },
    {
      selector: 'node[type="endpoint"]',
      style: {
        'shape': 'ellipse',
        'width': 20,
        'height': 20,
        'border-color': '#4A5568',
      }
    },
    {
      selector: 'node[type="vulnerability"]',
      style: {
        'shape': 'diamond',
        'width': 30,
        'height': 30,
        'border-color': '#FFB800',
        'background-color': 'rgba(255, 184, 0, 0.2)',
      }
    },
    {
      selector: 'node[severity="CRITICAL"]',
      style: {
        'border-color': '#FF2D55',
        'background-color': 'rgba(255, 45, 85, 0.3)',
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 1,
        'line-color': '#4A5568',
        'target-arrow-color': '#4A5568',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.6
      }
    },
    {
      selector: 'edge[type="exploitation"]',
      style: {
        'line-color': '#FF2D55',
        'target-arrow-color': '#FF2D55',
        'line-style': 'dashed',
        'width': 2,
        'opacity': 0.8
      }
    }
  ];

  return (
    <div className="w-full h-full relative font-mono bg-[#080B14]">
      <CytoscapeComponent 
        elements={elements} 
        style={{ width: '100%', height: '100%' }}
        stylesheet={style}
        layout={layout}
        cy={(cyInstance) => {
          setCy(cyInstance);
        }}
      />
      <div className="absolute top-2 right-2 flex gap-2">
        <button 
          onClick={() => cy?.layout(layout).run()}
          className="px-2 py-1 text-[10px] uppercase border border-[#00D4FF]/30 text-[#00D4FF] hover:bg-[#00D4FF]/10 transition-colors"
        >
          Reset View
        </button>
      </div>
    </div>
  );
}
