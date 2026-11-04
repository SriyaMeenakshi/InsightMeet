import os
import sys
import tempfile
from pathlib import Path

# Isolate the database BEFORE the app is imported.
_tmp = tempfile.mkdtemp(prefix="insightmeet_test_")
os.environ["INSIGHTMEET_DB"] = str(Path(_tmp) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from app.nlp.pipeline import analyze_transcript  # noqa: E402


@pytest.fixture(scope="session")
def analyze():
    def _run(text, meeting_date="2025-03-10", title="t"):
        return analyze_transcript(text, title, meeting_date)
    return _run


@pytest.fixture(scope="session")
def example_analysis():
    text = (Path(__file__).resolve().parent.parent / "data" / "example_transcript.txt").read_text(encoding="utf-8")
    return analyze_transcript(text, "Example", "2025-03-10")
