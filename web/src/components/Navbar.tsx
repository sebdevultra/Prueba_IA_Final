import React from 'react';
import { Activity, Bot, FileText, Server, LogOut, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { LiveFeedBadge } from './LiveFeedBadge';

interface NavbarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  isConnected: boolean;
  lastHeartbeat?: string | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  isConnected,
  lastHeartbeat,
}) => {
  const { user, isAdmin, logout } = useAuth();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'agent', label: 'Agente IA (Gold)', icon: Bot },
    { id: 'reports', label: 'Reportes IA', icon: FileText },
    { id: 'pipeline', label: 'Estado Pipeline', icon: Server },
  ];

  return (
    <header
      style={{
        background: 'rgba(11, 15, 25, 0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border-color)',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        padding: '12px 0',
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '24px',
        }}
      >
        {/* Logo & Marca */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => onSelectTab('dashboard')}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #06B6D4 0%, #3B82F6 50%, #6366F1 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(6, 182, 212, 0.5)',
            }}
          >
            <Activity size={24} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: '19px', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
              Sismo<span style={{ color: 'var(--accent-cyan-bright)', textShadow: '0 0 10px rgba(56, 189, 248, 0.4)' }}>Watch</span>
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
              SuperApp Risk Platform
            </div>
          </div>
        </div>

        {/* Links de Navegación */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 16px',
                  borderRadius: '10px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: '1px solid',
                  borderColor: active ? 'rgba(99, 102, 241, 0.6)' : 'transparent',
                  background: active ? 'rgba(59, 130, 246, 0.16)' : 'transparent',
                  color: active ? 'var(--accent-cyan-bright)' : 'var(--text-muted)',
                  boxShadow: active ? '0 0 14px rgba(6, 182, 212, 0.25)' : 'none',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Live SSE Badge & Usuario */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
          <LiveFeedBadge isConnected={isConnected} lastUpdate={lastHeartbeat} />

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '6px 12px',
              borderRadius: '8px',
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid var(--border-color)',
            }}
          >
            <User size={15} color="var(--accent-cyan)" />
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
              {user?.username}
            </span>
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                fontWeight: 700,
                textTransform: 'uppercase',
                background: isAdmin ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                color: isAdmin ? '#fca5a5' : '#7dd3fc',
                border: `1px solid ${isAdmin ? 'rgba(239, 68, 68, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
              }}
            >
              {isAdmin ? 'ADMIN' : 'VIEWER'}
            </span>
          </div>

          <button
            className="btn btn-secondary"
            onClick={logout}
            title="Cerrar Sesión"
            style={{ padding: '8px 12px' }}
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </header>
  );
};
