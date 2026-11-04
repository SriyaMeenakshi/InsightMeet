"""Pydantic models for API requests and responses."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ------------------------------------------------------------ requests
class AnalyzeRequest(BaseModel):
    transcript: str = Field(..., description="Raw meeting transcript text")
    title: str | None = Field(None, max_length=200)
    meeting_date: str | None = Field(None, description="ISO date (YYYY-MM-DD) used to resolve relative deadlines")
    save: bool = True

    @field_validator("transcript")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Transcript is empty. Paste or upload a meeting transcript.")
        return v


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Please type a question.")
        return v


# ------------------------------------------------------------ building blocks
class EvidenceRef(BaseModel):
    sentence_id: int
    speaker: str | None = None
    text: str
    start: int
    end: int


class DeadlineInfo(BaseModel):
    raw: str
    kind: str                       # absolute | relative | event | unresolved
    resolved: bool
    date: str | None = None         # ISO date when resolved
    precision: str = "unknown"      # day | week | month | unknown
    normalized: str
    note: str | None = None


class DeadlineVersion(BaseModel):
    role: Literal["original", "revised", "single"]
    deadline: DeadlineInfo
    evidence: EvidenceRef


class ActionItem(BaseModel):
    id: str
    task: str
    owner: str | None = None
    owners: list[str] = []
    owner_basis: str | None = None
    said_by: str | None = None
    commitment: Literal["definite", "tentative", "requested", "unassigned"]
    deadline: DeadlineInfo | None = None
    original_deadline: DeadlineInfo | None = None
    deadline_history: list[DeadlineVersion] = []
    status: Literal["open", "done"] = "open"
    blocked: bool = False
    blocked_by: list[str] = []
    components: list[str] = []
    confidence: float
    needs_review: bool = False
    review_reasons: list[str] = []
    mentions: int = 1
    context: str | None = None
    evidence: list[EvidenceRef]


class Decision(BaseModel):
    id: str
    text: str
    status: Literal["confirmed", "superseded"] = "confirmed"
    basis: str
    decided_by: str | None = None
    components: list[str] = []
    supersedes: str | None = None
    superseded_by: str | None = None
    confidence: float
    needs_review: bool = False
    review_reasons: list[str] = []
    evidence: list[EvidenceRef]


class Issue(BaseModel):
    id: str
    problem: str
    component: str | None = None
    impact: str | None = None
    blocked_activity: str | None = None
    status: Literal["open", "resolved"] = "open"
    raised_by: str | None = None
    confidence: float
    needs_review: bool = False
    review_reasons: list[str] = []
    evidence: list[EvidenceRef]


class Suggestion(BaseModel):
    id: str
    text: str
    proposer: str | None = None
    status: Literal["unconfirmed", "accepted", "rejected"] = "unconfirmed"
    tentative: bool = False
    components: list[str] = []
    evidence: list[EvidenceRef]
    response: EvidenceRef | None = None


class DeadlineEntry(BaseModel):
    id: str
    task_id: str | None = None
    task: str | None = None
    owner: str | None = None
    deadline: DeadlineInfo
    role: Literal["original", "revised", "single", "standalone"]
    is_latest: bool = True
    superseded: bool = False
    evidence: EvidenceRef
    needs_review: bool = False
    review_reasons: list[str] = []


class RelNode(BaseModel):
    kind: Literal["person", "action", "issue", "decision", "component", "text"]
    id: str | None = None
    text: str


class Relationship(BaseModel):
    id: str
    type: Literal["ASSIGNED_TO", "DEPENDS_ON", "BLOCKS", "AFFECTS"]
    source: RelNode
    target: RelNode
    explicit: bool
    basis: str
    confidence: float
    evidence: list[EvidenceRef]


class Entity(BaseModel):
    text: str
    label: str
    count: int
    sentence_ids: list[int]
    source: str


class Participant(BaseModel):
    name: str
    sentences: int
    turns: int
    words: int
    share: float
    actions_owned: int


class Keyphrase(BaseModel):
    phrase: str
    score: float
    mentions: int
    sentence_ids: list[int]


class Topic(BaseModel):
    topic: str
    mentions: int
    share: float
    first_sentence_id: int
    sentence_ids: list[int]


class SummaryOut(BaseModel):
    overview: str
    highlights: list[EvidenceRef]
    method: str


class SentenceOut(BaseModel):
    id: int
    index: int
    turn_index: int
    speaker: str | None
    speaker_inherited: bool
    text: str
    original: str
    start: int
    end: int
    label: str
    confidence: float
    label_source: str
    model_label: str
    model_confidence: float
    tokens: list[str]
    lemmas: list[str]
    is_question: bool


class ReviewItem(BaseModel):
    item_type: str
    item_id: str
    text: str
    reasons: list[str]


class Overview(BaseModel):
    title: str
    meeting_date: str | None
    sentences: int
    words: int
    participants: int
    action_items: int
    decisions: int
    issues_open: int
    issues_total: int
    suggestions: int
    needs_review: int
    unresolved_deadlines: int


class Analysis(BaseModel):
    meeting_id: str | None = None
    created_at: str | None = None
    title: str
    meeting_date: str | None = None
    transcript: str
    overview: Overview
    summary: SummaryOut
    topics: list[Topic]
    keyphrases: list[Keyphrase]
    participants: list[Participant]
    entities: list[Entity]
    action_items: list[ActionItem]
    decisions: list[Decision]
    issues: list[Issue]
    suggestions: list[Suggestion]
    deadlines: list[DeadlineEntry]
    relationships: list[Relationship]
    distribution: dict[str, int]
    review_queue: list[ReviewItem]
    sentences: list[SentenceOut]
    representation: dict[str, Any]
    warnings: list[str]
    nlp_info: dict[str, Any]


class MeetingSummary(BaseModel):
    id: str
    title: str
    created_at: str
    meeting_date: str | None
    snippet: str
    counts: dict[str, int]


class MeetingList(BaseModel):
    total: int
    meetings: list[MeetingSummary]


class AskResponse(BaseModel):
    question: str
    found: bool
    answer: str
    method: str
    confidence: float
    evidence: list[EvidenceRef]
    related: list[dict[str, Any]] = []


class SearchHit(BaseModel):
    score: float
    evidence: EvidenceRef
    label: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class TextExtraction(BaseModel):
    filename: str
    text: str
    characters: int
