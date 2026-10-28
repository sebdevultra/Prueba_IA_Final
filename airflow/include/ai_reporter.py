"""
Módulo de Automatización con IA para Reportes Ejecutivos Diarios de SismoWatch.
Incluye:
- Sanitización de texto contra Prompt Injection (OWASP LLM01).
- Generación de Structured Outputs con Google Gemini.
- Verificación numérica programática contra métricas precalculadas.
- Plan alterno (Fallback) determinista basado en Jinja2 si la IA falla o se agota el tiempo.
- Registro de observabilidad: tokens, latencia y costo estimado en curated.ai_execution_logs.
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from jinja2 import Template
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

PROMPT_FILE_PATH = Path(__file__).parent / "prompts" / "daily_executive_report_v1.txt"
PROMPT_VERSION = "v1.0.0"


class NotableEventItem(BaseModel):
    event_id: str
    place: str
    mag: float
    severity: str = "MEDIA"


class ComputedMetricsItem(BaseModel):
    total_events: int
    max_mag: float
    avg_mag: float
    tsunami_count: int


class DailyReportSchema(BaseModel):
    headline: str = Field(description="Titular ejecutivo conciso de la jornada")
    executive_summary: str = Field(description="Resumen formal de la actividad sísmica")
    most_active_zones: List[str] = Field(default_factory=list, description="Regiones más activas")
    notable_events: List[NotableEventItem] = Field(default_factory=list, description="Eventos destacados")
    computed_metrics: ComputedMetricsItem = Field(description="Métricas calculadas preverificadas")


def sanitize_place_text(text_val: Optional[str]) -> str:
    """
    Mitiga inyecciones de instrucciones (OWASP LLM01 - Prompt Injection).
    Elimina caracteres especiales no alfanuméricos ni de puntuación básica geográfica
    y acota la longitud máxima a 120 caracteres.
    """
    if not text_val:
        return "Ubicación no especificada"
    cleaned = re.sub(r"[^\w\s,.\-/()]", "", str(text_val))
    return cleaned.strip()[:120]


def render_prompt_template(
    metrics: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    notable_events: List[Dict[str, Any]],
) -> str:
    """Carga y renderiza el prompt v1 con Jinja2."""
    if not PROMPT_FILE_PATH.exists():
        raw_prompt = """
        Genera un informe ejecutivo para SismoWatch.
        Total sismos: {{ total_events }}, Mag Máx: {{ max_mag }}, Promedio: {{ avg_mag }}.
        """
    else:
        raw_prompt = PROMPT_FILE_PATH.read_text(encoding="utf-8")

    template = Template(raw_prompt)
    return template.render(
        total_events=metrics.get("total_events", 0),
        max_mag=metrics.get("max_mag", 0.0),
        avg_mag=metrics.get("avg_mag", 0.0),
        tsunami_count=metrics.get("tsunami_count", 0),
        earliest_time=metrics.get("earliest_time", ""),
        latest_time=metrics.get("latest_time", ""),
        anomalies=anomalies,
        notable_events=notable_events,
    )


def generate_deterministic_fallback(
    metrics: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    notable_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Plan alterno determinista (Fallback): Genera el reporte ejecutivo completo sin LLM
    cuando la API de IA no está configurada, excede el tiempo o genera cifras desfasadas.
    """
    total = metrics.get("total_events", 0)
    max_m = metrics.get("max_mag", 0.0)
    avg_m = metrics.get("avg_mag", 0.0)
    tsunami = metrics.get("tsunami_count", 0)

    # Identificar zonas más activas a partir de notables
    zones = []
    seen_places = set()
    for ev in notable_events:
        pl = ev.get("place", "Región general")
        if pl not in seen_places:
            seen_places.add(pl)
            zones.append(f"{pl} (Mag {ev.get('mag', 0.0)})")
        if len(zones) >= 4:
            break

    if not zones:
        zones = ["Monitoreo global continuo sin concentraciones críticas"]

    # Titular según severidad
    if max_m >= 6.0:
        headline = f"Alerta Sísmica: Registro de Evento Mayor M{max_m} en las últimas 24 Horas"
    elif max_m >= 4.5:
        headline = f"Monitoreo Sísmico Moderado: M{max_m} con {total} eventos monitoreados"
    else:
        headline = f"Estabilidad Sísmica Global: Actividad de baja intensidad ({total} eventos)"

    tsunami_note = f" Se emitieron {tsunami} alertas preventivas de tsunami." if tsunami > 0 else " No se registraron alertas de tsunami."
    anom_note = f" Se identificaron {len(anomalies)} agrupaciones o enjambres sísmicos por el motor analítico." if anomalies else " No se detectaron enjambres anómalos significativos."

    summary = (
        f"Durante el período de monitoreo de 24 horas se registraron un total de {total} eventos sísmicos válidos "
        f"a nivel global, con una magnitud promedio de {avg_m:.2f} y un pico máximo de {max_m:.1f}.{tsunami_note}{anom_note} "
        f"Las operaciones de SuperApp se mantienen en estado normal con seguimiento focalizado en zonas de subducción activas."
    )

    clean_notables = []
    for ev in notable_events[:5]:
        m = ev.get("mag", 0.0)
        sev = "ALTA" if m >= 5.5 else ("MEDIA" if m >= 4.0 else "BAJA")
        clean_notables.append({
            "event_id": str(ev.get("event_id")),
            "place": str(ev.get("place")),
            "mag": float(m),
            "severity": sev,
        })

    return {
        "headline": headline[:120],
        "executive_summary": summary,
        "most_active_zones": zones,
        "notable_events": clean_notables,
        "computed_metrics": {
            "total_events": total,
            "max_mag": max_m,
            "avg_mag": avg_m,
            "tsunami_count": tsunami,
        },
        "is_fallback": True,
    }


def call_gemini_api(prompt_text: str, api_key: str) -> Tuple[Dict[str, Any], int, int, int, str]:
    """
    Invoca la API de Google Gemini con structured outputs en formato JSON.
    Intenta con los modelos disponibles (gemini-3.5-flash, gemini-2.5-flash-lite, etc.).
    Retorna (parsed_dict, input_tokens, output_tokens, latency_ms, used_model).
    """
    import requests

    start_time = time.time()
    env_model = os.getenv("GEMINI_MODEL", "").strip()
    candidate_models = [env_model] if env_model else ["gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-1.5-flash"]
    candidate_models = [m for m in candidate_models if m]

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    last_error = None
    data = {}
    used_model = "gemini-3.5-flash"

    for model in candidate_models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=25,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("candidates"):
                    used_model = model
                    last_error = None
                    break
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as e:
            last_error = str(e)

    latency_ms = int((time.time() - start_time) * 1000)

    # Extraer contenido y tokens de uso
    usage = data.get("usageMetadata", {})
    input_tokens = usage.get("promptTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0)

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini retornó sin candidatos de respuesta. Detalle: {last_error}")

    content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}").strip()
    if content_text.startswith("```"):
        content_text = re.sub(r"^```(?:json)?\s*", "", content_text)
        content_text = re.sub(r"\s*```$", "", content_text)

    parsed_json = json.loads(content_text)

    return parsed_json, input_tokens, output_tokens, latency_ms, used_model


def generate_daily_report(
    metrics: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Genera el reporte ejecutivo diario:
    1. Sanitiza los lugares de eventos notables para prevenir Prompt Injection.
    2. Si existe GEMINI_API_KEY, invoca a Gemini.
    3. Valida la respuesta con Pydantic y comprueba que las cifras coincidan.
    4. Si falla cualquier paso, conmuta al fallback determinista.
    5. Retorna (report_dict, execution_log_dict).
    """
    # Preparar eventos notables sanitizados (Top 5 por magnitud)
    sorted_events = sorted(events, key=lambda x: x.get("mag") or 0.0, reverse=True)
    notable_events = []
    for ev in sorted_events[:5]:
        notable_events.append({
            "event_id": str(ev.get("event_id") or ""),
            "place": sanitize_place_text(ev.get("place")),
            "mag": float(ev.get("mag") or 0.0),
            "depth_km": float(ev.get("depth_km") or 0.0),
            "tsunami": int(ev.get("tsunami") or 0),
        })

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    is_fallback = True
    error_msg = None
    input_tokens = 0
    output_tokens = 0
    latency_ms = 0
    cost_usd = 0.0
    active_model = "gemini-3.5-flash"
    report_dict: Dict[str, Any] = {}

    if api_key:
        try:
            prompt_text = render_prompt_template(metrics, anomalies, notable_events)
            raw_result, in_tok, out_tok, lat, active_model = call_gemini_api(prompt_text, api_key)
            input_tokens = in_tok
            output_tokens = out_tok
            latency_ms = lat

            # Costo aproximado Gemini Flash
            cost_usd = (in_tok * 0.000000075) + (out_tok * 0.0000003)

            # Validación de esquema con Pydantic
            validated = DailyReportSchema.model_validate(raw_result)

            # Verificación programática de cifras calculadas
            exp_total = metrics.get("total_events", 0)
            exp_max_mag = metrics.get("max_mag", 0.0)
            rep_total = validated.computed_metrics.total_events
            rep_max = validated.computed_metrics.max_mag

            if rep_total != exp_total or abs(rep_max - exp_max_mag) > 0.1:
                raise ValueError(
                    f"Discrepancia numérica en LLM: esperados total={exp_total}, max={exp_max_mag}; "
                    f"recibidos total={rep_total}, max={rep_max}"
                )

            report_dict = validated.model_dump()
            report_dict["is_fallback"] = False
            is_fallback = False
            logger.info("Reporte generado exitosamente con Gemini API (%s, latencia: %d ms)", active_model, latency_ms)

        except Exception as exc:
            error_msg = f"Error en generación LLM: {str(exc)}"
            logger.warning("%s. Conmutando a plantilla determinista.", error_msg)

    # Si no hay API key o hubo error, activar fallback determinista
    if is_fallback:
        fallback_data = generate_deterministic_fallback(metrics, anomalies, notable_events)
        report_dict = fallback_data
        report_dict["is_fallback"] = True
        if not error_msg:
            error_msg = "GEMINI_API_KEY no configurada; ejecutado mediante fallback determinista Jinja2."

    log_dict = {
        "log_id": str(uuid.uuid4()),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model_name": active_model if not is_fallback else "deterministic_jinja2_fallback",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "estimated_cost_usd": round(cost_usd, 6),
        "validation_passed": not is_fallback,
        "error_message": error_msg,
    }

    return report_dict, log_dict


def save_daily_report_to_curated(
    engine: Engine,
    report_dict: Dict[str, Any],
    log_dict: Dict[str, Any],
    report_date: Optional[date] = None,
) -> str:
    """Persiste el reporte y el log de auditoría en la capa Gold."""
    if report_date is None:
        report_date = date.today()

    report_id = str(uuid.uuid4())

    stmt_report = text("""
        INSERT INTO curated.ai_daily_reports (
            report_id, report_date, headline, executive_summary,
            most_active_zones, notable_events, computed_metrics, is_fallback, created_at
        ) VALUES (
            CAST(:report_id AS uuid), :report_date, :headline, :executive_summary,
            CAST(:most_active_zones AS jsonb), CAST(:notable_events AS jsonb),
            CAST(:computed_metrics AS jsonb), :is_fallback, NOW()
        )
        ON CONFLICT (report_date) DO UPDATE
        SET headline = EXCLUDED.headline,
            executive_summary = EXCLUDED.executive_summary,
            most_active_zones = EXCLUDED.most_active_zones,
            notable_events = EXCLUDED.notable_events,
            computed_metrics = EXCLUDED.computed_metrics,
            is_fallback = EXCLUDED.is_fallback,
            created_at = NOW();
    """)

    stmt_log = text("""
        INSERT INTO curated.ai_execution_logs (
            log_id, executed_at, prompt_version, model_name,
            input_tokens, output_tokens, latency_ms, estimated_cost_usd,
            validation_passed, error_message
        ) VALUES (
            CAST(:log_id AS uuid), CAST(:executed_at AS timestamptz), :prompt_version, :model_name,
            :input_tokens, :output_tokens, :latency_ms, :estimated_cost_usd,
            :validation_passed, :error_message
        );
    """)

    with engine.begin() as conn:
        conn.execute(stmt_report, {
            "report_id": report_id,
            "report_date": report_date,
            "headline": report_dict.get("headline", ""),
            "executive_summary": report_dict.get("executive_summary", ""),
            "most_active_zones": json.dumps(report_dict.get("most_active_zones", [])),
            "notable_events": json.dumps(report_dict.get("notable_events", [])),
            "computed_metrics": json.dumps(report_dict.get("computed_metrics", {})),
            "is_fallback": bool(report_dict.get("is_fallback", False)),
        })

        conn.execute(stmt_log, {
            "log_id": log_dict.get("log_id", str(uuid.uuid4())),
            "executed_at": log_dict.get("executed_at", datetime.now(timezone.utc).isoformat()),
            "prompt_version": log_dict.get("prompt_version", PROMPT_VERSION),
            "model_name": log_dict.get("model_name", "fallback"),
            "input_tokens": log_dict.get("input_tokens", 0),
            "output_tokens": log_dict.get("output_tokens", 0),
            "latency_ms": log_dict.get("latency_ms", 0),
            "estimated_cost_usd": log_dict.get("estimated_cost_usd", 0.0),
            "validation_passed": bool(log_dict.get("validation_passed", False)),
            "error_message": log_dict.get("error_message"),
        })

    logger.info("Reporte y log de IA guardados para la fecha %s", str(report_date))
    return report_id
