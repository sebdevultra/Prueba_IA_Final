/**
 * Cliente HTTP tipado para interactuar con la API FastAPI de SismoWatch.
 * Adjunta automáticamente el token Bearer JWT en las peticiones.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface UserSession {
  username: string;
  role: 'admin' | 'viewer';
  token: string;
}

export interface KpiData {
  events_24h: number;
  max_magnitude: number;
  avg_magnitude: number;
  tsunami_count: number;
  quality_score: number;
  last_update_utc?: string;
  freshness_ok: boolean;
}

export interface SeismicEvent {
  event_id: string;
  mag: number;
  place: string;
  time_utc: string;
  updated_utc?: string;
  tsunami: number;
  sig?: number;
  status?: string;
  mag_type?: string;
  event_type?: string;
  url?: string;
  longitude: number;
  latitude: number;
  depth_km: number;
}

export interface EventsResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  events: SeismicEvent[];
}

export interface TimeseriesPoint {
  hour: string;
  event_count: number;
  avg_mag: number;
  max_mag: number;
}

export interface TimeseriesData {
  points: TimeseriesPoint[];
  distribution_by_magnitude: Record<string, number>;
  top_active_regions: { region: string; count: number; max_mag: number }[];
}

export interface DailyReport {
  report_id: string;
  report_date: string;
  headline: string;
  executive_summary: string;
  most_active_zones: string[];
  notable_events: { event_id: string; place: string; mag: number; severity: string }[];
  computed_metrics: { total_events: number; max_mag: number; avg_mag: number; tsunami_count: number };
  is_fallback: boolean;
  created_at: string;
}

export interface AgentQueryResponse {
  reply: string;
  model: string;
  data_points_analyzed: number;
  queried_at: string;
  sources_used: string[];
}

export interface PipelineStatusData {
  airflow_online: boolean;
  dags_status: { dag_id: string; schedule: string; state: string; description: string }[];
  last_quality_run?: {
    run_id: string;
    evaluated_at: string;
    total_records: number;
    valid_records: number;
    invalid_records: number;
    quality_score: number;
    freshness_ok: boolean;
    volume_ok: boolean;
    rule_breakdown: Record<string, number>;
  };
  database_status: string;
}

// Fetch helper con inyección de JWT
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('sismowatch_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('sismowatch_token');
    localStorage.removeItem('sismowatch_user');
    window.location.href = '/login';
    throw new Error('Sesión expirada. Por favor inicie sesión nuevamente.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Error HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Autenticación
  login: async (username: string, password: string) => {
    return apiFetch<{ access_token: string; token_type: string; role: 'admin' | 'viewer'; username: string }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }
    );
  },

  getMe: async () => apiFetch<{ username: string; role: 'admin' | 'viewer' }>('/auth/me'),

  // Analítica & Dashboard
  getKpis: async () => apiFetch<KpiData>('/api/kpis'),

  getEvents: async (params: {
    min_mag?: number;
    start_date?: string;
    end_date?: string;
    region?: string;
    tsunami?: boolean;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.min_mag !== undefined && params.min_mag !== null) query.append('min_mag', params.min_mag.toString());
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.region) query.append('region', params.region);
    if (params.tsunami !== undefined && params.tsunami !== null) query.append('tsunami', params.tsunami.toString());
    if (params.sort_by) query.append('sort_by', params.sort_by);
    if (params.sort_order) query.append('sort_order', params.sort_order);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    return apiFetch<EventsResponse>(`/api/events?${query.toString()}`);
  },

  getTimeseries: async () => apiFetch<TimeseriesData>('/api/stats/timeseries'),

  getDailyReports: async (limit = 15) => apiFetch<DailyReport[]>(`/api/reports?limit=${limit}`),

  getPipelineStatus: async () => apiFetch<PipelineStatusData>('/api/pipeline/status'),

  // Agente de IA para Consultas a la Capa Curated (Gold) - Ollama 8B
  askGoldAgent: async (message: string, history: { role: string; content: string }[] = []) => {
    return apiFetch<AgentQueryResponse>('/api/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history }),
    });
  },

  // Rutas de Administración (Requieren rol admin)
  triggerBackfill: async (options: { days_back?: number; min_magnitude?: number; start_date?: string; end_date?: string } | number = 30, min_magnitude = 2.5) => {
    let payload = {};
    if (typeof options === 'number') {
      payload = { days_back: options, min_magnitude };
    } else {
      payload = options;
    }
    return apiFetch<{ status: string; message: string; action_id?: string }>('/api/admin/backfill', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  regenerateReport: async () =>
    apiFetch<{ status: string; message: string; action_id?: string }>('/api/admin/reports/regenerate', {
      method: 'POST',
    }),
};
