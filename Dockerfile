# ---- Builder ----
FROM python:3.11-slim AS builder
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY argos ./argos
COPY detection-engine ./detection-engine
COPY chat-ui ./chat-ui
COPY README.md ./README.md
RUN pip install --no-cache-dir -e ".[dev]"

# ---- Runtime ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    ARGOS_DATA_DIR=/data \
    ARGOS_REQUIRE_AUTH=false
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app
RUN useradd -m -u 10001 argos
USER argos
VOLUME ["/data", "/app/models"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"
CMD ["python", "-m", "argos.server"]
