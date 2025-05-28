import React from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  TrendingUp, 
  Clock, 
  AlertCircle,
  ArrowRight,
  Building2,
  Calendar,
  DollarSign
} from 'lucide-react';

const Dashboard = () => {
  // Mock data for recent leases
  const recentLeases = [
    {
      id: '1',
      name: '123 Main Street - Retail Space',
      type: 'Retail',
      tenant: 'Starbucks Corporation',
      processedAt: '2024-01-15T10:30:00',
      riskLevel: 'low',
      rentAmount: '$15,000/mo',
      term: '10 years',
      sqft: '2,500 sq ft'
    },
    {
      id: '2', 
      name: 'One Financial Plaza - Suite 2100',
      type: 'Office',
      tenant: 'Tech Innovations Inc.',
      processedAt: '2024-01-14T14:20:00',
      riskLevel: 'medium',
      rentAmount: '$45,000/mo',
      term: '5 years',
      sqft: '8,200 sq ft'
    },
    {
      id: '3',
      name: 'Industrial Park Building A',
      type: 'Industrial',
      tenant: 'Global Logistics Co.',
      processedAt: '2024-01-13T09:15:00',
      riskLevel: 'high',
      rentAmount: '$32,000/mo',
      term: '7 years',
      sqft: '45,000 sq ft'
    }
  ];

  const stats = [
    { label: 'Leases Processed', value: '284', change: '+12%', icon: FileText },
    { label: 'Total Portfolio Value', value: '$45.2M', change: '+8%', icon: DollarSign },
    { label: 'Avg Processing Time', value: '32s', change: '-15%', icon: Clock },
    { label: 'Risk Flags Identified', value: '47', change: '+5%', icon: AlertCircle },
  ];

  const getRiskBadge = (level) => {
    const styles = {
      low: 'bg-green-100 text-green-700',
      medium: 'bg-amber-100 text-amber-700',
      high: 'bg-red-100 text-red-700'
    };
    return styles[level] || styles.low;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now - date) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    if (diffInHours < 48) return 'Yesterday';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">Welcome back! Here's an overview of your lease portfolio.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white rounded-2xl p-6 border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
                  <Icon className="w-6 h-6 text-blue-600" />
                </div>
                <span className={`text-sm font-medium ${
                  stat.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {stat.change}
                </span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900">{stat.value}</h3>
              <p className="text-sm text-gray-600 mt-1">{stat.label}</p>
            </div>
          );
        })}
      </div>

      {/* Recent Leases */}
      <div className="bg-white rounded-2xl border border-gray-200">
        <div className="px-6 py-5 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">Recent Leases</h2>
            <Link
              to="/process"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Process New Lease
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {recentLeases.map((lease) => (
            <Link
              key={lease.id}
              to={`/lease/${lease.id}`}
              className="block px-6 py-5 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-6 h-6 text-gray-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-semibold text-gray-900 truncate">
                        {lease.name}
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">{lease.tenant}</p>
                      
                      <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <DollarSign className="w-4 h-4" />
                          {lease.rentAmount}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {lease.term}
                        </span>
                        <span>{lease.sqft}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 ml-4">
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${getRiskBadge(lease.riskLevel)}`}>
                    {lease.riskLevel === 'low' ? 'Low Risk' : lease.riskLevel === 'medium' ? 'Medium Risk' : 'High Risk'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatDate(lease.processedAt)}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>

        <div className="px-6 py-4 border-t border-gray-200">
          <Link
            to="/leases"
            className="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            View all leases
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
