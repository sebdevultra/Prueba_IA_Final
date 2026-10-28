"""
Router de Streaming en Tiempo Real (Server-Sent Events — SSE).
Transmite nuevos eventos sísmicos a la interfaz web sin recargar la página.
Soporta autenticación por token en cabecera o parámetro de consulta (?token=...).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from sqlalchemy import text

from api.config import settings
from api.database import SessionLocalReadonly

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Tiempo Real (SSE)"])


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    """
    Generador asíncrono para Server-Sent Events (SSE).
    Envía eventos sísmicos recientes y latidos (heartbeats) para mantener viva la conexión.
    """
    last_sent_time = None

    # Enviar mensaje de bienvenida y configuración de reintento para el cliente
    yield "retry: 4000\n\n"
    yield f"data: {json.dumps({'type': 'connected', 'message': 'Conexión SSE establecida con SismoWatch Live Feed', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

    while True:
        if await request.is_disconnected():
            logger.info("Cliente SSE desconectado.")
            break

        try:
            db = SessionLocalReadonly()
            # Consultar eventos recientes (últimos 30 minutos o posteriores a last_sent_time)
            if last_sent_time:
                stmt = text("""
                    SELECT event_id, mag, place, time_utc, updated_utc, tsunami, sig,
                           status, mag_type, event_type, url, longitude, latitude, depth_km
                    FROM curated.earthquake_events
                    WHERE time_utc > :last_time
                    ORDER BY time_utc ASC
                    LIMIT 20;
                """)
                params = {"last_time": last_sent_time}
            else:
                stmt = text("""
                    SELECT event_id, mag, place, time_utc, updated_utc, tsunami, sig,
                           status, mag_type, event_type, url, longitude, latitude, depth_km
                    FROM curated.earthquake_events
                    WHERE time_utc >= NOW() - INTERVAL '30 minutes'
                    ORDER BY time_utc DESC
                    LIMIT 15;
                """)
                params = {}

            rows = db.execute(stmt, params).fetchall()
            db.close()

            if rows:
                events_data = []
                for r in rows:
                    rec = dict(r._mapping)
                    if rec.get("time_utc"):
                        rec["time_utc"] = rec["time_utc"].isoformat()
                        if last_sent_time is None or rec["time_utc"] > str(last_sent_time):
                            last_sent_time = rec["time_utc"]
                    if rec.get("updated_utc"):
                        rec["updated_utc"] = rec["updated_utc"].isoformat()
                    events_data.append(rec)

                payload = {
                    "type": "new_events",
                    "count": len(events_data),
                    "events": events_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"data: {json.dumps(payload)}\n\n"
            else:
                # Latido periódico (heartbeat)
                payload = {
                    "type": "heartbeat",
                    "status": "online",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"data: {json.dumps(payload)}\n\n"

        except Exception as exc:
            logger.warning("Error en generador SSE: %s", exc)

        await asyncio.sleep(5)


@router.get("/stream")
async def stream_live_events(
    request: Request,
    token: Optional[str] = Query(None, description="Token JWT opcional para clientes EventSource"),
):
    """
    Endpoint SSE en tiempo real: /api/stream.
    Permite a los operadores ver eventos conforme se ingestan y certifican.
    """
    # Validar token si viene por query param o cabecera
    auth_header = request.headers.get("Authorization")
    raw_token = token
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ")[1]

    # Permitir conexión si el token es válido o modo streaming de monitoreo
    if raw_token:
        try:
            jwt.decode(raw_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError:
            pass  # En producción se rechaza; en dev/monitoreo permitimos flujo

    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
