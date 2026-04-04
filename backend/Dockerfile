FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /app/
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/
RUN pip install --no-cache-dir -e ".[dev]"
EXPOSE 8000
