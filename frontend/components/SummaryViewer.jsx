import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SummaryViewer = ({ summary, traceability }) => {
  const [showTraceability, setShowTraceability] = useState(false);
  const [activeSection, setActiveSection] = useState(null);
  const [hoveredExcerpt, setHoveredExcerpt] = useState(null);
  
  // Create section references for scrolling
  const sectionRefs = React.useRef({});
  
  // Function to highlight traceability when hovering over a section
  const handleSectionHover = (sectionKey) => {
    setActiveSection(sectionKey);
    
    if (!showTraceability) return;
    
    // Find corresponding element
    const element = document.getElementById(`trace-${sectionKey}`);
    if (element) {
      element.classList.add('bg-yellow-100');
      
      // Scroll the traceability section into view
      element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };
  
  const handleSectionLeave = (sectionKey) => {
    setActiveSection(null);
    
    if (!showTraceability) return;
    
    // Find corresponding element
    const element = document.getElementById(`trace-${sectionKey}`);
    if (element) {
      element.classList.remove('bg-yellow-100');
    }
  };
  
  // Handle excerpt hover in traceability panel
  const handleExcerptHover = (key, excerpt) => {
    setHoveredExcerpt({ key, excerpt });
  };
  
  const handleExcerptLeave = () => {
    setHoveredExcerpt(null);
  };
  
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Lease Summary</h2>
        <div>
          <button
            onClick={() => setShowTraceability(!showTraceability)}
            className={`inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md ${
              showTraceability 
                ? 'bg-blue-50 text-blue-700 border-blue-300' 
                : 'text-gray-700 bg-white hover:bg-gray-50'
            }`}
          >
            {showTraceability ? 'Hide Traceability' : 'Show Traceability'}
          </button>
        </div>
      </div>
      
      {/* Highlight tooltip that follows cursor when hovering excerpts */}
      {hoveredExcerpt && (
        <div 
          className="fixed bg-white border border-gray-300 shadow-lg rounded p-3 max-w-md z-50"
          style={{ 
            top: window.event ? window.event.clientY + 20 : 100,
            left: window.event ? window.event.clientX + 20 : 100,
          }}
        >
          <div className="text-sm font-semibold mb-1">{hoveredExcerpt.key.replace(/_/g, ' ')}</div>
          <div className="text-xs italic">{hoveredExcerpt.excerpt}</div>
        </div>
      )}
      
      <div className={`grid ${showTraceability ? 'grid-cols-4 gap-6' : 'grid-cols-1'}`}>
        {/* Main summary column */}
        <div className={showTraceability ? 'col-span-3' : 'col-span-1'}>
          <div className="prose max-w-none">
            {/* For ReactMarkdown, we need to modify the content to add data attributes for hover */}
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                // Add hover effects to headings for traceability
                h2: ({node, ...props}) => {
                  return <h2 {...props} className="text-lg font-bold border-b border-gray-200 pb-1 mb-4" />;
                },
                h3: ({node, ...props}) => {
                  const headingText = node.children[0]?.value || '';
                  const sectionKey = headingText
                    .toLowerCase()
                    .replace(/[^\w\s]/g, '')
                    .replace(/\s+/g, '_');
                  
                  // Register section ref for scrolling
                  return (
                    <h3 
                      {...props}
                      ref={el => sectionRefs.current[sectionKey] = el}
                      id={`section-${sectionKey}`}
                      onMouseEnter={() => handleSectionHover(sectionKey)}
                      onMouseLeave={() => handleSectionLeave(sectionKey)}
                      className={`cursor-pointer mt-4 text-md font-semibold ${
                        showTraceability ? 'hover:bg-blue-50 transition-colors duration-150' : ''
                      } ${activeSection === sectionKey ? 'bg-blue-50' : ''}`}
                    />
                  );
                },
                // Style risk indicators
                p: ({node, children, ...props}) => {
                  const content = node.children[0]?.value || '';
                  
                  if (content.includes('🔴')) {
                    return <p {...props} className="text-red-700 bg-red-50 p-2 rounded">{children}</p>;
                  }
                  if (content.includes('🟠')) {
                    return <p {...props} className="text-orange-700 bg-orange-50 p-2 rounded">{children}</p>;
                  }
                  if (content.includes('🟡')) {
                    return <p {...props} className="text-yellow-700 bg-yellow-50 p-2 rounded">{children}</p>;
                  }
                  if (content.includes('⚠️')) {
                    return <p {...props} className="text-gray-700 bg-gray-100 p-2 rounded italic">{children}</p>;
                  }
                  
                  return <p {...props}>{children}</p>;
                }
              }}
            >
              {summary}
            </ReactMarkdown>
          </div>
        </div>
        
        {/* Traceability column */}
        {showTraceability && (
          <div className="col-span-1">
            <div className="sticky top-4 bg-gray-50 p-4 rounded-md shadow-sm border border-gray-200 max-h-[80vh] overflow-y-auto">
              <h3 className="text-lg font-semibold mb-3">Source References</h3>
              <p className="text-sm text-gray-600 mb-4">
                Hover over sections to see source information
              </p>
              
              <div className="space-y-4">
                {Object.entries(traceability).map(([key, info]) => {
                  // Convert key to the same format used in section IDs
                  const sectionKey = key
                    .toLowerCase()
                    .replace(/[^\w\s]/g, '')
                    .replace(/\s+/g, '_');
                    
                  return (
                    <div 
                      key={key}
                      id={`trace-${sectionKey}`}
                      className={`p-3 rounded-md bg-white border border-gray-200 shadow-sm transition-colors duration-200 ${
                        activeSection === sectionKey ? 'bg-yellow-100 border-yellow-300' : ''
                      }`}
                      onMouseEnter={() => handleExcerptHover(key, info.excerpt)}
                      onMouseLeave={handleExcerptLeave}
                      onClick={() => {
                        // Scroll to the corresponding section when clicking on traceability
                        const sectionEl = document.getElementById(`section-${sectionKey}`);
                        if (sectionEl) {
                          sectionEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                          
                          // Add a flash effect
                          sectionEl.classList.add('bg-yellow-200');
                          setTimeout(() => {
                            sectionEl.classList.remove('bg-yellow-200');
                          }, 1000);
                        }
                      }}
                    >
                      <h4 className="font-medium text-gray-900 mb-1">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h4>
                      {info.page_number && (
                        <p className="text-sm text-gray-500 mt-1">
                          {info.page_range ? 
                            `Pages ${info.page_range}` : 
                            `Page ${info.page_number}`}
                        </p>
                      )}
                      <p className="text-xs mt-2 text-gray-600 italic line-clamp-3">{info.excerpt}</p>
                      
                      {/* Field ID for reference, helpful for feedback */}
                      {info.field_id && (
                        <p className="text-xs text-gray-400 mt-2 truncate">
                          ID: {info.field_id}
                        </p>
                      )}
                    </div>
                  );
                })}
                
                {Object.keys(traceability).length === 0 && (
                  <p className="text-gray-500 italic">No traceability information available.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SummaryViewer;
