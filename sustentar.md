```bash
cp .env.example .env && \
python3 -m venv .venv && \
source .venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt && \
pytest tests && \
mkdir -p airflow/logs && chmod -R 777 airflow/logs && \
docker compose up -d --build
```

*Servicios orquestados:*
1. `sismowatch_postgres`: PostgreSQL 16 con esquemas Medallion (`raw`, `staging`, `curated`).
2. `sismowatch_airflow_init`: Ejecuta migraciones y crea el usuario admin.
3. `sismowatch_airflow_webserver`: Servidor web de Airflow (puerto 8080).
4. `sismowatch_airflow_scheduler`: Planificador y ejecutor de tareas.
5. `sismowatch_api`: Backend FastAPI con JWT, SSE y agente IA (puerto 8000).
6. `sismowatch_web`: Frontend React + Vite con mapas y dashboard (puerto 3000).

---

#### Paso 8: Verificación del estado y salud de los servicios

1. **Estado general de contenedores:**
   ```bash
   docker compose ps
   ```
2. **Probar salud del Backend (FastAPI):**
   ```bash
   curl -s http://localhost:8000/health
   # Retorna: {"status":"healthy","service":"sismowatch_api","version":"1.0.0"}
   ```
3. **Probar salud del Scheduler y Metadata de Airflow:**
   ```bash
   curl -s http://localhost:8080/health
   # Retorna: {"metadatabase":{"status":"healthy"},"scheduler":{"status":"healthy"}}
   ```
4. **Probar Frontend React:**
   ```bash
   curl -s -I http://localhost:3000
   # Retorna: HTTP/1.1 200 OK
   ```

---

### Puertos y Credenciales de Acceso

| Servicio | URL Local | Credenciales por Defecto |
| :--- | :--- | :--- |
| **Plataforma Web (React)** | [http://localhost:3000](http://localhost:3000) | `admin` / `AdminSismo2026!` (Admin)<br/>`viewer` / `ViewerSismo2026!` (Viewer) |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Autenticación Bearer vía `/auth/login` |
| **Airflow UI** | [http://localhost:8080](http://localhost:8080) | `admin` / `AdminAirflow2026!` |
| **PostgreSQL (Host)** | `localhost:5435` | `postgres` / `postgres_master_secret` |

---

### Comandos de Utilidad Adicional

- **Ver logs en tiempo real de un servicio específico:**
  ```bash
  docker compose logs -f api
  docker compose logs -f airflow-scheduler
  docker compose logs -f web
  ```
- **Detener el sistema completo:**
  ```bash
  docker compose down
  ```
- **Reiniciar un servicio específico (ejemplo, backend API):**
  ```bash
  docker compose restart api
  ```
  A continuación se detalla la lista clasificada de todas las **herramientas, tecnologías, frameworks y librerías** utilizadas en la arquitectura de **SismoWatch**, agrupadas por su rol en el sistema:

---

### 1. Infraestructura, Virtualización y Base de Datos
- **Docker y Docker Compose (v2)**: Orquestación multi-contenedor del ecosistema completo (6 microservicios comunicados a través de una red bridge dedicada).
- **PostgreSQL 16**: Motor de base de datos relacional central (`sismowatch_db`), estructurado bajo la arquitectura Medallion (`raw`, `staging`, `curated`) con segregación estricta de roles (`role_ingest`, `role_transform`, `role_readonly`).
- **Alpine Linux / Debian Slim**: Imágenes base ligeras y seguras para los contenedores (`postgres:16-alpine`, `node:20-alpine`, `python:3.12-slim`).

---

### 2. Orquestación y Pipelines de Datos (Data Engineering)
- **Apache Airflow (2.8+ / 2.11)**: Orquestador central de flujo de datos con `LocalExecutor`:
  - **TaskFlow API (`@dag`, `@task`)**: Paradigma moderno de definición de tareas con tipado Python.
  - **Airflow Datasets**: Disparadores reactivos basados en datos (`Dataset("postgres://...")`) para encadenar la transformación inmediatamente después de la ingesta.
  - **Callbacks Operacionales (`on_failure_callback`)**: Registro de alertas y trazabilidad ante caídas de red o fallas de validación.

---

### 3. Backend, APIs y Streaming en Tiempo Real
- **FastAPI (0.109+)**: Framework web ASGI de alto rendimiento para el backend analítico y de consumo.
- **Uvicorn**: Servidor ASGI con soporte para recarga en caliente (`--reload`).
- **Server-Sent Events (SSE)**: Protocolo de transmisión unidireccional en tiempo real (`/api/stream`) para telemetría sísmica y latidos (*heartbeats*) con reconexión nativa (`retry: 4000`).
- **SQLAlchemy (1.4+ / 2.0)**: Capa de abstracción relacional (Core / ORM) y pooling de conexiones para transacciones seguras.
- **Psycopg2-binary**: Driver nativo de conexión en Python para PostgreSQL.
- **Pydantic (v2) y Pydantic Settings**: Validación estricta de tipos de datos, serialización JSON y gestión tipada de variables de entorno desde `.env`.

---

### 4. Seguridad, Autenticación y Criptografía
- **JSON Web Tokens (JWT) con `python-jose`**: Autenticación Bearer desacoplada mediante firmas seguras con algoritmo `HS256`.
- **Passlib y Bcrypt**: Haseo y verificación unidireccional de contraseñas.
- **RBAC (Role-Based Access Control)**: Control de acceso basado en roles (`admin` con privilegios de backfill/regeneración y `viewer` con solo lectura).
- **CORS Middleware**: Control de orígenes cruzados para la comunicación API-Frontend.
- **Bandit**: Herramienta de escaneo estático de seguridad (AST) para certificar cero vulnerabilidades y cero credenciales expuestas.

---

### 5. Frontend y Visualización Geoespacial
- **React (18.2)**: Librería declarativa para la interfaz de usuario en componentes desacoplados.
- **TypeScript**: Tipado estático estricto en todo el código frontend para prevenir errores en tiempo de ejecución.
- **Vite**: Herramienta de empaquetado y servidor de desarrollo con Hot Module Replacement (HMR).
- **Leaflet y React-Leaflet**: Motor de mapas interactivos geoespaciales para la renderización de epicentros sísmicos con código de color según magnitud y profundidad.
- **Lucide React**: Conjunto de iconos vectoriales SVG para la interfaz.
- **Vanilla CSS (Glassmorphism & Dark Mode)**: Sistema de diseño personalizado con estética oscura, gradientes sutiles y micro-animaciones sin sobrecarga de frameworks externos pesados.

---

### 6. Inteligencia Artificial, Machine Learning y Analítica
- **Google Gemini API (`gemini-3.5-flash` / `gemini-2.5-flash-lite`)**: Modelo generativo multimodal utilizado con **Structured Outputs (JSON)** para la redacción de reportes ejecutivos diarios sin alucinaciones numéricas.
- **Ollama (`llama3:8b`)**: Modelo de lenguaje local de 8 mil millones de parámetros para el **Agente IA (Gold)**, permitiendo consultas en lenguaje natural directamente sobre la capa certificada sin dependencias de la nube.
- **Scikit-Learn**:
  - **DBSCAN (Density-Based Spatial Clustering)**: Algoritmo de agrupación no supervisada con métrica espacial de Haversine para detectar enjambres sísmicos (`SPATIAL_SWARM`).
- **NumPy y SciPy**: Cálculo del estadístico **Z-Score** sobre agrupaciones horarias para identificar picos temporales inusuales (`TEMPORAL_SPIKE`).
- **Pandas**: Manipulación, normalización tabular y agregaciones de métricas sísmicas.
- **Jinja2**: Motor de plantillas utilizado para:
  1. Renderizado seguro de prompts con sanitización contra *Prompt Injection* (OWASP LLM01).
  2. Plan alterno determinista (*Fallback*) si el LLM excede el tiempo o genera discrepancias.
- **ReportLab**: Librería para la compilación y exportación de reportes ejecutivos en formato **PDF**.

---

### 7. Testing, Aseguramiento de Calidad y Linter
- **Pytest**: Suite automatizada con **21 pruebas unitarias e integración** (`test_api_rbac.py`, `test_dag_integrity.py`, `test_quality_rules.py`, `test_transformations.py`).
- **HTTPX y Requests**: Clientes HTTP para pruebas de integración contra endpoints protegidos y consumo de APIs externas.
- **Ruff**: Linter y formateador ultrarrápido de código Python.

---

Viewed SKILL.md:1-439
Listed directory sismowatch_entrega
Viewed README.md:1-150
Viewed docker-compose.yml:1-150
Listed directory airflow
Listed directory dags
Listed directory include
Listed directory init
Listed directory docs
Viewed sustentar.md:1-72
Viewed ARQUITECTURA.md:1-160
Viewed ARQUITECTURA.md:160-213
Searched for "minio"
Viewed CHANGELOG.md:1-60
Viewed dag_usgs_ingest_realtime.py:1-60
Viewed dag_usgs_ingest_realtime.py:60-105

Evaluar la adopción de **MinIO** (servidor de almacenamiento de objetos compatible con Amazon S3) en **SismoWatch** requiere balancear dos factores: la **viabilidad técnica** (completamente alcanzable) y la **justificación arquitectónica de negocio** frente a la solución actual documentada en [docs/ARQUITECTURA.md](file:///home/Coder/Escritorio/sismowatch_entrega/docs/ARQUITECTURA.md).

---

### 1. Dictamen Ejecutivo de Viabilidad

| Dimensión | Nivel | Diagnóstico |
| :--- | :--- | :--- |
| **Viabilidad Técnica** | **100% (ALTA)** | MinIO se orquesta trivialmente en Docker, se integra con Apache Airflow mediante `apache-airflow-providers-amazon` o `boto3`, y cuenta con SDK nativo en Python. |
| **Viabilidad Operativa** | **MEDIA** | Añade un contenedor adicional (~250-400 MB de RAM), gestión de buckets, credenciales S3 y puertos adicionales (`9000` y `9001`). |
| **Justificación de Negocio** | **HÍBRIDA** | Para la volumetría de USGS (~50 a 300 eventos cada 5 min; ~2.000 eventos/mes), PostgreSQL con `JSONB` resuelve Bronze sin sobrecosto de red. Sin embargo, MinIO es **altamente viable y recomendado** como almacén inmutable de auditoría (Data Lake landing), repositorio de artefactos/reportes y backups. |

---

### 2. Comparativa de Trade-offs: PostgreSQL Medallion vs. MinIO

| Criterio | Arquitectura Actual (Postgres JSONB) | Con MinIO como Capa Bronze |
| :--- | :--- | :--- |
| **Garantías Transaccionales** | ACID completa. `ON CONFLICT DO UPDATE` atómico. | Consistencia eventual. Sobrescritura de objetos por clave S3. |
| **Latencia de Ingesta** | Submilimétrica (< 15 ms por lote de sismos). | 40-120 ms (overhead de HTTP multipart y roundtrip de red S3). |
| **Consultabilidad Inmediata** | Directa con sintaxis SQL nativa (`raw_payload->'properties'`). | Requiere descargar el objeto o emplear un motor federado (DuckDB/Trino). |
| **Costos de Almacenamiento a Escala** | El almacenamiento en bloque/SSD de BD es costoso si se retienen años de GeoJSON crudos. | Muy eficiente; almacenamiento de objetos desacoplado del cómputo. |
| **Seguridad y Permisos** | RBAC nativo por esquemas (`role_ingest`, `role_transform`). | Políticas IAM / S3 Bucket Policies + Access Keys. |
| **Footprint de Memoria en Docker** | 0 MB extra (aprovecha la misma instancia Postgres). | +250 MB a 400 MB de RAM para el daemon MinIO + Console. |

---

### 3. Casos de Uso Concretos donde MinIO SÍ aporta Valor a SismoWatch

Si decides incorporar MinIO, los siguientes escenarios aportan valor real sin desestabilizar la plataforma:

#### A. Data Lake Inmutable (Bronze Puro como archivos GeoJSON particionados)
En lugar de depender exclusivamente de la tabla `raw.earthquake_events_raw`, el DAG de ingesta [dag_usgs_ingest_realtime.py](file:///home/Coder/Escritorio/sismowatch_entrega/airflow/dags/dag_usgs_ingest_realtime.py) guarda el payload HTTP original como un archivo inmutable:
- `s3://sismowatch-bronze/usgs/year=2026/month=10/day=28/feed_120000.json.gz`
- **Ventaja**: Auditoría forense exacta sin inflar la base de datos relacional y permitiendo reprocesar cualquier ventana de tiempo histórica en el futuro.

#### B. Repositorio de Artefactos y Reportes Ejecutivos (Gold Artifacts)
Actualmente, el DAG de IA [dag_ai_daily_report_and_anomalies.py](file:///home/Coder/Escritorio/sismowatch_entrega/airflow/dags/dag_ai_daily_report_and_anomalies.py) almacena los reportes en la tabla `curated.ai_daily_reports`.
- Con MinIO, se pueden compilar y almacenar versiones descargables en PDF, Markdown o CSV consolidados:
  - `s3://sismowatch-artifacts/reports/2026-10-28_informe_riesgo.pdf`
  - `s3://sismowatch-artifacts/anomalies/clusters_dbscan_20261028.png`
- La API de FastAPI puede entregar URLs prefirmadas (`presigned URLs`) temporales para descarga directa desde el frontend.

#### C. Bóveda de Backups Automatizados de PostgreSQL
Un DAG programado de Airflow o un cron de mantenimiento puede ejecutar `pg_dump` de `sismowatch_db` y subir el archivo comprimido a `s3://sismowatch-backups/db/sismowatch_db_20261028.sql.gz` con ciclo de vida (retención de 30 días).

---

### 4. Blueprint Técnico de Integración

Para habilitar MinIO en el ecosistema actual, los cambios requeridos son:

#### 1. Servicio en [docker-compose.yml](file:///home/Coder/Escritorio/sismowatch_entrega/docker-compose.yml)
```yaml
  minio:
    image: minio/minio:RELEASE.2024-05-10T01-41-38Z
    container_name: sismowatch_minio
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-sismowatch_admin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-MinioSecretPass2026!}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - sismowatch_net

volumes:
  minio_data:
```

#### 2. Variables en `.env`
```bash
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=sismowatch_admin
MINIO_SECRET_KEY=MinioSecretPass2026!
MINIO_BRONZE_BUCKET=sismowatch-bronze
```

#### 3. Tarea de subida en Airflow (`airflow/include/s3_utils.py`)
```python
import io
import json
import boto3
from botocore.client import Config

def upload_geojson_to_minio(payload: dict, bucket: str, object_key: str):
    # cliente compatible con S3 para MinIO interno
    s3_client = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="sismowatch_admin",
        aws_secret_access_key="MinioSecretPass2026!",
        config=Config(signature_version="s3v4")
    )
    buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))
    s3_client.upload_fileobj(buffer, bucket, object_key)
```

---

### 5. Categorización de Recomendaciones

### CRÍTICO
- **No reemplazar la capa Silver ni Gold de PostgreSQL por MinIO**: La API FastAPI y el Dashboard en tiempo real dependen de índices relacionales, SSE rápido y consultas analíticas de latencia < 30 ms. Reemplazar Postgres por consultas directas a archivos S3 degradaría la experiencia en vivo.

### RECOMENDADO
- **Adoptar MinIO bajo una arquitectura híbrida**: Mantener Postgres para las consultas operativas y usar MinIO como *Data Lake Landing Bucket* para almacenar los feeds crudos GeoJSON y los respaldos periódicos de base de datos.
- Si se sustenta este proyecto ante evaluadores o comités, justificar que en un entorno enterprise (con estaciones sismológicas transmitiendo señales a 100 Hz), MinIO/S3 es el estándar de facto antes de procesar hacia Apache Iceberg o Parquet.

### OPCIONAL
- **Almacenar los reportes de IA y gráficas de DBSCAN en MinIO**: Permitiría descargar informes ejecutivos en PDF/PNG directamente desde el frontend mediante URLs prefirmadas.

### FUTURO
- **Migración a formato Apache Parquet / DuckDB**: Si el histórico supera millones de eventos, mover la capa Silver a archivos Parquet particionados en MinIO y consultarlos con DuckDB desde la API sin saturar la memoria de PostgreSQL.

### 8. Fuente de Datos Externa
- **USGS Earthquake API (Servicio Geológico de los Estados Unidos)**:
  - Feed en tiempo casi real: `all_hour.geojson` (actualizado cada minuto).
  - API de consulta histórica: USGS FDSN Web Services para backfills de hasta 30 días con paginación por ventanas temporales.
