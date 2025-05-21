import React, { useState } from 'react';
import axios from 'axios';

export default function Home() {
  const [leaseType, setLeaseType] = useState('retail');
  const [summaryStyle, setSummaryStyle] = useState('executive');
  const [processing, setProcessing] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      setFile(null);
      setError('Please select a PDF file');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile);
      setError(null);
    } else {
      setFile(null);
      setError('Please drop a PDF file');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('lease_file', file);
      formData.append('lease_type', leaseType);
      formData.append('summary_style', summaryStyle);

      const response = await axios.post('http://localhost:8000/api/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setResult(response.data);
    } catch (err) {
      console.error('Error processing file:', err);
      
      // Check if it's a structured error from the backend
      const errorDetail = err.response?.data?.detail;
      
      if (typeof errorDetail === 'object' && errorDetail.error) {
        // This is a structured error with details
        setError(
          <div className="p-4 bg-red-50 text-red-800 rounded-md">
            <h3 className="font-bold mb-2">{errorDetail.error}</h3>
            {errorDetail.possible_causes && (
              <>
                <p className="mb-2">Possible causes:</p>
                <ul className="list-disc pl-5 mb-2">{errorDetail.possible_causes.map((cause, i) => 
                  <li key={i}>{cause}</li>
                )}</ul>
              </>
            )}
            {errorDetail.debug_location && (
              <p className="text-sm text-gray-600">Debug info available at: {errorDetail.debug_location}</p>
            )}
          </div>
        );
      } else {
        // Generic error
        setError(err.response?.data?.detail || 'Error processing the file. Please try again.');
      }
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Lease Abstraction</h1>
        <p className="text-gray-600">
          Upload a commercial lease PDF to generate an AI-powered abstract in seconds.
        </p>
      </div>

      {!result ? (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Upload Lease</h2>
          
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Lease Type
              </label>
              <select
                value={leaseType}
                onChange={(e) => setLeaseType(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                disabled={processing}
              >
                <option value="retail">Retail</option>
                <option value="office">Office</option>
                <option value="industrial">Industrial</option>
              </select>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Summary Style
              </label>
              <select
                value={summaryStyle}
                onChange={(e) => setSummaryStyle(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                disabled={processing}
              >
                <option value="executive">Executive Brief</option>
                <option value="legal">Legal Detail</option>
              </select>
            </div>
            
            <div 
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-upload').click()}
            >
              {processing ? (
                <div>
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
                  <p>Processing your lease...</p>
                </div>
              ) : (
                <div>
                  <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="mt-2 text-sm text-gray-600">
                    {file ? file.name : 'Drag and drop your lease PDF here, or click to select'}
                  </p>
                </div>
              )}
              <input
                id="file-upload"
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleFileChange}
                disabled={processing}
              />
            </div>
            
            {error && (
              <div className="mt-2 text-sm text-red-600">
                {error}
              </div>
            )}
            
            <div className="mt-4">
              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                disabled={!file || processing}
              >
                {processing ? 'Processing...' : 'Process Lease'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Results</h2>
          <div className="mb-4">
            <button
              onClick={() => setResult(null)}
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-2 px-4 rounded"
            >
              Upload Another Lease
            </button>
          </div>
          
          {/* Check if there was an issue with extraction */}
          {(!result.raw_clauses || Object.keys(result.raw_clauses).length === 0) && (
            <div className="mb-6 p-4 bg-yellow-50 text-yellow-800 rounded-md">
              <h3 className="font-bold mb-2">Notice: Template Lease Detected</h3>
              <p>The system detected that this appears to be a lease template with placeholders rather than a completed lease.</p>
              <p className="mt-2">For best results:</p>
              <ul className="list-disc pl-5 mt-1">
                <li>Use a completed lease document with actual values rather than a template</li>
                <li>Ensure the document is a standard commercial lease format</li>
                <li>Check that the PDF is properly formatted and readable</li>
              </ul>
              <p className="mt-2 italic">A generalized summary has been provided below, but specific clause extraction was limited.</p>
            </div>
          )}
          
          {/* Show missing clauses alert */}
          {result.missing_clauses && result.missing_clauses.length > 0 && (
            <div className="mb-6 p-4 bg-orange-50 text-orange-800 rounded-md">
              <h3 className="font-bold mb-2">Missing Important Clauses</h3>
              <p>The following important lease clauses were not found:</p>
              <ul className="list-disc pl-5 mt-1">
                {result.missing_clauses.map((clause, index) => (
                  <li key={index}>{clause}</li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="prose max-w-none mb-6">
            <h3 className="text-lg font-semibold">Extraction Summary</h3>
            <ul className="bg-gray-50 p-4 rounded-md">
              <li>Clauses extracted: {result.raw_clauses ? Object.keys(result.raw_clauses).length : 0}</li>
              <li>Processing time: {result.processing_time.toFixed(2)} seconds</li>
              <li>Risk flags: {result.risk_flags ? result.risk_flags.length : 0}</li>
            </ul>
          </div>
          
          <div className="prose max-w-none">
            <h3 className="text-lg font-semibold mb-3">Lease Summary</h3>
            {result.summary_markdown ? (
              <div className="bg-gray-100 p-4 rounded-md overflow-auto">
                <pre className="whitespace-pre-wrap">{
                  result.summary_markdown
                }</pre>
              </div>
            ) : (
              <p className="text-gray-500 italic">No summary available</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
