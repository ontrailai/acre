import React from 'react';
import ReactMarkdown from 'react-markdown';

const SummaryRenderer = ({ summary }) => {
  // Custom components for markdown rendering
  const components = {
    h1: ({ children }) => (
      <h1 className="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b border-gray-200">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4 flex items-center gap-2">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-lg font-semibold text-gray-800 mt-6 mb-3">
        {children}
      </h3>
    ),
    p: ({ children }) => (
      <p className="text-gray-700 leading-relaxed mb-4">
        {children}
      </p>
    ),
    ul: ({ children }) => (
      <ul className="space-y-2 mb-4">
        {children}
      </ul>
    ),
    li: ({ children }) => (
      <li className="flex items-start">
        <span className="text-blue-600 mr-2 mt-1">•</span>
        <span className="text-gray-700">{children}</span>
      </li>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-gray-900">{children}</strong>
    ),
    blockquote: ({ children }) => (
      <blockquote className="pl-4 border-l-4 border-blue-500 italic text-gray-600 my-4">
        {children}
      </blockquote>
    ),
  };

  return (
    <div className="prose prose-lg max-w-none">
      <ReactMarkdown components={components}>
        {summary}
      </ReactMarkdown>
    </div>
  );
};

export default SummaryRenderer;
