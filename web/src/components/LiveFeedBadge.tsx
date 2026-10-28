import React from 'react';
import { Radio, WifiOff } from 'lucide-react';

interface LiveFeedBadgeProps {
  isConnected: boolean;
  lastUpdate?: string | null;
}

export const LiveFeedBadge: React.FC<LiveFeedBadgeProps> = ({ isConnected, lastUpdate }) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div className={`badge ${isConnected ? 'badge-live' : 'badge-offline'}`}>
        <span className="pulse-dot" />
        {isConnected ? (
          <>
            <Radio size={13} style={{ marginRight: '3px' }} />
            <span>EN VIVO (SSE)</span>
          </>
        ) : (
          <>
            <WifiOff size={13} style={{ marginRight: '3px' }} />
            <span>RECONECTANDO...</span>
          </>
        )}
      </div>
      <span style={{ fontSize: '11px', color: 'var(--text-dim)', letterSpacing: '0.02em' }}>
        {lastUpdate ? `Act: ${new Date(lastUpdate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : 'Transmisión directa'}
      </span>
    </div>
  );
};
