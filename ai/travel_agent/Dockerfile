FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

RUN useradd --system --create-home --uid 10001 appuser
WORKDIR /app

COPY pyproject.toml ./
RUN mkdir app \
    && touch README.md app/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf app README.md

COPY app ./app

USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
