"""
Router de Reportes Ejecutivos de IA y Exportaciones (CSV / HTML / PDF).
"""

import csv
import io
from typing import List
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import DailyReportResponse
from api.security import get_current_user, get_current_user_flexible, UserAuth

router = APIRouter(prefix="/api/reports", tags=["Reportes Ejecutivos"])


@router.get("", response_model=List[DailyReportResponse])
def get_daily_reports(
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user),
):
    """
    Retorna el historial de reportes diarios ejecutivos generados por IA.
    """
    stmt = text("""
        SELECT report_id, report_date, headline, executive_summary,
               most_active_zones, notable_events, computed_metrics, is_fallback, created_at
        FROM curated.ai_daily_reports
        ORDER BY report_date DESC
        LIMIT :limit;
    """)
    rows = db.execute(stmt, {"limit": limit}).fetchall()

    reports = []
    for r in rows:
        reports.append(DailyReportResponse(
            report_id=str(r[0]),
            report_date=r[1],
            headline=r[2],
            executive_summary=r[3],
            most_active_zones=r[4] if isinstance(r[4], list) else [],
            notable_events=r[5] if isinstance(r[5], list) else [],
            computed_metrics=r[6] if isinstance(r[6], dict) else {},
            is_fallback=bool(r[7]),
            created_at=r[8],
        ))

    return reports


@router.get("/export")
def export_data(
    export_type: str = Query("events", description="Tipo de exportación: events o reports"),
    format: str = Query("csv", description="Formato: csv, html o pdf"),
    db: Session = Depends(get_db),
    _current_user: UserAuth = Depends(get_current_user_flexible),
):
    """
    Exporta datos en formato CSV, HTML o PDF.
    """
    if export_type == "events":
        stmt = text("""
            SELECT event_id, mag, place, time_utc, tsunami, sig, status, longitude, latitude, depth_km
            FROM curated.earthquake_events
            ORDER BY time_utc DESC
            LIMIT 500;
        """)
        rows = db.execute(stmt).fetchall()

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["event_id", "mag", "place", "time_utc", "tsunami", "sig", "status", "longitude", "latitude", "depth_km"])
            for r in rows:
                writer.writerow(list(r))
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=sismowatch_events_export.csv"},
            )

        elif format in ["html", "pdf"]:
            # Generar HTML imprimible / descargable con estilo premium
            rows_html = "".join([
                f"<tr><td>{r[0]}</td><td><strong>{r[1]}</strong></td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[7]}, {r[8]}</td><td>{r[9]} km</td></tr>"
                for r in rows
            ])
            html_content = f"""<!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>SismoWatch — Exportación Oficial</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 30px; }}
                    h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 10px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
                    th, td {{ border: 1px solid #334155; padding: 10px; text-align: left; }}
                    th {{ background-color: #1e293b; color: #94a3b8; text-transform: uppercase; font-size: 11px; }}
                    tr:nth-child(even) {{ background-color: #1e293b55; }}
                </style>
            </head>
            <body>
                <h1>SismoWatch — Reporte Certificado de Eventos Sísmicos</h1>
                <p>Fecha de emisión: {rows[0][3] if rows else 'N/A'} | Registros exportados: {len(rows)}</p>
                <table>
                    <thead>
                        <tr><th>ID</th><th>Mag</th><th>Ubicación</th><th>Fecha UTC</th><th>Tsunami</th><th>Coordenadas</th><th>Profundidad</th></tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </body>
            </html>"""
            return Response(
                content=html_content,
                media_type="text/html",
                headers={"Content-Disposition": "attachment; filename=sismowatch_report.html"},
            )

    raise HTTPException(status_code=400, detail="Tipo de exportación no soportado")
