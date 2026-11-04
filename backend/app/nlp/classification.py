"""Sentence classification: TF-IDF + Logistic Regression baseline, plus a
transparent rule layer for high-precision cues.

Labels: ACTION, DECISION, ISSUE, SUGGESTION, INFORMATION, QUESTION.
"""
from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from typing import Iterable

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             precision_recall_fscore_support)
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from .. import config
from . import cues

LABELS = ["ACTION", "DECISION", "ISSUE", "SUGGESTION", "INFORMATION", "QUESTION"]
SEED = 42


# ------------------------------------------------------------------ data
def load_split(path=config.DATASET_PATH) -> dict[str, tuple[list[str], list[str]]]:
    out: dict[str, tuple[list[str], list[str]]] = {"train": ([], []), "validation": ([], []), "test": ([], [])}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[row["split"]][0].append(row["text"])
            out[row["split"]][1].append(row["label"])
    return out


def load_handwritten(path=config.HANDWRITTEN_PATH) -> tuple[list[str], list[str]]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r["text"] for r in rows], [r["label"] for r in rows]


# ------------------------------------------------------------------ models
def make_model(kind: str = "logreg") -> Pipeline:
    # Stop words are KEPT for classification: "will", "should", "not", "maybe"
    # are exactly the words that signal intent.
    tfidf = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    clf = {
        "logreg": LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced", random_state=SEED),
        "naive_bayes": MultinomialNB(alpha=0.3),
        "svm": LinearSVC(C=1.0, class_weight="balanced", random_state=SEED),
    }[kind]
    return Pipeline([("tfidf", tfidf), ("clf", clf)])


def _scores(y_true, y_pred) -> dict:
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    per = classification_report(y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0)
    return {
        "n": len(y_true),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_precision": round(float(p), 4),
        "macro_recall": round(float(r), 4),
        "macro_f1": round(float(f), 4),
        "per_class": {l: {k: round(float(per[l][k]), 4) for k in ("precision", "recall", "f1-score")}
                      | {"support": int(per[l]["support"])} for l in LABELS},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
    }


def evaluate_all() -> dict:
    """Train on `train`, tune/compare on `validation`, report ONCE on `test`.

    Also evaluates on the hand-written set, which is never used for training,
    for the plain model and for the model + rule layer.
    """
    data = load_split()
    (Xtr, ytr), (Xva, yva), (Xte, yte) = data["train"], data["validation"], data["test"]
    hw_x, hw_y = load_handwritten()

    results = {}
    for kind in ("logreg", "naive_bayes", "svm"):
        m = make_model(kind).fit(Xtr, ytr)
        results[kind] = {
            "validation": _scores(yva, m.predict(Xva)),
            "test": _scores(yte, m.predict(Xte)),
            "handwritten": _scores(hw_y, m.predict(hw_x)),
        }

    # served model = logistic regression baseline (+ rule layer), refit on train+validation
    served = make_model("logreg").fit(Xtr, ytr)
    hybrid_hw = [predict_with_rules(t, served)[0] for t in hw_x]
    hybrid_te = [predict_with_rules(t, served)[0] for t in Xte]
    results["logreg_plus_rules"] = {
        "test": _scores(yte, hybrid_te),
        "handwritten": _scores(hw_y, hybrid_hw),
    }
    return {
        "labels": LABELS,
        "dataset": {
            "path": "backend/data/sentences.csv",
            "type": "synthetic template-generated sentences (split by template) + hand-written evaluation set",
            "sizes": {k: len(v[0]) for k, v in data.items()} | {"handwritten": len(hw_x)},
            "label_counts_train": {l: ytr.count(l) for l in LABELS},
        },
        "split_policy": "Split by sentence template: no template appears in more than one split.",
        "results": results,
        "caveat": ("Read these numbers with care. (1) The synthetic data is template-generated, so test scores are "
                   "optimistic. (2) The rule layer was written by the developers while looking at the same "
                   "template families, so 'logreg_plus_rules' on the synthetic test split is NOT an independent "
                   f"measurement. (3) The hand-written set (n={len(hw_x)}) is small and was labelled by the "
                   "developers, who also tuned some rules after seeing its errors; treat it as a rough indicator, "
                   "not as proof of real-world accuracy. No evaluation on real, independently labelled meetings "
                   "has been done."),
    }


def train_and_save() -> dict:
    metrics = evaluate_all()
    data = load_split()
    X = data["train"][0] + data["validation"][0]
    y = data["train"][1] + data["validation"][1]
    model = make_model("logreg").fit(X, y)
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, config.MODEL_PATH)
    config.METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


@lru_cache(maxsize=1)
def get_model() -> Pipeline:
    if config.MODEL_PATH.exists():
        try:
            return joblib.load(config.MODEL_PATH)
        except Exception:
            pass
    if config.DATASET_PATH.exists():
        train_and_save()
        return joblib.load(config.MODEL_PATH)
    raise RuntimeError("No sentence classifier available. Run: python scripts/build_dataset.py && python scripts/train_classifier.py")


def load_metrics() -> dict | None:
    if config.METRICS_PATH.exists():
        return json.loads(config.METRICS_PATH.read_text(encoding="utf-8"))
    return None


# ------------------------------------------------------------------ rule layer
_WORK_SHOULD = re.compile(r"\bwe should (?:finish|complete|fix|write|prepare|test|update|review|build|implement|deploy|"
                          r"submit|send|finali[sz]e|create|design|schedule|set up|check|add|document|plan)\b", cues.I)
_VERBS = cues.WORK_VERB_HINT.pattern.replace("^(?:", "(?:", 1)
_NAMED_WILL_WORK = re.compile(
    rf"\b[A-Z][a-z]+ (?:will|{cues._A}ll|is going to|is gonna|needs to|has to) (?:also )?{_VERBS}", 0)
_NAMEY_ACTION =re.compile(r"\b[A-Za-z]+\s+(?:will|needs? to|has to|is going to|is responsible for|is handling)\s+\w+", cues.I)
_CANDIDATE_SELF = re.compile(
    rf"\b(?:{cues.SELF_DEFINITE}|{cues.SELF_OBLIG}|{cues.SELF_TENTATIVE})\s+\w+", cues.I)


def rule_label(text: str) -> tuple[str | None, str | None]:
    """High-precision rules.  Returns (label, reason) or (None, None) to defer to the model."""
    t = text.strip()
    low = t.lower()
    ends_q = t.endswith("?")
    hedged = cues.is_hedged(low)

    # requests ("Can you ...", "Rahul, could you ...", "Please ...") are ACTIONS even though phrased as questions
    if re.match(r"^(?:(?:hey|so|okay|ok|and)[, ]+)?(?:[A-Za-z]+[, ]+)?(?:can|could|would|will) you\b", t, cues.I) \
            and not re.match(r"^(?:could|can|would) you (?:explain|tell|say|clarify|confirm|remind)\b", t, cues.I):
        return "ACTION", "request addressed to someone"
    if re.match(r"^(?:(?:hey|so|okay|ok|and|[A-Za-z]+)[, ]+)?please\s+\w+", t, cues.I) and not ends_q:
        return "ACTION", "polite imperative"

    if cues.SUGGESTION_RE.search(low) and not cues.DECISION_RE.search(low):
        return "SUGGESTION", "suggestion phrase"
    if re.search(r"\bi (?:can|will|'ll) try\b", low):
        return "ACTION", "tentative first-person commitment"
    if ends_q:
        return "QUESTION", "ends with '?'"
    if cues.DECISION_RE.search(low) and not hedged and not cues.QUESTION_START_RE.match(t):
        return "DECISION", "explicit decision phrase"
    if re.search(r"\b(?:we|i|they) (?:should|could|can|might)\b.*\b(?:later|eventually|someday|in the future|down the line|next phase|phase two)\b", low):
        return "SUGGESTION", "future / optional proposal"
    if cues.ACCEPT_STRONG_RE.search(low) and len(low.split()) <= 10:
        return "ACTION", "accepts a request"
    if len(low.split()) <= 6 and (cues.AFFIRM_RE.match(low) or cues.REJECT_RE.match(low)) and not cues.DECISION_RE.search(low) \
            and not re.search(cues.SELF_DEFINITE + r"\s+\w+", low):
        return "INFORMATION", "short reaction / agreement"
    if re.match(r"^(?:thanks|thank you|great|good|cool|nice|ok|okay|right|alright|hello|hi|hey|bye|cheers|welcome)\b", low) and len(low.split()) <= 5:
        return "INFORMATION", "conversational filler"
    if (cues.DONE_RE.search(low) or cues.ISSUE_RESOLVED_RE.search(low)) and not cues.UNFINISHED_RE.search(low) \
            and not re.search(r"\b(?:will|'ll|going to|to be|should be|need|needs|must|until|when|once|if|can't|cannot)\b", low) and not ends_q:
        return "INFORMATION", "status update (done / fixed)"
    if _WORK_SHOULD.search(low):
        return "ACTION", "obligation phrase without owner"
    if re.search(rf"\b(?:{cues.SELF_DEFINITE}|{cues.SELF_OBLIG})\s+\w+", low):
        return "ACTION", "first-person commitment"
    if re.search(rf"\b(?:{cues.SELF_TENTATIVE})\s+\w+", low) \
            and re.search(r"\b(?:i can|i could|i might|i may|i'll try|i will try|i can try)\s+(?:also )?(?:take|do|handle|finish|fix|write|update|review|test|prepare|send|check|look|pick|set|build|draft)", low):
        return "ACTION", "tentative first-person commitment"
    if re.search(r"\b(?:needs? to|has to|have to|must|is responsible for|is going to|will take care of|is assigned to|assigned to)\b", low) \
            and not cues.ISSUE_STRONG_RE.search(low):
        return "ACTION", "obligation / assignment phrase"
    if _NAMED_WILL_WORK.search(t) and not cues.QUESTION_START_RE.match(t):
        return "ACTION", "named person + will + work verb"
    if re.match(r"^(who|what|when|where|why|how|which)\b", t, cues.I) \
            or re.match(r"^(?:has|does|did|is|are|do|was) (?:anyone|anybody|someone|everyone)\b", t, cues.I) \
            or re.match(r"^anyone\b", t, cues.I):
        return "QUESTION", "question form without '?'"
    if cues.ISSUE_STRONG_RE.search(low):
        return "ISSUE", "failure / blocker phrase"
    if cues.SUGGESTION_RE.search(low):
        return "SUGGESTION", "suggestion phrase"
    return None, None


def predict_with_rules(text: str, model: Pipeline | None = None) -> tuple[str, float, str]:
    """Return (label, confidence, source) where source is 'rules' or 'model'."""
    model = model or get_model()
    proba = model.predict_proba([text])[0] if hasattr(model, "predict_proba") else None
    classes = list(model.classes_)
    if proba is not None and "QUESTION" in classes and not (text.strip().endswith("?") or cues.QUESTION_START_RE.match(text.strip())):
        # a statement that is neither phrased as a question nor ends in '?' cannot be a QUESTION
        proba = proba.copy()
        proba[classes.index("QUESTION")] = 0.0
        proba = proba / proba.sum()
    if proba is None:
        pred = model.predict([text])[0]
        conf = 0.0
    else:
        idx = int(np.argmax(proba))
        pred, conf = classes[idx], float(proba[idx])
    label, _ = rule_label(text)
    if label is not None:
        # the rule decides the label; report the model's agreement as confidence
        p_label = float(proba[classes.index(label)]) if proba is not None and label in classes else 0.0
        return label, round(max(0.75, p_label) if pred == label else 0.7, 3), "rules"
    return pred, round(conf, 3), "model"


def classify_sentences(texts: Iterable[str]) -> list[dict]:
    model = get_model()
    out = []
    for t in texts:
        label, conf, src = predict_with_rules(t, model)
        probs = model.predict_proba([t])[0]
        out.append({"label": label, "confidence": conf, "source": src,
                    "model_label": str(model.classes_[int(np.argmax(probs))]),
                    "model_confidence": round(float(np.max(probs)), 3)})
    return out
