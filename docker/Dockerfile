FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS runtime

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser data/processed/ /app/data/processed/

WORKDIR /app
USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "legal_rag.api.main:app", "--host", "0.0.0.0", "--port", "8000"]