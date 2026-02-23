# ── Build Stage ──
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Gleicher Pfad wie Runtime-Stage (Shebang-Kompatibilität)
WORKDIR /app

# Dependencies zuerst (Cache-Layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Projektcode kopieren
COPY app/ app/

# ── Runtime Stage ──
FROM python:3.13-slim

# ffmpeg für pydub (MP3 → mulaw Konvertierung)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Virtual Environment und App-Code aus Build-Stage kopieren
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.endpoint:app", "--host", "0.0.0.0", "--port", "8000"]
