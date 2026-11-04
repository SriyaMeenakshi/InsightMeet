"""Relationship extraction between people, tasks, issues, decisions and components.

Every relationship says whether it is *explicit* (stated in a sentence) or
*inferred* (derived from a keyword/technology category), and carries evidence.
"""
from __future__ import annotations

import re

from . import cues
from .extraction import Extractor, ev_ref
from .lexicon import find_tech

_CATEGORY_COMPONENT = {"database": "Database", "frontend framework": "Frontend", "backend framework": "Backend / API",
                       "cloud": "Deployment", "styling": "Frontend", "ml": "NLP / Model"}


def extract_relationships(res: dict, ex: Extractor) -> list[dict]:
    rels: list[dict] = []
    seen: set[tuple] = set()

    def add(rtype, src, tgt, explicit, basis, conf, evidence):
        key = (rtype, src["kind"], src.get("id") or src["text"].lower(), tgt["kind"], tgt.get("id") or tgt["text"].lower())
        if key in seen:
            return
        seen.add(key)
        rels.append({"id": f"R{len(rels) + 1}", "type": rtype, "source": src, "target": tgt, "explicit": explicit,
                     "basis": basis, "confidence": round(conf, 2), "evidence": evidence})

    actions = res["actions"]

    def action_node(a):
        return {"kind": "action", "id": a["id"], "text": a["task"]}

    def best_action(text: str, exclude: str | None = None):
        best, sc = None, 0.0
        for a in actions:
            if a["id"] == exclude:
                continue
            v = ex.link_score(a["task"], text)
            if v > sc:
                best, sc = a, v
        return (best, sc) if best is not None and sc >= 0.34 else (None, 0.0)

    # 1) person ASSIGNED_TO task
    for a in actions:
        for o in a["owners"]:
            confirmed = a["commitment"] != "requested" or a.get("_accepted")
            add("ASSIGNED_TO", {"kind": "person", "id": None, "text": o}, action_node(a), bool(confirmed),
                a["owner_basis"] or "owner stated" if confirmed else "requested of this person; no acceptance found",
                a["confidence"], a["evidence"][:2])

    # 2) issue BLOCKS activity
    for iss in res["issues"]:
        if not iss.get("blocked_activity") or iss["status"] == "resolved":
            continue
        a, sc = best_action(iss["blocked_activity"])
        tgt = action_node(a) if a else {"kind": "text", "id": None, "text": iss["blocked_activity"]}
        add("BLOCKS", {"kind": "issue", "id": iss["id"], "text": iss["problem"]}, tgt, True,
            "stated in the sentence" + ("" if a else " (blocked activity not matched to a tracked task)"),
            iss["confidence"], iss["evidence"][:2])
        if a is not None:
            a["blocked"] = True
            if iss["id"] not in a["blocked_by"]:
                a["blocked_by"].append(iss["id"])

    # 3) task DEPENDS_ON task
    for i, s in enumerate(ex.sents):
        if s.is_question:
            continue
        text = s.text
        first = second = None
        m = cues.DEPENDS_RE.match(text)
        if m:
            second, first = m.group("second"), m.group("first")
        else:
            m = cues.AFTER_RE.match(text) or (cues.THEN_AFTER_RE.match(text) if ex.by_sentence_actions.get(i) else None)
            if m:
                first, second = m.group("first"), m.group("second")
            else:
                m = cues.CANT_UNTIL_RE.search(text)
                if m:
                    second, first = m.group("impact"), m.group("problem")
        if not (first and second):
            continue
        own = ex.by_sentence_actions.get(i, [])
        a2 = own[0] if own and ex.link_score(own[0]["task"], second) >= 0.2 or (own and m.re is cues.THEN_AFTER_RE) else None
        if a2 is None:
            a2, _ = best_action(second)
        a1, _ = best_action(first, exclude=a2["id"] if a2 else None)
        if a1 is None and a2 is None:
            continue
        n2 = action_node(a2) if a2 else {"kind": "text", "id": None, "text": cues.clean_task(second)}
        n1 = action_node(a1) if a1 else {"kind": "text", "id": None, "text": cues.clean_task(first)}
        add("DEPENDS_ON", n2, n1, True, "stated in the sentence" + ("" if (a1 and a2) else " (one side is not a tracked task)"),
            0.7 if (a1 and a2) else 0.55, [ev_ref(s)])

    # 4) decision AFFECTS component
    for d in res["decisions"]:
        if d["status"] == "superseded":
            continue
        for c in d["components"]:
            add("AFFECTS", {"kind": "decision", "id": d["id"], "text": d["text"]}, {"kind": "component", "id": None, "text": c},
                True, "component named in the decision sentence", d["confidence"], d["evidence"][:2])
        for name, cat, _a, _b in find_tech(d["text"]):
            comp = _CATEGORY_COMPONENT.get(cat)
            if comp and comp not in d["components"]:
                add("AFFECTS", {"kind": "decision", "id": d["id"], "text": d["text"]}, {"kind": "component", "id": None, "text": comp},
                    False, f"inferred: {name} is a {cat}", min(d["confidence"], 0.6), d["evidence"][:2])
    return rels
