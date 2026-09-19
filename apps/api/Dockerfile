# Vantage API. One process on purpose: the scheduler, the login throttle and SQLite all assume a single worker.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/data/vantage.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docker-entrypoint.sh ./
# Windows checkouts can leave CRLF line endings, which break a shell script.
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && useradd --system --uid 10001 vantage \
    && mkdir -p /app/data \
    && chown -R vantage:vantage /app

USER vantage

# The database, the session signing key and the import cache all live here. Mount a volume on it.
VOLUME /app/data
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
