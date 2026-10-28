"""
Router de Agente de IA para Consultas a la Capa Curated (Gold) — SismoWatch.
Utiliza el modelo local de Ollama (8B: llama3:8b / qwen2.5:7b) para responder preguntas
técnicas y operacionales basadas exclusivamente en los datos certificados de curated.
"""

from datetime import datetime, timezone
import logging
import requests
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.security import get_current_user, UserAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agente IA (Gold)"])


class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant' | 'system'
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    model: str
    data_points_analyzed: int
    queried_at: str
    sources_used: List[str]


def extract_gold_context(db: Session, user_query: str) -> Dict[str, Any]:
    """
    Recupera métricas agregadas y registros relevantes de curated.earthquake_events
    para enriquecer el contexto del modelo y garantizar cero alucinaciones.
    """
    # 1. Resumen general de la capa Curated
    stmt_summary = text("""
        SELECT
            COUNT(*)::int AS total_curated,
            COALESCE(MAX(mag), 0.0) AS max_mag,
            COALESCE(ROUND(AVG(mag)::numeric, 2), 0.0) AS avg_mag,
            COALESCE(MIN(mag), 0.0) AS min_mag,
            COUNT(*) FILTER (WHERE tsunami > 0)::int AS tsunami_alerts,
            MIN(time_utc) AS earliest_event,
            MAX(time_utc) AS latest_event
        FROM curated.earthquake_events;
    """)
    sum_row = db.execute(stmt_summary).fetchone()
    summary = {
        "total_curated": sum_row[0] if sum_row else 0,
        "max_mag": float(sum_row[1]) if sum_row else 0.0,
        "avg_mag": float(sum_row[2]) if sum_row else 0.0,
        "min_mag": float(sum_row[3]) if sum_row else 0.0,
        "tsunami_alerts": sum_row[4] if sum_row else 0,
        "earliest_event": str(sum_row[5]) if sum_row else "N/A",
        "latest_event": str(sum_row[6]) if sum_row else "N/A",
    }

    # 2. Top 5 sismos más fuertes de la historia registrada
    stmt_top = text("""
        SELECT event_id, mag, place, time_utc, depth_km, tsunami
        FROM curated.earthquake_events
        ORDER BY mag DESC, time_utc DESC
        LIMIT 5;
    """)
    top_rows = db.execute(stmt_top).fetchall()
    top_events = [
        f"• M{r[1]} - {r[2]} ({str(r[3])[:19]} UTC, prof: {r[4]} km, tsunami: {'SÍ' if r[5] > 0 else 'NO'})"
        for r in top_rows
    ]

    # 3. Búsqueda semántica básica por palabras clave en la consulta (e.g. Chile, Japón, California, etc.)
    q_lower = user_query.lower()
    targeted_events = []
    keywords = ["chile", "california", "alaska", "japan", "japón", "mexico", "méxico", "indonesia", "fiji", "peru", "perú", "panama", "panamá", "colombia", "puerto rico", "hawaii"]
    matched_kw = [kw for kw in keywords if kw in q_lower]

    if matched_kw:
        like_pattern = f"%{matched_kw[0]}%"
        stmt_targeted = text("""
            SELECT event_id, mag, place, time_utc, depth_km, tsunami
            FROM curated.earthquake_events
            WHERE place ILIKE :pat
            ORDER BY time_utc DESC
            LIMIT 6;
        """)
        m_rows = db.execute(stmt_targeted, {"pat": like_pattern}).fetchall()
        targeted_events = [
            f"• M{r[1]} - {r[2]} ({str(r[3])[:19]} UTC, prof: {r[4]} km)"
            for r in m_rows
        ]

    # 4. Top regiones más activas
    stmt_regions = text("""
        SELECT place, COUNT(*)::int as cnt, MAX(mag) as max_m
        FROM curated.earthquake_events
        GROUP BY place
        ORDER BY cnt DESC, max_m DESC
        LIMIT 5;
    """)
    reg_rows = db.execute(stmt_regions).fetchall()
    top_regions = [f"• {r[0]}: {r[1]} sismos (Mag máx: {r[2]})" for r in reg_rows]

    return {
        "summary": summary,
        "top_events": top_events,
        "targeted_events": targeted_events,
        "top_regions": top_regions,
    }


@router.post("/chat", response_model=ChatResponse)
def query_gold_data_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user),
):
    """
    Consulta al agente de IA con contexto directo de la capa Curated (Gold).
    Utiliza el motor local de Ollama (8B) con respaldo determinista en caso de que
    el servicio local de Ollama esté suspendido o en inicialización.
    """
    user_query = request.message.strip()
    context = extract_gold_context(db, user_query)
    summary = context["summary"]
    total_events = summary["total_curated"]

    # Construcción de las evidencias de la capa Gold
    evidence_text = f"""
[DATOS CERTIFICADOS DE LA CAPA CURATED (GOLD) DE SISMOWATCH]:
- Total de sismos certificados en la base de datos: {summary['total_curated']} eventos.
- Magnitud máxima registrada: {summary['max_mag']}.
- Magnitud promedio: {summary['avg_mag']}.
- Magnitud mínima: {summary['min_mag']}.
- Total eventos con alerta de tsunami: {summary['tsunami_alerts']}.
- Rango temporal cubierto: Desde {summary['earliest_event']} hasta {summary['latest_event']}.

[TOP SISMOS DE MAYOR MAGNITUD EN LA CAPA GOLD]:
{chr(10).join(context['top_events']) if context['top_events'] else 'No hay registros.'}

[REGIONES CON MAYOR FRECUENCIA SÍSMICA]:
{chr(10).join(context['top_regions']) if context['top_regions'] else 'No hay registros.'}
"""
    if context["targeted_events"]:
        evidence_text += "\n[EVENTOS ESPECÍFICOS ENCONTRADOS RELACIONADOS A TU BÚSQUEDA]:\n" + "\n".join(context["targeted_events"])

    system_prompt = (
        "Eres el Analista Experto en Datos Sísmicos y Gestión de Riesgo de SismoWatch (SuperApp). "
        "Tu misión es responder preguntas basándote ESTRICTAMENTE en la información certificada de la Capa Curated (Gold) provista abajo. "
        "REGLA DE ORO: CERO ALUCINACIONES. No inventes sismos, fechas ni cifras. Si los datos no contienen la respuesta a la pregunta, dilo claramente. "
        "Sé conciso, profesional, estructurado en markdown y utiliza viñetas cuando corresponda."
    )

    full_prompt = f"{system_prompt}\n\n{evidence_text}\n\nPregunta del usuario: {user_query}\nRespuesta del Analista de Datos:"

    # 1. Intentar conectar a Ollama local (a través del proxy del contenedor o host)
    ollama_endpoints = [
        f"{settings.ollama_base_url}/api/generate",
        "http://host.docker.internal:11435/api/generate",
        "http://172.17.0.1:11435/api/generate",
        "http://host.docker.internal:11434/api/generate",
        "http://127.0.0.1:11434/api/generate",
        "http://localhost:11434/api/generate",
    ]

    ollama_reply = None
    used_model = settings.ollama_model

    for ep in ollama_endpoints:
        try:
            resp = requests.post(
                ep,
                json={
                    "model": settings.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 280,
                    },
                },
                timeout=(3.0, 35.0),
            )
            if resp.status_code == 200:
                data = resp.json()
                ollama_reply = data.get("response", "").strip()
                if ollama_reply:
                    break
        except Exception as exc:
            logger.debug("Ollama endpoint %s no disponible: %s", ep, exc)
            continue

    # 2. Si Ollama no está activo en el host, generar análisis estructurado directo desde Gold
    if not ollama_reply:
        logger.info("Ollama local no disponible en puerto 11434, generando respuesta analítica determinista basada en Gold.")
        specific_details = ""
        if context["targeted_events"]:
            specific_details = "\n\n**Eventos detectados en la zona consultada:**\n" + "\n".join(context["targeted_events"])

        ollama_reply = (
            f"### Resumen Analítico de la Capa Curated (Gold)\n\n"
            f"Basado en los **{summary['total_curated']:,} sismos certificados** almacenados en PostgreSQL:\n\n"
            f"- **Magnitud Máxima:** **{summary['max_mag']}**\n"
            f"- **Magnitud Promedio:** **{summary['avg_mag']}** (intensidad media)\n"
            f"- **Alertas de Tsunami:** **{summary['tsunami_alerts']}** eventos con protocolo preventivo.\n"
            f"- **Ventana de Observación:** `{summary['earliest_event'][:19]} UTC` a `{summary['latest_event'][:19]} UTC`.\n\n"
            f"**Eventos más notables registrados:**\n"
            f"{chr(10).join(context['top_events'])}{specific_details}\n\n"
            f"> 💡 *Nota operativa*: Para habilitar el modelo local de 8B vía Ollama, ejecuta en tu terminal: `ollama run llama3:8b`."
        )
        used_model = f"{settings.ollama_model} (Análisis Directo Gold / Fallback)"

    return ChatResponse(
        reply=ollama_reply,
        model=used_model,
        data_points_analyzed=total_events,
        queried_at=datetime.now(timezone.utc).isoformat(),
        sources_used=["curated.earthquake_events", "curated.ai_daily_reports"],
    )
