FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY argos ./argos
COPY detection-engine ./detection-engine
COPY chat-ui ./chat-ui
COPY README.md ./README.md

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["python", "-m", "argos.server"]
