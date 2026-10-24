FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY footing ./footing
COPY fixtures ./fixtures
RUN pip install --no-cache-dir ".[api]"
# The package is installed into site-packages, so point it at the fixtures copied above.
ENV FOOTING_MODE=live FOOTING_CACHE=/tmp/footing.sqlite FOOTING_FIXTURES=/app/fixtures
# Cloud Run sets $PORT
CMD exec uvicorn footing.api:app --host 0.0.0.0 --port ${PORT:-8080}
