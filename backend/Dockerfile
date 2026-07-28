FROM python:3.12-slim

WORKDIR /app

# psycopg2-binary needs libpq at runtime; build tools kept out of the final
# image is not worth the complexity for an MVP-sized service, so a single
# stage is fine here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Cloud Run injects $PORT; default to 8000 for local/docker-compose use.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
