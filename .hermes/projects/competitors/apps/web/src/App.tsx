import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./lib/auth-context";
import { Header } from "./components/Header";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ReelsPage } from "./pages/ReelsPage";
import { RunsPage } from "./pages/RunsPage";

import styles from "./lib/styles.module.css";

function AppRoutes() {
  const { auth, username } = useAuth();

  if (auth === "loading") {
    return (
      <div className={styles.loginPage}>
        <p style={{ color: "#fdfbf7" }}>Loading...</p>
      </div>
    );
  }

  if (auth === "anonymous") {
    // Only the login page is reachable. Any other path is bounced back
    // to /login so the user cannot accidentally land on a gated page
    // when their session has expired.
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Authenticated: all pages are gated. Visiting /login when already
  // signed in bounces to the dashboard.
  return (
    <div className={styles.appRoot}>
      <Header username={username ?? "operator"} />
      <main className={styles.appMain}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/reels" element={<ReelsPage />} />
          <Route path="/reels/:id" element={<ReelsPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
