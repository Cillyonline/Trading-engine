import { Navigate, Route, Routes } from 'react-router-dom';
import OwnerDashboard from './pages/OwnerDashboard';

function App() {
  return (
    <Routes>
      <Route path="/ui" element={<OwnerDashboard />} />
      <Route path="/owner" element={<Navigate to="/ui" replace />} />
      <Route path="*" element={<Navigate to="/ui" replace />} />
    </Routes>
  );
}

export default App;
