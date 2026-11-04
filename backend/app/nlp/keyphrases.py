"""Keyphrase and topic extraction (unsupervised, from the transcript only)."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from .lexicon import COMPONENT_TERMS, find_components, find_tech
from .preprocessing import STOP_WORDS, Preprocessed

_BAD_HEADS = {"we", "it", "this", "that", "they", "you", "i", "he", "she", "there", "what", "who", "everyone",
              "something", "anything", "thing", "things", "one", "lot", "way", "guys", "bit", "time", "today",
              "tomorrow", "week", "day", "friday", "monday", "tuesday", "wednesday", "thursday", "kind", "sort",
              "point", "question", "idea", "need", "sure", "okay", "yeah", "meeting", "morning", "sec"}


def _candidates(pre: Preprocessed) -> dict[str, set[int]]:
    cand: dict[str, set[int]] = defaultdict(set)
    for s in pre.sentences:
        if s.doc is not None:
            for nc in s.doc.noun_chunks:
                toks = [t for t in nc if not t.is_stop and not t.is_punct and t.pos_ != "PRON"
                        and t.text.lower() not in STOP_WORDS and re.search(r"[A-Za-z]", t.text)]
                if not toks:
                    continue
                phrase = " ".join(t.lemma_.lower() if t.pos_ in ("NOUN",) else t.text.lower() for t in toks)
                if toks[-1].lemma_.lower() in _BAD_HEADS or phrase in _BAD_HEADS or len(phrase) < 3:
                    continue
                cand[phrase].add(s.id)
        else:
            words = [w for w in s.content_lemmas if w not in _BAD_HEADS]
            for a, b in zip(words, words[1:]):
                cand[f"{a} {b}"].add(s.id)
            for w in words:
                cand[w].add(s.id)
        for display, _cat, _s, _e in find_tech(s.text):
            cand[display.lower()].add(s.id)
    return cand


def extract_keyphrases(pre: Preprocessed, top_n: int = 12) -> list[dict]:
    n = max(len(pre.sentences), 1)
    cand = _candidates(pre)
    df = Counter()
    for s in pre.sentences:
        for w in set(s.content_lemmas):
            df[w] += 1
    scored = []
    for phrase, sids in cand.items():
        words = phrase.split()
        idf = sum(math.log((n + 1) / (df.get(w, 0) + 1)) + 1 for w in words) / len(words)
        score = len(sids) * idf * (1 + 0.15 * (len(words) - 1))
        scored.append((score, phrase, sorted(sids)))
    scored.sort(key=lambda x: -x[0])

    chosen: list[tuple[float, str, list[int]]] = []
    for score, phrase, sids in scored:
        redundant = False
        for _, p2, s2 in chosen:
            if (phrase in p2 or p2 in phrase) and set(sids) <= set(s2) | set(sids) and abs(len(sids) - len(s2)) <= 1:
                redundant = True
                break
        if not redundant:
            chosen.append((score, phrase, sids))
        if len(chosen) >= top_n:
            break
    top = chosen[0][0] if chosen else 1
    return [{"phrase": p, "score": round(sc / top, 3), "mentions": len(sids), "sentence_ids": sids}
            for sc, p, sids in chosen]


def extract_topics(pre: Preprocessed) -> list[dict]:
    """Group sentences by the project component they talk about."""
    by_comp: dict[str, list[int]] = defaultdict(list)
    for s in pre.sentences:
        for c in find_components(s.text):
            by_comp[c].append(s.id)
    total = sum(len(v) for v in by_comp.values()) or 1
    out = [{"topic": c, "mentions": len(ids), "share": round(len(ids) / total, 3),
            "first_sentence_id": ids[0], "sentence_ids": ids}
           for c, ids in by_comp.items()]
    return sorted(out, key=lambda t: -t["mentions"])
