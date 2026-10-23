
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression


# Example sentences with labels for our initial prototype.
TRAINING_DATA = [
    # ACTION
    ("I will finish the frontend by Friday", "ACTION"),
    ("I'll fix the login issue tomorrow", "ACTION"),
    ("Rahul needs to update the API", "ACTION"),
    ("Please prepare the project report", "ACTION"),
    ("Ananya will test the dashboard", "ACTION"),
    ("We need to complete the database module", "ACTION"),

    # DECISION
    ("Let's use SQLite for now", "DECISION"),
    ("We decided to use Python", "DECISION"),
    ("The team agreed to move testing to Monday", "DECISION"),
    ("We will use React for the frontend", "DECISION"),
    ("The final choice is to deploy on the cloud", "DECISION"),
    ("We approved the proposed design", "DECISION"),

    # ISSUE
    ("The API is failing", "ISSUE"),
    ("The login module is not working", "ISSUE"),
    ("We are blocked by a database error", "ISSUE"),
    ("The server keeps crashing", "ISSUE"),
    ("The integration is delayed", "ISSUE"),
    ("The application has a serious bug", "ISSUE"),

    # SUGGESTION
    ("Maybe we should use MongoDB", "SUGGESTION"),
    ("Could we try another approach", "SUGGESTION"),
    ("I suggest changing the design", "SUGGESTION"),
    ("Perhaps we can postpone the meeting", "SUGGESTION"),
    ("We could consider using an API", "SUGGESTION"),
    ("What if we use a different model", "SUGGESTION"),

    # INFORMATION
    ("The dashboard is ready", "INFORMATION"),
    ("The meeting starts at ten", "INFORMATION"),
    ("The database contains five tables", "INFORMATION"),
    ("The frontend uses React", "INFORMATION"),
    ("The project has four team members", "INFORMATION"),
    ("The server is running successfully", "INFORMATION"),
]


def build_classifier():
    """Create and train the baseline text classifier."""

    sentences = [text for text, label in TRAINING_DATA]
    labels = [label for text, label in TRAINING_DATA]

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
            ),
        ),
    ])

    model.fit(sentences, labels)
    return model


classifier = build_classifier()


def classify_sentence(sentence: str) -> dict:
    """Predict the category of a meeting sentence."""

    prediction = classifier.predict([sentence])[0]
    probabilities = classifier.predict_proba([sentence])[0]

    confidence = float(max(probabilities))

    return {
        "sentence": sentence,
        "category": prediction,
        "confidence": round(confidence, 3),
    }


if __name__ == "__main__":
    examples = [
        "I'll fix the login issue tomorrow",
        "Let's use SQLite for now",
        "The API is failing",
        "Maybe we should use MongoDB",
        "The dashboard is ready",
    ]

    for sentence in examples:
        print(classify_sentence(sentence))
