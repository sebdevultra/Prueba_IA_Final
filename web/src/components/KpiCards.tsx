import React from 'react';
import { Activity, Flame, Waves, CheckCircle2, AlertTriangle, TrendingUp } from 'lucide-react';
import { KpiData } from '../api/client';

interface KpiCardsProps {
  data: KpiData | null;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ data }) => {
  const events24h = data?.events_24h ?? 0;
  const maxMag = data?.max_magnitude ?? 0.0;
  const avgMag = data?.avg_magnitude ?? 0.0;
  const tsunamiCount = data?.tsunami_count ?? 0;
  const qualityScore = data?.quality_score ?? 100.0;
  const freshnessOk = data?.freshness_ok ?? true;

  const cards = [
    {
      title: 'Eventos Monitoreados (24h)',
      value: events24h.toLocaleString(),
      subtitle: 'Capa Gold Certificada',
      icon: Activity,
      color: 'var(--accent-cyan-bright)',
      glow: 'rgba(6, 182, 212, 0.25)',
    },
    {
      title: 'Magnitud Máxima',
      value: maxMag.toFixed(1),
      subtitle: maxMag >= 6.0 ? 'Alerta Mayor Activa' : (maxMag >= 4.5 ? 'Moderado' : 'Baja Intensidad'),
      icon: Flame,
      color: maxMag >= 6.0 ? 'var(--accent-crimson)' : (maxMag >= 4.5 ? 'var(--accent-amber)' : 'var(--accent-cyan-bright)'),
      glow: maxMag >= 6.0 ? 'rgba(239, 68, 68, 0.25)' : 'rgba(245, 158, 11, 0.2)',
    },
    {
      title: 'Magnitud Promedio',
      value: avgMag.toFixed(2),
      subtitle: 'Intensidad media global',
      icon: TrendingUp,
      color: 'var(--accent-galactic-blue)',
      glow: 'rgba(59, 130, 246, 0.25)',
    },
    {
      title: 'Alertas de Tsunami',
      value: tsunamiCount.toString(),
      subtitle: tsunamiCount > 0 ? 'Protocolo preventivo activo' : 'Sin amenazas registradas',
      icon: Waves,
      color: tsunamiCount > 0 ? 'var(--accent-crimson)' : 'var(--text-muted)',
      glow: tsunamiCount > 0 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.05)',
    },
    {
      title: 'Quality Score Pipeline',
      value: `${qualityScore.toFixed(1)}%`,
      subtitle: freshnessOk ? 'Frescura de datos: Óptima (<30m)' : 'Advertencia de frescura',
      icon: freshnessOk ? CheckCircle2 : AlertTriangle,
      color: qualityScore >= 90.0 ? 'var(--accent-emerald)' : 'var(--accent-amber)',
      glow: 'rgba(16, 185, 129, 0.15)',
    },
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}
    >
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="glass-panel"
            style={{
              padding: '20px',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: 0,
                right: 0,
                width: '80px',
                height: '80px',
                background: `radial-gradient(circle, ${card.glow} 0%, transparent 70%)`,
                pointerEvents: 'none',
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {card.title}
              </span>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: card.glow,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Icon size={18} color={card.color} />
              </div>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: card.color, lineHeight: 1.1, marginBottom: '6px' }}>
              {card.value}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              {card.subtitle}
            </div>
          </div>
        );
      })}
    </div>
  );
};
