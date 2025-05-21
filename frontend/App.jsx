import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './pages/index';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-blue-600">Lease Logik 2</h1>
            <span className="ml-3 bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">Beta</span>
          </div>
          <nav className="flex space-x-4">
            <a href="/" className="text-gray-700 hover:text-blue-600">Home</a>
            <a href="/about" className="text-gray-700 hover:text-blue-600">About</a>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Home />} />
          {/* Additional routes can be added here */}
        </Routes>
      </main>

      <footer className="bg-white border-t mt-8">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} Lease Logik 2. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
