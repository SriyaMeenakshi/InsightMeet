"""Central configuration. Everything is overridable with environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

DATASET_PATH = DATA_DIR / "sentences.csv"
HANDWRITTEN_PATH = DATA_DIR / "handwritten_eval.csv"
MODEL_PATH = MODEL_DIR / "sentence_classifier.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
EXAMPLE_TRANSCRIPT_PATH = DATA_DIR / "example_transcript.txt"

DB_PATH = Path(os.getenv("INSIGHTMEET_DB", str(DATA_DIR / "insightmeet.db")))

MAX_TRANSCRIPT_CHARS = int(os.getenv("INSIGHTMEET_MAX_CHARS", "200000"))
MAX_UPLOAD_BYTES = int(os.getenv("INSIGHTMEET_MAX_UPLOAD", str(2 * 1024 * 1024)))
MIN_TRANSCRIPT_CHARS = 20

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "INSIGHTMEET_CORS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]
