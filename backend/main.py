
import re # regular expressions for emails or dates
from collections import Counter #counting purpose of each word in transcript
from extraction import extract_information
import spacy #for extraction of entities
from fastapi import FastAPI, HTTPException #FastAPI TO CREATE BACKEND API , HTTPException to send error response when something is wrong
from preprocessing import preprocess_transcript
from fastapi.middleware.cors import CORSMiddleware #to communicate frontend and backend working on different ports
from pydantic import BaseModel, Field #to define and validate the data out API receives and returns

app = FastAPI(title="InsightMeet API", version="0.1.0") #create FastAPI application

app.add_middleware( #for frontend communication, add rules for handling requests
    CORSMiddleware, #control cross-origin communication between frontend and backend
    allow_origins=["http://localhost:3000"], #allows requests from frontend running at this address
    allow_credentials=True, #allows credentials such as cookies, in cross-origin requests
    allow_methods=["*"], #allow all methods such as get,post
    allow_headers=["*"], #allow all requestes headers
)

try:
    nlp = spacy.load("en_core_web_sm") #loading spacy 
except OSError:
    nlp = None


class TranscriptRequest(BaseModel): #creates a datamodel that validates data sent to backend
    transcript: str = Field(min_length=1, max_length=100_000)
#the input should be a text value transcript with min 1 character to 100,000 characters

def split_sentences(text: str) -> list[str]:
    """Split text while preserving the original sentence wording."""
    text = re.sub(r"\s+", " ", text).strip() #remove whitespace
    return re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) #splits based on punctuations


def get_speaker(sentence: str) -> str | None:
    match = re.match(
        r"^\s*([A-Za-z][A-Za-z .'-]{0,39}):\s*", sentence
    )
    return match.group(1).strip() if match else None #getting speaker name


def extract_insights(transcript: str) -> dict:
    preprocessed_sentences=preprocess_transcript(transcript)
    sentences=[item['original_text'] for item in preprocessed_sentences]

    processed_sentences = preprocess_transcript(transcript)

    extracted = extract_information(processed_sentences)

    actions = []
    decisions = []
    issues = []
    suggestions = []
    topics = Counter()

    action_pattern = re.compile(
        r"\b("
        r"i['’]?ll|we['’]?ll|will|please|need to|has to|"
        r"have to|should|assigned to|responsible for"
        r")\b",
        re.IGNORECASE,
    )

    decision_pattern = re.compile(
        r"\b("
        r"let['’]?s use|decided to|agreed to|"
        r"we will use|we'll use|approved|"
        r"fine,?\s+(?:let['’]?s|we['’]?ll)"
        r")\b",
        re.IGNORECASE,
    )

    suggestion_pattern = re.compile(
        r"\b("
        r"maybe|perhaps|could we|what if|"
        r"i suggest|we could|should we"
        r")\b",
        re.IGNORECASE,
    )

    issue_pattern = re.compile(
        r"\b("
        r"issue|problem|blocked|blocking|failing|"
        r"not working|pending|delay|delayed|"
        r"too costly|too expensive|difficult"
        r")\b",
        re.IGNORECASE,
    )

    for sentence in sentences:
        speaker = get_speaker(sentence)
        item = {
            "text": sentence,
            "speaker": speaker,
            "evidence": sentence,
        }

        # Suggestions should not automatically become decisions.
        if suggestion_pattern.search(sentence):
            suggestions.append(item)

        elif decision_pattern.search(sentence):
            decisions.append(item)

        if action_pattern.search(sentence):
            actions.append({
                **item,
                "owner": speaker,
                "deadline": None,
                "status": "unverified",
            })

        if issue_pattern.search(sentence):
            issues.append(item)

        if nlp:
            doc = nlp(sentence)
            for chunk in doc.noun_chunks:
                phrase = chunk.text.lower().strip()
                if len(phrase) > 2 and phrase not in {
                    "the team", "we", "it", "this"
                }:
                    topics[phrase] += 1

    entities = []
    if nlp:
        doc = nlp(transcript)
        entities = [
            {
                "text": ent.text,
                "label": ent.label_,
            }
            for ent in doc.ents
        ]

    return {
        "summary": (
            " ".join(sentences[:3])
            if sentences else ""
        ),
        "topics": [
            {"topic": phrase, "mentions": count}
            for phrase, count in topics.most_common(10)
        ],
        "entities": entities,
        "action_items": actions,
        "decisions": decisions,
        "issues": issues,
        "suggestions": suggestions,
        "sentence_count": len(sentences),
        "notice": (
            "Initial rule-based prototype. Extracted items "
            "require verification; owners, deadlines, and "
            "decisions are not yet reliably resolved."
        ),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "InsightMeet"}


@app.post("/analyze")
def analyze(request: TranscriptRequest):
    if not request.transcript.strip():
        raise HTTPException(
            status_code=422,
            detail="Please provide a non-empty transcript.",
        )

    return extract_insights(request.transcript)
