FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    INSIGHTMEET_DB=/data/insightmeet.db

WORKDIR /app

# Dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY . .

# Train the sentence classifier at build time so the container starts quickly
RUN python scripts/train_classifier.py

EXPOSE 8000

# Render injects $PORT; fall back to 8000 for local `docker run`
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
