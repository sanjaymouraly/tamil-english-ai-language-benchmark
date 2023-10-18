FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TEB_DATA_DIR=/app/data

WORKDIR /app

# System deps (sqlite is builtin; curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY benchmark ./benchmark
COPY migrations ./migrations
RUN pip install --no-cache-dir -e .

# Pre-build the dataset and apply migrations on first boot via entrypoint.
EXPOSE 8000 8501

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
