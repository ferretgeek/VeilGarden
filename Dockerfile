FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VEIL_BIND_HOST=0.0.0.0 \
    VEIL_PORT=8768 \
    VEIL_DATA_DIR=/data \
    VEIL_ALLOW_PRIVATE_HTTP=1

WORKDIR /app

RUN addgroup -S veil && adduser -S -G veil -h /app veil
COPY --chown=veil:veil pyproject.toml README_EN.md LICENSE ./
COPY --chown=veil:veil src ./src
RUN pip install --no-cache-dir --no-deps .

USER veil
VOLUME ["/data"]
EXPOSE 8768
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8768/health', timeout=2)"

ENTRYPOINT ["veil-garden"]
