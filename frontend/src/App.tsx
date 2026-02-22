import { Navigate, Route, Routes } from 'react-router-dom';
import OwnerDashboard from './pages/OwnerDashboard';

function App() {
  return (
    <Routes>
      <Route path="/owner" element={<OwnerDashboard />} />
      <Route path="*" element={<Navigate to="/owner" replace />} />
    </Routes>
  );
}

export default App;
