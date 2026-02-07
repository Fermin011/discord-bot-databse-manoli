FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo
COPY run.py .
COPY app/ app/

# Crear directorios de datos y logs
RUN mkdir -p data logs

EXPOSE 8000

CMD ["python", "run.py"]
