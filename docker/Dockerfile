# ─────────────────────────────────────────────────────────────────────────────
# Huron GenAI Knowledge Assistant — Development Dockerfile
# FastAPI backend for local development
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements_production.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements_production.txt

# Copy application
COPY backend/ .

ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8004

# Development mode with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004", "--reload"]

