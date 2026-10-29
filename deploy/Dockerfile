FROM node:22-bookworm-slim AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HOME=/data CHRONICLE_STATE_DIR=/data/state \
    CHRONICLE_WEB_STATIC_DIR=/app/ui/dist PORT=8000
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY chronicle/ ./chronicle/
RUN pip install --no-cache-dir .
COPY --from=ui /ui/dist ./ui/dist
RUN useradd --uid 10001 --create-home --home-dir /data chronicle \
    && chown -R chronicle:chronicle /data
USER chronicle
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import os, http.client; c=http.client.HTTPConnection('127.0.0.1', int(os.environ.get('PORT', '8000')), timeout=4); c.request('GET', '/healthz'); raise SystemExit(0 if c.getresponse().status == 200 else 1)"
CMD ["python", "-m", "chronicle.web"]
