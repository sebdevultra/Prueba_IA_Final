"""
Esquemas Pydantic para validación de entradas y respuestas de la API SismoWatch.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Autenticación ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserProfileResponse(BaseModel):
    username: str
    role: str


# --- KPIs del Dashboard ---
class KpiResponse(BaseModel):
    events_24h: int
    max_magnitude: float
    avg_magnitude: float
    tsunami_count: int
    quality_score: float
    last_update_utc: Optional[str] = None
    freshness_ok: bool = True


# --- Eventos Sísmicos ---
class EarthquakeEventSchema(BaseModel):
    event_id: str
    mag: Optional[float] = None
    place: Optional[str] = None
    time_utc: Optional[datetime] = None
    updated_utc: Optional[datetime] = None
    tsunami: int = 0
    sig: Optional[int] = None
    status: Optional[str] = None
    mag_type: Optional[str] = None
    event_type: Optional[str] = None
    url: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    depth_km: Optional[float] = None


class EventsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    events: List[EarthquakeEventSchema]


# --- Series Temporales para Gráficos ---
class TimeseriesPoint(BaseModel):
    hour: str
    event_count: int
    avg_mag: float
    max_mag: float


class TimeseriesResponse(BaseModel):
    points: List[TimeseriesPoint]
    distribution_by_magnitude: Dict[str, int]
    top_active_regions: List[Dict[str, Any]]


# --- Reportes Ejecutivos de IA ---
class DailyReportResponse(BaseModel):
    report_id: str
    report_date: date
    headline: str
    executive_summary: str
    most_active_zones: List[str]
    notable_events: List[Dict[str, Any]]
    computed_metrics: Dict[str, Any]
    is_fallback: bool
    created_at: datetime


# --- Estado del Pipeline y Calidad ---
class DataQualityRunSchema(BaseModel):
    run_id: str
    dag_run_id: Optional[str] = None
    evaluated_at: datetime
    total_records: int
    valid_records: int
    invalid_records: int
    freshness_ok: bool
    volume_ok: bool
    quality_score: float
    rule_breakdown: Dict[str, Any]


class PipelineStatusResponse(BaseModel):
    airflow_online: bool
    dags_status: List[Dict[str, Any]]
    last_quality_run: Optional[DataQualityRunSchema] = None
    database_status: str = "connected"


# --- Solicitudes de Administración ---
class BackfillRequest(BaseModel):
    days_back: Optional[int] = Field(default=30, ge=1, le=90)
    min_magnitude: float = Field(default=2.5, ge=0.0, le=10.0)
    start_date: Optional[str] = Field(default=None, description="Fecha de inicio (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="Fecha de fin (YYYY-MM-DD)")


class ActionStatusResponse(BaseModel):
    status: str
    message: str
    action_id: Optional[str] = None

