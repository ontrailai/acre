import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network/standalone';

const ClauseGraphViewer = ({ clauses, insights }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !clauses) return;

    // Create nodes from clauses
    const nodes = [
      { id: 'lease', label: 'Master Lease', color: '#3b82f6', shape: 'box', font: { color: 'white' } },
      { id: 'base_rent', label: 'Base Rent\n$15,000/mo', color: '#10b981', shape: 'box', font: { color: 'white' } },
      { id: 'percentage_rent', label: 'Percentage Rent\n6% over $3M', color: '#10b981', shape: 'box', font: { color: 'white' } },
      { id: 'co_tenancy', label: 'Co-Tenancy\n50% reduction', color: '#ef4444', shape: 'box', font: { color: 'white' } },
      { id: 'cam', label: 'CAM Charges\n$2,500/mo', color: '#6366f1', shape: 'box', font: { color: 'white' } },
      { id: 'insurance', label: 'Insurance\n$500/mo', color: '#6366f1', shape: 'box', font: { color: 'white' } },
      { id: 'assignment', label: 'Assignment Rights\nLiberal', color: '#f59e0b', shape: 'box', font: { color: 'white' } },
      { id: 'renewal', label: 'Renewal Options\n2 x 5 years', color: '#8b5cf6', shape: 'box', font: { color: 'white' } },
      { id: 'maintenance', label: 'Maintenance\nSplit responsibility', color: '#06b6d4', shape: 'box', font: { color: 'white' } },
      { id: 'exclusive_use', label: 'Exclusive Use\nCoffee shop', color: '#8b5cf6', shape: 'box', font: { color: 'white' } }
    ];

    // Create edges showing relationships
    const edges = [
      { from: 'lease', to: 'base_rent', label: 'contains' },
      { from: 'lease', to: 'percentage_rent', label: 'contains' },
      { from: 'lease', to: 'co_tenancy', label: 'contains' },
      { from: 'lease', to: 'cam', label: 'contains' },
      { from: 'lease', to: 'insurance', label: 'contains' },
      { from: 'lease', to: 'assignment', label: 'contains' },
      { from: 'lease', to: 'renewal', label: 'contains' },
      { from: 'lease', to: 'maintenance', label: 'contains' },
      { from: 'lease', to: 'exclusive_use', label: 'contains' },
      { from: 'co_tenancy', to: 'base_rent', label: 'affects', color: '#ef4444', dashes: true },
      { from: 'percentage_rent', to: 'base_rent', label: 'supplements', color: '#10b981' },
      { from: 'exclusive_use', to: 'percentage_rent', label: 'protects', color: '#8b5cf6', dashes: true }
    ];

    // Network options
    const options = {
      nodes: {
        borderWidth: 0,
        shadow: true,
        font: {
          size: 14,
          face: 'Inter, system-ui, sans-serif'
        }
      },
      edges: {
        smooth: {
          type: 'cubicBezier',
          forceDirection: 'horizontal',
          roundness: 0.4
        },
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 0.5
          }
        },
        font: {
          size: 12,
          align: 'middle',
          background: 'white'
        }
      },
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 200,
          levelSeparation: 150
        }
      },
      physics: {
        enabled: false
      },
      interaction: {
        hover: true,
        tooltipDelay: 200
      }
    };

    // Create network
    const network = new Network(containerRef.current, { nodes, edges }, options);

    // Add hover effects
    network.on('hoverNode', (params) => {
      containerRef.current.style.cursor = 'pointer';
    });

    network.on('blurNode', () => {
      containerRef.current.style.cursor = 'default';
    });

    // Clean up
    return () => {
      network.destroy();
    };
  }, [clauses]);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Clause Relationship Graph</h2>
        <p className="text-sm text-gray-600">
          Visual representation of how different lease clauses interact and affect each other
        </p>
      </div>

      <div className="relative">
        <div 
          ref={containerRef} 
          className="w-full h-[600px] border border-gray-200 rounded-xl bg-gray-50"
        />
        
        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 text-sm">
          <h3 className="font-medium text-gray-900 mb-2">Legend</h3>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span className="text-gray-600">Master Document</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-gray-600">Financial Terms</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span className="text-gray-600">Risk Factors</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-purple-500 rounded"></div>
              <span className="text-gray-600">Rights & Options</span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-4 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-gray-500">Clauses</p>
              <p className="text-xl font-bold text-gray-900">10</p>
            </div>
            <div>
              <p className="text-gray-500">Relationships</p>
              <p className="text-xl font-bold text-gray-900">12</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClauseGraphViewer;
