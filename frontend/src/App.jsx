import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RiskQueuePage from "./pages/RiskQueuePage";
import TransactionDetailPage from "./pages/TransactionDetailPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import "./App.css";

function ProtectedRoutes() {
  const { session, loading } = useAuth();

  if (loading) return <div className="empty-state">Loading…</div>;
  if (!session) return <Navigate to="/login" replace />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/queue" replace />} />
        <Route path="/queue" element={<RiskQueuePage />} />
        <Route path="/transactions/:id" element={<TransactionDetailPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="*" element={<Navigate to="/queue" replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<ProtectedRoutes />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
