import { Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from './layout/DashboardLayout';
import { Dashboard } from './pages/Dashboard';
import { Targets } from './pages/Targets';
import { Findings } from './pages/Findings';
import { LiveMonitor } from './pages/LiveMonitor';
import { AttackGraph } from './pages/AttackGraph';
import { Settings } from './pages/Settings';

// Placeholder Pages
import { Analytics } from './pages/Analytics';
import { Reports } from './pages/Reports';
const Team = () => <div className="p-10 text-center"><h1 className="text-4xl font-bold opacity-20 uppercase tracking-widest italic">TEAM_MANAGEMENT_STUB</h1></div>;

function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardLayout />}>
        {/* Redirect root to dashboard */}
        <Route index element={<Navigate to="/dashboard" replace />} />
        
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="targets" element={<Targets />} />
        <Route path="scans" element={<LiveMonitor />} />
        <Route path="findings" element={<Findings />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="team" element={<Team />} />
        
        <Route path="attack-graph" element={<AttackGraph />} />
        {/* Add more routes here */}
        
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
