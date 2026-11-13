import { lazy, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import LoginPage from "./pages/LoginPage";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const MapPage = lazy(() => import("./pages/MapPage"));
const PrevalencePage = lazy(() => import("./pages/PrevalencePage"));
const SpeciesPage = lazy(() => import("./pages/SpeciesPage"));
const EnvironmentPage = lazy(() => import("./pages/EnvironmentPage"));
const PopulationRiskPage = lazy(() => import("./pages/PopulationRiskPage"));
const DrugEfficacyPage = lazy(() => import("./pages/DrugEfficacyPage"));
const ResistancePage = lazy(() => import("./pages/ResistancePage"));
const AssistantPage = lazy(() => import("./pages/AssistantPage"));
const BriefsPage = lazy(() => import("./pages/BriefsPage"));

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/prevalence" element={<PrevalencePage />} />
        <Route path="/species" element={<SpeciesPage />} />
        <Route path="/environment" element={<EnvironmentPage />} />
        <Route path="/population-risk" element={<PopulationRiskPage />} />
        <Route path="/drug-efficacy" element={<DrugEfficacyPage />} />
        <Route path="/resistance" element={<ResistancePage />} />
        <Route path="/assistant" element={<AssistantPage />} />
        <Route path="/briefs" element={<BriefsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
