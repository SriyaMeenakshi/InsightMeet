"""Meeting-specific question answering.

Answers are assembled ONLY from (a) items already extracted from this
transcript and (b) transcript sentences retrieved by TF-IDF similarity.
Nothing is generated from outside knowledge; if nothing relevant is found the
answer says so.
"""
from __future__ import annotations

import re

from .lexicon import find_components
from .preprocessing import STOP_WORDS
from .representation import Retriever

_INTENT_WORDS = {
    "responsible", "owner", "own", "handle", "handling", "work", "working", "doing", "charge", "assign", "assigned",
    "deadline", "due", "latest", "earliest", "decision", "decide", "make", "made", "issue", "problem", "unresolved",
    "remain", "open", "task", "action", "item", "blocked", "block", "say", "mention", "discuss", "meeting",
    "transcript", "suggest", "idea", "current", "final", "last", "first", "still", "anyone", "people", "team", "tell",
    "list", "show", "give", "many", "status", "need", "take", "taking", "agree", "agreed", "date", "propose", "proposal",
    "participant", "attend", "what", "which", "who", "when", "know", "think", "talk", "say", "said",
}


def _terms(text: str) -> list[str]:
    return Retriever.query_terms(text)


def _ev(analysis_sentences: list[dict], sid: int) -> dict:
    s = analysis_sentences[sid]
    return {"sentence_id": s["id"], "speaker": s["speaker"], "text": s["original"], "start": s["start"], "end": s["end"]}


def _match(topic: list[str], comps: list[str], text: str) -> float:
    if not topic and not comps:
        return 0.0
    tl = set(_terms(text))
    score = len(set(topic) & tl) / len(topic) if topic else 0.0
    if comps and set(comps) & set(find_components(text)):
        score = max(score, 0.6)
    return score


def _dl(d: dict | None) -> str:
    if not d:
        return "no deadline stated"
    if d["resolved"]:
        return d["normalized"] + (f" (“{d['raw']}”)" if d["raw"].lower() not in d["normalized"].lower() else "")
    return f"“{d['raw']}” (calendar date not resolved{': ' + d['note'] if d.get('note') else ''})"


def _result(question, found, answer, method, confidence, evidence, related=None):
    seen, uniq = set(), []
    for e in evidence:
        if e["sentence_id"] not in seen:
            seen.add(e["sentence_id"])
            uniq.append(e)
    return {"question": question, "found": found, "answer": answer, "method": method,
            "confidence": round(float(confidence), 2), "evidence": uniq, "related": related or []}


def _not_found(question: str, what: str):
    return _result(question, False, f"Not found in the transcript: {what}", "structured lookup", 0.0, [])


def answer_question(analysis: dict, question: str) -> dict:
    q = question.strip()
    ql = q.lower()
    sents = analysis["sentences"]
    if not sents:
        return _not_found(q, "the transcript has no content.")
    comps = find_components(q)
    people = [p["name"] for p in analysis["participants"] if re.search(rf"\b{re.escape(p['name'].split()[0].lower())}\b", ql)]
    topic = [t for t in _terms(q) if t not in _INTENT_WORDS and t not in {p.lower() for p in people}
             and t not in {w for n in people for w in n.lower().split()}]

    def wants(*pats):
        return any(re.search(p, ql) for p in pats)

    # ---- participants
    if wants(r"\bwho (was|were|is|are) (in|at|present|attending|there)\b", r"\bparticipants?\b", r"\battendees?\b", r"\bwho attended\b",
             r"\bwho spoke\b", r"\bwho took part\b"):
        ps = analysis["participants"]
        if not ps:
            return _not_found(q, "no speaker labels were found, so participants are unknown.")
        lines = [f"{p['name']} ({p['sentences']} sentences, {int(p['share'] * 100)}% of words)" for p in ps]
        ev = [_ev(sents, next(s["id"] for s in sents if s["speaker"] == p["name"])) for p in ps]
        return _result(q, True, "Participants identified from speaker labels: " + "; ".join(lines) + ".", "structured lookup", 0.9, ev)

    # ---- blocked tasks
    if wants(r"\bblocked\b", r"\bblocking\b", r"\bblockers?\b") and wants(r"\btasks?\b", r"\bactions?\b", r"\bwhat\b", r"\bwhich\b", r"\bwork\b"):
        blocked = [a for a in analysis["action_items"] if a["blocked"]]
        issues_by_id = {i["id"]: i for i in analysis["issues"]}
        if topic or comps:
            blocked = [a for a in blocked if _match(topic, comps, a["task"]) > 0] or []
        if not blocked:
            open_blockers = [i for i in analysis["issues"] if i["status"] == "open" and i.get("blocked_activity")]
            if open_blockers and not topic:
                lines = [f"“{i['blocked_activity']}” is blocked by: {i['problem']}" for i in open_blockers]
                ev = [e for i in open_blockers for e in i["evidence"]]
                return _result(q, True, "No tracked task is linked to a blocker, but the transcript says: " + " | ".join(lines),
                               "structured lookup", 0.6, ev, [{"type": "issue", "id": i["id"]} for i in open_blockers])
            return _not_found(q, "no task is described as blocked by an open issue.")
        lines, ev = [], []
        for a in blocked:
            by = "; ".join(issues_by_id[i]["problem"] for i in a["blocked_by"] if i in issues_by_id)
            lines.append(f"“{a['task']}”{' (' + a['owner'] + ')' if a['owner'] else ''} is blocked by: {by}")
            ev += a["evidence"][:1] + [e for i in a["blocked_by"] if i in issues_by_id for e in issues_by_id[i]["evidence"][:1]]
        return _result(q, True, "Blocked tasks: " + " | ".join(lines), "structured lookup", 0.8, ev,
                       [{"type": "action", "id": a["id"]} for a in blocked])

    # ---- deadlines
    if wants(r"\bdeadlines?\b", r"\bdue\b", r"\bby when\b", r"^when\b", r"\bwhen (is|are|do|does|will|should)\b"):
        entries = analysis["deadlines"]
        if topic or comps:
            entries = [e for e in entries if _match(topic, comps, (e["task"] or "") + " " + e["evidence"]["text"]) > 0]
        if not entries:
            return _not_found(q, "no deadline matching that topic.")
        only_latest = wants(r"\blatest\b", r"\bcurrent\b", r"\bfinal\b", r"\bnew\b", r"\blast\b")
        by_task: dict[str, list[dict]] = {}
        for e in entries:
            by_task.setdefault(e["task_id"] or f"standalone-{e['id']}", []).append(e)
        lines, ev = [], []
        for chain in by_task.values():
            latest = [e for e in chain if e["is_latest"]][-1]
            task = latest["task"] or "(unspecified)"
            line = f"“{task}”{' — ' + latest['owner'] if latest['owner'] else ''}: {_dl(latest['deadline'])}"
            earlier = [e for e in chain if e["superseded"]]
            if earlier and not only_latest:
                line += " [revised from " + ", ".join(_dl(e["deadline"]) for e in earlier) + "]"
            elif earlier:
                line += " [latest; earlier: " + ", ".join(_dl(e["deadline"]) for e in earlier) + "]"
            lines.append(line)
            ev += [e["evidence"] for e in chain]
        return _result(q, True, ("Latest deadline(s): " if only_latest else "Deadlines found: ") + " | ".join(lines), "structured lookup", 0.8, ev)

    # ---- decisions
    if wants(r"\bdecisions?\b", r"\bdecided\b", r"\bagreed\b", r"\bsettled\b", r"\bchose\b", r"\bchosen\b"):
        ds = analysis["decisions"]
        if topic or comps:
            ds = [d for d in ds if _match(topic, comps, d["text"]) > 0]
        if not ds:
            return _not_found(q, "no confirmed decision" + (" about that topic." if topic or comps else "."))
        lines, ev = [], []
        for d in ds:
            tag = " (later superseded)" if d["status"] == "superseded" else ""
            lines.append(f"{d['text']}{tag}")
            ev += d["evidence"]
        return _result(q, True, "Decisions: " + " | ".join(lines), "structured lookup", 0.85, ev,
                       [{"type": "decision", "id": d["id"]} for d in ds])

    # ---- issues / unresolved
    if wants(r"\bissues?\b", r"\bproblems?\b", r"\bunresolved\b", r"\bblockers?\b", r"\brisks?\b", r"\bremain\b", r"\boutstanding\b"):
        its = analysis["issues"]
        if wants(r"\bunresolved\b", r"\bremain", r"\bopen\b", r"\boutstanding\b", r"\bstill\b", r"\bcurrent"):
            its = [i for i in its if i["status"] == "open"]
        if topic or comps:
            its = [i for i in its if _match(topic, comps, i["problem"] + " " + (i.get("blocked_activity") or "")) > 0]
        if not its:
            return _not_found(q, "no matching open issue.")
        lines = [f"{i['problem']} [{i['status']}]" + (f" — impact: {i['impact']}" if i.get("impact") else "") for i in its]
        return _result(q, True, "Issues: " + " | ".join(lines), "structured lookup", 0.8, [e for i in its for e in i["evidence"]],
                       [{"type": "issue", "id": i["id"]} for i in its])

    # ---- suggestions
    if wants(r"\bsuggest", r"\bideas?\b", r"\bproposals?\b", r"\bproposed\b"):
        ss = analysis["suggestions"]
        if topic or comps:
            ss = [s for s in ss if _match(topic, comps, s["text"]) > 0]
        if not ss:
            return _not_found(q, "no suggestions.")
        lines = [f"{s['text']} [{s['status']}]" + (f" by {s['proposer']}" if s["proposer"] else "") for s in ss]
        return _result(q, True, "Suggestions: " + " | ".join(lines), "structured lookup", 0.8, [e for s in ss for e in s["evidence"]],
                       [{"type": "suggestion", "id": s["id"]} for s in ss])

    # ---- responsibility / a person's tasks / action items
    if wants(r"\bwho\b.*\b(responsible|owns?|handl\w+|work\w* on|doing|in charge|assigned|taking|take|lead\w*|will|has to|needs? to|should)\b",
             r"\bresponsible\b", r"\bowners?\b", r"\bin charge\b") or people or wants(r"\baction items?\b", r"\btasks?\b", r"\bto-?do\b", r"\bnext steps\b"):
        acts = analysis["action_items"]
        if people:
            acts = [a for a in acts if any(p in a["owners"] for p in people)]
            what = f"No task is assigned to {', '.join(people)} in the transcript."
        else:
            what = "no matching action item."
            if topic or comps:
                acts = [a for a in acts if _match(topic, comps, a["task"] + " " + a["evidence"][0]["text"]) > 0]
        if not acts:
            return _not_found(q, what)
        lines, ev = [], []
        for a in acts:
            who = a["owner"] or "no responsible person stated"
            flags = []
            if a["commitment"] != "definite":
                flags.append(a["commitment"])
            if a["status"] == "done":
                flags.append("done")
            if a["blocked"]:
                flags.append("blocked")
            lines.append(f"{who}: “{a['task']}” — {_dl(a['deadline'])}" + (f" [{', '.join(flags)}]" if flags else ""))
            ev += a["evidence"]
        head = "Responsibility: " if wants(r"\bwho\b") else "Action items: "
        return _result(q, True, head + " | ".join(lines), "structured lookup", 0.8, ev, [{"type": "action", "id": a["id"]} for a in acts])

    # ---- summary
    if wants(r"\bsummar", r"\boverview\b", r"\bwhat was (this|the) meeting about\b", r"\bmain points?\b", r"\bkey points?\b"):
        sm = analysis["summary"]
        return _result(q, True, sm["overview"] + " Key sentences: " + " ".join(f"“{h['text']}”" for h in sm["highlights"][:3]),
                       "extractive summary", 0.7, sm["highlights"])

    # ---- retrieval fallback
    docs = []
    for s in sents:
        d = " ".join(l for l in s["lemmas"] if l not in STOP_WORDS and re.search(r"[a-z0-9]", l))
        docs.append(d or s["text"].lower())
    retr = Retriever(docs)
    hits = retr.search(q, k=3)
    qterms = set(_terms(q)) - _INTENT_WORDS
    good = [(i, sc) for i, sc in hits if sc >= 0.12 and qterms & set(docs[i].split())]
    if not good:
        return _result(q, False, "Not found in the transcript. No sentence is similar enough to this question.", "retrieval (TF-IDF)", hits[0][1] if hits else 0.0, [])
    best_i, best_sc = good[0]
    b = sents[best_i]
    ans = f"The closest passage in the transcript" + (f" ({b['speaker']})" if b["speaker"] else "") + f" says: “{b['original'].strip()}”"
    if len(good) > 1:
        ans += f" Related passages are listed as evidence."
    return _result(q, True, ans, "retrieval (TF-IDF cosine over transcript sentences)", min(best_sc * 1.5, 0.95),
                   [_ev(sents, i) for i, _ in good])


def search_transcript(analysis: dict, query: str, k: int = 8) -> list[dict]:
    sents = analysis["sentences"]
    docs = [" ".join(l for l in s["lemmas"] if l not in STOP_WORDS and re.search(r"[a-z0-9]", l)) or s["text"].lower() for s in sents]
    hits = Retriever(docs).search(query, k=k)
    out = [(i, sc) for i, sc in hits if sc > 0]
    # exact substring matches always count
    ql = query.lower().strip()
    if ql:
        for s in sents:
            if ql in s["original"].lower() and s["id"] not in {i for i, _ in out}:
                out.append((s["id"], 0.5))
    out.sort(key=lambda x: -x[1])
    return [{"score": round(sc, 3), "evidence": _ev(sents, i), "label": sents[i]["label"]} for i, sc in out[:k]]
