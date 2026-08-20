# ---------- Builder ----------
FROM 172.16.50.13/platform/python:3.12-slim-bookworm-build AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml poetry.lock ./

# Install Poetry from Nexus
RUN pip install --no-cache-dir \
    --trusted-host 172.16.50.12 \
    --index-url http://172.16.50.12:8081/repository/pypi-group-prod/simple \
    poetry

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-root

COPY . .


# ---------- Runtime ----------
FROM 172.16.50.13/platform/python:3.12-slim-bookworm-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

RUN mkdir -p /app/static /app/media && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD [ \
    "gunicorn", \
    "swmm.wsgi:application", \
    "--bind=0.0.0.0:8000", \
    "--workers=3", \
    "--timeout=300", \
    "--access-logfile=-", \
    "--error-logfile=-" \
]
