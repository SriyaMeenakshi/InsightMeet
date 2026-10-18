
import re #Regular expression library


def normalize_text(text: str) -> str: #remove unnecessary spaces
    """Normalize whitespace without changing the original wording."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text) 
    return text.strip()


def split_sentences(text: str) -> list[str]: #seperates transcripts to sentences
    """Split a transcript into sentences."""
    text = normalize_text(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def extract_speaker(sentence: str) -> str | None: #identifies speaker in Name: message format
    """Extract a speaker name from formats such as 'Rahul: Hello'."""
    match = re.match(
        r"^\s*([A-Za-z][A-Za-z .'-]{0,39}):\s*(.+)$",
        sentence,
    )
    return match.group(1).strip() if match else None


def preprocess_transcript(text: str) -> list[dict]: #combine everything into one while preserving original sentence
    """Return structured sentences with their speakers."""
    sentences = split_sentences(text)
    result = []

    for sentence in sentences:
        speaker = extract_speaker(sentence)

        # Keep the original sentence available as evidence.
        content = sentence
        if speaker:
            content = re.sub(
                r"^\s*[A-Za-z][A-Za-z .'-]{0,39}:\s*",
                "",
                sentence,
                count=1,
            )

        result.append({
            "speaker": speaker,
            "text": content,
            "original_text": sentence,
        })

    return result
