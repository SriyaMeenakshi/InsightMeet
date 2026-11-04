import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nlp import qa

client = TestClient(app)

SAMPLE = (
    "Sriya: Rahul will finish the frontend by Thursday.\n"
    "Rahul: That won't work, let's push the frontend deadline to Monday.\n"
    "Ananya: Testing is blocked because the login isn't working.\n"
    "Ananya: I'll test the dashboard tomorrow.\n"
    "Sriya: Fine, let's use SQLite for now.\n"
)


@pytest.fixture(scope="module")
def saved():
    r = client.post("/api/analyze", json={"transcript": SAMPLE, "title": "QA sample", "meeting_date": "2025-03-10"})
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ Q&A
def ask(mid, q):
    r = client.post(f"/api/meetings/{mid}/ask", json={"question": q})
    assert r.status_code == 200, r.text
    return r.json()


def test_who_is_responsible(saved):
    r = ask(saved["meeting_id"], "Who is responsible for the frontend?")
    assert r["found"] and "Rahul" in r["answer"] and r["evidence"]


def test_what_decisions(saved):
    r = ask(saved["meeting_id"], "What decisions were made?")
    assert r["found"] and "SQLite" in r["answer"] and r["evidence"]


def test_latest_deadline_reports_revision(saved):
    r = ask(saved["meeting_id"], "What is the latest frontend deadline?")
    assert r["found"] and "17 Mar 2025" in r["answer"] and "13 Mar 2025" in r["answer"]


def test_unresolved_issues_and_blocked_tasks(saved):
    r = ask(saved["meeting_id"], "What issues remain unresolved?")
    assert r["found"] and "login" in r["answer"].lower()
    r = ask(saved["meeting_id"], "Which tasks are blocked?")
    assert r["evidence"]


def test_answer_not_in_transcript_says_not_found(saved):
    for q in ("What is the budget for marketing?", "Who is the CEO of the company?", "What was decided about Kubernetes?"):
        r = ask(saved["meeting_id"], q)
        assert r["found"] is False, q
        assert "not found" in r["answer"].lower()
        assert r["evidence"] == []


def test_person_without_tasks(saved):
    r = ask(saved["meeting_id"], "What does Sriya need to do?")
    assert r["found"] is False


def test_search_function(saved):
    a = client.get(f"/api/meetings/{saved['meeting_id']}").json()
    hits = qa.search_transcript(a, "sqlite")
    assert hits and "SQLite" in hits[0]["evidence"]["text"]


# ------------------------------------------------------------------ API
def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_analyze_response_shape(saved):
    for key in ("overview", "summary", "action_items", "decisions", "issues", "deadlines", "relationships",
                "distribution", "sentences", "participants", "entities", "keyphrases", "topics", "representation"):
        assert key in saved
    assert set(saved["distribution"]) == {"ACTION", "DECISION", "ISSUE", "SUGGESTION", "INFORMATION", "QUESTION"}
    assert sum(saved["distribution"].values()) == len(saved["sentences"])


def test_empty_and_short_input_rejected():
    assert client.post("/api/analyze", json={"transcript": "   "}).status_code == 422
    assert client.post("/api/analyze", json={"transcript": "hi"}).status_code == 422
    assert client.post("/api/analyze", json={}).status_code == 422


def test_bad_meeting_date_rejected():
    r = client.post("/api/analyze", json={"transcript": SAMPLE, "meeting_date": "10th March"})
    assert r.status_code == 422 and "meeting_date" in r.text


def test_too_long_rejected(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "MAX_TRANSCRIPT_CHARS", 100)
    r = client.post("/api/analyze", json={"transcript": "Sriya: hello team. " * 20})
    assert r.status_code == 413


def test_upload_txt_and_docx(saved):
    r = client.post("/api/analyze/upload", files={"file": ("standup.txt", SAMPLE.encode(), "text/plain")},
                    data={"meeting_date": "2025-03-10", "save": "false"})
    assert r.status_code == 200 and r.json()["title"] == "standup" and r.json()["meeting_id"] is None
    from docx import Document
    doc = Document()
    for line in SAMPLE.strip().split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    r = client.post("/api/extract-text", files={"file": ("m.docx", buf.getvalue(), "application/octet-stream")})
    assert r.status_code == 200 and "Rahul will finish" in r.json()["text"]


def test_upload_errors():
    assert client.post("/api/analyze/upload", files={"file": ("a.pdf", b"x", "application/pdf")}).status_code == 415
    assert client.post("/api/analyze/upload", files={"file": ("a.txt", b"", "text/plain")}).status_code == 422
    assert client.post("/api/extract-text", files={"file": ("a.docx", b"not a zip", "application/octet-stream")}).status_code == 422
    assert client.post("/api/extract-text", files={"file": ("a.doc", b"x", "application/msword")}).status_code == 415


def test_history_list_search_open_delete():
    r = client.post("/api/analyze", json={"transcript": SAMPLE, "title": "Findable unique title zeta"})
    mid = r.json()["meeting_id"]
    listing = client.get("/api/meetings", params={"q": "zeta"}).json()
    assert any(m["id"] == mid for m in listing["meetings"])
    assert client.get("/api/meetings", params={"q": "nothing-matches-this-xyz"}).json()["total"] == 0
    assert client.get(f"/api/meetings/{mid}").json()["title"] == "Findable unique title zeta"
    assert client.delete(f"/api/meetings/{mid}").status_code == 204
    assert client.get(f"/api/meetings/{mid}").status_code == 404
    assert client.delete(f"/api/meetings/{mid}").status_code == 404
    assert client.post(f"/api/meetings/{mid}/ask", json={"question": "anything"}).status_code == 404


def test_ask_validation(saved):
    assert client.post(f"/api/meetings/{saved['meeting_id']}/ask", json={"question": " "}).status_code == 422


def test_example_and_metrics_endpoints():
    ex = client.get("/api/example-transcript").json()
    assert "transcript" in ex and ex["meeting_date"]
    m = client.get("/api/model/metrics")
    assert m.status_code == 200 and "results" in m.json()
