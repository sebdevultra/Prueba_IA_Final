"""
Configuración centralizada del backend FastAPI de SismoWatch.
Utiliza Pydantic Settings para cargar variables de entorno seguras.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Seguridad y JWT
    jwt_secret_key: str = "sismowatch_jwt_super_secret_signing_key_2026"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # Credenciales sembradas por variables de entorno
    admin_username: str = "admin"
    admin_password: str = "AdminSismo2026!"
    viewer_username: str = "viewer"
    viewer_password: str = "ViewerSismo2026!"

    # Base de Datos (Mínimo Privilegio: readonly_user)
    db_readonly_conn_uri: str = "postgresql+psycopg2://readonly_user:readonly_secure_pass@postgres:5432/sismowatch_db"
    db_transform_conn_uri: str = "postgresql+psycopg2://transform_user:transform_secure_pass@postgres:5432/sismowatch_db"

    # Airflow API
    airflow_internal_url: str = "http://airflow-webserver:8080"
    airflow_username: str = "admin"
    airflow_password: str = "AdminAirflow2026!"

    # Motor de IA Local (Ollama 8B)
    ollama_base_url: str = "http://172.17.0.1:11435"
    ollama_model: str = "llama3:8b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
