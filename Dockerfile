FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SIGNALS_DB=/data/signals.db
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home signals && mkdir /data && chown signals /data

USER signals
EXPOSE 8000
CMD ["uvicorn", "account_signals.server:app", "--host", "0.0.0.0", "--port", "8000"]
