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