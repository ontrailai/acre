import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ProcessLease from './pages/ProcessLease';
import LeaseDetails from './pages/LeaseDetails';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="process" element={<ProcessLease />} />
        <Route path="lease/:leaseId" element={<LeaseDetails />} />
      </Route>
    </Routes>
  );
}

export default App;
