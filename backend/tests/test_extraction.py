"""Extraction behaviour, including the hard cases: speaker != owner, suggestion != decision,
tentative vs definite, revised deadlines, duplicates, contradictions, missing speakers/deadlines."""


def actions_by_task(a, word):
    return [x for x in a["action_items"] if word in x["task"].lower()]


def test_speaker_is_not_assumed_to_be_owner(analyze):
    a = analyze("Sriya: Rahul will finish the frontend by Friday.\nRahul: okay.")
    act = actions_by_task(a, "frontend")[0]
    assert act["owner"] == "Rahul" and act["said_by"] == "Sriya"
    assert "named by Sriya" in act["owner_basis"]


def test_first_person_commitment_owner_is_speaker(analyze):
    a = analyze("Kiran: I'll update the API docs by Tuesday.")
    act = actions_by_task(a, "api docs")[0]
    assert act["owner"] == "Kiran" and act["commitment"] == "definite"
    assert act["deadline"]["date"] == "2025-03-11"


def test_request_without_acceptance_is_flagged(analyze):
    a = analyze("Sriya: Kiran, can you update the API documentation by tuesday?\nAnanya: I like the new logo.")
    act = actions_by_task(a, "documentation")[0]
    assert act["owner"] == "Kiran" and act["commitment"] == "requested"
    assert act["needs_review"] and any("acceptance" in r for r in act["review_reasons"])


def test_request_accepted_becomes_definite(analyze):
    a = analyze("Sriya: Kiran, can you update the API documentation by tuesday?\nKiran: sure, I'll do it.")
    act = actions_by_task(a, "documentation")[0]
    assert act["commitment"] == "definite" and not act["needs_review"]
    assert len(a["action_items"]) == 1  # acceptance merged, not duplicated
    assert len(act["evidence"]) == 2


def test_tentative_commitment_is_marked(analyze):
    a = analyze("Ananya: maybe I can try to write the unit tests.")
    act = actions_by_task(a, "unit tests")[0]
    assert act["commitment"] == "tentative" and act["needs_review"]


def test_group_obligation_has_no_invented_owner(analyze):
    a = analyze("Sriya: we need to prepare the deployment script.")
    act = actions_by_task(a, "deployment")[0]
    assert act["owner"] is None and act["needs_review"]


def test_suggestion_is_not_a_decision_until_accepted(analyze):
    a = analyze("Sriya: Maybe we should use MongoDB for the database.\nRahul: Let me think about it.")
    assert a["suggestions"] and a["suggestions"][0]["status"] == "unconfirmed"
    assert not any("mongodb" in d["text"].lower() for d in a["decisions"])


def test_accepted_suggestion_becomes_decision_with_both_sentences_as_evidence(analyze):
    a = analyze("Sriya: Maybe we should use PostgreSQL for the database.\nRahul: Sounds good, let's do that.")
    assert a["suggestions"][0]["status"] == "accepted"
    d = [d for d in a["decisions"] if "postgresql" in d["text"].lower()]
    assert d and len(d[0]["evidence"]) == 2 and "accepted" in d[0]["basis"]


def test_rejected_suggestion_stays_rejected(analyze):
    a = analyze("Sriya: Maybe we should use MongoDB.\nRahul: No, I don't think so. Too expensive.")
    assert a["suggestions"][0]["status"] == "rejected"
    assert a["decisions"] == []


def test_revised_deadline_keeps_original_and_latest(analyze):
    a = analyze("Sriya: Rahul will finish the frontend by Thursday.\nRahul: That won't work, let's push the frontend deadline to Monday.")
    act = actions_by_task(a, "frontend")[0]
    assert act["original_deadline"]["date"] == "2025-03-13"
    assert act["deadline"]["date"] == "2025-03-17"
    roles = [e["role"] for e in a["deadlines"] if e["task_id"] == act["id"]]
    assert roles == ["original", "revised"]
    latest = [e for e in a["deadlines"] if e["task_id"] == act["id"] and e["is_latest"]]
    assert len(latest) == 1 and latest[0]["deadline"]["date"] == "2025-03-17"


def test_repeated_information_is_merged_not_duplicated(analyze):
    a = analyze("Rahul: I'll fix the login bug by Friday.\nSriya: Please remember Rahul is fixing the login bug.\nRahul: Yes I'll fix the login bug by Friday.")
    assert len([x for x in a["action_items"] if "login" in x["task"].lower()]) == 1
    assert a["action_items"][0]["mentions"] >= 2


def test_contradictory_assignments_are_flagged(analyze):
    a = analyze("Sriya: Rahul will write the project report.\nKiran: Ananya will write the project report.")
    acts = [x for x in a["action_items"] if "report" in x["task"]]
    assert len(acts) == 2
    assert all(x["needs_review"] and any("contradiction" in r.lower() for r in x["review_reasons"]) for x in acts)


def test_conflicting_decisions_supersede_earlier(analyze):
    a = analyze("Sriya: We decided to use MySQL for the database.\nRahul: Actually let's switch to PostgreSQL instead.")
    statuses = {d["id"]: d["status"] for d in a["decisions"]}
    assert "superseded" in statuses.values() and "confirmed" in statuses.values()


def test_missing_speaker_first_person_commitment_is_not_assigned(analyze):
    a = analyze("I'll finish the report by Friday.")
    act = actions_by_task(a, "report")[0]
    assert act["owner"] is None and act["needs_review"]


def test_missing_deadline_is_none_not_invented(analyze):
    a = analyze("Rahul: I'll fix the login page.")
    assert a["action_items"][0]["deadline"] is None


def test_relative_deadline_unresolved_without_meeting_date(analyze):
    a = analyze("Rahul: I'll fix the login page by Friday.", meeting_date=None)
    dl = a["action_items"][0]["deadline"]
    assert dl["resolved"] is False and dl["date"] is None and "Friday" in dl["normalized"]
    assert any("meeting date" in w for w in a["warnings"])


def test_issue_with_blocked_activity_and_relationship(analyze):
    a = analyze("Ananya: I'll test the dashboard tomorrow.\nAnanya: Testing is blocked because the login isn't working.")
    issue = a["issues"][0]
    assert "login" in issue["problem"].lower() and "testing" in issue["blocked_activity"].lower()
    assert any(r["type"] == "BLOCKS" for r in a["relationships"])


def test_issue_can_be_resolved_later(analyze):
    a = analyze("Rahul: The login page is broken on Safari.\nRahul: The login page works now, it is fixed.")
    assert a["issues"][0]["status"] == "resolved"


def test_commitment_to_fix_bug_is_not_reported_as_issue(analyze):
    a = analyze("Dev: I'll sort out the login bug tomorrow.")
    assert a["issues"] == []


def test_action_marked_done_when_completion_reported(analyze):
    a = analyze("Kiran: I'll update the API docs by Tuesday.\nKiran: the API docs are done.")
    assert a["action_items"][0]["status"] == "done"


def test_every_item_has_valid_evidence_offsets(example_analysis):
    a = example_analysis
    text = a["transcript"]
    groups = [a["action_items"], a["decisions"], a["issues"], a["suggestions"]]
    n = 0
    for items in groups:
        for it in items:
            assert it["evidence"], it["id"]
            for e in it["evidence"]:
                assert text[e["start"]:e["end"]] == e["text"]
                n += 1
    for d in a["deadlines"]:
        e = d["evidence"]
        assert text[e["start"]:e["end"]] == e["text"]
    assert n > 10


def test_dependency_relationship(analyze):
    a = analyze("Sriya: Rahul will finish the API by Friday.\nSriya: Ananya will test the dashboard after the API is finished.")
    assert any(r["type"] == "DEPENDS_ON" for r in a["relationships"])


def test_decision_affects_component(analyze):
    a = analyze("Sriya: Okay, we decided to use React for the frontend.")
    assert any(r["type"] == "AFFECTS" and r["target"]["text"] == "Frontend" and r["explicit"] for r in a["relationships"])


def test_entities_include_people_and_technologies(example_analysis):
    labels = {(e["label"], e["text"]) for e in example_analysis["entities"]}
    assert ("PERSON", "Rahul") in labels and ("TECHNOLOGY", "SQLite") in labels and ("TECHNOLOGY", "MongoDB") in labels


def test_example_transcript_key_facts(example_analysis):
    a = example_analysis
    front = actions_by_task(a, "frontend")[0]
    assert front["owner"] == "Rahul"
    assert front["original_deadline"]["date"] == "2025-03-13" and front["deadline"]["date"] == "2025-03-17"
    assert any("sqlite" in d["text"].lower() for d in a["decisions"])
    mongo = [s for s in a["suggestions"] if "mongodb" in s["text"].lower()][0]
    assert mongo["status"] == "rejected"
    assert a["overview"]["participants"] == 4
