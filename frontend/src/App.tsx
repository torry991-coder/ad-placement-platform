import { Routes, Route } from "react-router-dom";
import DashboardLayout from "./components/layout/DashboardLayout";
import DashboardPage from "./pages/DashboardPage";
import CampaignsPage from "./pages/CampaignsPage";
import SettingsPage from "./pages/SettingsPage";
import ExperimentsPage from "./pages/ExperimentsPage";
import AlertsPage from "./pages/AlertsPage";
import AIAgentPage from "./pages/AIAgentPage";
import CreativePage from "./pages/CreativePage";
import AudiencePage from "./pages/AudiencePage";
import ReportsPage from "./pages/ReportsPage";
import BigscreenPage from "./pages/BigscreenPage";
import { CommandPalette } from "./components/common/CommandPalette";
import { useCommandPalette } from "./hooks/useKeyboardShortcuts";

export default function App() {
  const { open, setOpen, query, setQuery, commands, navigate } = useCommandPalette();

  return (
    <>
      <CommandPalette
        open={open}
        onClose={() => setOpen(false)}
        query={query}
        onQueryChange={setQuery}
        commands={commands}
        onNavigate={navigate}
      />
      <Routes>
        <Route path="/bigscreen" element={<BigscreenPage />} />
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/creative" element={<CreativePage />} />
          <Route path="/audience" element={<AudiencePage />} />
          <Route path="/experiments" element={<ExperimentsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/ai-agent" element={<AIAgentPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </>
  );
}
