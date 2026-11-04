"""Transcript preprocessing.

Design rule: the original transcript is never modified.  Every sentence keeps
the exact character span (`start`, `end`) it occupies in the stored transcript
and its original wording (`original`).  Normalised / tokenised / lemmatised
views are *additional* fields used for analysis only.

Note on line endings: `normalize_newlines` converts CRLF/CR to LF once at
ingestion.  The converted text is the canonical transcript that is stored, so
all offsets refer to it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from .lexicon import NOT_SPEAKER_LABELS

try:  # stop words need no model download
    from spacy.lang.en.stop_words import STOP_WORDS as _SPACY_STOP
except Exception:  # pragma: no cover
    _SPACY_STOP = set()

# Words that carry meaning in meetings even though they are "stop words".
_KEEP = {"not", "no", "never", "cannot", "can't", "won't", "n't", "will", "should", "must", "need"}
STOP_WORDS = frozenset(w for w in _SPACY_STOP if w not in _KEEP) | {
    "okay", "ok", "yeah", "yes", "um", "uh", "hmm", "like", "just", "also", "guys", "gonna",
}


def normalize_newlines(text: str) -> str:
    text = text.replace("﻿", "").replace("\x00", "")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (used for the analysis view only)."""
    return re.sub(r"\s+", " ", text).strip()


_CONTRACTIONS = {
    "lets": "let's", "isnt": "isn't", "arent": "aren't", "wasnt": "wasn't", "werent": "weren't", "dont": "don't",
    "doesnt": "doesn't", "didnt": "didn't", "cant": "can't", "wont": "won't", "couldnt": "couldn't",
    "wouldnt": "wouldn't", "shouldnt": "shouldn't", "hasnt": "hasn't", "havent": "haven't", "im": "i'm",
    "ive": "i've", "youre": "you're", "theyre": "they're", "weve": "we've", "thats": "that's", "whats": "what's",
    "theres": "there's", "heres": "here's", "shes": "she's",
}
_CONTRACTION_RE = re.compile(r"\b(" + "|".join(_CONTRACTIONS) + r")\b(?!\s+(?:us|you|me|them|him|her)\b)", re.I)
_ILL_RE = re.compile(r"\bill\b(?=\s+(?:do|fix|take|handle|test|finish|update|send|check|write|try|get|look|review|work|"
                     r"set|make|ping|pick|build|deploy|prepare|share|call|email|follow|be|sort|start|add|talk|ask|draft)\b)", re.I)


def restore_contractions(text: str) -> str:
    """'lets use sqlite, i cant test' -> "let's use sqlite, i can't test".

    Messy chat transcripts drop apostrophes; restoring them lets the cue
    patterns work.  Only the analysis view (`Sentence.text`) is changed - the
    evidence (`Sentence.original`) is never touched.
    """
    def fix(m: re.Match) -> str:
        rep = _CONTRACTIONS[m.group(1).lower()]
        return rep.capitalize() if m.group(1)[0].isupper() else rep

    text = _CONTRACTION_RE.sub(fix, text)
    text = _ILL_RE.sub(lambda m: "I'll" if m.group(0)[0].isupper() else "i'll", text)
    # "yep ill pair with dev": a bare 'ill' right after a discourse word / punctuation is "i'll"
    return _ILL_AFTER_RE.sub(lambda m: m.group(1) + "i'll ", text)


_ILL_AFTER_RE = re.compile(r"((?:^|[,;.!?]\s*|\b(?:and|ok|okay|yeah|yep|yes|sure|so|then|also|but|well|fine|right|alright)\s+))ill\s+(?=[a-z])", re.I)


# ---------------------------------------------------------------- speakers
_TS = r"(?:\[?\(?\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?\)?\]?)"
_NAME_WORD = r"[A-Za-z][A-Za-z.'\-]*"
_LABEL_RE = re.compile(
    rf"^(?P<lead>\s*(?:[-*•]\s+)?(?:{_TS}\s*[-–]?\s*)?)"
    rf"(?P<name>{_NAME_WORD}(?:\s+{_NAME_WORD}){{0,2}})"
    rf"(?:\s*[\[(]\s*{_TS}\s*[\])])?\s*:\s*(?P<body>.*)$"
)


def parse_speaker_line(line: str) -> tuple[str | None, int]:
    """Return (speaker, body_offset_in_line).  speaker is None if no label."""
    m = _LABEL_RE.match(line)
    if not m:
        return None, 0
    name = m.group("name").strip().strip(".")
    words = name.split()
    if name.lower() in NOT_SPEAKER_LABELS or words[0].lower() in NOT_SPEAKER_LABELS and len(words) > 1:
        return None, 0
    if len(name) > 32:
        return None, 0
    if len(words) > 1 and not all(w[0].isupper() for w in words):
        return None, 0  # "Agenda for today:" is not a speaker
    if re.fullmatch(r"[A-Za-z]", name):
        return None, 0
    return name, m.start("body")


def canonical_speaker(name: str) -> str:
    """Display name: tidy casing for all-lower / all-upper labels."""
    return name.title() if (name.islower() or name.isupper()) else name


# ---------------------------------------------------------------- sentences
_ABBREV = {"e.g", "i.e", "vs", "etc", "dr", "mr", "mrs", "ms", "prof", "approx",
           "fig", "st", "sr", "jr", "inc", "ltd", "co", "p.m", "a.m", "w/o", "cf", "est"}
_BOUNDARY = re.compile(r"""([.!?]+["')\]]*)(\s+)(?=["'(\[]?[A-Za-z0-9])""")


def split_into_spans(text: str) -> list[tuple[int, int]]:
    """Sentence spans (relative to `text`), splitting after . ! ? and abbreviations-aware."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        before = text[start:m.start(1) + 1]
        last_word = re.findall(r"[A-Za-z.]+$", text[start:m.start(1)] + ".")
        token = (last_word[0] if last_word else "").rstrip(".").lower()
        punct = m.group(1)
        if punct.startswith(".") and (token in _ABBREV or re.fullmatch(r"[A-Za-z]", token or "")):
            continue
        if punct == "." and re.search(r"\d$", text[start:m.start(1)]) and re.match(r"\d", text[m.end():m.end() + 1] or ""):
            continue  # decimals / list numbering like "3. 5"
        end = m.end(1)
        if text[start:end].strip():
            spans.append((start, end))
        start = m.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    # trim whitespace inside spans
    out = []
    for s, e in spans:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            out.append((s, e))
    return out


# ---------------------------------------------------------------- NLP model
@lru_cache(maxsize=1)
def get_nlp():
    """Load spaCy once.  Returns None when the model is unavailable."""
    try:
        import spacy
        return spacy.load("en_core_web_sm")
    except Exception:
        return None


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['’.\-][A-Za-z0-9]+)*")


@dataclass
class Sentence:
    id: int
    index: int
    turn_index: int
    speaker: str | None
    speaker_inherited: bool
    text: str                 # cleaned view (speaker label removed, whitespace collapsed)
    original: str             # exact slice of the transcript
    start: int
    end: int
    tokens: list[str] = field(default_factory=list)
    lemmas: list[str] = field(default_factory=list)
    content_lemmas: list[str] = field(default_factory=list)
    noun_lemmas: list[str] = field(default_factory=list)
    is_question: bool = False
    doc: object | None = field(default=None, repr=False)


@dataclass
class Preprocessed:
    text: str
    sentences: list[Sentence]
    speakers: list[str]
    warnings: list[str]
    spacy_available: bool


def _naive_lemma(tok: str) -> str:
    t = tok.lower()
    for suf, rep in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)] + rep
    return t


def preprocess(raw_text: str) -> Preprocessed:
    text = normalize_newlines(raw_text)
    warnings: list[str] = []
    sentences: list[Sentence] = []
    speakers_seen: dict[str, str] = {}
    last_speaker: str | None = None
    turn = -1
    labelled_lines = 0
    pos = 0

    for line in text.split("\n"):
        line_start = pos
        pos += len(line) + 1
        if not line.strip():
            continue
        speaker, body_off = parse_speaker_line(line)
        inherited = False
        if speaker:
            labelled_lines += 1
            key = speaker.lower()
            speakers_seen.setdefault(key, canonical_speaker(speaker))
            speaker = speakers_seen[key]
            last_speaker = speaker
            turn += 1
        else:
            body_off = 0
            if last_speaker is not None:
                speaker, inherited = last_speaker, True  # continuation of a chat message
            else:
                turn += 1
        body = line[body_off:]
        for s, e in split_into_spans(body):
            abs_s, abs_e = line_start + body_off + s, line_start + body_off + e
            original = text[abs_s:abs_e]
            clean = restore_contractions(normalize_whitespace(original))
            if not re.search(r"[A-Za-z0-9]", clean):
                continue
            sentences.append(Sentence(
                id=len(sentences), index=len(sentences), turn_index=turn,
                speaker=speaker, speaker_inherited=inherited, text=clean,
                original=original, start=abs_s, end=abs_e,
                is_question=clean.rstrip().endswith("?"),
            ))

    if not sentences:
        warnings.append("No sentences could be extracted from the text.")
    elif labelled_lines == 0:
        warnings.append("No speaker labels were found (expected lines like 'Name: message'). "
                        "Owners can only be taken from names mentioned in the text.")
    elif any(s.speaker is None for s in sentences):
        warnings.append("Some lines appear before the first speaker label and have no speaker.")

    nlp = get_nlp()
    if nlp is not None and sentences:
        for sent, doc in zip(sentences, nlp.pipe([s.text for s in sentences], batch_size=64)):
            sent.doc = doc
            toks = [t for t in doc if not t.is_space and not t.is_punct]
            sent.tokens = [t.text for t in toks]
            sent.lemmas = [t.lemma_.lower() for t in toks]
            content = [t for t in toks if t.lemma_.lower() not in STOP_WORDS
                       and t.text.lower() not in STOP_WORDS and re.search(r"[A-Za-z0-9]", t.text)]
            sent.content_lemmas = [t.lemma_.lower() for t in content]
            sent.noun_lemmas = [t.lemma_.lower() for t in content if t.pos_ in ("NOUN", "PROPN", "X")]
    else:
        if sentences:
            warnings.append("spaCy model 'en_core_web_sm' not found; using simplified tokenisation "
                            "(run: python -m spacy download en_core_web_sm).")
        for sent in sentences:
            toks = _TOKEN_RE.findall(sent.text)
            sent.tokens = toks
            sent.lemmas = [_naive_lemma(t) for t in toks]
            sent.content_lemmas = [l for t, l in zip(toks, sent.lemmas) if t.lower() not in STOP_WORDS and len(l) > 1]
            sent.noun_lemmas = list(sent.content_lemmas)

    return Preprocessed(
        text=text, sentences=sentences, speakers=list(speakers_seen.values()),
        warnings=warnings, spacy_available=nlp is not None,
    )
