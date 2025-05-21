import React, { useState } from 'react';
import axios from 'axios';

const ExportControls = ({ leaseId }) => {
  const [exporting, setExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState('pdf');
  const [exportError, setExportError] = useState(null);
  
  const handleExport = async () => {
    try {
      setExporting(true);
      setExportError(null);
      
      // Call the export API
      const response = await axios.get(`/api/export/${leaseId}?format=${exportFormat}`, {
        responseType: 'blob' // Important for file downloads
      });
      
      // Create download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `lease_summary_${leaseId}.${exportFormat}`);
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setExporting(false);
      
    } catch (err) {
      console.error('Error exporting lease summary:', err);
      setExportError('Error exporting lease summary. Please try again.');
      setExporting(false);
    }
  };
  
  // Get file icon based on format
  const getFileIcon = () => {
    switch (exportFormat) {
      case 'pdf':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
          </svg>
        );
      case 'docx':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
          </svg>
        );
      case 'xlsx':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" d="M5 4a1 1 0 00-1 1v10a1 1 0 001 1h10a1 1 0 001-1V5a1 1 0 00-1-1H5zm6 9a1 1 0 110-2 1 1 0 010 2zM5 7a1 1 0 000 2h10a1 1 0 100-2H5zM5 11a1 1 0 000 2h4a1 1 0 100-2H5z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
          </svg>
        );
    }
  };
  
  return (
    <div className="relative inline-block text-left">
      <div className="flex">
        <select
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value)}
          disabled={exporting}
          className="inline-flex items-center rounded-l-md border border-r-0 border-gray-300 bg-white px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:z-10 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="pdf">PDF</option>
          <option value="docx">Word</option>
          <option value="xlsx">Excel</option>
          <option value="markdown">Markdown</option>
        </select>
        
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting || !leaseId}
          className={`inline-flex items-center rounded-r-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium ${
            exporting 
              ? 'text-gray-400 cursor-not-allowed' 
              : 'text-gray-700 hover:bg-gray-50'
          }`}
        >
          {exporting ? (
            <>
              <div className="animate-spin h-4 w-4 mr-2 border-t-2 border-blue-500 rounded-full"></div>
              Exporting...
            </>
          ) : (
            <>
              {getFileIcon()}
              <span className="ml-1">Export</span>
            </>
          )}
        </button>
      </div>
      
      {exportError && (
        <div className="absolute mt-1 w-full rounded-md bg-red-50 p-2 text-xs text-red-600">
          {exportError}
        </div>
      )}
    </div>
  );
};

export default ExportControls;
