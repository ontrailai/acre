import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import {
  Upload,
  FileText,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  Building2,
  FileCheck,
  Sparkles,
  Clock,
  Shield
} from 'lucide-react';

const ProcessLease = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [leaseType, setLeaseType] = useState('retail');
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [error, setError] = useState(null);

  const processingStages = [
    { id: 'upload', label: 'Uploading document', icon: Upload },
    { id: 'ocr', label: 'Extracting text', icon: FileText },
    { id: 'segment', label: 'Analyzing structure', icon: FileCheck },
    { id: 'extract', label: 'AI clause extraction', icon: Sparkles },
    { id: 'validate', label: 'Validating & risk analysis', icon: Shield },
    { id: 'complete', label: 'Complete', icon: CheckCircle }
  ];

  const onDrop = useCallback((acceptedFiles) => {
    setError(null);
    const pdfFiles = acceptedFiles.filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length !== acceptedFiles.length) {
      setError('Only PDF files are supported');
    }
    
    setFiles(prev => [...prev, ...pdfFiles.map(file => ({
      file,
      id: Math.random().toString(36).substring(7),
      type: determineDocType(file.name)
    }))]);
  }, []);

  const determineDocType = (filename) => {
    const lower = filename.toLowerCase();
    if (lower.includes('amendment')) return 'amendment';
    if (lower.includes('exhibit')) return 'exhibit';
    if (lower.includes('addendum')) return 'addendum';
    return 'lease';
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: true
  });

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      setError('Please upload at least one PDF file');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      // Simulate processing stages
      for (let i = 0; i < processingStages.length - 1; i++) {
        setProcessingStage(processingStages[i].id);
        await new Promise(resolve => setTimeout(resolve, 1500));
      }

      const formData = new FormData();
      
      if (files.length === 1) {
        // Single document processing
        formData.append('lease_file', files[0].file);
        formData.append('lease_type', leaseType);
        formData.append('use_enhanced_extraction', 'true');

        const response = await axios.post('http://localhost:8000/api/process', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        setProcessingStage('complete');
        setTimeout(() => {
          navigate(`/lease/${response.data.lease_id}`);
        }, 500);
      } else {
        // Multi-document processing
        files.forEach(f => {
          formData.append('files', f.file);
        });
        formData.append('lease_type', leaseType);

        const response = await axios.post('http://localhost:8000/api/process-multi-document', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        setProcessingStage('complete');
        setTimeout(() => {
          navigate(`/lease/${response.data.doc_set_id}`);
        }, 500);
      }
    } catch (err) {
      console.error('Error processing:', err);
      // Enhanced error handling for validation errors
      const errorData = err.response?.data?.detail;
      
      if (typeof errorData === 'object' && errorData.error) {
        // This is a validation error with detailed information
        const { error, detected_type, warnings, suggestion, document_info } = errorData;
        
        let errorMessage = `${error}\n\n`;
        errorMessage += `Detected document type: ${detected_type?.replace('_', ' ')}\n\n`;
        
        if (warnings && warnings.length > 0) {
          errorMessage += 'Issues found:\n';
          warnings.forEach(warning => {
            errorMessage += `• ${warning}\n`;
          });
          errorMessage += '\n';
        }
        
        if (suggestion) {
          errorMessage += `Suggestion: ${suggestion}\n\n`;
        }
        
        if (document_info) {
          errorMessage += 'Document info:\n';
          if (document_info.word_count) errorMessage += `• Words: ${document_info.word_count}\n`;
          if (document_info.page_count) errorMessage += `• Pages: ${document_info.page_count}\n`;
          if (document_info.has_tables) errorMessage += `• Contains tables: Yes\n`;
          if (document_info.property_name) errorMessage += `• Property: ${document_info.property_name}\n`;
        }
        
        errorMessage += '\nPlease ensure you\'re uploading a lease agreement document.';
        
        setError(errorMessage);
      } else {
        // Standard error
        setError(err.response?.data?.detail || 'Error processing the document(s)');
      }
      
      setProcessing(false);
      setProcessingStage('');
    }
  };

  const getDocIcon = (type) => {
    const icons = {
      lease: <Building2 className="w-5 h-5" />,
      amendment: <FileText className="w-5 h-5" />,
      exhibit: <FileCheck className="w-5 h-5" />,
      addendum: <FileText className="w-5 h-5" />
    };
    return icons[type] || icons.lease;
  };

  const getDocColor = (type) => {
    const colors = {
      lease: 'bg-blue-100 text-blue-700',
      amendment: 'bg-purple-100 text-purple-700',
      exhibit: 'bg-green-100 text-green-700',
      addendum: 'bg-amber-100 text-amber-700'
    };
    return colors[type] || colors.lease;
  };

  if (processing) {
    const currentStageIndex = processingStages.findIndex(s => s.id === processingStage);

    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-md w-full">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Processing your lease</h2>
            <p className="text-gray-600">This typically takes 30-60 seconds</p>
          </div>

          <div className="space-y-4">
            {processingStages.map((stage, index) => {
              const Icon = stage.icon;
              const isActive = stage.id === processingStage;
              const isCompleted = index < currentStageIndex;

              return (
                <div
                  key={stage.id}
                  className={`flex items-center gap-4 p-4 rounded-xl transition-all ${
                    isActive ? 'bg-blue-50 border border-blue-200' : 
                    isCompleted ? 'bg-green-50 border border-green-200' : 
                    'bg-gray-50 border border-gray-200'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isActive ? 'bg-blue-600' :
                    isCompleted ? 'bg-green-600' :
                    'bg-gray-300'
                  }`}>
                    {isActive ? (
                      <Loader2 className="w-5 h-5 text-white animate-spin" />
                    ) : isCompleted ? (
                      <CheckCircle className="w-5 h-5 text-white" />
                    ) : (
                      <Icon className="w-5 h-5 text-white" />
                    )}
                  </div>
                  <span className={`font-medium ${
                    isActive ? 'text-blue-900' :
                    isCompleted ? 'text-green-900' :
                    'text-gray-500'
                  }`}>
                    {stage.label}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-8 flex items-center justify-center gap-2 text-sm text-gray-500">
            <Clock className="w-4 h-4" />
            <span>Estimated time remaining: {Math.max(0, (5 - currentStageIndex) * 10)}s</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Process New Lease</h1>
        <p className="mt-2 text-gray-600">
          Upload lease documents for AI-powered analysis and risk assessment
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Lease Type Selection */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Lease Type</h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              { value: 'retail', label: 'Retail', icon: '🏪' },
              { value: 'office', label: 'Office', icon: '🏢' },
              { value: 'industrial', label: 'Industrial', icon: '🏭' }
            ].map((type) => (
              <label
                key={type.value}
                className={`relative flex items-center justify-center gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  leaseType === type.value
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="leaseType"
                  value={type.value}
                  checked={leaseType === type.value}
                  onChange={(e) => setLeaseType(e.target.value)}
                  className="sr-only"
                />
                <span className="text-2xl">{type.icon}</span>
                <span className={`font-medium ${
                  leaseType === type.value ? 'text-blue-900' : 'text-gray-700'
                }`}>
                  {type.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* File Upload */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Documents</h2>
          
          <div
            {...getRootProps()}
            className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              isDragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400 bg-gray-50'
            }`}
          >
            <input {...getInputProps()} />
            
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <Upload className="w-8 h-8 text-blue-600" />
              </div>
              
              <p className="text-base font-medium text-gray-900 mb-1">
                {isDragActive ? 'Drop your files here' : 'Drag & drop your lease documents'}
              </p>
              <p className="text-sm text-gray-500 mb-4">
                or <span className="text-blue-600 font-medium">browse files</span>
              </p>
              <p className="text-xs text-gray-400">
                Supports PDF files including leases, amendments, and exhibits
              </p>
            </div>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-4 space-y-2">
              {files.map((fileItem) => (
                <div
                  key={fileItem.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${getDocColor(fileItem.type)}`}>
                      {getDocIcon(fileItem.type)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {fileItem.file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(fileItem.file.size / 1024 / 1024).toFixed(2)} MB • {fileItem.type}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(fileItem.id)}
                    className="p-1 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm text-red-800 whitespace-pre-wrap">{error}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={files.length === 0 || processing}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Sparkles className="w-5 h-5" />
            Process with AI
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProcessLease;
