import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { MapPin } from 'lucide-react';
import { TimeseriesData } from '../api/client';

interface SeismicChartsProps {
  data: TimeseriesData | null;
}

export const SeismicCharts: React.FC<SeismicChartsProps> = ({ data }) => {
  const points = data?.points || [];
  const distribution = data?.distribution_by_magnitude || {};
  const topRegions = data?.top_active_regions || [];

  const defaultCategories = [
    'Menor (< 2.5)',
    'Ligero (2.5 - 4.4)',
    'Moderado (4.5 - 5.9)',
    'Mayor / Fuerte (>= 6.0)',
  ];

  const distColors: Record<string, string> = {
    'Menor (< 2.5)': '#06B6D4',
    'Ligero (2.5 - 4.4)': '#3B82F6',
    'Moderado (4.5 - 5.9)': '#F59E0B',
    'Mayor / Fuerte (>= 6.0)': '#EF4444',
    'Fuerte / Mayor (>= 6.0)': '#EF4444',
  };

  const distArray = defaultCategories.map((category) => {
    // Buscar coincidencia exacta o alternativa
    const count = distribution[category] ?? (category.includes('Mayor') ? (distribution['Fuerte / Mayor (>= 6.0)'] ?? 0) : 0);
    return {
      category,
      count,
    };
  });

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: '20px',
        marginBottom: '24px',
      }}
    >
      {/* 1. Gráfico de Serie Temporal por Hora */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '15px', color: '#F8FAFC', marginBottom: '14px' }}>
          Actividad Sísmica por Hora (Últimas 24h)
        </h3>
        <div style={{ width: '100%', height: '220px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points}>
              <defs>
                <linearGradient id="galacticGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
              <XAxis
                dataKey="hour"
                stroke="#64748b"
                fontSize={11}
                tickFormatter={(val) => val.split(' ')[1] || val}
              />
              <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0F172A',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="event_count"
                name="Sismos"
                stroke="#06B6D4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#galacticGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Distribución por Magnitudes */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '15px', color: '#F8FAFC', marginBottom: '14px' }}>
          Distribución por Rango de Magnitud
        </h3>
        <div style={{ width: '100%', height: '220px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={distArray} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
              <XAxis type="number" stroke="#64748b" fontSize={11} />
              <YAxis dataKey="category" type="category" stroke="#64748b" fontSize={11} width={130} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0F172A',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="count" name="Eventos" radius={[0, 6, 6, 0]}>
                {distArray.map((entry) => (
                  <Cell
                    key={entry.category}
                    fill={distColors[entry.category] || '#38BDF8'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Top Regiones Activas (Utiliza la variable topRegions con llaves estables) */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '15px', color: '#F8FAFC', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MapPin size={16} color="var(--accent-cyan-bright)" />
          <span>Top Regiones Más Activas</span>
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', height: '220px', overflowY: 'auto' }}>
          {topRegions.length === 0 ? (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '40px' }}>
              Sin datos de regiones activas en el período.
            </div>
          ) : (
            topRegions.map((item) => (
              <div
                key={item.region}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(51, 65, 85, 0.4)',
                }}
              >
                <span
                  style={{
                    fontSize: '12px',
                    color: '#F8FAFC',
                    fontWeight: 500,
                    maxWidth: '180px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={item.region}
                >
                  {item.region}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    <strong>{item.count}</strong> sismos
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: item.max_mag >= 5.0 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.15)',
                      color: item.max_mag >= 5.0 ? '#FCA5A5' : 'var(--accent-cyan-bright)',
                      border: `1px solid ${item.max_mag >= 5.0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
                    }}
                  >
                    M{item.max_mag.toFixed(1)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
