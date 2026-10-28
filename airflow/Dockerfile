FROM apache/airflow:2.8.1-python3.11

USER root
# Instalar utilidades básicas y cliente de PostgreSQL si es necesario
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libpq-dev \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Instalar dependencias de Python del proyecto SismoWatch
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt

# Enlace simbólico para resolución nativa de 'from airflow.include.xyz import ...'
RUN ln -s /opt/airflow/include /home/airflow/.local/lib/python3.11/site-packages/airflow/include

