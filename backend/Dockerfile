# NEXUS IMS — Backend (FastAPI)
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# 🚀 RUN MIGRATIONS + START APP
CMD python create_superuser.py && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
