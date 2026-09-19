#!/bin/sh
# Prepare the database, then start the API. Both seed steps are safe to repeat on every start:
#   app.seed         creates the tables and loads the curated data into an empty database
#   app.seed --sync  adds curated roles, skills, companies and feeds that are missing, wipes nothing
set -e

python -m app.seed
python -m app.seed --sync

# --proxy-headers so the real client address and https show through the web container and Caddy.
exec uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers 1 \
    --timeout-keep-alive 75 \
    --proxy-headers --forwarded-allow-ips "*"
