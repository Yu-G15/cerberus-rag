FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl tini && \
    rm -rf /var/lib/apt/lists/*

# Install deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code
COPY . .

# Non-root (optional)
RUN useradd -m appuser
USER appuser

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["gunicorn","cerberus_ms_rest.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","60"]
