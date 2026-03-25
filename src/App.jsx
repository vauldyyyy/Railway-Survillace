import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Cameras from './pages/Cameras';
import Incidents from './pages/Incidents';
import Analytics from './pages/Analytics';
import Tracking from './pages/Tracking';
import Settings from './pages/Settings';

/**
 * App — Root component with routing.
 * Architecture: Layout wraps all pages with Sidebar + TopBar.
 * Ready for API integration (swap mock data imports for fetch/axios calls).
 */
export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="cameras" element={<Cameras />} />
          <Route path="incidents" element={<Incidents />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="tracking" element={<Tracking />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}
