# Changelog

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y se rige por las políticas de documentación técnica del proyecto con zona horaria `America/Bogota` (UTC-5).

## [1.2.2] - 2026-10-28 10:48:00 -05:00

### Fixed
- **Agente de Preguntas IA Gold (Ollama 8B)**:
  - *Qué*: En `api/routers/agent.py`, se solucionó un error crítico de tipografía (`NameError: name 'endpoint' is not defined`) en el bloque `except` del logger (cambiando `endpoint` por `ep`). Se priorizaron las rutas directas hacia el host y proxy (`172.17.0.1:11435` y `host.docker.internal:11435`) y se amplió el tiempo de espera para inferencia en CPU.
  - *Por qué*: Permitir que el contenedor de la API se comunique fluidamente con el modelo local `llama3:8b` alojado en el host, respondiendo preguntas analíticas estructuradas sobre la capa Gold sin errores 500.

- **Generador de Reportes Ejecutivos con Google Gemini**:
  - *Qué*: En `airflow/include/ai_reporter.py`, se actualizó la función `call_gemini_api` para consultar los modelos activos de Google Gemini (`gemini-3.5-flash`, `gemini-2.5-flash-lite`), reemplazando el endpoint obsoleto de `gemini-1.5-flash` que arrojaba 404 en la API v1beta. Además, se limpiaron posibles bloques delimitadores markdown (` ```json `) antes de la validación estricta de esquemas Pydantic.
  - *Por qué*: Garantizar que, al suministrar `GEMINI_API_KEY` en `.env` y recrear los contenedores, los reportes se generen de forma 100% asistida por IA (`validation_passed: true`, `is_fallback: false`), erradicando las caídas no deseadas a la plantilla determinista Jinja2.

## [1.2.1] - 2026-10-28 08:05:00 -05:00

### Added
- **Archivo de Dependencias Raíz (`requirements.txt`)**:
  - *Qué*: Se creó el archivo `requirements.txt` consolidado en la raíz del proyecto, integrando las librerías compartidas de FastAPI, Apache Airflow, procesamiento de datos (Pandas, Scikit-Learn), testing (Pytest) y clientes de bases de datos (SQLAlchemy, Psycopg2).
  - *Por qué*: Permitir la creación del entorno virtual local (`.venv`), resolución de imports y ejecución exitosa de la batería completa de pruebas unitarias (`pytest tests`, 21/21 passed) fuera de los contenedores Docker.

### Changed
- **Puesta en Marcha y Despliegue de Infraestructura Docker**:
  - *Qué*: Se generó el archivo `.env` a partir de `.env.example`, se creó la carpeta `airflow/logs` con permisos de escritura, se liberaron puertos y se desplegó todo el ecosistema de microservicios con `docker compose up -d --build` (`sismowatch_postgres`, `sismowatch_airflow_init`, `sismowatch_airflow_webserver`, `sismowatch_airflow_scheduler`, `sismowatch_api` y `sismowatch_web`).
  - *Por qué*: Habilitar el levantamiento íntegro del sistema desde el estado inicial hasta el estado operativo validado.

## [1.2.0] - 2026-10-27 13:30:00 -05:00

### Fixed
- **Depuración Integral de Linter y Advertencias del IDE**:
  - *Qué*: Se corrigieron todas las advertencias amarillas del IDE en backend y frontend:
    - `api/security.py`: Se convirtieron las funciones de seguridad sincrónicas (`get_current_user`, `get_current_user_flexible`, `require_admin`) de `async def` a `def`, eliminando la advertencia de función asíncrona sin expresiones `await` y permitiendo a FastAPI ejecutarlas en el threadpool sin bloquear el event loop.
    - `api/routers/admin.py`, `dashboard.py`, `reports.py`, `agent.py`: Se renombraron las variables de usuario inyectadas pero no referenciadas a `_admin_user` y `_current_user`.
    - `api/routers/admin.py`, `stream.py`, `config.py`, `database.py`: Se eliminaron importaciones no utilizadas (`HTTPException`, `status`, `Depends`, `os`, `contextmanager`).
    - `airflow/dags/dag_ai_daily_report_and_anomalies.py`, `airflow/include/`: Se eliminaron importaciones no utilizadas (`AirflowException`, `ValidationError`, `Optional`).
    - `web/src/components/` y `web/src/pages/`: Se eliminaron todos los íconos e interfaces no referenciadas (`Shield`, `Filter`, `Zap`, `AlertTriangle`, `Database`, `AlertCircle`, `CornerDownLeft`, `UserSession`), alcanzando 100% de limpieza de imports en el frontend.
  - *Por qué*: Resolver las alertas y subrayados amarillos en el IDE sin alterar la funcionalidad del sistema.

- **Integración y Observabilidad en Tiempo Real con Apache Airflow**:
  - *Qué*: En `api/routers/dashboard.py` (`/api/pipeline/status`), se reemplazaron los estados estáticos por consultas directas y dinámicas a la API REST de Apache Airflow (`/api/v1/dags` y `/api/v1/dags/{dag_id}/dagRuns`), recuperando el estado real de ejecución (`state`), indicador de pausa (`is_paused`) y marca temporal de la última corrida (`last_run_time`). Se actualizó `web/src/pages/PipelineStatusPage.tsx` para reflejar visualmente estos estados con insignias temáticas y marcas de hora legibles.
  - *Por qué*: Atender el requerimiento de poder actualizar y visualizar el estado real de los DAGs en el orquestador con el botón "Actualizar Estado".

- **Corrección en Ventana de Backfill Histórico para Días Específicos**:
  - *Qué*: En `airflow/dags/dag_usgs_backfill_30d.py` (`create_windows`), se ajustó el cálculo de fechas sumando `+ timedelta(days=1)` a `end_dt` cuando se ingresan fechas explícitas (`start_date`, `end_date`), garantizando que consultas para un solo día (e.g. `2026-10-27` a `2026-10-27`) generen la partición completa que abarca las 24 horas en el endpoint de USGS.
  - *Por qué*: Resolver el problema donde consultas de una misma fecha generaban 0 ventanas temporales y no persistían sismos en la base de datos.

- **Visualización de Marca Temporal en Indicador En Vivo (SSE)**:
  - *Qué*: Se actualizó `web/src/components/LiveFeedBadge.tsx` para aprovechar la prop `lastUpdate` y desplegar la hora exacta de la última actualización (`Act: HH:MM:SS`), cumpliendo con el requerimiento de la guía de evaluación.
  - *Por qué*: Dar visibilidad al operador de la hora del último evento sísmico recibido.

- **Conectividad Persistente con Modelo Local Ollama 8B**:
  - *Qué*: Se implementó el servicio de usuario persistente en systemd `ollama-proxy.service` en el puerto 11435, permitiendo al contenedor Docker de la API comunicarse con la instancia local de Ollama (`llama3:8b`). Se optimizaron los timeouts de conexión y número de tokens generados en `api/routers/agent.py` para respuestas ágiles sobre CPU.
  - *Por qué*: Garantizar que las consultas de lenguaje natural al agente de IA en la pestaña Gold utilicen el modelo local descargado sin fallas de red ni dependencias de nube.

## [1.1.0] - 2026-10-27 12:40:00 -05:00

### Removed
- **Cuarentena del Pipeline y Frontend**:
  - *Qué*: Se eliminó el endpoint administrativo `/api/quality/quarantine`, el componente `web/src/components/QuarantineTable.tsx`, los esquemas asociados en `api/schemas.py`, y todas las referencias y accesos de cuarentena en la barra de navegación y enrutamiento.
  - *Por qué*: Requerimiento explícito de diseño: los registros con errores severos o invalidantes quedan exclusivamente retenidos en la capa Bronze (`raw.earthquake_events_raw`), abortando su propagación al pipeline y eliminando la necesidad de una tabla/vista de cuarentena separada.
- **Pandera**:
  - *Qué*: Se eliminó cualquier dependencia de Pandera a favor de Pandas estándar y validación tipada con esquemas Pydantic v2.
  - *Por qué*: Estandarización de dependencias y mayor compatibilidad de tipos relacionales y geoespaciales.

### Added
- **Agente IA Gold Local (Ollama 8B)**:
  - *Qué*: Se incorporó una nueva pestaña "Agente IA (Gold)" en la barra de navegación (`web/src/pages/AgentChatPage.tsx`) situada entre "Dashboard" y "Reportes IA". Está conectada al endpoint `POST /api/agent/chat` (`api/routers/agent.py`), compatible con el modelo local de Ollama `llama3:8b` (puerto host 11434) y modo analítico directo con cero alucinaciones respaldado por consultas agregadas sobre la capa Gold (`curated.earthquake_events`).
  - *Por qué*: Permitir al equipo operativo y analistas consultar métricas, tendencias y sismos notables en lenguaje natural con total privacidad y sin requerir servicios en la nube.
- **Filtro de Tsunami y Ordenamiento de Tabla en Dashboard**:
  - *Qué*: Se agregaron controles interactivos en la barra de herramientas del dashboard (`web/src/pages/DashboardPage.tsx`) y cabeceras clickeables en la tabla (`Mag`, `Fecha UTC`, `Profundidad`) que permiten filtrar eventos por alerta de tsunami (`tsunami`) y ordenarlos de forma ascendente o descendente (`sort_by`, `sort_order`).
  - *Por qué*: Facilitar a los operadores la localización inmediata de eventos tsunamigénicos y la priorización de eventos según profundidad o magnitud.
- **Categoría Fija de Magnitud Mayor (≥ 6.0)**:
  - *Qué*: Se garantizó la presencia permanente de la categoría `"Fuerte / Mayor (>= 6.0)"` en `distribution_by_magnitude` en `/api/stats/timeseries` y en el gráfico analítico `SeismicCharts.tsx`, mostrando 0 cuando no existan eventos en esa ventana.
  - *Por qué*: Asegurar la visualización constante de la escala de peligro mayor para alertas operativas.
- **Rango de Fechas Específico en Backfill Histórico**:
  - *Qué*: Se añadieron selectores de fecha `start_date` y `end_date` (formato `YYYY-MM-DD`) en el formulario de backfill administrativo de `PipelineStatusPage.tsx`, y se actualizó el DAG de Airflow `dag_usgs_backfill_30d.py` para leer estos parámetros desde `dag_run.conf` y descargar particiones exactas desde USGS.
  - *Por qué*: Habilitar al administrador la carga de cualquier rango histórico arbitrario sin depender únicamente de un número relativo de días.

### Fixed
- **Autenticación en Descargas de Archivos (CSV / HTML / PDF)**:
  - *Qué*: Se implementó la dependencia `get_current_user_flexible` en `api/security.py` que admite autenticación tanto por la cabecera `Authorization: Bearer` como por el parámetro de consulta `?token=`. Asimismo, `ReportsPage.tsx` descarga los archivos vía `fetch()` con autenticación de cabecera y Blob URL local.
  - *Por qué*: Corregir el error `{"detail":"No autenticado: cabecera Authorization Bearer requerida"}` que ocurría al abrir enlaces directos desde el navegador.
- **Regeneración y Visualización Inmediata de Reportes IA**:
  - *Qué*: El endpoint administrativo `POST /api/admin/reports/regenerate` genera y persiste de forma síncrona el reporte diario en `curated.ai_daily_reports` utilizando una conexión con privilegios de escritura (`role_transform`), y el frontend actualiza inmediatamente la lista y visualiza el reporte en pantalla.
  - *Por qué*: Corregir la falla donde la interfaz solo mostraba "solicitud procesada" pero no desplegaba el informe en pantalla.
- **Desacoplamiento de Latido SSE de la Hora de Datos**:
  - *Qué*: En `web/src/components/LiveFeedBadge.tsx`, se separó el pulso de conexión SSE (heartbeat cada 5 segundos) de la marca de tiempo del último sismo recibido.
  - *Por qué*: Evitar la confusión visual del usuario de que la página se recargaba cada 5 segundos en lugar de mantenerse conectada en tiempo real.

---

## [1.0.0] - 2026-10-27 10:25:00 -05:00

### Added
- **docs/ARQUITECTURA.md**: Documento de arquitectura detallado con propósito de negocio, diagrama de componentes en Mermaid, diseño de capas Medallion (`raw`, `staging`, `curated`), retención de registros inválidos en staging, políticas RBAC de mínimo privilegio y justificación de decisiones técnicas.
  - *Por qué*: Requerimiento fundamental de la prueba para sustentar diseño técnico y alineación con la decisión del staff de retener inválidos en `staging` con `is_valid = FALSE` sin tabla física independiente de cuarentena.
- **antigravity_plan.json**: Plan estructurado de tareas de Antigravity organizado en 7 fases secuenciales con dependencias y archivos objetivos.
  - *Por qué*: Habilitar la importación y trazabilidad del ciclo de desarrollo en Antigravity.
- **db/init/01_init.sql**: Script de aprovisionamiento de PostgreSQL con creación de bases de datos `airflow_db` y `sismowatch_db`, esquemas Medallion, roles segregados (`role_ingest`, `role_transform`, `role_readonly`) y tablas operativas.
  - *Por qué*: Implementar principio de mínimo privilegio en base de datos e inmutabilidad/calidad por capas.
- **docker-compose.yml**: Orquestación integral de PostgreSQL 16, Apache Airflow (LocalExecutor: webserver, scheduler, init), FastAPI backend y React Vite frontend.
  - *Por qué*: Requerimiento de arranque unificado en un solo comando `docker compose up -d`.
- **.env.example** y **.env**: Plantilla y configuración de secretos con Fernet key para Airflow, JWT secret key, credenciales segregadas de base de datos y usuario admin por variables de entorno.
  - *Por qué*: Cumplimiento estricto de seguridad OWASP y prevención de exposición de credenciales en Git.
- **.gitignore**: Exclusión de archivos de entorno, caches de Python/Node, bases de datos locales y artefactos temporales.
  - *Por qué*: Evitar fugas de secretos y polución del repositorio.
- **airflow/include/usgs_client.py**: Cliente HTTP con reintentos exponenciales, timeouts y excepción estructurada `USGSUnavailableError`.
  - *Por qué*: Ingesta robusta y resiliente de USGS GeoJSON en tiempo real e histórico.
- **airflow/include/transformer.py**: Aplanamiento de GeoJSON, conversión a UTC y tipado relacional.
  - *Por qué*: Normalizar datos volátiles para capas relacionales Medallion.
- **airflow/include/quality_engine.py**: Compuertas de calidad de datos a nivel de registro y lote, cálculo de Quality Score y desglose de reglas evaluadas.
  - *Por qué*: Asegurar que ningún registro erróneo ingrese a curated y retener inválidos en staging para auditoría.
- **airflow/include/db_utils.py**: Utilidades de conexión por roles RBAC e instrucciones UPSERT idempotentes.
  - *Por qué*: Garantizar idempotencia e inmutabilidad con mínimo privilegio en PostgreSQL.
- **airflow/include/anomaly_detector.py**: Detección de picos temporales (Z-Score) y enjambres espaciales con DBSCAN (métrica Haversine).
  - *Por qué*: Proveer inteligencia analítica de clustering sísmico sin depender exclusivamente de LLMs.
- **airflow/include/ai_reporter.py**: Generador de reportes ejecutivos diarios con Gemini, sanitización contra Prompt Injection (OWASP LLM01), validación de esquemas Pydantic, verificación numérica estricta y plan alterno determinista Jinja2.
  - *Por qué*: Cumplir requerimiento obligatorio de cero alucinaciones y alta disponibilidad ante caídas del proveedor de IA.
- **airflow/include/prompts/daily_executive_report_v1.txt**: Plantilla de prompt versionada v1.
  - *Por qué*: Versionamiento explícito de prompts y trazabilidad de ingeniería de prompts.
- **airflow/dags/dag_usgs_ingest_realtime.py**: Ingesta continua cada 5 minutos del feed en tiempo real de USGS a la capa Bronze (raw) emitiendo Dataset.
  - *Por qué*: Automatizar la captura sin intervención manual respetando inmutabilidad e idempotencia.
- **airflow/dags/dag_usgs_transform_and_quality.py**: DAG reactivo activado por Dataset con TaskGroups para aplanamiento, validación bloqueante de calidad y promoción a curated.
  - *Por qué*: Garantizar que solo los eventos limpios ingresen a Gold y retener inválidos en Silver (staging) para auditoría.
- **airflow/dags/dag_ai_daily_report_and_anomalies.py**: DAG diario y on-demand para clustering espacial DBSCAN, detección de picos Z-Score y generación de informe ejecutivo con Gemini y fallback.
  - *Por qué*: Aportar valor predictivo y analítico automatizado con observabilidad de costos de IA.
- **airflow/dags/dag_usgs_backfill_30d.py**: DAG parametrizado con particionamiento de ventanas temporales de 5 días para ingesta histórica de 30 días sin duplicados.
  - *Por qué*: Cumplir requerimiento de carga histórica bajo demanda e idempotente.
- **api/**: Backend FastAPI con autenticación JWT, RBAC (`admin` vs `viewer`), SSE en tiempo real (`/api/stream`), endpoints de analítica (`/api/kpis`, `/api/events`, `/api/stats/timeseries`, `/api/reports`, `/api/pipeline/status`) y rutas administrativas protegidas (`/api/quality/quarantine`, `/api/admin/backfill`, `/api/admin/reports/regenerate`).
  - *Por qué*: Proporcionar una plataforma de consumo segura de alto rendimiento que expone exclusivamente la capa Gold (curated) y permite a los administradores auditar la retención de registros inválidos en staging.
- **web/**: SPA en React 18 + Vite + TypeScript con tema Dark Mode **"Azul Galáctico"**:
  - *Fondo Principal:* `#0B0F19` y `#0F172A` (espacio exterior).
  - *Fondo de Superficies:* `#1E293B` con glassmorphism `rgba(30, 41, 59, 0.78)`.
  - *Color Primario / Acento:* `#3B82F6` a `#6366F1` (Azul Galáctico / Índigo eléctrico).
  - *Color de Brillo / Destello:* `#06B6D4` y `#38BDF8` (Cian Neón con resplandor glow).
  - *Texto Principal y Secundario:* `#F8FAFC` y `#94A3B8`.
  - *Componentes:* `Navbar`, `KpiCards`, `SeismicMap` (Leaflet Dark Matter), `SeismicCharts` (Recharts con gradiente galáctico), `LiveFeedBadge` (indicador SSE con reconexión), `QuarantineTable` (auditoría exclusiva admin) y `StateWrapper` (sin pantallas en blanco).
  - *Por qué*: Cumplir requerimientos estéticos de alto impacto visual y experiencia interactiva en tiempo real.
- **tests/**: Batería de 20 pruebas automatizadas en Pytest cubriendo transformaciones GeoJSON, integridad de los 4 DAGs de Airflow, compuertas de calidad y control de acceso RBAC de endpoints.
  - *Por qué*: Garantizar confiabilidad técnica, cobertura funcional y seguridad verificable con un solo comando `pytest tests`.
- **README.md**: Documentación operativa integral con guía de despliegue, respuestas defensivas para la sustentación y evidencia de escaneo de seguridad sin vulnerabilidades (Bandit con 0 issues).
  - *Por qué*: Facilitar la sustentación individual y cumplir criterios de evaluación.

### Fixed
- **web/src/components/SeismicCharts.tsx**:
  - *Qué*: Se corrigió la llave inestable `key={`cell-${index}`}` reemplazándola por la llave constante y única `key={entry.category}`. Se integró la variable no referenciada `topRegions` (`data?.top_active_regions`) creando un tercer panel visual con el listado de regiones más activas, número de sismos y magnitud máxima.
  - *Por qué*: Evitar desincronizaciones en el renderizado virtual de React ante cambios de lista y aprovechar métricas analíticas provistas por el backend.
- **airflow/include/db_utils.py** y entorno de desarrollo:
  - *Qué*: Instalación de `sqlalchemy` y `psycopg2-binary` (además de `pandas`, `pydantic` y `scikit-learn`) en el entorno de usuario del sistema y configuración de `.vscode/settings.json` apuntando a `.venv/bin/python`.
  - *Por qué*: Resolver la advertencia de módulos no encontrados en el editor/IDE al inspeccionar el archivo fuera del contenedor Docker.
- **api/Dockerfile**, **docker-compose.yml**, **api/__init__.py**:
  - *Qué*: Se crearon los archivos de paquete `api/__init__.py` y `api/routers/__init__.py`, se ajustó el Dockerfile para copiar los fuentes a `/app/api` con `ENV PYTHONPATH=/app` y `CMD ["uvicorn", "api.main:app", ...]`, y se corrigió el volumen montado en `docker-compose.yml` de `./api:/app` a `./api:/app/api`.
  - *Por qué*: Resolver la falla de inicio y healthcheck en `sismowatch_api` causada por `ModuleNotFoundError: No module named 'api'`, permitiendo a Uvicorn importar correctamente el paquete modular tanto en el contenedor como en pruebas locales, habilitando también el arranque automático del frontend `sismowatch_web`.
- **web/src/components/SeismicMap.tsx** y **web/src/index.css**:
  - *Qué*: Se reemplazó el proveedor de teselas de mapa CartoDB por la capa base oficial de OpenStreetMap (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`), añadiendo la clase `.dark-galactic-tiles` con filtros CSS (`brightness`, `invert`, `contrast`, `hue-rotate`) para preservar la estética Azul Galáctico sin requerir API keys ni suscripciones externas.
  - *Por qué*: Evitar el bloqueo de teselas y mensajes de cobro/clave API que CartoDB exige en navegadores web modernos, garantizando un mapa 100% libre, gratuito y funcional.
- **airflow/** y orquestación de datos:
  - *Qué*: Se corrigieron los permisos de escritura de `/opt/airflow/logs` para el usuario `airflow` (UID 50000), se creó el enlace simbólico del paquete `include` en el contenedor de Airflow, se configuró `AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=False` y se despausaron y ejecutaron los DAGs `dag_usgs_ingest_realtime` y `dag_usgs_backfill_30d`.
  - *Por qué*: El scheduler de Airflow se encontraba bloqueado en un bucle de permisos y los DAGs estaban pausados por defecto, lo que impedía que la base de datos PostgreSQL poblara las capas Medallion. Tras la activación y ejecución del backfill, se cargaron y certificaron 1,984 eventos sísmicos en la capa Gold (`curated.earthquake_events`), reflejando de inmediato los KPIs, mapa y gráficos en el frontend.



