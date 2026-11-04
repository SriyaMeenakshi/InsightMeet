"""Extractive meeting summary: the highlighted sentences are quotes from the transcript."""
from __future__ import annotations

import numpy as np

from .extraction import ev_ref
from .preprocessing import Preprocessed
from .representation import build_tfidf, sentence_docs


def summarize(pre: Preprocessed, labels: list[dict], res: dict, topics: list[dict], max_sentences: int = 5) -> dict:
    sents = pre.sentences
    n = len(sents)
    parts = []
    speakers = pre.speakers
    if speakers:
        parts.append(f"{len(speakers)} participant{'s' if len(speakers) != 1 else ''} ({', '.join(speakers[:6])}"
                     f"{'…' if len(speakers) > 6 else ''}) over {n} sentences.")
    else:
        parts.append(f"{n} sentences (no speaker labels).")
    if topics:
        parts.append("Most discussed: " + ", ".join(t["topic"] for t in topics[:3]) + ".")
    open_issues = sum(1 for i in res["issues"] if i["status"] == "open")
    parts.append(f"Found {len(res['actions'])} action item(s), {len(res['decisions'])} decision(s) and "
                 f"{len(res['issues'])} issue(s) ({open_issues} still open).")
    overview = " ".join(parts)

    highlights: list[dict] = []
    if n >= 3:
        docs = sentence_docs(sents)
        _vec, mat = build_tfidf(docs)
        weight = np.asarray(mat.sum(axis=1)).ravel()
        length_norm = np.array([max(len(s.content_lemmas), 1) ** 0.5 for s in sents])
        score = weight / length_norm
        evidence_ids = ({e["sentence_id"] for d in res["decisions"] if d["status"] == "confirmed" for e in d["evidence"]}
                        | {a["evidence"][0]["sentence_id"] for a in res["actions"]}
                        | {iss["evidence"][0]["sentence_id"] for iss in res["issues"]})
        for k, s in enumerate(sents):
            lab = labels[k]["label"]
            if lab in ("DECISION", "ACTION", "ISSUE"):
                score[k] += 0.4
            if s.id in evidence_ids:
                score[k] += 0.4
            if lab == "QUESTION" or len(s.tokens) < 5:
                score[k] -= 0.6
        chosen: list[int] = []
        for k in np.argsort(-score):
            if score[k] <= 0:
                break
            if any(float((mat[k] @ mat[c].T).toarray()[0, 0]) > 0.6 for c in chosen):
                continue  # skip near-duplicates (repeated information)
            chosen.append(int(k))
            if len(chosen) >= max_sentences:
                break
        highlights = [ev_ref(sents[k]) for k in sorted(chosen)]
    elif n:
        highlights = [ev_ref(s) for s in sents]
    return {"overview": overview, "highlights": highlights,
            "method": "Extractive: highlights are original transcript sentences ranked by TF-IDF weight, "
                      "boosted when they contain an extracted action, decision or issue; near-duplicates are skipped."}
