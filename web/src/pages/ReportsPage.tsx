import React, { useState, useEffect } from 'react';
import { FileText, Download, Sparkles, CheckCircle } from 'lucide-react';
import { api, DailyReport, API_BASE_URL } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { StateWrapper } from '../components/StateWrapper';

export const ReportsPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<boolean>(false);

  const fetchReports = async () => {
    setError(null);
    try {
      const data = await api.getDailyReports(20);
      setReports(data);
      if (data.length > 0) {
        setSelectedReport(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando reportes ejecutivos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleRegenerate = async () => {
    if (!isAdmin) return;
    setRegenerating(true);
    setActionMsg(null);
    try {
      const res = await api.regenerateReport();
      setActionMsg(res.message);
      await fetchReports();
    } catch (err: any) {
      setError(err.message || 'Error al solicitar regeneración');
    } finally {
      setRegenerating(false);
    }
  };

  const handleDownload = async (format: 'csv' | 'html') => {
    try {
      const token = localStorage.getItem('sismowatch_token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE_URL}/api/reports/export?export_type=events&format=${format}${token ? `&token=${token}` : ''}`, {
        headers,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Error en la descarga (${res.status}): ${errText}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sismowatch_export_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || 'Error al descargar archivo');
    }
  };

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Encabezado y Acciones */}
      <div
        className="glass-panel"
        style={{
          padding: '24px',
          marginBottom: '24px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '20px', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={22} color="var(--accent-cyan)" />
            <span>Reportes Ejecutivos Diarios con Inteligencia Artificial</span>
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Informes narrativos con cifras calculadas previamente en SQL/Python y validadas con Pydantic.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={() => handleDownload('csv')}>
            <Download size={14} />
            <span>Exportar CSV</span>
          </button>
          <button className="btn btn-secondary" onClick={() => handleDownload('html')}>
            <Download size={14} />
            <span>Descargar HTML/PDF</span>
          </button>

          {/* Botón exclusivo para ADMINISTRADOR */}
          {isAdmin && (
            <button className="btn btn-primary" onClick={handleRegenerate} disabled={regenerating}>
              <Sparkles size={15} />
              <span>{regenerating ? 'Encolando en Airflow...' : 'Regenerar con IA'}</span>
            </button>
          )}
        </div>
      </div>

      {actionMsg && (
        <div
          style={{
            padding: '12px 16px',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '8px',
            color: '#6ee7b7',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: '20px',
          }}
        >
          <CheckCircle size={16} />
          <span>{actionMsg}</span>
        </div>
      )}

      <StateWrapper loading={loading} error={error} empty={reports.length === 0} onRetry={fetchReports}>
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
          {/* Historial de Fechas */}
          <div className="glass-panel" style={{ padding: '16px', height: 'fit-content' }}>
            <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px' }}>
              Historial de Jornadas
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reports.map((rep) => {
                const active = selectedReport?.report_id === rep.report_id;
                return (
                  <button
                    key={rep.report_id}
                    onClick={() => setSelectedReport(rep)}
                    style={{
                      textAlign: 'left',
                      padding: '12px 14px',
                      borderRadius: '8px',
                      border: '1px solid',
                      borderColor: active ? 'rgba(56, 189, 248, 0.4)' : 'transparent',
                      background: active ? 'rgba(56, 189, 248, 0.12)' : 'rgba(30, 41, 59, 0.4)',
                      color: active ? '#fff' : 'var(--text-muted)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ fontSize: '13px', fontWeight: 700, color: active ? 'var(--accent-cyan)' : '#f8fafc' }}>
                      {rep.report_date}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {rep.headline}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Visor de Reporte Seleccionado */}
          {selectedReport && (
            <div className="glass-panel" style={{ padding: '30px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span
                  style={{
                    fontSize: '11px',
                    padding: '4px 10px',
                    borderRadius: '9999px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    background: selectedReport.is_fallback ? 'rgba(245, 158, 11, 0.15)' : 'rgba(168, 85, 247, 0.15)',
                    color: selectedReport.is_fallback ? '#fcd34d' : '#d8b4fe',
                    border: `1px solid ${selectedReport.is_fallback ? 'rgba(245, 158, 11, 0.3)' : 'rgba(168, 85, 247, 0.3)'}`,
                  }}
                >
                  {selectedReport.is_fallback ? 'FALLBACK DETERMINISTA JINJA2' : 'GOOGLE GEMINI 1.5 FLASH'}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                  Generado: {new Date(selectedReport.created_at).toLocaleString()}
                </span>
              </div>

              <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '18px', lineHeight: 1.25 }}>
                {selectedReport.headline}
              </h1>

              {/* Métricas preverificadas */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '12px',
                  padding: '16px',
                  background: 'rgba(15, 23, 42, 0.7)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '24px',
                }}
              >
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Total Sismos</span>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--accent-cyan)' }}>
                    {selectedReport.computed_metrics.total_events}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Magnitud Máx</span>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--accent-amber)' }}>
                    {selectedReport.computed_metrics.max_mag?.toFixed(1)}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Promedio</span>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--accent-blue)' }}>
                    {selectedReport.computed_metrics.avg_mag?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Tsunamis</span>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: selectedReport.computed_metrics.tsunami_count > 0 ? 'var(--accent-crimson)' : 'var(--text-muted)' }}>
                    {selectedReport.computed_metrics.tsunami_count}
                  </div>
                </div>
              </div>

              {/* Resumen Ejecutivo */}
              <div style={{ marginBottom: '28px' }}>
                <h4 style={{ fontSize: '14px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Resumen Ejecutivo
                </h4>
                <p style={{ fontSize: '15px', lineHeight: 1.7, color: '#e2e8f0' }}>
                  {selectedReport.executive_summary}
                </p>
              </div>

              {/* Zonas Activas */}
              {selectedReport.most_active_zones?.length > 0 && (
                <div style={{ marginBottom: '28px' }}>
                  <h4 style={{ fontSize: '14px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Regiones con Mayor Actividad
                  </h4>
                  <ul style={{ paddingLeft: '20px', color: '#94a3b8', fontSize: '14px', lineHeight: 1.6 }}>
                    {selectedReport.most_active_zones.map((zone, idx) => (
                      <li key={idx} style={{ marginBottom: '4px' }}>{zone}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Eventos Notables */}
              {selectedReport.notable_events?.length > 0 && (
                <div>
                  <h4 style={{ fontSize: '14px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Eventos Notables de la Jornada
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {selectedReport.notable_events.map((ev, i) => (
                      <div
                        key={i}
                        style={{
                          padding: '10px 14px',
                          background: 'rgba(30, 41, 59, 0.4)',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          border: '1px solid var(--border-color)',
                        }}
                      >
                        <span style={{ fontSize: '13px', color: '#f8fafc' }}>{ev.place}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-amber)' }}>
                            M{ev.mag?.toFixed(1)}
                          </span>
                          <span
                            style={{
                              fontSize: '10px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: ev.severity === 'ALTA' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                              color: ev.severity === 'ALTA' ? '#fca5a5' : '#7dd3fc',
                              fontWeight: 700,
                            }}
                          >
                            {ev.severity}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </StateWrapper>
    </div>
  );
};
