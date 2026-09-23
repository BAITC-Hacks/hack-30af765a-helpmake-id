FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Install the application and the versioned dataset in the image.
COPY pyproject.toml .
COPY api/ ./api/
COPY data/ ./data/
RUN pip install --no-cache-dir .

# Non-root user for production safety
RUN addgroup --system app && adduser --system --group app \
    && mkdir -p /var/lib/akim && chown app:app /var/lib/akim
ENV SCENARIO_DB_PATH=/var/lib/akim/scenarios.sqlite3
USER app

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
