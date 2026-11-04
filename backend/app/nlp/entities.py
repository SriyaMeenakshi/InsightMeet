"""Entity extraction: spaCy NER + transparent lexicons + speaker labels."""
from __future__ import annotations

import re
from collections import defaultdict

from .lexicon import NOT_PEOPLE, WEEKDAYS, MONTHS, find_tech
from .preprocessing import Preprocessed

_PROJECT_RE = re.compile(
    r"\b(?:project|product|app|platform|system|tool)\s+(?P<a>[A-Z][\w-]{2,}(?:\s[A-Z][\w-]{2,})?)"
    r"|\b(?:the\s+)?(?P<b>[A-Z][\w-]{2,}(?:\s[A-Z][\w-]{2,})?)\s+(?:project|app|platform|system)\b")
_PROJECT_STOP = {"The", "This", "That", "Our", "New", "Old", "Main", "Next", "Final", "First", "Last", "Test", "Demo"}


_ADDRESS_RE = re.compile(
    r"(?:^|(?<=[.!?]\s))(?:(?:hey|ok|okay|so|and)[, ]+)?(?P<n>[A-Z][a-z]{2,})\s*,\s*(?:can|could|would|will|please)\b")
_ASSIGN_RE = re.compile(
    r"(?<![\w])(?P<n>[A-Z][a-z]{2,})\s+(?:will|is going to|needs to|has to|should)\s+(?:also\s+)?[a-z]+")


def first_names(speakers: list[str]) -> dict[str, str]:
    """alias (lowercase) -> canonical speaker name, including first-name aliases."""
    out: dict[str, str] = {}
    for sp in speakers:
        out[sp.lower()] = sp
        out.setdefault(sp.split()[0].lower(), sp)
    return out


def extract_entities(pre: Preprocessed) -> tuple[list[dict], dict[str, str]]:
    """Return (entities, people_alias_map).

    people_alias_map maps lowercase names (speakers, first names and spaCy PERSON
    mentions) to a canonical display name; extractors use it to recognise owners.
    """
    ents: dict[tuple[str, str], dict] = {}

    def add(text: str, label: str, sid: int, source: str):
        key = (text.lower(), label)
        e = ents.setdefault(key, {"text": text, "label": label, "count": 0, "sentence_ids": [], "source": source})
        e["count"] += 1
        if sid not in e["sentence_ids"]:
            e["sentence_ids"].append(sid)

    people = first_names(pre.speakers)
    speaker_re = (re.compile(r"\b(" + "|".join(re.escape(a) for a in sorted(people, key=len, reverse=True)) + r")\b", re.I)
                  if people else None)

    for s in pre.sentences:
        if s.speaker:
            add(s.speaker, "PERSON", s.id, "speaker label") if s.id == 0 or pre.sentences[s.id - 1].speaker != s.speaker else None
        if speaker_re:
            for m in speaker_re.finditer(s.text):
                add(people[m.group(1).lower()], "PERSON", s.id, "participant name")
        # people who never speak but are addressed / assigned: "Kiran, can you ..." / "Meera will ..."
        for rx, kind in ((_ADDRESS_RE, "address"), (_ASSIGN_RE, "assign")):
            for m in rx.finditer(s.text):
                nm = m.group("n")
                if nm.lower() in NOT_PEOPLE or find_tech(nm):
                    continue
                if kind == "assign" and m.start("n") == 0 and s.doc is not None:
                    tok = next((t for t in s.doc if t.idx == 0), None)
                    if tok is not None and tok.pos_ != "PROPN":
                        continue
                if people.setdefault(nm.lower(), nm) == nm:
                    add(nm, "PERSON", s.id, "addressed / assigned by name")
        for display, cat, _a, _b in find_tech(s.text):
            add(display, "TECHNOLOGY", s.id, f"lexicon ({cat})")
        for m in _PROJECT_RE.finditer(s.text):
            name = (m.group("a") or m.group("b") or "").strip()
            if name and name.split()[0] not in _PROJECT_STOP and name.lower() not in NOT_PEOPLE:
                add(name, "PROJECT", s.id, "pattern")
        if s.doc is not None:
            for ent in s.doc.ents:
                txt = ent.text.strip()
                low = txt.lower()
                if low in NOT_PEOPLE or low in WEEKDAYS or low in MONTHS or len(txt) < 2:
                    continue
                if ent.label_ != "PERSON" and low in people:
                    continue  # spaCy mislabels first names as places / organisations
                if ent.label_ == "PERSON":
                    if txt[0].isupper() and len(txt) > 2:
                        canon = people.get(low)
                        if canon is None and not any(low == t[0].lower() for t in find_tech(txt)):
                            people.setdefault(low, txt)  # a new person mentioned but not speaking
                        add(people.get(low, txt), "PERSON", s.id, "spaCy NER")
                elif ent.label_ == "ORG":
                    if not find_tech(txt):
                        add(txt, "ORGANIZATION", s.id, "spaCy NER")
                elif ent.label_ in ("GPE", "LOC", "FAC"):
                    add(txt, "LOCATION", s.id, "spaCy NER")
                elif ent.label_ in ("DATE", "TIME"):
                    add(txt, "DATE", s.id, "spaCy NER")
                elif ent.label_ == "PRODUCT" and not find_tech(txt):
                    add(txt, "PROJECT", s.id, "spaCy NER (product)")

    # a speaker label is evidence of a person even if the speaker is never mentioned
    for sp in pre.speakers:
        key = (sp.lower(), "PERSON")
        ents.setdefault(key, {"text": sp, "label": "PERSON", "count": 0, "sentence_ids": [], "source": "speaker label"})

    out = sorted(ents.values(), key=lambda e: (e["label"], -e["count"], e["text"].lower()))
    return out, people
