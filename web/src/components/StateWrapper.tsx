import React from 'react';
import { AlertCircle, RefreshCw, Inbox } from 'lucide-react';

interface StateWrapperProps {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  onRetry?: () => void;
  children: React.ReactNode;
}

export const StateWrapper: React.FC<StateWrapperProps> = ({
  loading,
  error,
  empty,
  emptyMessage = 'No se encontraron registros disponibles.',
  onRetry,
  children,
}) => {
  if (loading) {
    return (
      <div
        className="glass-panel"
        style={{
          padding: '48px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
          minHeight: '240px',
        }}
      >
        <div
          style={{
            width: '36px',
            height: '36px',
            border: '3px solid rgba(56, 189, 248, 0.2)',
            borderTopColor: 'var(--accent-cyan)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Cargando datos certificados...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="glass-panel"
        style={{
          padding: '36px',
          borderColor: 'rgba(239, 68, 68, 0.4)',
          background: 'rgba(239, 68, 68, 0.05)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
          textAlign: 'center',
        }}
      >
        <AlertCircle size={36} color="var(--accent-crimson)" />
        <div>
          <h4 style={{ color: '#fca5a5', marginBottom: '6px' }}>Error al consultar datos</h4>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '460px' }}>{error}</p>
        </div>
        {onRetry && (
          <button className="btn btn-secondary" onClick={onRetry}>
            <RefreshCw size={14} />
            <span>Reintentar</span>
          </button>
        )}
      </div>
    );
  }

  if (empty) {
    return (
      <div
        className="glass-panel"
        style={{
          padding: '48px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '14px',
          textAlign: 'center',
          minHeight: '200px',
        }}
      >
        <Inbox size={40} color="var(--text-dim)" />
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>{emptyMessage}</p>
        {onRetry && (
          <button className="btn btn-secondary" onClick={onRetry}>
            <RefreshCw size={14} />
            <span>Actualizar</span>
          </button>
        )}
      </div>
    );
  }

  return <>{children}</>;
};
