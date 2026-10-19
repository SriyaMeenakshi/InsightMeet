
import re


# Words and phrases that often indicate an assigned task
ACTION_PATTERN = re.compile(
    r"\b(i['’]?ll|we['’]?ll|will|need to|have to|"
    r"must|please|responsible for|assigned to)\b",
    re.IGNORECASE,
)

# Phrases that indicate a decision was made
DECISION_PATTERN = re.compile(
    r"\b(let['’]?s use|decided to|agreed to|"
    r"we decided|we agreed|we['’]?ll use|"
    r"we will use|approved|fine,?\s+let['’]?s use)\b",
    re.IGNORECASE,
)

# Phrases that often indicate a problem
ISSUE_PATTERN = re.compile(
    r"\b(issue|problem|blocked|blocking|failing|"
    r"not working|error|bug|delayed|too costly|"
    r"too expensive)\b",
    re.IGNORECASE,
)

# Phrases that indicate a suggestion or uncertainty
SUGGESTION_PATTERN = re.compile(
    r"\b(maybe|perhaps|could we|what if|"
    r"i suggest|we could|might|possibly)\b",
    re.IGNORECASE,
)

# Basic deadline extraction
DEADLINE_PATTERN = re.compile(
    r"\b(today|tomorrow|tonight|"
    r"monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|next week|next month|"
    r"by \w+|before \w+)\b",
    re.IGNORECASE,
)


def extract_information(
    processed_sentences: list[dict],
) -> dict:
    """Extract actions, decisions, issues, and suggestions."""

    actions = []
    decisions = []
    issues = []
    suggestions = []

    for sentence in processed_sentences:
        text = sentence["text"]
        original_text = sentence["original_text"]
        speaker = sentence["speaker"]

        item = {
            "text": text,
            "speaker": speaker,
            "evidence": original_text,
        }

        is_suggestion = bool(
            SUGGESTION_PATTERN.search(text)
        )

        # Suggestions should not automatically become decisions.
        if is_suggestion:
            suggestions.append(item)

        elif DECISION_PATTERN.search(text):
            decisions.append(item)

        # Extract possible action items.
        if ACTION_PATTERN.search(text):
            deadline_match = DEADLINE_PATTERN.search(text)

            actions.append({
                **item,
                "owner": speaker,
                "deadline": (
                    deadline_match.group(0)
                    if deadline_match else None
                ),
                "status": (
                    "tentative"
                    if is_suggestion
                    else "needs_review"
                ),
            })

        # Extract possible problems or blockers.
        if ISSUE_PATTERN.search(text):
            issues.append(item)

    return {
        "action_items": actions,
        "decisions": decisions,
        "issues": issues,
        "suggestions": suggestions,
    }
