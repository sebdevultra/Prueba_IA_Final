import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { AgentChatPage } from './pages/AgentChatPage';
import { ReportsPage } from './pages/ReportsPage';
import { PipelineStatusPage } from './pages/PipelineStatusPage';
import { useEventStream } from './hooks/useEventStream';

const MainAppContent: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');

  // Streaming SSE
  const { isConnected, lastHeartbeat, liveEvents } = useEventStream();

  const handleSelectTab = (tab: string) => {
    setCurrentTab(tab);
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)' }}>Inicializando SismoWatch...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
        isConnected={isConnected}
        lastHeartbeat={lastHeartbeat}
      />

      <main className="container" style={{ flex: 1, paddingTop: '24px' }}>
        {currentTab === 'dashboard' && <DashboardPage liveEvents={liveEvents} />}
        {currentTab === 'agent' && <AgentChatPage />}
        {currentTab === 'reports' && <ReportsPage />}
        {currentTab === 'pipeline' && <PipelineStatusPage />}
      </main>

      <footer
        style={{
          borderTop: '1px solid var(--border-color)',
          padding: '16px 0',
          textAlign: 'center',
          fontSize: '12px',
          color: 'var(--text-dim)',
          background: 'rgba(11, 15, 25, 0.8)',
        }}
      >
        <div className="container">
          SismoWatch &copy; 2026 — Plataforma de Datos Sísmicos en Tiempo Casi Real. SuperApp Operaciones & Gestión de Riesgo.
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
};

export default App;
