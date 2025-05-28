import React, { useState } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronRight,
  FileWarning,
  TrendingUp,
  Shield,
  DollarSign,
  Building2,
  Users,
  FileText,
  X
} from 'lucide-react';

const RiskPanel = ({ riskFlags, missingClauses }) => {
  const [selectedRisk, setSelectedRisk] = useState(null);
  const [filterLevel, setFilterLevel] = useState('all');

  const getRiskIcon = (category) => {
    const icons = {
      'Co-Tenancy': Users,
      'Assignment': FileText,
      'Maintenance': Building2,
      'Financial': DollarSign,
      'Legal': Shield,
      'Operational': TrendingUp
    };
    return icons[category] || AlertCircle;
  };

  const getRiskColor = (level) => {
    const colors = {
      high: 'text-red-600 bg-red-50 border-red-200',
      medium: 'text-amber-600 bg-amber-50 border-amber-200',
      low: 'text-blue-600 bg-blue-50 border-blue-200'
    };
    return colors[level] || colors.low;
  };

  const getRiskBadgeColor = (level) => {
    const colors = {
      high: 'bg-red-100 text-red-700 border-red-200',
      medium: 'bg-amber-100 text-amber-700 border-amber-200',
      low: 'bg-blue-100 text-blue-700 border-blue-200'
    };
    return colors[level] || colors.low;
  };

  const filteredRisks = filterLevel === 'all' 
    ? riskFlags 
    : riskFlags.filter(risk => risk.level === filterLevel);

  const riskCounts = {
    high: riskFlags.filter(r => r.level === 'high').length,
    medium: riskFlags.filter(r => r.level === 'medium').length,
    low: riskFlags.filter(r => r.level === 'low').length
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Risk List */}
      <div className="lg:col-span-2 space-y-6">
        {/* Filter Tabs */}
        <div className="bg-white rounded-2xl border border-gray-200 p-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilterLevel('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterLevel === 'all' 
                  ? 'bg-gray-900 text-white' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              All Risks ({riskFlags.length})
            </button>
            <button
              onClick={() => setFilterLevel('high')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                filterLevel === 'high' 
                  ? 'bg-red-600 text-white' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <span className="w-2 h-2 bg-red-500 rounded-full"></span>
              High ({riskCounts.high})
            </button>
            <button
              onClick={() => setFilterLevel('medium')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                filterLevel === 'medium' 
                  ? 'bg-amber-600 text-white' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
              Medium ({riskCounts.medium})
            </button>
            <button
              onClick={() => setFilterLevel('low')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                filterLevel === 'low' 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
              Low ({riskCounts.low})
            </button>
          </div>
        </div>

        {/* Risk Cards */}
        <div className="space-y-4">
          {filteredRisks.map((risk, index) => {
            const Icon = getRiskIcon(risk.category);
            return (
              <div
                key={index}
                className={`bg-white rounded-xl border-2 p-6 cursor-pointer transition-all hover:shadow-lg ${
                  selectedRisk === index ? 'ring-2 ring-blue-500' : ''
                } ${getRiskColor(risk.level)}`}
                onClick={() => setSelectedRisk(index)}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    risk.level === 'high' ? 'bg-red-100' :
                    risk.level === 'medium' ? 'bg-amber-100' :
                    'bg-blue-100'
                  }`}>
                    <Icon className={`w-6 h-6 ${
                      risk.level === 'high' ? 'text-red-600' :
                      risk.level === 'medium' ? 'text-amber-600' :
                      'text-blue-600'
                    }`} />
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {risk.title}
                      </h3>
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${getRiskBadgeColor(risk.level)}`}>
                        {risk.level.toUpperCase()} RISK
                      </span>
                    </div>
                    
                    <p className="text-gray-700 mb-3">{risk.description}</p>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">
                        Location: <span className="font-medium text-gray-900">{risk.location}</span>
                      </span>
                      <span className="text-gray-600">
                        Impact: <span className="font-medium text-gray-900">{risk.impact}</span>
                      </span>
                    </div>
                  </div>
                  
                  <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 mt-1" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        {/* Risk Summary */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Risk Summary</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Total Risk Score</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-green-500 via-amber-500 to-red-500 rounded-full"
                    style={{ width: '65%' }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900">65/100</span>
              </div>
            </div>
            
            <div className="pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                  <span className="text-sm text-gray-600">High Risk</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{riskCounts.high} issues</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-amber-500 rounded-full"></span>
                  <span className="text-sm text-gray-600">Medium Risk</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{riskCounts.medium} issues</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                  <span className="text-sm text-gray-600">Low Risk</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{riskCounts.low} issues</span>
              </div>
            </div>
          </div>
        </div>

        {/* Missing Clauses */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileWarning className="w-5 h-5 text-amber-600" />
            Missing Clauses
          </h3>
          
          <div className="space-y-3">
            {missingClauses.map((clause, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg"
              >
                <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <span className="text-sm text-amber-900">{clause}</span>
              </div>
            ))}
          </div>
          
          <p className="text-xs text-gray-500 mt-4">
            These clauses are commonly found in {riskFlags[0]?.leaseType || 'commercial'} leases but were not detected in this document.
          </p>
        </div>

        {/* Risk Mitigation Tips */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl p-6 border border-blue-200">
          <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Risk Mitigation Tips
          </h3>
          
          <ul className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Review co-tenancy provisions with legal counsel</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Consider negotiating assignment consent requirements</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Clarify maintenance responsibilities in writing</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Risk Detail Modal */}
      {selectedRisk !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    {riskFlags[selectedRisk].title}
                  </h2>
                  <p className="text-gray-600 mt-1">
                    {riskFlags[selectedRisk].category} • {riskFlags[selectedRisk].location}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedRisk(null)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
            </div>
            
            <div className="p-6">
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Risk Level
                  </h3>
                  <span className={`inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium border ${
                    getRiskBadgeColor(riskFlags[selectedRisk].level)
                  }`}>
                    {riskFlags[selectedRisk].level.toUpperCase()} RISK
                  </span>
                </div>
                
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Description
                  </h3>
                  <p className="text-gray-700">
                    {riskFlags[selectedRisk].description}
                  </p>
                </div>
                
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Potential Impact
                  </h3>
                  <p className="text-gray-700">
                    {riskFlags[selectedRisk].impact}
                  </p>
                </div>
                
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Recommended Actions
                  </h3>
                  <ul className="space-y-2">
                    <li className="flex items-start gap-2">
                      <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700">Review this provision with legal counsel</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700">Consider negotiating more favorable terms</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700">Document any verbal agreements in writing</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskPanel;
