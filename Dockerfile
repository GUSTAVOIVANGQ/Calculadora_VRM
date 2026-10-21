# CRT VMR 5G | Build multi-etapa para Podman/Docker.
# Para producción, fijar imágenes por digest y conservar frontend/package-lock.json en GitLab.
FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package*.json ./
# Compatible con la entrega v13, que no incluye package-lock.json todavía.
# Cuando CI genere y versione el lock, utiliza npm ci automáticamente.
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi
COPY frontend/ ./
RUN npm run build && test -s dist/index.html

FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VMR_USERS_DB=/var/lib/crt-vmr-5g/users.sqlite3
WORKDIR /app
RUN groupadd --gid 10001 vmr && useradd --uid 10001 --gid 10001 \
    --home-dir /app --shell /usr/sbin/nologin --no-create-home vmr \
    && mkdir -p /var/lib/crt-vmr-5g \
    && chown -R 10001:10001 /var/lib/crt-vmr-5g
COPY --chown=10001:10001 server.py api.py accounts.py login.html register.html robots.txt ./
COPY --chown=10001:10001 assets ./assets
COPY --chown=10001:10001 archivos ./archivos
COPY --chown=10001:10001 --from=frontend-builder /build/frontend/dist ./frontend/dist
COPY --chown=10001:10001 container/healthcheck.py container/check_credentials.py ./container/
RUN python -m py_compile server.py api.py accounts.py && test -s frontend/dist/index.html
USER 10001:10001
EXPOSE 8084
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "/app/container/healthcheck.py"]
CMD ["python", "server.py", "--bind", "0.0.0.0", "--port", "8084"]
