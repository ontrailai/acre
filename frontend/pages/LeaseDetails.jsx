import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  ArrowLeft,
  Download,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Share2,
  Printer,
  ChevronDown,
  ChevronRight,
  Building2,
  Calendar,
  DollarSign,
  Users,
  Shield,
  FileWarning,
  BarChart3,
  Network,
  Eye,
  Clock,
  AlertCircle,
  TrendingUp,
  Briefcase,
  MapPin,
  Hash,
  FileSearch
} from 'lucide-react';
import SummaryRenderer from '../components/SummaryRenderer';
import RiskPanel from '../components/RiskPanel';
import ClauseGraphViewer from '../components/ClauseGraphViewer';
import DownloadButton from '../components/DownloadButton';

const LeaseDetails = () => {
  const { leaseId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('summary');
  const [leaseData, setLeaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({});

  useEffect(() => {
    fetchLeaseData();
  }, [leaseId]);

  const fetchLeaseData = async () => {
    try {
      setLoading(true);
      
      // Fetch the actual lease data from the backend
      const response = await axios.get(`http://localhost:8000/api/lease/${leaseId}`);
      
      // Transform the backend response to match the expected format
      const data = response.data;
      
      // Parse the raw clauses to extract key information
      const parsedClauses = data.raw_clauses || {};
      
      // Better extraction logic that handles the actual data structure
      const extractedData = extractAllData(parsedClauses);
      
      // Build the lease data structure
      const transformedData = {
        leaseId: data.lease_id,
        propertyName: extractedData.propertyAddress || 'Property Details',
        leaseType: data.lease_type || 'Unknown',
        tenant: extractedData.tenant || 'Tenant Information',
        landlord: extractedData.landlord || 'Landlord Information',
        processedAt: new Date().toISOString(),
        processingTime: data.processing_time || 0,
        
        overview: {
          commencementDate: extractedData.commencementDate || 'Not Specified',
          expirationDate: extractedData.expirationDate || 'Not Specified',
          term: extractedData.termLength || 'Not Specified',
          rentableSquareFeet: extractedData.squareFeet || 'Not Specified',
          useType: extractedData.permittedUse || 'Not Specified',
          guarantor: extractedData.guarantor || 'None Specified'
        },
        
        financial: {
          baseRent: extractedData.baseRent || 'Not Specified',
          annualRent: extractedData.annualRent || calculateAnnualRentFromMonthly(extractedData.baseRent),
          rentPSF: calculateRentPSF(extractedData.baseRent, extractedData.squareFeet),
          escalations: extractedData.escalations || 'Not Specified',
          percentageRent: extractedData.percentageRent || 'None',
          cam: extractedData.cam || 'Not Specified',
          insurance: extractedData.insurance || 'Not Specified',
          taxes: extractedData.taxes || 'Not Specified',
          securityDeposit: extractedData.securityDeposit || 'Not Specified'
        },
        
        keyDates: extractKeyDates(extractedData),
        
        riskFlags: data.risk_flags || [],
        
        missingClauses: data.missing_clauses || [],
        
        enhancedResults: data.enhanced_results || {
          validationScore: 0,
          tablesFound: 0,
          clauseRelationships: [],
          insights: {
            leaseStructure: {
              leaseType: 'Unknown',
              hasPercentageRent: false,
              hasCoTenancy: false,
              hasExclusiveUse: false
            },
            financialSummary: {
              totalEstimatedRent: 'Not Calculated',
              effectiveRentPSF: 'Not Calculated'
            },
            complexityScore: 0
          }
        },
        
        summary: data.summary_markdown || '# No Summary Available',
        
        // Store raw data for debugging
        rawResponse: data,
        extractedData: extractedData
      };
      
      setLeaseData(transformedData);
      
    } catch (error) {
      console.error('Error fetching lease data:', error);
      // Show error state
      setLeaseData(null);
    } finally {
      setLoading(false);
    }
  };

  // Enhanced extraction logic that handles various data formats
  const extractAllData = (clauses) => {
    const extracted = {};
    
    // Process each clause
    for (const [key, clause] of Object.entries(clauses)) {
      // Handle different data structures
      let data = {};
      
      // First try structured_data
      if (clause.structured_data && typeof clause.structured_data === 'object') {
        data = { ...clause.structured_data };
      }
      
      // Then try parsing content if it's JSON
      if (clause.content) {
        try {
          const parsedContent = JSON.parse(clause.content);
          data = { ...data, ...parsedContent };
        } catch (e) {
          // Not JSON, try to extract values from text
          const contentData = extractFromText(clause.content);
          data = { ...data, ...contentData };
        }
      }
      
      // Map data to our expected fields based on clause type
      if (key.includes('parties')) {
        extracted.landlord = data.landlord_name || data.landlord || extracted.landlord;
        extracted.tenant = data.tenant_name || data.tenant || extracted.tenant;
      }
      
      if (key.includes('premises')) {
        extracted.propertyAddress = data.address || extracted.propertyAddress;
        extracted.squareFeet = data.square_feet || data.square_footage || extracted.squareFeet;
        extracted.suite = data.suite || extracted.suite;
      }
      
      if (key.includes('term')) {
        extracted.commencementDate = data.commencement_date || extracted.commencementDate;
        extracted.expirationDate = data.expiration_date || extracted.expirationDate;
        extracted.termLength = data.term_length || data.term || extracted.termLength;
      }
      
      if (key.includes('rent')) {
        extracted.baseRent = data.base_rent || data.monthly_rent || extracted.baseRent;
        extracted.annualRent = data.annual_rent || extracted.annualRent;
        extracted.escalations = data.escalation || data.escalation_rate || extracted.escalations;
      }
      
      if (key.includes('use')) {
        extracted.permittedUse = data.permitted_use || extracted.permittedUse;
      }
      
      if (key.includes('security')) {
        extracted.securityDeposit = data.amount || data.security_deposit || extracted.securityDeposit;
      }
      
      if (key.includes('insurance')) {
        extracted.insurance = data.general_liability || data.coverage || extracted.insurance;
      }
      
      if (key.includes('document_overview')) {
        // Handle document overview data
        extracted.documentType = data.document_type || extracted.documentType;
        extracted.pageCount = data.page_count || extracted.pageCount;
        extracted.datesFound = data.dates_found || extracted.datesFound;
        extracted.amountsFound = data.amounts_found || extracted.amountsFound;
      }
    }
    
    return extracted;
  };

  // Extract values from plain text
  const extractFromText = (text) => {
    const data = {};
    
    // Try to extract common patterns
    const patterns = {
      landlord: /landlord[:\s]+([^\n,]+)/i,
      tenant: /tenant[:\s]+([^\n,]+)/i,
      address: /(?:address|premises)[:\s]+([^\n]+)/i,
      rent: /(?:rent|monthly)[:\s]+(\$[\d,]+(?:\.\d{2})?)/i,
      squareFeet: /([\d,]+)\s*(?:square feet|sq\.?\s*ft\.?)/i,
      commencement: /commencement[:\s]+([^\n]+)/i,
      term: /term[:\s]+([^\n]+)/i
    };
    
    for (const [field, pattern] of Object.entries(patterns)) {
      const match = text.match(pattern);
      if (match) {
        data[field] = match[1].trim();
      }
    }
    
    return data;
  };

  const calculateAnnualRentFromMonthly = (monthlyRent) => {
    if (!monthlyRent || monthlyRent === 'Not Specified') return 'Not Calculated';
    
    const match = monthlyRent.match(/\$([\d,]+(?:\.\d{2})?)/);
    if (match) {
      const monthly = parseFloat(match[1].replace(/,/g, ''));
      const annual = monthly * 12;
      return `$${annual.toLocaleString()}/year`;
    }
    
    return 'Not Calculated';
  };

  const calculateRentPSF = (rent, sqft) => {
    if (!rent || !sqft || rent === 'Not Specified' || sqft === 'Not Specified') {
      return 'Not Calculated';
    }
    
    const rentMatch = rent.match(/\$([\d,]+(?:\.\d{2})?)/);
    const sqftNum = parseFloat(sqft.replace(/,/g, ''));
    
    if (rentMatch && sqftNum > 0) {
      const monthly = parseFloat(rentMatch[1].replace(/,/g, ''));
      const annual = monthly * 12;
      const psf = annual / sqftNum;
      return `$${psf.toFixed(2)}`;
    }
    
    return 'Not Calculated';
  };

  const extractKeyDates = (extractedData) => {
    const dates = [];
    
    if (extractedData.commencementDate && extractedData.commencementDate !== 'Not Specified') {
      dates.push({
        date: extractedData.commencementDate,
        event: 'Lease Commencement',
        type: 'primary'
      });
    }
    
    if (extractedData.expirationDate && extractedData.expirationDate !== 'Not Specified') {
      dates.push({
        date: extractedData.expirationDate,
        event: 'Lease Expiration',
        type: 'primary'
      });
    }
    
    // Add any dates found in document overview
    if (extractedData.datesFound && Array.isArray(extractedData.datesFound)) {
      extractedData.datesFound.forEach((date, index) => {
        if (!dates.some(d => d.date === date)) {
          dates.push({
            date: date,
            event: `Date found in document`,
            type: 'secondary'
          });
        }
      });
    }
    
    return dates;
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading lease details...</p>
        </div>
      </div>
    );
  }

  if (!leaseData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Load Lease</h2>
          <p className="text-gray-600 mb-4">There was an error loading the lease details.</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Determine if this is a partial extraction
  const isPartialExtraction = leaseData.extractedData?.documentType || 
                            leaseData.summary.includes('extraction found limited') ||
                            Object.values(leaseData.overview).filter(v => v === 'Not Specified').length > 3;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-20 z-20">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(-1)}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </button>
              
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {leaseData.propertyName === 'Property Details' && isPartialExtraction ? 
                    'Lease Document Analysis' : leaseData.propertyName}
                </h1>
                <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                  {!isPartialExtraction ? (
                    <>
                      <span className="flex items-center gap-1">
                        <Building2 className="w-4 h-4" />
                        {leaseData.tenant}
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        {leaseData.landlord}
                      </span>
                    </>
                  ) : (
                    <span className="flex items-center gap-1">
                      <FileSearch className="w-4 h-4" />
                      {leaseData.extractedData?.documentType || 'Lease'} Document
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    Processed in {leaseData.processingTime.toFixed(1)}s
                  </span>
                  {isPartialExtraction ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-700 rounded-lg">
                      <AlertCircle className="w-4 h-4" />
                      Partial Extraction
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded-lg">
                      <CheckCircle className="w-4 h-4" />
                      Validated
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button className="p-2.5 rounded-lg hover:bg-gray-100 transition-colors">
                <Share2 className="w-5 h-5 text-gray-600" />
              </button>
              <button className="p-2.5 rounded-lg hover:bg-gray-100 transition-colors">
                <Printer className="w-5 h-5 text-gray-600" />
              </button>
              <DownloadButton leaseData={leaseData} />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6">
          <div className="flex gap-8 border-b border-gray-200">
            {[
              { id: 'summary', label: 'Summary', icon: FileText },
              { id: 'extracted', label: 'Extracted Data', icon: FileSearch },
              { id: 'risks', label: 'Risk Analysis', icon: AlertTriangle, badge: leaseData.riskFlags.length },
              { id: 'insights', label: 'Insights', icon: BarChart3 }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative pb-3 px-1 text-sm font-medium transition-colors flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                  {tab.badge && tab.badge > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 bg-red-100 text-red-600 text-xs font-medium rounded-full">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === 'summary' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Summary */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                {isPartialExtraction && (
                  <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-amber-900">Limited Information Extracted</p>
                        <p className="text-sm text-amber-700 mt-1">
                          The automated extraction found limited structured data in this document. 
                          Please review the summary below for available information.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                <SummaryRenderer summary={leaseData.summary} />
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Key Information */}
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Information</h3>
                <div className="space-y-4">
                  {leaseData.overview.commencementDate !== 'Not Specified' && (
                    <div>
                      <p className="text-sm text-gray-600">Commencement Date</p>
                      <p className="text-base font-semibold text-gray-900">{leaseData.overview.commencementDate}</p>
                    </div>
                  )}
                  
                  {leaseData.overview.term !== 'Not Specified' && (
                    <div>
                      <p className="text-sm text-gray-600">Lease Term</p>
                      <p className="text-base font-semibold text-gray-900">{leaseData.overview.term}</p>
                    </div>
                  )}
                  
                  {leaseData.financial.baseRent !== 'Not Specified' && (
                    <div>
                      <p className="text-sm text-gray-600">Base Rent</p>
                      <p className="text-base font-semibold text-gray-900">{leaseData.financial.baseRent}</p>
                    </div>
                  )}
                  
                  {leaseData.overview.rentableSquareFeet !== 'Not Specified' && (
                    <div>
                      <p className="text-sm text-gray-600">Square Footage</p>
                      <p className="text-base font-semibold text-gray-900">{leaseData.overview.rentableSquareFeet}</p>
                    </div>
                  )}
                  
                  {isPartialExtraction && leaseData.extractedData?.pageCount && (
                    <div>
                      <p className="text-sm text-gray-600">Document Pages</p>
                      <p className="text-base font-semibold text-gray-900">{leaseData.extractedData.pageCount}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Dates or Amounts Found */}
              {isPartialExtraction && (leaseData.extractedData?.datesFound?.length > 0 || leaseData.extractedData?.amountsFound?.length > 0) && (
                <div className="bg-white rounded-2xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Values Found</h3>
                  
                  {leaseData.extractedData?.datesFound?.length > 0 && (
                    <div className="mb-4">
                      <p className="text-sm font-medium text-gray-700 mb-2">Dates:</p>
                      <div className="space-y-1">
                        {leaseData.extractedData.datesFound.map((date, idx) => (
                          <p key={idx} className="text-sm text-gray-600">{date}</p>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {leaseData.extractedData?.amountsFound?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">Amounts:</p>
                      <div className="space-y-1">
                        {leaseData.extractedData.amountsFound.map((amount, idx) => (
                          <p key={idx} className="text-sm text-gray-600">${amount}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Missing Clauses */}
              {leaseData.missingClauses.length > 0 && (
                <div className="bg-white rounded-2xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Missing Clauses</h3>
                  <div className="space-y-2">
                    {leaseData.missingClauses.map((clause, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm text-gray-600">
                        <XCircle className="w-4 h-4 text-gray-400" />
                        <span>{clause}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'extracted' && (
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Extracted Data Details</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Parties */}
              {(leaseData.tenant !== 'Tenant Information' || leaseData.landlord !== 'Landlord Information') && (
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900 flex items-center gap-2">
                    <Users className="w-4 h-4 text-gray-600" />
                    Parties
                  </h4>
                  <div className="pl-6 space-y-2">
                    {leaseData.tenant !== 'Tenant Information' && (
                      <p className="text-sm"><span className="text-gray-600">Tenant:</span> <span className="font-medium">{leaseData.tenant}</span></p>
                    )}
                    {leaseData.landlord !== 'Landlord Information' && (
                      <p className="text-sm"><span className="text-gray-600">Landlord:</span> <span className="font-medium">{leaseData.landlord}</span></p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Property */}
              {(leaseData.propertyName !== 'Property Details' || leaseData.overview.rentableSquareFeet !== 'Not Specified') && (
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900 flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-gray-600" />
                    Property
                  </h4>
                  <div className="pl-6 space-y-2">
                    {leaseData.propertyName !== 'Property Details' && (
                      <p className="text-sm"><span className="text-gray-600">Address:</span> <span className="font-medium">{leaseData.propertyName}</span></p>
                    )}
                    {leaseData.overview.rentableSquareFeet !== 'Not Specified' && (
                      <p className="text-sm"><span className="text-gray-600">Size:</span> <span className="font-medium">{leaseData.overview.rentableSquareFeet} sq ft</span></p>
                    )}
                    {leaseData.extractedData?.suite && (
                      <p className="text-sm"><span className="text-gray-600">Suite:</span> <span className="font-medium">{leaseData.extractedData.suite}</span></p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Financial */}
              {Object.values(leaseData.financial).some(v => v !== 'Not Specified' && v !== 'Not Calculated') && (
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900 flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-gray-600" />
                    Financial Terms
                  </h4>
                  <div className="pl-6 space-y-2">
                    {leaseData.financial.baseRent !== 'Not Specified' && (
                      <p className="text-sm"><span className="text-gray-600">Base Rent:</span> <span className="font-medium">{leaseData.financial.baseRent}</span></p>
                    )}
                    {leaseData.financial.annualRent !== 'Not Calculated' && (
                      <p className="text-sm"><span className="text-gray-600">Annual:</span> <span className="font-medium">{leaseData.financial.annualRent}</span></p>
                    )}
                    {leaseData.financial.securityDeposit !== 'Not Specified' && (
                      <p className="text-sm"><span className="text-gray-600">Security Deposit:</span> <span className="font-medium">{leaseData.financial.securityDeposit}</span></p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Term */}
              {Object.values(leaseData.overview).some(v => v !== 'Not Specified') && (
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-600" />
                    Term & Dates
                  </h4>
                  <div className="pl-6 space-y-2">
                    {leaseData.overview.commencementDate !== 'Not Specified' && (
                      <p className="text-sm"><span className="text-gray-600">Commencement:</span> <span className="font-medium">{leaseData.overview.commencementDate}</span></p>
                    )}
                    {leaseData.overview.expirationDate !== 'Not Specified' && (
                      <p className="text-sm"><span className="text-gray-600">Expiration:</span> <span className="font-medium">{leaseData.overview.expirationDate}</span></p>
                    )}
                    {leaseData.overview.term !== 'Not Specified' && (
                      <p className="text-sm"><span className="text-gray-600">Term:</span> <span className="font-medium">{leaseData.overview.term}</span></p>
                    )}
                  </div>
                </div>
              )}
            </div>
            
            {/* Raw Clauses Debug Info */}
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-8">
                <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900">
                  Debug: View Raw Extracted Clauses
                </summary>
                <pre className="mt-4 p-4 bg-gray-50 rounded-lg text-xs overflow-auto">
                  {JSON.stringify(leaseData.rawResponse.raw_clauses, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {activeTab === 'risks' && (
          <RiskPanel 
            riskFlags={leaseData.riskFlags}
            missingClauses={leaseData.missingClauses}
          />
        )}

        {activeTab === 'insights' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Extraction Summary */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileSearch className="w-5 h-5 text-gray-600" />
                Extraction Summary
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-gray-100">
                  <span className="text-sm text-gray-600">Document Type</span>
                  <span className="text-sm font-medium text-gray-900">
                    {leaseData.leaseType} Lease
                  </span>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-gray-100">
                  <span className="text-sm text-gray-600">Clauses Found</span>
                  <span className="text-sm font-medium text-gray-900">
                    {Object.keys(leaseData.rawResponse.raw_clauses || {}).length}
                  </span>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-gray-100">
                  <span className="text-sm text-gray-600">Missing Clauses</span>
                  <span className="text-sm font-medium text-gray-900">
                    {leaseData.missingClauses.length}
                  </span>
                </div>
                <div className="flex items-center justify-between py-3">
                  <span className="text-sm text-gray-600">Processing Time</span>
                  <span className="text-sm font-medium text-gray-900">
                    {leaseData.processingTime.toFixed(1)} seconds
                  </span>
                </div>
              </div>
            </div>

            {/* AI Confidence */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-gray-600" />
                Extraction Status
              </h3>
              <div className="space-y-4">
                {isPartialExtraction ? (
                  <>
                    <div className="p-4 bg-amber-50 rounded-xl text-center">
                      <AlertCircle className="w-12 h-12 text-amber-600 mx-auto mb-2" />
                      <p className="text-sm font-medium text-amber-900">Partial Extraction</p>
                      <p className="text-xs text-amber-700 mt-1">Limited data could be automatically extracted</p>
                    </div>
                    <div className="space-y-2 text-sm">
                      <p className="text-gray-600">Possible reasons:</p>
                      <ul className="list-disc list-inside text-gray-500 space-y-1">
                        <li>Document may be a scanned image</li>
                        <li>Non-standard lease format</li>
                        <li>Template or draft document</li>
                      </ul>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-4">
                    <div className="relative w-24 h-24 mx-auto">
                      <svg className="w-24 h-24 transform -rotate-90">
                        <circle
                          cx="48"
                          cy="48"
                          r="40"
                          stroke="#e5e7eb"
                          strokeWidth="8"
                          fill="none"
                        />
                        <circle
                          cx="48"
                          cy="48"
                          r="40"
                          stroke="#3b82f6"
                          strokeWidth="8"
                          fill="none"
                          strokeDasharray={`${2 * Math.PI * 40 * (leaseData.enhancedResults?.validationScore || 50) / 100} ${2 * Math.PI * 40}`}
                          className="transition-all duration-1000"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-2xl font-bold text-gray-900">
                          {leaseData.enhancedResults?.validationScore || 50}%
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mt-2">Validation Score</p>
                  </div>
                )}
              </div>
            </div>

            {/* Key Findings */}
            {!isPartialExtraction && (
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-gray-600" />
                  Key Findings
                </h3>
                <div className="space-y-3">
                  {leaseData.financial.rentPSF !== 'Not Calculated' && (
                    <div className="p-3 bg-blue-50 rounded-lg">
                      <p className="text-xs text-blue-600 mb-1">Rent PSF</p>
                      <p className="text-lg font-semibold text-blue-900">{leaseData.financial.rentPSF}</p>
                    </div>
                  )}
                  {leaseData.financial.annualRent !== 'Not Calculated' && (
                    <div className="p-3 bg-green-50 rounded-lg">
                      <p className="text-xs text-green-600 mb-1">Annual Rent</p>
                      <p className="text-lg font-semibold text-green-900">{leaseData.financial.annualRent}</p>
                    </div>
                  )}
                  {leaseData.riskFlags.length > 0 && (
                    <div className="p-3 bg-red-50 rounded-lg">
                      <p className="text-xs text-red-600 mb-1">Risk Flags</p>
                      <p className="text-lg font-semibold text-red-900">{leaseData.riskFlags.length} identified</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Processing Stats */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-gray-600" />
                Processing Details
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Enhanced Extraction</span>
                  <span className="text-sm font-medium text-gray-900">
                    {leaseData.enhancedResults ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Tables Found</span>
                  <span className="text-sm font-medium text-gray-900">
                    {leaseData.enhancedResults?.tablesFound || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Document Pages</span>
                  <span className="text-sm font-medium text-gray-900">
                    {leaseData.extractedData?.pageCount || 'Unknown'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Processing ID</span>
                  <span className="text-sm font-mono text-gray-500">
                    {leaseData.leaseId.slice(0, 8)}...
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LeaseDetails;