"""Train the sentence classifier, evaluate it, and save model + metrics.

Run (from the backend folder):  python scripts/train_classifier.py
Outputs: models/sentence_classifier.joblib and models/metrics.json
The numbers printed are whatever the evaluation really produced - nothing is hard-coded.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.nlp.classification import LABELS, train_and_save  # noqa: E402


def main() -> None:
    m = train_and_save()
    print("Dataset sizes:", m["dataset"]["sizes"])
    for name, res in m["results"].items():
        for split, s in res.items():
            print(f"{name:20s} {split:12s} n={s['n']:4d} acc={s['accuracy']:.3f} "
                  f"P={s['macro_precision']:.3f} R={s['macro_recall']:.3f} F1={s['macro_f1']:.3f}")
    cm = m["results"]["logreg"]["test"]["confusion_matrix"]
    print("\nLogistic regression test confusion matrix (rows=true, cols=pred):", LABELS)
    for l, row in zip(LABELS, cm):
        print(f"{l:12s}", row)
    print("\n" + m["caveat"])


if __name__ == "__main__":
    main()
