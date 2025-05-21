import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FeedbackPanel = ({ leaseId, summary, traceability }) => {
  const [feedbackField, setFeedbackField] = useState('');
  const [fieldId, setFieldId] = useState('');
  const [originalText, setOriginalText] = useState('');
  const [correctedText, setCorrectedText] = useState('');
  const [additionalNotes, setAdditionalNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [availableFields, setAvailableFields] = useState([]);
  
  // Set up available fields based on traceability info
  useEffect(() => {
    if (traceability) {
      const fields = Object.entries(traceability).map(([key, info]) => ({
        name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        id: info.field_id || key,
        excerpt: info.excerpt || '',
        page: info.page_number
      }));
      
      setAvailableFields(fields);
    }
  }, [traceability]);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!feedbackField || !originalText || !correctedText) {
      setError('Please fill in all required fields');
      return;
    }
    
    try {
      setSubmitting(true);
      setError(null);
      
      // Call the feedback API with structured field ID
      const response = await axios.post('/api/feedback', {
        lease_id: leaseId,
        field_id: fieldId || feedbackField.toLowerCase().replace(/ /g, '_'),
        clause_name: feedbackField,
        original: originalText,
        corrected: correctedText,
        additional_notes: additionalNotes
      });
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      
      // Reset form
      setFeedbackField('');
      setFieldId('');
      setOriginalText('');
      setCorrectedText('');
      setAdditionalNotes('');
      
      setSubmitting(false);
      
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError('Error submitting feedback. Please try again.');
      setSubmitting(false);
    }
  };
  
  // Handle selecting a field from dropdown
  const handleFieldSelect = (e) => {
    const fieldName = e.target.value;
    setFeedbackField(fieldName);
    
    // Find matching field in availableFields
    const field = availableFields.find(f => f.name === fieldName);
    if (field) {
      setFieldId(field.id);
      setOriginalText(field.excerpt);
    }
  };
  
  return (
    <div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="feedback-field" className="block text-sm font-medium text-gray-700 mb-1">
            Field Name*
          </label>
          {availableFields.length > 0 ? (
            <select
              id="feedback-field"
              value={feedbackField}
              onChange={handleFieldSelect}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              disabled={submitting}
            >
              <option value="">Select a field</option>
              {availableFields.map((field) => (
                <option key={field.id} value={field.name}>
                  {field.name} {field.page ? `(Page ${field.page})` : ''}
                </option>
              ))}
            </select>
          ) : (
            <input
              id="feedback-field"
              type="text"
              value={feedbackField}
              onChange={(e) => setFeedbackField(e.target.value)}
              placeholder="e.g., Rent Amount, Term, etc."
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              disabled={submitting}
            />
          )}
        </div>
        
        <div>
          <label htmlFor="original-text" className="block text-sm font-medium text-gray-700 mb-1">
            Original Text*
          </label>
          <textarea
            id="original-text"
            value={originalText}
            onChange={(e) => setOriginalText(e.target.value)}
            placeholder="Paste the text that needs correction"
            rows={3}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            disabled={submitting}
          />
        </div>
        
        <div>
          <label htmlFor="corrected-text" className="block text-sm font-medium text-gray-700 mb-1">
            Corrected Text*
          </label>
          <textarea
            id="corrected-text"
            value={correctedText}
            onChange={(e) => setCorrectedText(e.target.value)}
            placeholder="Enter the corrected version"
            rows={3}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            disabled={submitting}
          />
        </div>
        
        <div>
          <label htmlFor="additional-notes" className="block text-sm font-medium text-gray-700 mb-1">
            Additional Notes <span className="text-gray-400 text-xs">(Optional)</span>
          </label>
          <textarea
            id="additional-notes"
            value={additionalNotes}
            onChange={(e) => setAdditionalNotes(e.target.value)}
            placeholder="Any additional context or comments"
            rows={2}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            disabled={submitting}
          />
        </div>
        
        {error && (
          <div className="text-sm text-red-600">
            {error}
          </div>
        )}
        
        {success && (
          <div className="text-sm text-green-600">
            Feedback submitted successfully. Thank you!
          </div>
        )}
        
        <div>
          <button
            type="submit"
            disabled={submitting}
            className={`inline-flex items-center rounded-md border border-transparent ${
              submitting 
                ? 'bg-blue-300 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
            } px-4 py-2 text-sm font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
          >
            {submitting ? (
              <>
                <div className="animate-spin h-4 w-4 mr-2 border-t-2 border-white rounded-full"></div>
                Submitting...
              </>
            ) : 'Submit Feedback'}
          </button>
        </div>
      </form>
      
      <div className="mt-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Why Give Feedback?</h4>
        <p className="text-xs text-gray-600">
          Your feedback helps our AI system learn and improve. Each correction you provide is stored with its specific field ID and used to train the model, making it more accurate for future lease abstractions.
        </p>
      </div>
    </div>
  );
};

export default FeedbackPanel;
