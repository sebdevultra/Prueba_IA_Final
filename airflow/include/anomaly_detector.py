"""
Módulo de Detección Analítica de Anomalías Sísmicas.
Combina Z-Score para picos temporales inusuales y DBSCAN con métrica Haversine
para identificar enjambres sísmicos espaciales (Spatial Swarms).
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def detect_seismic_anomalies(events: List[Dict[str, Any]] | pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detecta anomalías en la actividad sísmica:
    1. Pico temporal (Z-Score): Agrupa por hora y marca picos con Z > 2.5.
    2. Enjambre espacial (DBSCAN): Clústeres geográficos densos (50 km, min 5 sismos).

    Retorna lista de anomalías estructuradas.
    """
    if isinstance(events, list):
        if not events:
            return []
        df = pd.DataFrame(events)
    else:
        df = events.copy()

    if df.empty or "time_utc" not in df.columns or "latitude" not in df.columns:
        return []

    # Asegurar tipos correctos
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["mag"] = pd.to_numeric(df["mag"], errors="coerce").fillna(0.0)

    # Filtrar coordenadas nulas
    valid_geo_df = df.dropna(subset=["latitude", "longitude"]).copy()
    anomalies: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # 1. DETECCIÓN TEMPORAL CON Z-SCORE
    # --------------------------------------------------------------------------
    try:
        df["hour_bucket"] = df["time_utc"].dt.floor("h")
        hourly_counts = df.groupby("hour_bucket").size()

        if len(hourly_counts) >= 4:
            mean_count = hourly_counts.mean()
            std_count = hourly_counts.std()

            if std_count > 0:
                for hour, count in hourly_counts.items():
                    z_score = (count - mean_count) / std_count
                    if z_score > 2.5:
                        hour_events = df[df["hour_bucket"] == hour]
                        max_mag = float(hour_events["mag"].max())
                        top_event = hour_events.sort_values(by="mag", ascending=False).iloc[0]
                        region = str(top_event.get("place") or "Zona de alta sismicidad")
                        related_ids = [str(eid) for eid in hour_events["event_id"].tolist()]

                        anomalies.append({
                            "anomaly_id": str(uuid.uuid4()),
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                            "anomaly_type": "TEMPORAL_SPIKE",
                            "region": region,
                            "event_count": int(count),
                            "max_mag": max_mag,
                            "anomaly_score": round(float(z_score), 2),
                            "explanation": (
                                f"Pico temporal detectado en {hour.strftime('%Y-%m-%d %H:00 UTC')}: "
                                f"{count} sismos en 1 hora (promedio: {mean_count:.1f}, Z-Score: {z_score:.2f}). "
                                f"Magnitud máxima observada: {max_mag}."
                            ),
                            "related_event_ids": related_ids[:50],
                        })
    except Exception as exc:
        logger.warning("Error calculando Z-Score temporal: %s", exc)

    # --------------------------------------------------------------------------
    # 2. DETECCIÓN ESPACIAL CON DBSCAN (MÉTRICA HAVERSINE)
    # --------------------------------------------------------------------------
    try:
        if len(valid_geo_df) >= 5:
            # Radio de 50 km convertido a radianes (radio terrestre ~6371 km)
            earth_radius_km = 6371.0
            eps_rad = 50.0 / earth_radius_km
            min_samples = 5

            # DBSCAN con haversine requiere [lat_rad, lon_rad]
            coords_rad = np.radians(valid_geo_df[["latitude", "longitude"]].values)
            db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine")
            labels = db.fit_predict(coords_rad)

            valid_geo_df["cluster_label"] = labels
            unique_clusters = [lbl for lbl in set(labels) if lbl != -1]

            for cluster_id in unique_clusters:
                cluster_df = valid_geo_df[valid_geo_df["cluster_label"] == cluster_id]
                cluster_count = len(cluster_df)
                max_mag = float(cluster_df["mag"].max())
                top_event = cluster_df.sort_values(by="mag", ascending=False).iloc[0]
                region = str(top_event.get("place") or "Clúster sísmico localizado")
                density_score = round(cluster_count / 5.0, 2)
                related_ids = [str(eid) for eid in cluster_df["event_id"].tolist()]

                anomalies.append({
                    "anomaly_id": str(uuid.uuid4()),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "anomaly_type": "SPATIAL_SWARM",
                    "region": region,
                    "event_count": cluster_count,
                    "max_mag": max_mag,
                    "anomaly_score": density_score,
                    "explanation": (
                                f"Enjambre sísmico (DBSCAN) en radio de 50 km: {cluster_count} eventos concentrados. "
                                f"Magnitud máxima: {max_mag}. Epicentro representativo: {region}."
                    ),
                    "related_event_ids": related_ids[:50],
                })
    except Exception as exc:
        logger.warning("Error ejecutando DBSCAN espacial: %s", exc)

    logger.info("Detección de anomalías finalizada: %d anomalías identificadas", len(anomalies))
    return anomalies


def save_anomalies_to_curated(engine: Engine, anomalies: List[Dict[str, Any]]) -> int:
    """Persiste las anomalías identificadas en curated.seismic_anomalies."""
    if not anomalies:
        return 0

    stmt = text("""
        INSERT INTO curated.seismic_anomalies (
            anomaly_id, detected_at, anomaly_type, region,
            event_count, max_mag, anomaly_score, explanation, related_event_ids
        ) VALUES (
            CAST(:anomaly_id AS uuid), CAST(:detected_at AS timestamptz), :anomaly_type, :region,
            :event_count, :max_mag, :anomaly_score, :explanation, CAST(:related_event_ids AS jsonb)
        );
    """)

    params = []
    for a in anomalies:
        params.append({
            "anomaly_id": a.get("anomaly_id", str(uuid.uuid4())),
            "detected_at": a.get("detected_at", datetime.now(timezone.utc).isoformat()),
            "anomaly_type": a.get("anomaly_type", "UNKNOWN"),
            "region": a.get("region", "Global"),
            "event_count": a.get("event_count", 0),
            "max_mag": a.get("max_mag", 0.0),
            "anomaly_score": a.get("anomaly_score", 0.0),
            "explanation": a.get("explanation", ""),
            "related_event_ids": json.dumps(a.get("related_event_ids", [])),
        })

    with engine.begin() as conn:
        conn.execute(stmt, params)

    return len(params)
