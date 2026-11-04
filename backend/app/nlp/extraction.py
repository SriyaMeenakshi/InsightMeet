"""Information extraction: actions, decisions, issues, suggestions, deadlines.

Principles
----------
* Every item keeps the sentence(s) it came from (`evidence`) with character offsets.
* The *speaker* is not assumed to be the *owner*: an owner is only set from
  (a) first-person commitments ("I'll ..."), (b) a name in the sentence
  ("Rahul will ..."), or (c) a request that the named person accepted.
* Anything uncertain gets `needs_review=True` plus human-readable reasons
  instead of a guessed value.
* `confidence` is a heuristic cue-strength score, NOT a calibrated probability.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from . import cues
from .cues import I
from .dates import DateMatch, find_dates
from .lexicon import find_components, find_tech
from .preprocessing import Preprocessed, Sentence, get_nlp, STOP_WORDS

RANK = {"unassigned": 0, "tentative": 1, "requested": 2, "definite": 3}
_FILL = (r"(?:(?:ok|okay|so|and|then|also|well|alright|yeah|yep|yup|yes|sure|fine|right|actually|oh|hmm|um|uh|but|now|"
         r"good|great|cool|perfect|thanks|thank you|anyway|hey|guys|everyone|i think|i guess|i believe|maybe|"
         r"perhaps|probably|hopefully)\b[,.!]?\s*)*")
_NON_REQUEST_VERBS = re.compile(r"^(?:hear|see|explain|tell|say|repeat|confirm|remind|clarify|help|give me a|share your screen|"
                                r"mute|unmute|speak|join|turn|come|be there|make it|let me know)\b", I)
_NOUN_TASK_CUES = {"is responsible for", "are responsible for", "will be responsible for", "is handling", "are handling",
                   "is taking", "is working on", "is in charge of", "owns", "will take", "takes", "will own", "will handle"}
_STATE_RE = re.compile(
    r"\b(?:is|are|was|were|keeps?|still|stopped|has|have|had|got|gets)\b[^.]*\b(?:broken|failing|failed|crash\w*|not working|"
    r"blocked|stuck|down|delayed|throwing|timing out|timeout|error|bug|buggy)\b|"
    r"\b(?:isn['’]t|aren['’]t|doesn['’]t|won['’]t|can['’]t|cannot|couldn['’]t)\b", I)
_DUE_RE = re.compile(r"\b(?:due|deadline|submission|submit(?:ted)? by|must be (?:done|ready|submitted|finished|completed) by|needs? to be (?:done|ready|submitted|finished|completed))\b", I)
_FUTURE_BEFORE_DONE = re.compile(r"\b(?:will|['’]ll|going to|to be|should be|need(?:s)? to be|must be|has to be|until|when|once|if)\b", I)


def ev_ref(s: Sentence) -> dict:
    return {"sentence_id": s.id, "speaker": s.speaker, "text": s.original, "start": s.start, "end": s.end}


def _dl_dict(dm: DateMatch) -> dict:
    return {"raw": dm.raw, "kind": dm.kind, "resolved": dm.resolved,
            "date": dm.date.isoformat() if dm.date else None,
            "precision": dm.precision, "normalized": dm.normalized, "note": dm.note}


def _same_deadline(a: dict | None, b: dict | None) -> bool:
    if not a or not b:
        return False
    if a["resolved"] and b["resolved"]:
        return a["date"] == b["date"]
    return a["normalized"].lower() == b["normalized"].lower()


class Extractor:
    def __init__(self, pre: Preprocessed, labels: list[dict], people: dict[str, str], meeting_date: date | None):
        self.pre, self.sents, self.labels = pre, pre.sentences, labels
        self.people, self.ref = people, meeting_date
        self._key_cache: dict[str, set[str]] = {}
        names = sorted(people, key=len, reverse=True)
        self.NAME = "(?:" + "|".join(re.escape(n) for n in names) + ")" if names else r"(?!x)x"
        self.NAME_RE = re.compile(rf"\b{self.NAME}\b", I)
        N = self.NAME
        self.dates = [find_dates(s.text, meeting_date) for s in self.sents]

        self.re_self = re.compile(
            rf"^(?P<pre>{_FILL})(?:{N}\s*[,:]\s*)?(?P<pre2>{_FILL})"
            rf"(?:(?P<t>{cues.SELF_TENTATIVE})|(?P<d>{cues.SELF_DEFINITE})|(?P<o>{cues.SELF_OBLIG}))\b[\s,]*(?P<task>.+)$", I)
        self.re_self_mid = re.compile(
            rf"[,;]\s*(?:and |so |but |then |also )?(?:(?P<t>{cues.SELF_TENTATIVE})|(?P<d>{cues.SELF_DEFINITE})|(?P<o>{cues.SELF_OBLIG}))\b[\s,]*(?P<task>.+)$", I)
        owner_list = rf"{N}(?:\s*(?:,|and|&)\s*{N})*"
        self.re_third = re.compile(
            rf"^(?P<pre>{_FILL})(?P<owner>{owner_list})\s+(?:also\s+)?(?P<cue>{cues.MODAL_THIRD})\s+(?P<task>.+)$", I)
        self.re_assigned = re.compile(
            rf"^(?P<pre>{_FILL})(?P<task>.+?)\s+(?:is|was|has been|will be|gets|got)\s+(?:now\s+)?(?:assigned|given|handed|delegated|allocated)\s+to\s+(?P<owner>{owner_list})\b", I)
        self.re_let = re.compile(
            rf"^(?P<pre>{_FILL})(?:let|have|get)(?:['’]s let)?\s+(?P<owner>{owner_list})\s+(?P<task>(?:handle|take|do|own|lead|manage|write|build|test|work on|prepare|review|fix|deploy|draft|design).+)$", I)
        self.re_marker = re.compile(
            rf"^(?:action(?: item)?s?|todo|to-do|task)\s*[:\-–]\s*(?P<owner>{owner_list})\s*(?:to|will|:|-|–)\s*(?P<task>.+)$", I)
        self.re_req_named = re.compile(
            rf"^(?P<pre>{_FILL})(?P<owner>{N})\s*[,:]?\s*(?:(?:can|could|would|will) you|please)(?: please)?\s+(?P<task>.+?)\??$", I)
        self.re_req_unnamed = re.compile(
            rf"^(?P<pre>{_FILL})(?:(?:can|could|would|will) you(?: please)?|please)\s+(?P<task>.+?)\??$", I)
        self.re_group = re.compile(
            rf"^(?P<pre>{_FILL})(?P<subj>we|someone|somebody|everyone|everybody|the team|team|whoever|one of us)\s+(?:also\s+)?"
            rf"(?:(?:really|just|still|definitely|all)\s+)?(?P<cue>need to|needs to|have to|has to|must|should|ought to|will|[’']ll|are going to|gotta|got to)\s+(?P<task>.+)$", I)

        # outputs
        self.actions: list[dict] = []
        self.decisions: list[dict] = []
        self.issues: list[dict] = []
        self.suggestions: list[dict] = []
        self.standalone_deadlines: list[dict] = []
        self.by_sentence_actions: dict[int, list[dict]] = defaultdict(list)
        self.by_sentence_requests: dict[int, list[dict]] = defaultdict(list)
        self.handled_dates: set[int] = set()
        self._a = self._d = self._i = self._s = self._dl = 0

    # ------------------------------------------------------------ utilities
    def keyset(self, text: str) -> set[str]:
        """Content lemmas (for duplicate detection)."""
        if text in self._key_cache:
            return self._key_cache[text]
        nlp = get_nlp()
        if nlp is not None:
            doc = nlp(text)
            ks = {t.lemma_.lower() for t in doc if t.text.lower() not in STOP_WORDS and t.lemma_.lower() not in STOP_WORDS
                  and re.search(r"[A-Za-z0-9]", t.text)}
        else:
            ks = {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP_WORDS}
        self._key_cache[text] = ks
        return ks

    def topic_key(self, text: str) -> set[str]:
        """Nouns + component tags (for linking items that talk about the same thing)."""
        nlp = get_nlp()
        ks: set[str] = set()
        if nlp is not None:
            for t in nlp(text):
                if t.pos_ in ("NOUN", "PROPN") and t.lemma_.lower() not in STOP_WORDS and t.lemma_.lower() not in cues.GENERIC_TASK_WORDS:
                    ks.add(t.lemma_.lower())
        else:
            ks = {w for w in self.keyset(text) if w not in cues.GENERIC_TASK_WORDS}
        ks |= {f"@{c}" for c in find_components(text)}
        ks |= {f"#{n.lower()}" for n, _c, _a, _b in find_tech(text)}
        return ks

    def link_score(self, a: str, b: str) -> float:
        ka, kb = self.topic_key(a), self.topic_key(b)
        if not ka or not kb:
            return 0.0
        inter = ka & kb
        if not inter:
            return 0.0
        score = len(inter) / len(ka | kb)
        if any(x.startswith("@") for x in inter):
            score += 0.35
        return min(score, 1.0)

    @staticmethod
    def jaccard(a: set, b: set) -> float:
        return len(a & b) / len(a | b) if a and b else 0.0

    def owners_from(self, text: str) -> list[str]:
        out: list[str] = []
        for m in self.NAME_RE.finditer(text):
            n = self.people[m.group(0).lower()]
            if n not in out:
                out.append(n)
        return out

    def _strip_dates(self, i: int, task: str, offset_in_sentence: int) -> str:
        """Remove date expressions that fall inside the task phrase."""
        s_text = self.sents[i].text
        cut = [(dm.start, dm.end) for dm in self.dates[i] if dm.start >= offset_in_sentence - 1]
        if not cut:
            return task
        base = s_text[offset_in_sentence:]
        for st, en in sorted(cut, reverse=True):
            a, b = max(st - offset_in_sentence, 0), max(en - offset_in_sentence, 0)
            base = base[:a] + base[b:]
        return base

    def _first_pos_verb(self, s: Sentence, task: str) -> bool:
        if s.doc is None:
            return False
        pos = s.text.lower().find(task.lower()[:25])
        if pos < 0:
            return False
        for t in s.doc:
            if t.idx >= pos:
                return t.pos_ == "VERB"
        return False

    def _valid_task(self, s: Sentence, task: str, noun_ok: bool = False) -> bool:
        if len(task) < 3 or not re.search(r"[A-Za-z]{2,}", task):
            return False
        if cues.NON_TASK_START.match(task):
            return False
        if noun_ok:
            return True
        return bool(cues.WORK_VERB_HINT.match(task) or self._first_pos_verb(s, task))

    # ------------------------------------------------------------ commitments
    def _commitment(self, i: int, s: Sentence) -> dict | None:
        text = s.text
        speaker = s.speaker

        def build(owner_list, basis, task_raw, task_off, kind, via, reasons=None, pre=""):
            task = cues.clean_task(self._strip_dates(i, task_raw, task_off))
            tentative = bool(cues.HEDGE_RE.search(pre or "")) or (kind == "tentative")
            commitment = "tentative" if tentative else kind
            return {"owners": owner_list, "owner_basis": basis, "task": task, "commitment": commitment,
                    "via": via, "reasons": reasons or [], "task_offset": task_off}

        # 1) markers: "Action: Rahul to test the API"
        m = self.re_marker.match(text)
        if m:
            owners = self.owners_from(m.group("owner"))
            task = m.group("task")
            if owners and self._valid_task(s, cues.clean_task(task), noun_ok=True):
                return build(owners, "action-item marker", task, m.start("task"), "definite", "marker")

        # 2) requests (also phrased as questions)
        if not text.lower().startswith(("can you hear", "can you see")):
            m = self.re_req_named.match(text)
            if m:
                task = cues.clean_task(m.group("task"))
                if self._valid_task(s, task, noun_ok=False) and not _NON_REQUEST_VERBS.match(task):
                    owner = self.people[m.group("owner").lower()]
                    return build([owner], f"requested by {speaker or 'unknown speaker'}", m.group("task"), m.start("task"),
                                 "requested", "request", pre=m.group("pre"))
            m = self.re_req_unnamed.match(text)
            if m:
                task = cues.clean_task(m.group("task"))
                if self._valid_task(s, task, noun_ok=False) and not _NON_REQUEST_VERBS.match(task):
                    return build([], f"requested by {speaker or 'unknown speaker'}", m.group("task"), m.start("task"),
                                 "requested", "request", ["The person being asked is not named"], pre=m.group("pre"))

        if s.is_question:
            return None

        # 3) passive / delegated assignment
        for rx, via in ((self.re_assigned, "assignment"), (self.re_let, "assignment")):
            m = rx.match(text)
            if m:
                owners = self.owners_from(m.group("owner"))
                task = cues.clean_task(m.group("task"))
                if owners and self._valid_task(s, task, noun_ok=(via == "assignment" and rx is self.re_assigned)):
                    return build(owners, f"assigned by {speaker or 'unknown speaker'}", m.group("task"), m.start("task"),
                                 "definite", via, pre=m.group("pre"))

        # 4) first person
        m = self.re_self.match(text) or self.re_self_mid.search(text)
        if m and not re.search(rf"\b(?:won['’]t|can['’]t|cannot|not going to)\s*$", text[:m.start("task")], I):
            task_raw = m.group("task")
            task = cues.clean_task(task_raw)
            kind = "tentative" if m.group("t") else "definite"
            pre = (m.groupdict().get("pre") or "") + (m.groupdict().get("pre2") or "")
            if self._valid_task(s, task) or cues.ACCEPT_STRONG_RE.search(text):
                if not speaker:
                    return build([], "speaker unknown", task_raw, m.start("task"), kind, "self",
                                 ["First-person commitment but the transcript has no speaker label"], pre)
                return build([speaker], "first-person commitment", task_raw, m.start("task"), kind, "self", [], pre)

        # 5) named third person
        m = self.re_third.match(text)
        if m:
            owners = self.owners_from(m.group("owner"))
            cue = m.group("cue").lower().replace("’", "'")
            task_raw = m.group("task")
            task = cues.clean_task(task_raw)
            noun_ok = cue in _NOUN_TASK_CUES
            if owners and self._valid_task(s, task, noun_ok=noun_ok):
                kind = "tentative" if cues.TENTATIVE_THIRD.match(cue) else "definite"
                if speaker and owners == [speaker]:
                    basis = "stated by the owner"
                else:
                    basis = f"named by {speaker or 'unknown speaker'}"
                return build(owners, basis, task_raw, m.start("task"), kind, "third", pre=m.group("pre"))

        # 6) group obligation
        m = self.re_group.match(text)
        if m:
            cue = m.group("cue").lower()
            task_raw = m.group("task")
            task = cues.clean_task(task_raw)
            optional = cue in ("should", "ought to") and bool(re.search(r"\b(?:later|eventually|someday|in the future|down the line)\b", text, I))
            if self._valid_task(s, task) and not optional and not (cue == "should" and self.labels[s.id]["label"] == "SUGGESTION"):
                return build([], f"group statement ('{m.group('subj').lower()}')", task_raw, m.start("task"),
                             "unassigned", "group", ["Assigned to the group, no individual is named"], pre=m.group("pre"))
        return None

    # ------------------------------------------------------------ action store
    def _new_action(self, i: int, s: Sentence, c: dict) -> dict:
        dm = self.dates[i][0] if self.dates[i] else None
        # a deadline phrase *before* the commitment still applies, e.g. "By Friday, I'll ..."
        dl = _dl_dict(dm) if dm else None
        task = c["task"]
        anaphoric = bool(re.match(r"^[a-z]+(?: care of| up| on| out)?\s+(?:it|that|this|those|these|them)\b", task, I))
        owners = c["owners"]
        conf = {"definite": 0.9, "requested": 0.7, "tentative": 0.65, "unassigned": 0.55}[c["commitment"]]
        if not owners:
            conf -= 0.1
        a = {
            "id": f"A{self._a + 1}", "task": task, "owner": ", ".join(owners) if owners else None, "owners": owners,
            "owner_basis": c["owner_basis"] if owners else None, "said_by": s.speaker, "commitment": c["commitment"],
            "deadline": dl, "original_deadline": None, "deadline_history": [], "status": "open", "blocked": False,
            "blocked_by": [], "components": find_components(task), "confidence": round(conf, 2), "mentions": 1,
            "evidence": [ev_ref(s)], "_reasons": list(c["reasons"]), "_sid": s.id, "_via": c["via"],
            "_anaphoric": anaphoric, "_accepted": False,
        }
        if dl:
            a["deadline_history"] = [{"role": "single", "deadline": dl, "evidence": ev_ref(s)}]
        a["context"] = None
        if anaphoric:
            a["_reasons"].append("Task is referred to as 'it/that'; what it refers to must be read from the earlier context")
            for j in range(s.id - 1, max(s.id - 3, -1), -1):
                a["context"] = self.sents[j].original
                break
        self._a += 1
        return a

    def _add_action(self, a: dict) -> dict:
        ka = self.keyset(a["task"])
        # "Kiran, can you test X?" ... "Kiran: I'll test it"  -> the owner accepted the request
        for ex in reversed(self.actions):
            if (ex["commitment"] == "requested" and not ex["_accepted"] and a["owners"] and set(a["owners"]) <= set(ex["owners"])
                    and a["_via"] in ("self", "third") and 0 < a["_sid"] - ex["_sid"] <= 3
                    and (a["_anaphoric"] or self.jaccard(self.keyset(ex["task"]), ka) >= 0.34)):
                ex["_accepted"] = True
                ex["commitment"] = "definite" if a["commitment"] != "tentative" else "tentative"
                ex["confidence"] = 0.88
                ex["owner_basis"] = (ex["owner_basis"] or "requested") + "; accepted by the owner"
                ex["evidence"].append(a["evidence"][0])
                if a["deadline"]:
                    if not ex["deadline"]:
                        ex["deadline"], ex["deadline_history"] = a["deadline"], a["deadline_history"]
                    elif not _same_deadline(ex["deadline"], a["deadline"]):
                        self._revise_deadline(ex, a["deadline"], a["evidence"][0])
                self.by_sentence_actions[a["_sid"]].append(ex)
                return ex
        for ex in self.actions:
            sim = self.jaccard(ex["_key"] if "_key" in ex else self.keyset(ex["task"]), ka)
            if sim < 0.6:
                continue
            compatible = (not ex["owners"] or not a["owners"] or set(ex["owners"]) == set(a["owners"]))
            if compatible:
                self._merge_action(ex, a)
                return ex
            # same task, different owners -> contradiction, keep both and flag
            msg = "Possible contradiction: a very similar task is assigned to {} in sentence {}"
            ex["_reasons"].append(msg.format(a["owner"], a["_sid"]))
            a["_reasons"].append(msg.format(ex["owner"], ex["_sid"]))
        self.actions.append(a)
        self.by_sentence_actions[a["_sid"]].append(a)
        return a

    def _merge_action(self, ex: dict, new: dict) -> None:
        ex["mentions"] += 1
        ex["evidence"].extend(e for e in new["evidence"] if e["sentence_id"] not in {x["sentence_id"] for x in ex["evidence"]})
        if not ex["owners"] and new["owners"]:
            ex["owners"], ex["owner"], ex["owner_basis"] = new["owners"], new["owner"], new["owner_basis"]
        if RANK[new["commitment"]] > RANK[ex["commitment"]]:
            ex["commitment"] = new["commitment"]
            ex["confidence"] = max(ex["confidence"], new["confidence"])
        ex["components"] = sorted(set(ex["components"]) | set(new["components"]))
        if new["deadline"]:
            if not ex["deadline"]:
                ex["deadline"] = new["deadline"]
                ex["deadline_history"] = new["deadline_history"]
            elif not _same_deadline(ex["deadline"], new["deadline"]):
                self._revise_deadline(ex, new["deadline"], new["evidence"][0])
        self.by_sentence_actions[new["_sid"]].append(ex)

    def _revise_deadline(self, action: dict, dl: dict, evidence: dict) -> None:
        hist = action["deadline_history"]
        if hist and hist[0]["role"] == "single":
            hist[0]["role"] = "original"
        elif not hist and action["deadline"]:
            hist.append({"role": "original", "deadline": action["deadline"], "evidence": action["evidence"][0]})
        hist.append({"role": "revised", "deadline": dl, "evidence": evidence})
        action["original_deadline"] = hist[0]["deadline"]
        action["deadline"] = dl

    # ------------------------------------------------------------ acceptance
    def _try_acceptance(self, i: int, s: Sentence) -> bool:
        """'Sure, I'll do it' -> attach the speaker to the request that came just before."""
        text = s.text.strip()
        strong = bool(cues.ACCEPT_STRONG_RE.search(text)) and len(text.split()) <= 10
        weak = bool(cues.ACCEPT_WEAK_RE.match(text))
        if not (strong or weak) or not s.speaker:
            return False
        for j in range(i - 1, max(i - 4, -1), -1):
            prev = self.sents[j]
            if prev.speaker == s.speaker:
                continue
            cands = [a for a in self.by_sentence_actions.get(j, [])
                     if a["commitment"] in ("requested", "definite", "tentative") and (not a["owners"] or s.speaker in a["owners"])
                     and a["said_by"] != s.speaker]
            if not cands:
                if prev.speaker != s.speaker:
                    break
                continue
            for a in cands:
                if not a["owners"]:
                    a["owners"], a["owner"], a["owner_basis"] = [s.speaker], s.speaker, "accepted a request"
                    a["_reasons"] = [r for r in a["_reasons"] if "not named" not in r]
                    a["commitment"] = "definite"
                    a["confidence"] = 0.85
                elif s.speaker in a["owners"]:
                    a["_accepted"] = True
                    if a["commitment"] in ("requested", "tentative"):
                        a["commitment"] = "definite"
                    a["owner_basis"] = (a["owner_basis"] or "") + "; confirmed by the owner"
                    a["confidence"] = max(a["confidence"], 0.88)
                a["evidence"].append(ev_ref(s))
                a["_accepted"] = True
            return True
        if strong and not weak:
            return False  # let the normal commitment path create an unlinked action
        return False

    # ------------------------------------------------------------ deadlines
    def _revision_target(self, i: int, text: str) -> tuple[dict | None, bool]:
        """Find the action a deadline-change sentence refers to. Returns (action, explicit)."""
        best, best_score = None, 0.0
        for a in self.actions:
            if a["_sid"] >= i:
                continue
            sc = self.link_score(a["task"], text)
            if a["owner"] and a["owner"].lower() in text.lower():
                sc += 0.2
            sc += 0.001 * a["_sid"]  # prefer recent on ties
            if sc > best_score:
                best, best_score = a, sc
        if best is not None and best_score >= 0.34:
            return best, True
        recent = [a for a in self.actions if a["_sid"] < i and a["deadline"] and i - a["_sid"] <= 6]
        if recent and re.search(r"\b(it|that|this|deadline|due date)\b", text, I):
            return recent[-1], False
        return None, False

    def _deadline_revision(self, i: int, s: Sentence) -> bool:
        self.handled_dates.add(i)
        dms = [d for d in self.dates[i] if d.kind != "unresolved" or d.note]
        if not dms:
            return False
        dm = dms[-1]  # the NEW date normally comes last: "from Friday to Monday"
        dl = _dl_dict(dm)
        target, explicit = self._revision_target(i, s.text)
        if target is not None:
            if not _same_deadline(target["deadline"], dl):
                if target["deadline"] is None:
                    target["deadline"] = dl
                    target["deadline_history"] = [{"role": "single", "deadline": dl, "evidence": ev_ref(s)}]
                else:
                    self._revise_deadline(target, dl, ev_ref(s))
                target["evidence"].append(ev_ref(s))
                if not explicit:
                    target["_reasons"].append("Deadline change was matched to this task by recency, not by name")
            return True
        self._dl += 1
        self.standalone_deadlines.append({
            "id": f"D{self._dl}", "task_id": None, "task": self._due_subject(s.text), "owner": None, "deadline": dl,
            "role": "standalone", "evidence": ev_ref(s), "sid": i,
            "reasons": ["Deadline change could not be linked to a specific task"],
        })
        return True

    @staticmethod
    def _due_subject(text: str) -> str | None:
        m = re.match(r"^(?:the |our )?(?P<subj>.+?)\s+(?:is|are|was|will be|has been)?\s*(?:now )?(?:due|moved|pushed|delayed|postponed|rescheduled)", text, I)
        return cues.clean_task(m.group("subj")) if m else None

    def _due_statement(self, i: int, s: Sentence) -> bool:
        """'The report is due on Friday' -> attach to a task or keep as a standalone deadline."""
        if not (self.dates[i] and _DUE_RE.search(s.text)) or s.is_question:
            return False
        self.handled_dates.add(i)
        dm = self.dates[i][-1]
        dl = _dl_dict(dm)
        target, explicit = self._revision_target(i, s.text)
        if target is not None and explicit:
            if target["deadline"] is None:
                target["deadline"] = dl
                target["deadline_history"] = [{"role": "single", "deadline": dl, "evidence": ev_ref(s)}]
                target["evidence"].append(ev_ref(s))
            elif not _same_deadline(target["deadline"], dl):
                self._revise_deadline(target, dl, ev_ref(s))
                target["evidence"].append(ev_ref(s))
            return True
        self._dl += 1
        self.standalone_deadlines.append({
            "id": f"D{self._dl}", "task_id": None, "task": self._due_subject(s.text) or cues.clean_task(s.text),
            "owner": None, "deadline": dl, "role": "standalone", "evidence": ev_ref(s), "sid": i, "reasons": [],
        })
        return True

    # ------------------------------------------------------------ main loop
    def run(self) -> dict:
        for i, s in enumerate(self.sents):
            lab = self.labels[i]
            text = s.text
            produced_action = False
            accepted = self._try_acceptance(i, s)
            c = None if accepted else self._commitment(i, s)
            if accepted:
                produced_action = True
            elif c is not None:
                a = self._new_action(i, s, c)
                self._add_action(a)
                produced_action = True
                if c["via"] == "request":
                    self.by_sentence_requests[i].append(a)

            shift = bool(cues.PURE_DEADLINE_SHIFT_RE.search(text)) or bool(re.search(r"\b(?:actually|instead|now|new)\b", text, I))
            if self.dates[i] and not s.is_question:
                if produced_action:
                    self.handled_dates.add(i)
                if not produced_action and shift and self._revision_target(i, text)[0] is not None:
                    self._deadline_revision(i, s)
                elif not produced_action and cues.PURE_DEADLINE_SHIFT_RE.search(text):
                    self._deadline_revision(i, s)
                elif not produced_action and _DUE_RE.search(text):
                    self._due_statement(i, s)

            self._decision(i, s, lab)
            self._suggestion(i, s, lab, produced_action)
            self._issue(i, s, lab, produced_action)
            self._completion(i, s)
            self._model_only(i, s, lab, produced_action)

        self._confirm_suggestions()
        self._supersede_decisions()
        return self._finalize()

    # ------------------------------------------------------------ decisions
    def _decision(self, i: int, s: Sentence, lab: dict) -> None:
        text = s.text
        if s.is_question or cues.is_hedged(text) or not cues.DECISION_RE.search(text):
            return
        if lab["label"] in ("SUGGESTION", "QUESTION"):
            return
        clean = re.sub(rf"^{_FILL}", "", text, flags=I).strip() or text
        comps = find_components(text)
        if cues.AFFIRM_RE.match(text) or re.match(r"^(?:ok|okay|yes|yeah|so)?[, ]*agreed\b", text, I):
            for d in reversed(self.decisions):  # confirmation of a decision just made
                if 0 < i - d["_sid"] <= 3 and self.link_score(d["text"], text) >= 0.34:
                    d["evidence"].append(ev_ref(s))
                    return
        if len(text.split()) < 4 and not re.search(r"\b(?:decided|approved|settled)\b", text, I):
            return
        for d in self.decisions:
            if self.jaccard(self.keyset(d["text"]), self.keyset(clean)) >= 0.7:
                d["evidence"].append(ev_ref(s))
                return
        if self.dates[i] and i not in self.handled_dates:
            self._dl += 1
            self.standalone_deadlines.append({
                "id": f"D{self._dl}", "task_id": None, "task": clean, "owner": None, "deadline": _dl_dict(self.dates[i][-1]),
                "role": "standalone", "evidence": ev_ref(s), "sid": i, "reasons": []})
        self._d += 1
        self.decisions.append({
            "id": f"D{self._d}", "text": clean, "status": "confirmed", "basis": "explicit decision statement",
            "decided_by": s.speaker, "components": comps, "supersedes": None, "superseded_by": None,
            "confidence": 0.85, "evidence": [ev_ref(s)], "_reasons": [], "_sid": i,
            "_techs": {(n.lower(), cat) for n, cat, _a, _b in find_tech(text)},
            "_revision": bool(cues.REVISION_RE.search(text)),
        })

    def _supersede_decisions(self) -> None:
        for j, later in enumerate(self.decisions):
            for earlier in self.decisions[:j]:
                if earlier["status"] == "superseded":
                    continue
                conflict = False
                for cat in {c for _n, c in earlier["_techs"]} & {c for _n, c in later["_techs"]}:
                    e_names = {n for n, c in earlier["_techs"] if c == cat}
                    l_names = {n for n, c in later["_techs"] if c == cat}
                    if e_names and l_names and not (e_names & l_names):
                        conflict = True
                if not conflict and later["_revision"] and self.link_score(earlier["text"], later["text"]) >= 0.5 \
                        and not _same_text(earlier["text"], later["text"]):
                    conflict = True
                if conflict:
                    earlier["status"], earlier["superseded_by"] = "superseded", later["id"]
                    later["supersedes"] = earlier["id"]
                    if not later["_revision"]:
                        later["_reasons"].append(f"Conflicts with earlier decision {earlier['id']}; confirm which one stands")
                        earlier["_reasons"].append(f"Later decision {later['id']} conflicts with this one")

    # ------------------------------------------------------------ suggestions
    def _suggestion(self, i: int, s: Sentence, lab: dict, produced_action: bool) -> None:
        text = s.text
        is_sug = lab["label"] == "SUGGESTION" or (cues.SUGGESTION_RE.search(text) and not cues.DECISION_RE.search(text))
        if not is_sug or (s.is_question and not cues.SUGGESTION_RE.search(text)):
            return
        if cues.AFFIRM_RE.match(text) and len(text.split()) <= 4:
            return
        self._s += 1
        self.suggestions.append({
            "id": f"S{self._s}", "text": (re.sub(rf"^{_FILL}", "", text, flags=I).strip() or text).rstrip("?").strip(),
            "proposer": s.speaker,
            "status": "unconfirmed", "tentative": cues.is_hedged(text) or bool(cues.SUGGESTION_RE.search(text)),
            "components": find_components(text), "evidence": [ev_ref(s)], "response": None, "_sid": i,
            "_techs": {(n.lower(), cat) for n, cat, _a, _b in find_tech(text)},
        })

    def _confirm_suggestions(self) -> None:
        """A suggestion becomes a decision only if somebody else clearly agrees."""
        for sug in self.suggestions:
            i = sug["_sid"]
            for j in range(i + 1, min(i + 4, len(self.sents))):
                r = self.sents[j]
                t = r.text.strip()
                if r.speaker == sug["proposer"] and sug["proposer"] is not None:
                    continue
                if cues.REJECT_RE.match(t):
                    sug["status"], sug["response"] = "rejected", ev_ref(r)
                    break
                if cues.AFFIRM_RE.match(t) or (cues.DECISION_RE.search(t) and not cues.is_hedged(t) and not r.is_question):
                    if r.is_question:
                        continue
                    sug["status"], sug["response"] = "accepted", ev_ref(r)
                    self._promote(sug, r)
                    break
                if self.labels[j]["label"] in ("ACTION", "ISSUE", "SUGGESTION") and not cues.AFFIRM_RE.match(t):
                    break  # conversation moved on; no clear answer

    def _promote(self, sug: dict, reply: Sentence) -> None:
        for d in self.decisions:
            if sug["evidence"][0]["sentence_id"] in {e["sentence_id"] for e in d["evidence"]} or \
                    reply.id in {e["sentence_id"] for e in d["evidence"]}:
                if sug["evidence"][0]["sentence_id"] not in {e["sentence_id"] for e in d["evidence"]}:
                    d["evidence"].insert(0, sug["evidence"][0])
                return
        self._d += 1
        txt = re.sub(r"^(?:maybe|perhaps|what if|how about|why don['’]t we|should we|could we|we could|i suggest|i propose)\s+", "",
                     sug["text"], flags=I).rstrip("?").strip()
        self.decisions.append({
            "id": f"D{self._d}", "text": txt[:1].upper() + txt[1:], "status": "confirmed",
            "basis": f"suggestion by {sug['proposer'] or 'unknown'} accepted by {reply.speaker or 'unknown'}",
            "decided_by": reply.speaker, "components": sug["components"], "supersedes": None, "superseded_by": None,
            "confidence": 0.75, "evidence": [sug["evidence"][0], ev_ref(reply)], "_reasons": [], "_sid": sug["_sid"],
            "_techs": set(sug["_techs"]), "_revision": bool(cues.REVISION_RE.search(reply.text)),
        })
        self.decisions.sort(key=lambda d: d["_sid"])

    # ------------------------------------------------------------ issues
    def _issue(self, i: int, s: Sentence, lab: dict, produced_action: bool) -> None:
        text = s.text
        if s.is_question or cues.REJECT_RE.match(text) and len(text.split()) < 4:
            return
        strong = cues.ISSUE_STRONG_RE.search(text)
        weak = cues.ISSUE_WEAK_RE.search(text)
        if lab["label"] in ("DECISION",):
            return
        if lab["label"] == "SUGGESTION" and not strong:
            return
        if not (strong or (weak and lab["label"] == "ISSUE")):
            return
        if produced_action and not _STATE_RE.search(text):
            return  # "I'll fix the login bug" is a plan, not a statement of a problem
        m_res = cues.ISSUE_RESOLVED_RE.search(text)
        if m_res and not strong:
            return

        problem, impact, activity = text, None, None
        mcu = cues.CANT_UNTIL_RE.search(text)
        if mcu and re.match(r"^(?:it|its|it's|that|this)\b", mcu.group("problem").strip(), I):
            for ex in reversed(self.issues):
                if ex["status"] == "open" and 0 < i - ex["_sid"] <= 3:
                    act = mcu.group("impact").strip(" .,")
                    ex["evidence"].append(ev_ref(s))
                    if not ex["blocked_activity"]:
                        ex["blocked_activity"], ex["impact"] = act, f"{act} cannot proceed"
                    return
        for rx in (cues.BLOCK_BECAUSE_RE, cues.BLOCKING_RE, cues.CANT_UNTIL_RE, cues.WAITING_RE):
            m = rx.match(text) or (rx.search(text) if rx is cues.CANT_UNTIL_RE else None)
            if m:
                problem = m.group("problem").strip(" .,")
                activity = re.sub(r"\s+(?:is|are|was|were)\s*$", "", m.group("impact").strip(" .,"), flags=I)
                impact = f"{activity} is blocked" if rx is cues.BLOCK_BECAUSE_RE else f"blocks {activity}" if rx is cues.BLOCKING_RE else f"{activity} cannot proceed"
                break
        else:
            m = cues.IMPACT_CLAUSE_RE.search(text)
            if m:
                impact = m.group(0).strip(" ,;—-")
                problem = text[:m.start()].strip(" ,;—-") or text
        if produced_action:
            first = re.split(r"[,;]\s*(?:so |and |but |then )?(?:i['’]ll|i will|let me|we['’]ll)\b", text, maxsplit=1, flags=I)[0]
            problem = first.strip() or problem

        comps = find_components(problem) or find_components(text)
        techs = [n for n, _c, _a, _b in find_tech(problem)]
        component = comps[0] if comps else (techs[0] if techs else None)
        # an issue seen before? merge (repeated information)
        for ex in self.issues:
            if self.jaccard(self.keyset(ex["problem"]), self.keyset(problem)) >= 0.6:
                ex["evidence"].append(ev_ref(s))
                ex["status"] = "open" if ex["status"] == "open" else ex["status"]
                if impact and not ex["impact"]:
                    ex["impact"], ex["blocked_activity"] = impact, activity
                return
        self._i += 1
        conf = 0.85 if strong else 0.6
        reasons = []
        if not strong:
            reasons.append("Weak problem wording ('issue/risk/pending'); confirm it is a real problem")
        self.issues.append({
            "id": f"I{self._i}", "problem": cues.clean_task(problem), "component": component, "impact": impact,
            "blocked_activity": activity, "status": "open", "raised_by": s.speaker, "confidence": conf,
            "evidence": [ev_ref(s)], "_reasons": reasons, "_sid": i,
        })

    # ------------------------------------------------------------ completion / resolution
    def _completion(self, i: int, s: Sentence) -> None:
        text = s.text
        if s.is_question:
            return
        resolved = cues.ISSUE_RESOLVED_RE.search(text) and not cues.UNFINISHED_RE.search(text)
        m_done = cues.DONE_RE.search(text)
        done = m_done and not cues.UNFINISHED_RE.search(text) and not _FUTURE_BEFORE_DONE.search(text[:m_done.start()])
        if resolved:
            for iss in self.issues:
                if iss["_sid"] < i and iss["status"] == "open":
                    if self.link_score(iss["problem"], text) >= 0.34:
                        iss["status"] = "resolved"
                        iss["evidence"].append(ev_ref(s))
        if done:
            for a in self.actions:
                if a["_sid"] >= i or a["status"] == "done":
                    continue
                if a["owners"] and s.speaker and s.speaker not in a["owners"] and not self.owners_from(text):
                    continue
                if self.link_score(a["task"], text) >= 0.34:
                    a["status"] = "done"
                    a["evidence"].append(ev_ref(s))
                    break

    # ------------------------------------------------------------ model-only candidates
    def _model_only(self, i: int, s: Sentence, lab: dict, produced_action: bool) -> None:
        if lab["source"] != "model" or lab["confidence"] < 0.7 or s.is_question:
            return
        if lab["label"] == "ACTION" and not produced_action and not self.by_sentence_actions.get(i):
            c = {"owners": [], "owner_basis": None, "task": cues.clean_task(s.text), "commitment": "unassigned",
                 "via": "model", "reasons": ["Detected by the statistical classifier only; no clear owner or verb cue"],
                 "task_offset": 0}
            a = self._new_action(i, s, c)
            a["confidence"] = round(min(0.5, lab["confidence"] * 0.6), 2)
            self._add_action(a)
        elif lab["label"] == "DECISION" and not any(i in {e["sentence_id"] for e in d["evidence"]} for d in self.decisions):
            self._d += 1
            self.decisions.append({
                "id": f"D{self._d}", "text": s.text, "status": "confirmed", "basis": "classifier only",
                "decided_by": s.speaker, "components": find_components(s.text), "supersedes": None, "superseded_by": None,
                "confidence": 0.45, "evidence": [ev_ref(s)], "_reasons": ["Detected by the statistical classifier only"],
                "_sid": i, "_techs": {(n.lower(), cat) for n, cat, _a, _b in find_tech(s.text)}, "_revision": False})

    # ------------------------------------------------------------ finalize
    def _finalize(self) -> dict:
        for a in self.actions:
            reasons = list(dict.fromkeys(a["_reasons"]))
            if not a["owners"] and not any("not named" in r or "group" in r.lower() or "speaker" in r.lower() for r in reasons):
                reasons.append("No responsible person is stated")
            if a["commitment"] == "tentative":
                reasons.append("Tentative wording (e.g. 'maybe', 'might', 'try to'); not a firm commitment")
            if a["commitment"] == "requested" and not a["_accepted"]:
                reasons.append("Requested, but no acceptance was found in the transcript")
            dl = a["deadline"]
            if dl and dl["kind"] == "unresolved" and dl.get("note") and "Ambiguous" in dl["note"]:
                reasons.append(f"Deadline '{dl['raw']}' is ambiguous (day/month order)")
            if a["original_deadline"] and a["deadline"]:
                reasons.append(f"Deadline was revised from '{a['original_deadline']['normalized']}' to '{a['deadline']['normalized']}'; confirm the latest")
            a["review_reasons"] = reasons
            a["needs_review"] = bool(reasons) and not (len(reasons) == 1 and reasons[0].startswith("Deadline was revised"))
            if a["needs_review"]:
                a["confidence"] = round(min(a["confidence"], 0.8), 2)
        for coll in (self.decisions, self.issues):
            for x in coll:
                x["review_reasons"] = list(dict.fromkeys(x["_reasons"]))
                x["needs_review"] = bool(x["review_reasons"])
        return self._deadline_entries()

    def _deadline_entries(self) -> dict:
        entries: list[dict] = []
        n = 0
        for a in self.actions:
            hist = a["deadline_history"]
            for k, h in enumerate(hist):
                n += 1
                is_last = k == len(hist) - 1
                entries.append({
                    "id": f"DL{n}", "task_id": a["id"], "task": a["task"], "owner": a["owner"], "deadline": h["deadline"],
                    "role": h["role"], "is_latest": is_last, "superseded": not is_last, "evidence": h["evidence"],
                    "needs_review": False, "review_reasons": [], "_sid": h["evidence"]["sentence_id"],
                })
        stand = []
        for sd in self.standalone_deadlines:
            n += 1
            stand.append({"id": f"DL{n}", "task_id": None, "task": sd["task"], "owner": None, "deadline": sd["deadline"],
                          "role": "standalone", "is_latest": True, "superseded": False, "evidence": sd["evidence"],
                          "needs_review": bool(sd["reasons"]), "review_reasons": sd["reasons"], "_sid": sd["sid"]})
        # chain standalone entries that talk about the same thing
        for k, e in enumerate(stand):
            for prev in stand[:k]:
                if prev["superseded"] or not (e["task"] and prev["task"]):
                    continue
                if self.link_score(prev["task"], e["task"]) >= 0.5 and not _same_deadline(prev["deadline"], e["deadline"]):
                    prev["superseded"], prev["is_latest"] = True, False
                    prev["role"], e["role"] = "original", "revised"
        entries.extend(stand)
        entries.sort(key=lambda e: e["_sid"])
        for e in entries:
            e.pop("_sid", None)
        return {"actions": self.actions, "decisions": self.decisions, "issues": self.issues,
                "suggestions": self.suggestions, "deadlines": entries}


def _same_text(a: str, b: str) -> bool:
    return re.sub(r"\W+", "", a.lower()) == re.sub(r"\W+", "", b.lower())
