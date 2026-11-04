import csv

from app import config
from app.nlp import classification as C


def test_dataset_splits_do_not_leak():
    rows = list(csv.DictReader(open(config.DATASET_PATH, encoding="utf-8")))
    by_split = {"train": set(), "validation": set(), "test": set()}
    templates = {"train": set(), "validation": set(), "test": set()}
    for r in rows:
        by_split[r["split"]].add(r["text"].strip().lower().rstrip(".?!"))
        templates[r["split"]].add(r["template_id"])
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        assert not (by_split[a] & by_split[b]), f"identical sentences in {a} and {b}"
        assert not (templates[a] & templates[b]), f"template shared by {a} and {b}"


def test_all_classes_present_in_every_split():
    data = C.load_split()
    for split, (_, y) in data.items():
        assert set(y) == set(C.LABELS), split


def test_handwritten_set_is_disjoint_from_training():
    train = {t.lower().rstrip(".?!") for t in C.load_split()["train"][0]}
    hand = {t.lower().rstrip(".?!") for t in C.load_handwritten()[0]}
    assert not (train & hand)


def test_rule_layer_basic_cases():
    cases = {
        "Maybe we should use MongoDB": "SUGGESTION",
        "Let's use SQLite for now": "DECISION",
        "Rahul will finish the frontend by Friday": "ACTION",
        "Kiran, can you update the docs by Tuesday?": "ACTION",
        "What is the status of testing?": "QUESTION",
        "Testing is blocked because the login is broken": "ISSUE",
    }
    for text, expected in cases.items():
        assert C.rule_label(text)[0] == expected, text


def test_suggestion_question_is_not_a_plain_question():
    assert C.rule_label("What if we use Redis?")[0] == "SUGGESTION"
    assert C.rule_label("Should we move the demo?")[0] == "SUGGESTION"


def test_model_predicts_a_valid_label_with_probability():
    label, conf, src = C.predict_with_rules("The dashboard has four tabs")
    assert label in C.LABELS and 0.0 <= conf <= 1.0 and src in ("rules", "model")


def test_statement_without_question_shape_never_labelled_question():
    label, _, _ = C.predict_with_rules("sqlite is fine for the prototype and cheaper")
    assert label != "QUESTION"


def test_evaluation_reports_real_metrics_structure():
    m = C.evaluate_all()
    t = m["results"]["logreg"]["test"]
    assert 0 <= t["accuracy"] <= 1 and 0 <= t["macro_f1"] <= 1
    cm = t["confusion_matrix"]
    assert len(cm) == 6 and all(len(r) == 6 for r in cm)
    assert sum(map(sum, cm)) == t["n"]  # the matrix accounts for every test sentence
    for kind in ("logreg", "naive_bayes", "svm", "logreg_plus_rules"):
        assert kind in m["results"]


def test_hybrid_does_not_regress_below_floor():
    """Regression guard only: a floor well below the measured value, not an accuracy claim."""
    x, y = C.load_handwritten()
    pred = [C.predict_with_rules(t)[0] for t in x]
    acc = sum(p == t for p, t in zip(pred, y)) / len(y)
    assert acc >= 0.7
