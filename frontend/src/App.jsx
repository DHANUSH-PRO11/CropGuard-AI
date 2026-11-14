import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CropCheck from './pages/CropCheck';
import Result from './pages/Result';
import Assistant from './pages/Assistant';
import Weather from './pages/Weather';
import Schemes from './pages/Schemes';
import History from './pages/History';
import Profile from './pages/Profile';
import { AuthProvider, useAuth } from './context/AuthContext';
import './i18n/i18n';

function ProtectedRoute({ children }) {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function PublicOnlyRoute({ children }) {
  const { token } = useAuth();
  if (token) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
            <Route path="register" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="crop" element={<CropCheck />} />
            <Route path="result" element={<Result />} />
            <Route path="assistant" element={<Assistant />} />
            <Route path="weather" element={<Weather />} />
            <Route path="schemes" element={<Schemes />} />
            <Route path="history" element={<History />} />
            <Route path="profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
