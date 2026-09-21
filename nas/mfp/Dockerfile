# MyFitnessPal-MCP-Server mit selbstverlaengernder Session, fuer ARM64 (UGREEN DH2300) und amd64.
# Basis: offizielles python:3.12-slim (multi-arch). Alle Abhaengigkeiten haben aarch64-Wheels.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MFP_USERNAME=MarqEwi \
    XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/data \
    MFP_MCP_DATA_DIR=/data

RUN pip install --no-cache-dir "mfp-mcp==0.3.0" \
 && mkdir -p /app /config /data \
 && chown -R 1001:10 /config /data

COPY scripts/mfp_session.py /app/mfp_session.py

USER 1001:10
WORKDIR /app
EXPOSE 8484
CMD ["python", "/app/mfp_session.py", "serve", "--http", "--host", "0.0.0.0", "--port", "8484"]
