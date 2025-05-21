import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const PDFDropzone = ({ leaseType, summaryStyle, processing, setProcessing, onProcessComplete }) => {
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [fileDetails, setFileDetails] = useState(null);
  const [processingStage, setProcessingStage] = useState('idle');
  
  // Stages of processing for more detailed UI feedback
  const processingStages = [
    { id: 'idle', label: 'Ready' },
    { id: 'uploading', label: 'Uploading file' },
    { id: 'ocr', label: 'Running OCR (if needed)' },
    { id: 'segmenting', label: 'Segmenting lease sections' },
    { id: 'extracting', label: 'Extracting clauses with GPT' },
    { id: 'analyzing', label: 'Analyzing risks' },
    { id: 'summarizing', label: 'Generating summary' },
    { id: 'complete', label: 'Processing complete' }
  ];
  
  // Auto-advance stages for demo purposes (in real-world would be based on backend progress events)
  useEffect(() => {
    if (!processing) {
      setProcessingStage('idle');
      return;
    }
    
    // Simulate processing stages based on progress
    if (progress < 20) {
      setProcessingStage('uploading');
    } else if (progress < 30) {
      setProcessingStage('ocr');
    } else if (progress < 40) {
      setProcessingStage('segmenting');
    } else if (progress < 70) {
      setProcessingStage('extracting');
    } else if (progress < 85) {
      setProcessingStage('analyzing');
    } else if (progress < 95) {
      setProcessingStage('summarizing');
    } else {
      setProcessingStage('complete');
    }
  }, [processing, progress]);

  const onDrop = useCallback(acceptedFiles => {
    // Reset states
    setError(null);
    setProgress(0);
    
    // Check if we have a PDF
    const file = acceptedFiles[0];
    if (!file) return;
    
    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file');
      return;
    }
    
    // Store file details
    setFileDetails({
      name: file.name,
      size: (file.size / 1024 / 1024).toFixed(2) // Size in MB
    });
    
    // Process the file immediately - no separate "extract" button
    processFile(file);
  }, [leaseType, summaryStyle, onProcessComplete]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    disabled: processing
  });
  
  const processFile = async (file) => {
    try {
      setProcessing(true);
      setProcessingStage('uploading');
      
      // Create form data
      const formData = new FormData();
      formData.append('lease_file', file);
      formData.append('lease_type', leaseType);
      formData.append('summary_style', summaryStyle);
      
      // Call the API with a single endpoint that does everything
      const response = await axios.post('/api/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(percentCompleted > 20 ? 20 : percentCompleted); // Cap at 20% for upload phase
        }
      });
      
      // Simulate processing stages with progress updates
      const simulateProgress = () => {
        setProgress(prev => {
          if (prev >= 95) {
            clearInterval(timer);
            
            // Complete the process
            setTimeout(() => {
              setProgress(100);
              setProcessingStage('complete');
              
              // Set result
              onProcessComplete(response.data);
            }, 500);
            
            return 95;
          }
          return prev + 1;
        });
      };
      
      // Start progress simulation after upload
      const timer = setInterval(simulateProgress, 100);
      
    } catch (err) {
      console.error('Error processing file:', err);
      setError(err.response?.data?.detail || 'Error processing the file. Please try again.');
      setProcessing(false);
    }
  };
  
  return (
    <div className="space-y-4">
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'dropzone-active' : ''} ${processing ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        
        {processing ? (
          <div className="text-center">
            <div className="spinner mx-auto mb-4"></div>
            <p className="text-gray-500 font-medium">{processingStages.find(s => s.id === processingStage)?.label || 'Processing...'}</p>
            <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
              <div 
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-xs text-gray-400 mt-2">This usually takes 30-60 seconds</p>
          </div>
        ) : (
          <div className="text-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="mt-1 text-sm text-gray-600">
              Drag and drop your lease PDF here, or click to select
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Once you drop a file, processing will start automatically
            </p>
          </div>
        )}
      </div>
      
      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm">
          {error}
        </div>
      )}
      
      {fileDetails && !processing && !error && (
        <div className="bg-green-50 text-green-700 p-3 rounded-md text-sm flex justify-between items-center">
          <div>
            <p className="font-semibold">{fileDetails.name}</p>
            <p>{fileDetails.size} MB</p>
          </div>
          <button 
            onClick={() => setFileDetails(null)}
            className="text-green-700 hover:text-green-900"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      )}
      
      {/* Processing stages indicator */}
      {processing && (
        <div className="mt-4">
          <div className="flex items-center space-x-2 overflow-x-auto py-2">
            {processingStages.filter(stage => stage.id !== 'idle').map((stage, index) => (
              <div 
                key={stage.id}
                className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium ${
                  processingStage === stage.id 
                    ? 'bg-blue-100 text-blue-800 border border-blue-300' 
                    : processingStages.findIndex(s => s.id === processingStage) > index 
                      ? 'bg-green-100 text-green-800 border border-green-300'
                      : 'bg-gray-100 text-gray-500 border border-gray-200'
                }`}
              >
                {stage.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PDFDropzone;
