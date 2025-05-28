import React, { useState } from 'react';
import {
  Download,
  FileText,
  FileSpreadsheet,
  FileType,
  ChevronDown,
  Check
} from 'lucide-react';

const DownloadButton = ({ leaseData }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [downloading, setDownloading] = useState(null);

  const downloadFormats = [
    { id: 'pdf', label: 'PDF Document', icon: FileText, color: 'text-red-600' },
    { id: 'docx', label: 'Word Document', icon: FileType, color: 'text-blue-600' },
    { id: 'xlsx', label: 'Excel Spreadsheet', icon: FileSpreadsheet, color: 'text-green-600' },
    { id: 'csv', label: 'CSV Data', icon: FileText, color: 'text-gray-600' }
  ];

  const handleDownload = async (format) => {
    setDownloading(format);
    
    // Simulate download process
    setTimeout(() => {
      // In production, this would call the actual download API
      console.log(`Downloading lease ${leaseData.leaseId} in ${format} format`);
      
      // Create mock download
      const content = format === 'csv' 
        ? 'Property,Tenant,Rent,Term\n123 Main Street,Starbucks,$15000,10 years'
        : JSON.stringify(leaseData, null, 2);
      
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `lease_${leaseData.leaseId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setDownloading(null);
      setIsOpen(false);
    }, 1500);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors"
      >
        <Download className="w-4 h-4" />
        Export
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden z-20">
            <div className="p-2">
              {downloadFormats.map((format) => {
                const Icon = format.icon;
                const isDownloading = downloading === format.id;
                
                return (
                  <button
                    key={format.id}
                    onClick={() => handleDownload(format.id)}
                    disabled={downloading !== null}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    <div className={`w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center ${format.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{format.label}</p>
                      <p className="text-xs text-gray-500">
                        {format.id === 'pdf' ? 'Full summary with formatting' :
                         format.id === 'docx' ? 'Editable document' :
                         format.id === 'xlsx' ? 'Structured data & tables' :
                         'Raw data export'}
                      </p>
                    </div>
                    {isDownloading && (
                      <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    )}
                  </button>
                );
              })}
            </div>
            
            <div className="px-5 py-3 bg-gray-50 border-t border-gray-200">
              <p className="text-xs text-gray-600">
                All exports include extracted clauses, risk analysis, and traceability data
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DownloadButton;
