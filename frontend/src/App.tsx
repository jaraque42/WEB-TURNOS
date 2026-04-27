import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/useAuth';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import EmployeesPage from './pages/EmployeesPage';
import ShiftTypesPage from './pages/ShiftTypesPage';
import AssignmentsPage from './pages/AssignmentsPage';
import BusinessRulesPage from './pages/BusinessRulesPage';
import UsersPage from './pages/UsersPage';
import ForecastImportsPage from './pages/ForecastImportsPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div className="loading-page"><span className="spinner" /></div>;
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const { token, loading } = useAuth();

  if (loading) return <div className="loading-page"><span className="spinner" /></div>;

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="shift-types" element={<ShiftTypesPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="business-rules" element={<BusinessRulesPage />} />
        <Route path="imports" element={<ForecastImportsPage />} />
        <Route path="users" element={<UsersPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
