"""InsightMeet API entry point.   Run:  uvicorn app.main:app --reload --port 8000"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routes.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load heavy resources once at start-up so the first request is fast.
    from .nlp.classification import get_model
    from .nlp.preprocessing import get_nlp
    get_nlp()
    try:
        get_model()
    except RuntimeError as e:  # pragma: no cover
        print(f"[InsightMeet] WARNING: {e}")
    yield


app = FastAPI(
    title="InsightMeet API",
    version="1.0.0",
    description="NLP-based meeting insight extraction: actions, decisions, issues, deadlines, relationships, and grounded Q&A.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", include_in_schema=False)
def health_alias():
    return {"status": "ok", "service": "InsightMeet"}
