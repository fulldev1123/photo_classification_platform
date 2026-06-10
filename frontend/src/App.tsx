import { Navigate, Route, Routes } from "react-router-dom";

import NavBar from "./components/NavBar";
import RequireAuth from "./components/RequireAuth";
import AdminDashboardPage from "./features/admin/AdminDashboardPage";
import LoginPage from "./features/auth/LoginPage";
import RegisterPage from "./features/auth/RegisterPage";
import MySubmissionsPage from "./features/submissions/MySubmissionsPage";
import SubmitPage from "./features/submissions/SubmitPage";

export default function App() {
  return (
    <div className="min-h-full">
      <NavBar />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/submit" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/submit"
            element={
              <RequireAuth>
                <SubmitPage />
              </RequireAuth>
            }
          />
          <Route
            path="/me"
            element={
              <RequireAuth>
                <MySubmissionsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth adminOnly>
                <AdminDashboardPage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
