"""HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from .. import config, db
from ..nlp import classification, qa
from ..nlp.dates import parse_meeting_date
from ..nlp.pipeline import analyze_transcript
from ..schemas import (AnalyzeRequest, Analysis, AskRequest, AskResponse, MeetingList, SearchResponse, TextExtraction)
from ..textio import InputError, extract_text, validate_transcript

router = APIRouter(prefix="/api")


def _run(text: str, title: str | None, meeting_date: str | None, save: bool) -> dict:
    try:
        validate_transcript(text)
        parse_meeting_date(meeting_date)
    except InputError as e:
        raise HTTPException(e.status, e.message)
    except ValueError as e:
        raise HTTPException(422, str(e))
    analysis = analyze_transcript(text, title, meeting_date)
    return db.save_meeting(analysis) if save else analysis


@router.get("/health")
def health():
    from ..nlp.preprocessing import get_nlp
    return {"status": "ok", "service": "InsightMeet", "spacy_model": get_nlp() is not None,
            "classifier_ready": config.MODEL_PATH.exists() or config.DATASET_PATH.exists()}


@router.post("/analyze", response_model=Analysis)
def analyze(req: AnalyzeRequest):
    return _run(req.transcript, req.title, req.meeting_date, req.save)


@router.post("/extract-text", response_model=TextExtraction)
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    try:
        text = extract_text(file.filename or "", data)
    except InputError as e:
        raise HTTPException(e.status, e.message)
    return {"filename": file.filename, "text": text, "characters": len(text)}


@router.post("/analyze/upload", response_model=Analysis)
async def analyze_upload(file: UploadFile = File(...), title: str | None = Form(None),
                         meeting_date: str | None = Form(None), save: bool = Form(True)):
    data = await file.read()
    try:
        text = extract_text(file.filename or "", data)
    except InputError as e:
        raise HTTPException(e.status, e.message)
    default_title = (file.filename or "").rsplit(".", 1)[0] or None
    return _run(text, title or default_title, meeting_date, save)


@router.get("/example-transcript")
def example():
    if not config.EXAMPLE_TRANSCRIPT_PATH.exists():
        raise HTTPException(404, "Example transcript not found.")
    return {"title": "Demo preparation (example)", "meeting_date": "2025-03-10",
            "transcript": config.EXAMPLE_TRANSCRIPT_PATH.read_text(encoding="utf-8")}


@router.get("/meetings", response_model=MeetingList)
def meetings(q: str | None = Query(None, max_length=200), limit: int = Query(100, ge=1, le=500)):
    items = db.list_meetings(q, limit)
    return {"total": len(items), "meetings": items}


@router.get("/meetings/{meeting_id}", response_model=Analysis)
def meeting(meeting_id: str):
    a = db.get_meeting(meeting_id)
    if a is None:
        raise HTTPException(404, "Meeting not found. It may have been deleted.")
    return a


@router.delete("/meetings/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str):
    if not db.delete_meeting(meeting_id):
        raise HTTPException(404, "Meeting not found.")


@router.post("/meetings/{meeting_id}/ask", response_model=AskResponse)
def ask(meeting_id: str, req: AskRequest):
    a = db.get_meeting(meeting_id)
    if a is None:
        raise HTTPException(404, "Meeting not found. Analyse a transcript first.")
    return qa.answer_question(a, req.question)


@router.get("/meetings/{meeting_id}/search", response_model=SearchResponse)
def search(meeting_id: str, q: str = Query(..., min_length=1, max_length=200)):
    a = db.get_meeting(meeting_id)
    if a is None:
        raise HTTPException(404, "Meeting not found.")
    return {"query": q, "hits": qa.search_transcript(a, q)}


@router.get("/model/metrics")
def metrics():
    m = classification.load_metrics()
    if m is None:
        raise HTTPException(404, "No evaluation has been run yet. Run: python scripts/train_classifier.py")
    return m
