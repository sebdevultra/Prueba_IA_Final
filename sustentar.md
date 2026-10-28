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

### 8. Fuente de Datos Externa
- **USGS Earthquake API (Servicio Geológico de los Estados Unidos)**:
  - Feed en tiempo casi real: `all_hour.geojson` (actualizado cada minuto).
  - API de consulta histórica: USGS FDSN Web Services para backfills de hasta 30 días con paginación por ventanas temporales.
