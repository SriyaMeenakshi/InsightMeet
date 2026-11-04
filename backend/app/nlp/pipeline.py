"""End-to-end analysis pipeline: raw transcript -> structured meeting intelligence."""
from __future__ import annotations

from collections import Counter
from datetime import date

from . import classification, entities, keyphrases, representation, summarization
from .dates import parse_meeting_date
from .extraction import Extractor
from .preprocessing import Preprocessed, get_nlp, preprocess
from .relationships import extract_relationships

PUBLIC_HIDDEN = ("_",)


def _public(obj):
    """Drop internal helper keys (prefixed with '_') recursively."""
    if isinstance(obj, dict):
        return {k: _public(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_public(v) for v in obj]
    if isinstance(obj, set):
        return sorted(obj)
    return obj


def analyze_transcript(raw_text: str, title: str | None = None, meeting_date: str | date | None = None) -> dict:
    ref = parse_meeting_date(meeting_date) if isinstance(meeting_date, str) or meeting_date is None else meeting_date
    pre: Preprocessed = preprocess(raw_text)
    warnings = list(pre.warnings)
    if len(pre.sentences) < 3:
        warnings.append("Very short transcript: results will be sparse.")

    labels = classification.classify_sentences([s.text for s in pre.sentences])
    ents, people = entities.extract_entities(pre)

    ex = Extractor(pre, labels, people, ref)
    res = ex.run()
    rels = extract_relationships(res, ex)

    topics = keyphrases.extract_topics(pre)
    kps = keyphrases.extract_keyphrases(pre)
    summary = summarization.summarize(pre, labels, res, topics)
    rep = representation.describe_representations(pre.sentences)

    # participants
    stats: dict[str, dict] = {}
    last_turn: dict[str, int] = {}
    for s in pre.sentences:
        if not s.speaker:
            continue
        st = stats.setdefault(s.speaker, {"name": s.speaker, "sentences": 0, "turns": 0, "words": 0})
        st["sentences"] += 1
        st["words"] += len(s.tokens)
        if last_turn.get(s.speaker) != s.turn_index:
            st["turns"] += 1
            last_turn[s.speaker] = s.turn_index
    total_words = sum(v["words"] for v in stats.values()) or 1
    for v in stats.values():
        v["share"] = round(v["words"] / total_words, 3)
        v["actions_owned"] = sum(1 for a in res["actions"] if v["name"] in a["owners"])
    participants = sorted(stats.values(), key=lambda v: -v["words"])

    sentences_out = []
    for s, lab in zip(pre.sentences, labels):
        sentences_out.append({
            "id": s.id, "index": s.index, "turn_index": s.turn_index, "speaker": s.speaker,
            "speaker_inherited": s.speaker_inherited, "text": s.text, "original": s.original,
            "start": s.start, "end": s.end, "label": lab["label"], "confidence": lab["confidence"],
            "label_source": lab["source"], "model_label": lab["model_label"], "model_confidence": lab["model_confidence"],
            "tokens": s.tokens, "lemmas": s.lemmas, "is_question": s.is_question,
        })
    distribution = {l: 0 for l in classification.LABELS}
    distribution.update(Counter(l["label"] for l in labels))

    result = _public({**res, "relationships": rels})
    # review queue
    review = []
    for kind, key, textkey in (("action", "action_items", "task"), ("decision", "decisions", "text"),
                               ("issue", "issues", "problem"), ("deadline", "deadlines", "task")):
        src = result["actions"] if key == "action_items" else result[key if key != "action_items" else "actions"]
        for it in src:
            if it.get("needs_review"):
                review.append({"item_type": kind, "item_id": it["id"], "text": it.get(textkey) or it["evidence"]["text"],
                               "reasons": it["review_reasons"]})

    unresolved = sum(1 for d in result["deadlines"] if not d["deadline"]["resolved"] and d["is_latest"])
    if ref is None and unresolved:
        warnings.append(f"No meeting date was given, so {unresolved} deadline(s) such as 'Friday' or 'tomorrow' "
                        "were left unresolved instead of guessing. Add a meeting date to resolve them.")
    words = sum(len(s.tokens) for s in pre.sentences)
    open_issues = sum(1 for i in result["issues"] if i["status"] == "open")
    nlp = get_nlp()
    analysis = {
        "meeting_id": None, "created_at": None,
        "title": (title or "").strip() or "Untitled meeting",
        "meeting_date": ref.isoformat() if ref else None,
        "transcript": pre.text,
        "overview": {
            "title": (title or "").strip() or "Untitled meeting", "meeting_date": ref.isoformat() if ref else None,
            "sentences": len(pre.sentences), "words": words, "participants": len(participants),
            "action_items": len(result["actions"]), "decisions": len(result["decisions"]),
            "issues_open": open_issues, "issues_total": len(result["issues"]),
            "suggestions": len(result["suggestions"]), "needs_review": len(review), "unresolved_deadlines": unresolved,
        },
        "summary": summary, "topics": topics, "keyphrases": kps, "participants": participants, "entities": ents,
        "action_items": result["actions"], "decisions": result["decisions"], "issues": result["issues"],
        "suggestions": result["suggestions"], "deadlines": result["deadlines"], "relationships": result["relationships"],
        "distribution": distribution, "review_queue": review, "sentences": sentences_out, "representation": rep,
        "warnings": warnings,
        "nlp_info": {
            "spacy_model": nlp.meta["name"] + " " + nlp.meta["version"] if nlp is not None else None,
            "classifier": "TF-IDF + Logistic Regression with rule layer",
            "confidence_note": "Item confidence is a heuristic cue-strength score, not a calibrated probability.",
        },
    }
    return analysis
