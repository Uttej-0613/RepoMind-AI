FROM node:22-alpine AS frontend
WORKDIR /ui
COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
RUN npm install --no-audit --no-fund && npm run build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 REPOMIND_ROOT=/workspace REPOMIND_DATA_DIR=/data
WORKDIR /app
COPY pyproject.toml README.md ./
COPY repomind ./repomind
COPY --from=frontend /ui/dist ./frontend/dist
RUN pip install --no-cache-dir '.[api]' && mkdir -p /data && chown 65534:65534 /data
USER 65534:65534
EXPOSE 8000
CMD ["uvicorn", "repomind.api:app", "--host", "0.0.0.0", "--port", "8000"]
