import React, { useState, useEffect } from 'react';
import { Server, CheckCircle2, Play, RefreshCw, Layers, Clock } from 'lucide-react';
import { api, PipelineStatusData } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { StateWrapper } from '../components/StateWrapper';

export const PipelineStatusPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [statusData, setStatusData] = useState<PipelineStatusData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Parámetros de Backfill (Solo Admin)
  const [daysBack, setDaysBack] = useState<number>(30);
  const [minMag, setMinMag] = useState<number>(2.5);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [backfillLoading, setBackfillLoading] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchStatus = async () => {
    setError(null);
    try {
      const data = await api.getPipelineStatus();
      setStatusData(data);
    } catch (err: any) {
      setError(err.message || 'Error cargando estado del pipeline');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleLaunchBackfill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;
    setBackfillLoading(true);
    setActionMsg(null);
    try {
      const res = await api.triggerBackfill({
        days_back: daysBack,
        min_magnitude: minMag,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setActionMsg(res.message);
      setTimeout(fetchStatus, 4000);
    } catch (err: any) {
      setError(err.message || 'Error al disparar backfill');
    } finally {
      setBackfillLoading(false);
    }
  };

  const lastQ = statusData?.last_quality_run;

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* Encabezado */}
      <div
        className="glass-panel"
        style={{
          padding: '24px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <h2 style={{ fontSize: '20px', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server size={22} color="var(--accent-cyan)" />
            <span>Observabilidad y Orquestación de Datos (Apache Airflow)</span>
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Monitoreo en tiempo real de DAGs, compuertas de calidad Medallion y frescura del feed.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchStatus}>
          <RefreshCw size={14} />
          <span>Actualizar Estado</span>
        </button>
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
          <CheckCircle2 size={16} />
          <span>{actionMsg}</span>
        </div>
      )}

      <StateWrapper loading={loading} error={error} onRetry={fetchStatus}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', marginBottom: '24px' }}>
          {/* Card: Última Corrida de Calidad */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Layers size={20} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: '16px', color: '#fff' }}>Compuerta de Calidad (Último Lote)</h3>
              </div>
              <span
                style={{
                  fontSize: '14px',
                  fontWeight: 800,
                  color: (lastQ?.quality_score ?? 100) >= 90 ? 'var(--accent-emerald)' : 'var(--accent-amber)',
                }}
              >
                Score: {lastQ?.quality_score?.toFixed(1) ?? '100.0'}%
              </span>
            </div>

            {lastQ ? (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '16px', textAlign: 'center' }}>
                  <div style={{ padding: '10px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Evaluados</span>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>{lastQ.total_records}</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Aprobados</span>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--accent-emerald)' }}>{lastQ.valid_records}</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Retenidos</span>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--accent-crimson)' }}>{lastQ.invalid_records}</div>
                  </div>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px' }}>
                  <strong>Evaluado en:</strong> {new Date(lastQ.evaluated_at).toLocaleString()}
                </div>

                <h4 style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Desglose de Reglas Incumplidas:
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {Object.keys(lastQ.rule_breakdown || {}).length === 0 ? (
                    <span style={{ fontSize: '12px', color: 'var(--accent-emerald)' }}>100% registros conformes sin violaciones de reglas.</span>
                  ) : (
                    Object.entries(lastQ.rule_breakdown).map(([rule, cnt]) => (
                      <span
                        key={rule}
                        style={{
                          fontSize: '11px',
                          background: 'rgba(239, 68, 68, 0.15)',
                          color: '#fca5a5',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                        }}
                      >
                        {rule}: <strong>{cnt}</strong>
                      </span>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No se han ejecutado corridas de calidad aún.</p>
            )}
          </div>

          {/* Panel de Backfill Parametrizado (SOLO ADMIN) */}
          {isAdmin && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Play size={20} color="var(--accent-amber)" />
                  <h3 style={{ fontSize: '16px', color: '#fff' }}>Lanzar Backfill Histórico</h3>
                </div>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    background: 'rgba(239, 68, 68, 0.2)',
                    color: '#fca5a5',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                  }}
                >
                  SOLO ADMIN
                </span>
              </div>

              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                Dispara el DAG parametrizado <code style={{ color: 'var(--accent-cyan)' }}>dag_usgs_backfill_30d</code> con particionamiento en ventanas de 5 días e inserción idempotente.
              </p>

              <form onSubmit={handleLaunchBackfill}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '6px' }}>
                      Fecha Inicio (YYYY-MM-DD):
                    </label>
                    <input
                      type="date"
                      className="input-field"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '6px' }}>
                      Fecha Fin (YYYY-MM-DD):
                    </label>
                    <input
                      type="date"
                      className="input-field"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '6px' }}>
                      Días Históricos (si no hay fechas):
                    </label>
                    <input
                      type="number"
                      className="input-field"
                      min={1}
                      max={90}
                      value={daysBack}
                      onChange={(e) => setDaysBack(parseInt(e.target.value) || 30)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '6px' }}>
                      Magnitud Mínima:
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      className="input-field"
                      min={0}
                      max={10}
                      value={minMag}
                      onChange={(e) => setMinMag(parseFloat(e.target.value) || 2.5)}
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={backfillLoading}
                  style={{ width: '100%', padding: '10px' }}
                >
                  <Play size={15} />
                  <span>{backfillLoading ? 'Encolando en Airflow...' : 'Ejecutar Backfill'}</span>
                </button>
              </form>
            </div>
          )}
        </div>

        {/* Tabla de DAGs en Airflow */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', color: '#fff', marginBottom: '16px' }}>
            DAGs Registrados en el Orquestador
          </h3>
          <table className="custom-table">
            <thead>
              <tr>
                <th>DAG ID</th>
                <th>Frecuencia (Schedule)</th>
                <th>Propósito / Capa</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {statusData?.dags_status.map((dag: any) => {
                const stateStr = (dag.state || 'ready').toLowerCase();
                const isSuccess = stateStr === 'success' || stateStr === 'active' || stateStr === 'ready';
                const isRunning = stateStr === 'running' || stateStr === 'queued';
                const isFailed = stateStr === 'failed';
                const isPaused = dag.is_paused;

                let badgeColor = 'var(--accent-emerald)';
                let badgeText = 'Éxito / Listo';
                if (isPaused) {
                  badgeColor = 'var(--text-muted)';
                  badgeText = 'Pausado';
                } else if (isFailed) {
                  badgeColor = 'var(--accent-crimson)';
                  badgeText = 'Fallo';
                } else if (isRunning) {
                  badgeColor = 'var(--accent-amber)';
                  badgeText = stateStr === 'running' ? 'En Ejecución' : 'En Cola';
                } else if (stateStr === 'success') {
                  badgeText = 'Éxito';
                }

                return (
                  <tr key={dag.dag_id}>
                    <td style={{ fontFamily: 'monospace', color: 'var(--accent-cyan)', fontWeight: 600 }}>{dag.dag_id}</td>
                    <td>
                      <span style={{ fontSize: '12px', background: 'rgba(30, 41, 59, 0.6)', padding: '2px 8px', borderRadius: '4px' }}>
                        {dag.schedule}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-main)' }}>{dag.description}</td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '11px',
                            color: badgeColor,
                            fontWeight: 600,
                          }}
                        >
                          <CheckCircle2 size={13} /> {badgeText}
                        </span>
                        {dag.last_run_time && (
                          <span style={{ fontSize: '10px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Clock size={10} />
                            {new Date(dag.last_run_time).toLocaleString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', month: 'short', day: 'numeric' })}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </StateWrapper>
    </div>
  );
};
