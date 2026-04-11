import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import Layout from "./components/Layout.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Upload from "./pages/Upload.jsx";
import Results from "./pages/Results.jsx";
import FeedbackDashboard from "./pages/FeedbackDashboard.jsx";
import TeacherDashboard from "./pages/TeacherDashboard.jsx";

function Private({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/upload"
          element={
            <Private>
              <Upload />
            </Private>
          }
        />
        <Route
          path="/results"
          element={
            <Private>
              <Results />
            </Private>
          }
        />
        <Route
          path="/feedback"
          element={
            <Private>
              <FeedbackDashboard />
            </Private>
          }
        />
        <Route
          path="/teacher"
          element={
            <Private>
              <TeacherDashboard />
            </Private>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
