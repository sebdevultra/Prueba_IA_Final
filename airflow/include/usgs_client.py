"""
Módulo de cliente HTTP para la API pública de USGS Earthquake Catalog.
Maneja timeouts, reintentos con retraso exponencial y excepciones estructuradas.
"""

import logging
import time
import requests

logger = logging.getLogger(__name__)

USGS_REALTIME_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


class USGSUnavailableError(Exception):
    """Excepción lanzada cuando el servicio de USGS no responde o retorna error."""
    pass


def fetch_realtime_hour(timeout: int = 15, max_retries: int = 3) -> dict:
    """
    Consulta el feed de sismos de la última hora en tiempo real de USGS:
    https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson

    Verifica HTTP 200 y presencia de la clave 'features' (list).
    Lanza USGSUnavailableError si hay timeout o respuesta errónea tras agotar reintentos.
    """
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Consultando feed USGS en tiempo real (intento %d/%d)...", attempt, max_retries)
            response = requests.get(
                USGS_REALTIME_URL,
                headers={"Accept": "application/json", "User-Agent": "SismoWatch/1.0"},
                timeout=timeout,
            )

            if response.status_code != 200:
                raise USGSUnavailableError(
                    f"USGS retornó código de estado HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            if not isinstance(data, dict) or "features" not in data or not isinstance(data["features"], list):
                raise USGSUnavailableError("Estructura de respuesta inválida: no contiene el arreglo 'features'")

            logger.info("Respuesta exitosa de USGS con %d eventos sísmicos", len(data["features"]))
            return data

        except (requests.RequestException, ValueError, USGSUnavailableError) as exc:
            last_exception = exc
            logger.warning("Fallo en intento %d al consultar USGS: %s", attempt, str(exc))
            if attempt < max_retries:
                backoff_wait = 2 ** attempt
                time.sleep(backoff_wait)

    raise USGSUnavailableError(f"USGS no disponible tras {max_retries} intentos: {str(last_exception)}") from last_exception


def fetch_historical_window(
    start_iso: str,
    end_iso: str,
    min_mag: float = 2.5,
    timeout: int = 30,
    max_retries: int = 3,
) -> dict:
    """
    Consulta el endpoint histórico de USGS por ventana de fechas (ISO YYYY-MM-DD o ISO8601)
    y magnitud mínima:
    https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=...&endtime=...&minmagnitude=...

    Lanza USGSUnavailableError si la consulta falla o excede el timeout.
    """
    params = {
        "format": "geojson",
        "starttime": start_iso,
        "endtime": end_iso,
        "minmagnitude": min_mag,
    }

    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Consultando ventana histórica USGS (%s a %s, min_mag=%s, intento %d/%d)...",
                start_iso, end_iso, min_mag, attempt, max_retries
            )
            response = requests.get(
                USGS_QUERY_URL,
                params=params,
                headers={"Accept": "application/json", "User-Agent": "SismoWatch/1.0"},
                timeout=timeout,
            )

            if response.status_code != 200:
                raise USGSUnavailableError(
                    f"USGS Query retornó código de estado HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            if not isinstance(data, dict) or "features" not in data or not isinstance(data["features"], list):
                raise USGSUnavailableError("Respuesta histórica de USGS sin arreglo 'features' válido")

            logger.info("Consulta histórica exitosa: %d eventos recuperados", len(data["features"]))
            return data

        except (requests.RequestException, ValueError, USGSUnavailableError) as exc:
            last_exception = exc
            logger.warning("Fallo en intento %d al consultar histórico USGS: %s", attempt, str(exc))
            if attempt < max_retries:
                backoff_wait = 2 ** attempt
                time.sleep(backoff_wait)

    raise USGSUnavailableError(
        f"USGS Histórico no disponible tras {max_retries} intentos: {str(last_exception)}"
    ) from last_exception
