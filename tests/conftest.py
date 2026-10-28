"""
Configuración global de Pytest para SismoWatch.
Define fixtures reutilizables para pruebas unitarias y de integración.
"""

import sys
from pathlib import Path
import pytest

# Asegurar que el directorio raíz del proyecto y api estén en sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))


@pytest.fixture
def sample_geojson_feature():
    """Retorna un feature GeoJSON sintético válido conforme al feed de USGS."""
    return {
        "type": "Feature",
        "id": "us7000m8v5",
        "properties": {
            "mag": 5.4,
            "place": "12 km SSW of Volcano, Hawaii",
            "time": 1729000000000,
            "updated": 1729003600000,
            "tz": None,
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000m8v5",
            "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/us7000m8v5.geojson",
            "felt": 45,
            "cdi": 4.1,
            "mmi": 5.2,
            "alert": "green",
            "status": "reviewed",
            "tsunami": 0,
            "sig": 448,
            "net": "us",
            "code": "7000m8v5",
            "ids": ",us7000m8v5,",
            "sources": ",us,",
            "types": ",moment-tensor,origin,phase-data,",
            "nst": 65,
            "dmin": 0.08,
            "rms": 0.42,
            "gap": 42.0,
            "magType": "mww",
            "type": "earthquake",
            "title": "M 5.4 - 12 km SSW of Volcano, Hawaii",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [-155.28, 19.34, 10.2],
        },
    }


@pytest.fixture
def sample_invalid_geojson_feature():
    """Retorna un feature GeoJSON con coordenadas corruptas y magnitud fuera de rango."""
    return {
        "type": "Feature",
        "id": "corrupt_event_001",
        "properties": {
            "mag": 15.8,  # Magnitud imposible (> 10.0)
            "place": "Unknown Region",
            "time": 1729000000000,
            "updated": 1729000000000,
            "tsunami": 0,
            "sig": 100,
            "status": "automatic",
            "magType": "ml",
            "type": "earthquake",
            "url": None,
        },
        "geometry": {
            "type": "Point",
            "coordinates": [250.0, 120.0, -50.0],  # Latitud > 90, Longitud > 180, Profundidad < -10
        },
    }
