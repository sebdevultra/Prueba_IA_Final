import React, { useState, useEffect, useCallback } from 'react';
import { Search, RefreshCw, ChevronLeft, ChevronRight, Waves, ExternalLink } from 'lucide-react';
import { api, KpiData, SeismicEvent, TimeseriesData } from '../api/client';
import { KpiCards } from '../components/KpiCards';
import { SeismicMap } from '../components/SeismicMap';
import { SeismicCharts } from '../components/SeismicCharts';
import { StateWrapper } from '../components/StateWrapper';

interface DashboardPageProps {
  liveEvents: SeismicEvent[];
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ liveEvents }) => {
  const [kpis, setKpis] = useState<KpiData | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesData | null>(null);
  const [events, setEvents] = useState<SeismicEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  // Filtros, ordenamiento y paginación
  const [minMag, setMinMag] = useState<number | undefined>(undefined);
  const [regionQuery, setRegionQuery] = useState<string>('');
  const [tsunamiFilter, setTsunamiFilter] = useState<boolean | undefined>(undefined);
  const [sortBy, setSortBy] = useState<string>('time_utc');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(15);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalEvents, setTotalEvents] = useState<number>(0);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setError(null);
    try {
      const [kpiRes, tsRes, evRes] = await Promise.all([
        api.getKpis(),
        api.getTimeseries(),
        api.getEvents({
          min_mag: minMag,
          region: regionQuery.trim() || undefined,
          tsunami: tsunamiFilter,
          sort_by: sortBy,
          sort_order: sortOrder,
          page,
          page_size: pageSize,
        }),
      ]);

      setKpis(kpiRes);
      setTimeseries(tsRes);
      setEvents(evRes.events);
      setTotalPages(evRes.total_pages);
      setTotalEvents(evRes.total);
    } catch (err: any) {
      setError(err.message || 'Error cargando datos del dashboard');
    } finally {
      setLoading(false);
    }
  }, [minMag, regionQuery, tsunamiFilter, sortBy, sortOrder, page, pageSize]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Si llegan nuevos eventos por SSE, anteponerlos en la lista si no están filtrados
  useEffect(() => {
    if (liveEvents.length > 0 && page === 1 && !regionQuery && minMag === undefined) {
      setEvents((prev) => {
        const existingIds = new Set(prev.map((e) => e.event_id));
        const newOnes = liveEvents.filter((e) => !existingIds.has(e.event_id));
        if (newOnes.length > 0) {
          return [...newOnes, ...prev].slice(0, pageSize);
        }
        return prev;
      });
    }
  }, [liveEvents, page, regionQuery, minMag, pageSize]);

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const getSortIndicator = (column: string) => {
    if (sortBy !== column) return ' ⇅';
    return sortOrder === 'desc' ? ' ↓' : ' ↑';
  };

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* 1. Tarjetas de KPIs */}
      <StateWrapper loading={loading && !kpis} error={error} onRetry={fetchDashboardData}>
        <KpiCards data={kpis} />

        {/* 2. Mapa Sísmico Interactivo */}
        <div style={{ marginBottom: '24px' }}>
          <SeismicMap
            events={events}
            selectedEventId={selectedEventId}
            onSelectEvent={(ev) => setSelectedEventId(ev.event_id)}
          />
        </div>

        {/* 3. Gráficos Analíticos */}
        <SeismicCharts data={timeseries} />

        {/* 4. Barra de Filtros, Ordenamiento y Búsqueda */}
        <div
          className="glass-panel"
          style={{
            padding: '16px 20px',
            marginBottom: '20px',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '12px', flex: '1 1 500px' }}>
            <div style={{ position: 'relative', width: '100%', maxWidth: '260px' }}>
              <input
                type="text"
                className="input-field"
                placeholder="Buscar por país, región..."
                value={regionQuery}
                onChange={(e) => {
                  setRegionQuery(e.target.value);
                  setPage(1);
                }}
                style={{ paddingLeft: '36px' }}
              />
              <Search size={16} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            </div>

            <select
              className="input-field"
              value={minMag ?? ''}
              onChange={(e) => {
                const val = e.target.value ? parseFloat(e.target.value) : undefined;
                setMinMag(val);
                setPage(1);
              }}
              style={{ width: '160px' }}
            >
              <option value="">Todas las Magnitudes</option>
              <option value="2.5">&ge; 2.5 Ligero +</option>
              <option value="4.5">&ge; 4.5 Moderado +</option>
              <option value="6.0">&ge; 6.0 Mayor (Alerta)</option>
            </select>

            <select
              className="input-field"
              value={tsunamiFilter === undefined ? '' : String(tsunamiFilter)}
              onChange={(e) => {
                const val = e.target.value === '' ? undefined : e.target.value === 'true';
                setTsunamiFilter(val);
                setPage(1);
              }}
              style={{ width: '150px' }}
            >
              <option value="">Tsunami: Todos</option>
              <option value="true">🌊 Con Alerta</option>
              <option value="false">Sin Alerta</option>
            </select>

            <select
              className="input-field"
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              style={{ width: '160px' }}
            >
              <option value="time_utc">Ordenar: Fecha UTC</option>
              <option value="mag">Ordenar: Magnitud</option>
              <option value="depth_km">Ordenar: Profundidad</option>
            </select>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'));
                setPage(1);
              }}
              title="Cambiar orden ascendente/descendente"
              style={{ padding: '8px 12px', minWidth: '80px' }}
            >
              {sortOrder === 'desc' ? 'Desc ↓' : 'Asc ↑'}
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Mostrando <strong>{events.length}</strong> de <strong>{totalEvents}</strong> sismos
            </span>
            <button className="btn btn-secondary" onClick={fetchDashboardData} title="Refrescar">
              <RefreshCw size={14} />
              <span>Actualizar</span>
            </button>
          </div>
        </div>

        {/* 5. Tabla de Eventos Certificados */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th
                    onClick={() => handleSort('mag')}
                    style={{ cursor: 'pointer', userSelect: 'none', color: sortBy === 'mag' ? 'var(--accent-cyan)' : undefined }}
                    title="Clic para ordenar por Magnitud"
                  >
                    Mag{getSortIndicator('mag')}
                  </th>
                  <th>Lugar</th>
                  <th
                    onClick={() => handleSort('time_utc')}
                    style={{ cursor: 'pointer', userSelect: 'none', color: sortBy === 'time_utc' ? 'var(--accent-cyan)' : undefined }}
                    title="Clic para ordenar por Fecha UTC"
                  >
                    Fecha UTC{getSortIndicator('time_utc')}
                  </th>
                  <th
                    onClick={() => handleSort('depth_km')}
                    style={{ cursor: 'pointer', userSelect: 'none', color: sortBy === 'depth_km' ? 'var(--accent-cyan)' : undefined }}
                    title="Clic para ordenar por Profundidad"
                  >
                    Profundidad{getSortIndicator('depth_km')}
                  </th>
                  <th>Tsunami</th>
                  <th>Coordenadas</th>
                  <th>Detalles</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                      No se encontraron eventos sísmicos con los filtros actuales.
                    </td>
                  </tr>
                ) : (
                  events.map((ev) => {
                    const isSelected = ev.event_id === selectedEventId;
                    const mag = ev.mag ?? 0;
                    let magColor = '#38bdf8';
                    if (mag >= 6.0) magColor = '#ef4444';
                    else if (mag >= 4.5) magColor = '#f59e0b';

                    return (
                      <tr
                        key={ev.event_id}
                        onClick={() => setSelectedEventId(ev.event_id)}
                        style={{
                          cursor: 'pointer',
                          backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : undefined,
                        }}
                      >
                        <td style={{ fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>{ev.event_id}</td>
                        <td>
                          <span
                            style={{
                              display: 'inline-block',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontWeight: 700,
                              backgroundColor: `${magColor}22`,
                              color: magColor,
                              border: `1px solid ${magColor}44`,
                            }}
                          >
                            {mag.toFixed(1)}
                          </span>
                        </td>
                        <td style={{ fontWeight: 500, color: '#f8fafc' }}>{ev.place || 'Ubicación desconocida'}</td>
                        <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {ev.time_utc ? new Date(ev.time_utc).toUTCString() : 'N/A'}
                        </td>
                        <td>{ev.depth_km != null ? `${ev.depth_km.toFixed(1)} km` : 'N/A'}</td>
                        <td>
                          {ev.tsunami > 0 ? (
                            <span style={{ color: 'var(--accent-crimson)', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
                              <Waves size={14} /> Alerta
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-dim)' }}>No</span>
                          )}
                        </td>
                        <td style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                          {ev.latitude != null && ev.longitude != null ? `${ev.latitude.toFixed(2)}, ${ev.longitude.toFixed(2)}` : 'N/A'}
                        </td>
                        <td>
                          {ev.url ? (
                            <a
                              href={ev.url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: 'var(--accent-cyan)', display: 'inline-flex', alignItems: 'center' }}
                            >
                              <ExternalLink size={14} />
                            </a>
                          ) : (
                            '-'
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Paginador */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '16px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-color)',
            }}
          >
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Página <strong>{page}</strong> de <strong>{totalPages}</strong>
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{ padding: '6px 12px' }}
              >
                <ChevronLeft size={16} />
                <span>Anterior</span>
              </button>
              <button
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{ padding: '6px 12px' }}
              >
                <span>Siguiente</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </StateWrapper>
    </div>
  );
};
