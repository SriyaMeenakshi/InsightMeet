from app.nlp.preprocessing import parse_speaker_line, preprocess, restore_contractions, split_into_spans


def test_original_text_is_preserved_with_exact_offsets():
    raw = "[10:02] sriya:   okay guys we need to finish the dashboard.\nRahul: i'll handle the API   integration!"
    pre = preprocess(raw)
    assert len(pre.sentences) == 2
    for s in pre.sentences:
        assert pre.text[s.start:s.end] == s.original  # evidence is an exact slice
    assert pre.sentences[1].original.endswith("API   integration!")  # inner whitespace untouched in evidence
    assert "  " not in pre.sentences[1].text  # but the analysis view is normalised


def test_speaker_detection_variants_and_title_casing():
    assert parse_speaker_line("Sriya: hello")[0] == "Sriya"
    assert parse_speaker_line("[10:02] rahul: hi")[0] == "rahul"
    assert parse_speaker_line("Ananya (10:03): hi")[0] == "Ananya"
    assert parse_speaker_line("Dr Rao: hi")[0] == "Dr Rao"
    pre = preprocess("sriya: hello there everyone\nSRIYA: more text here")
    assert pre.speakers == ["Sriya"]  # case-insensitive merge


def test_non_speaker_labels_are_not_speakers():
    assert parse_speaker_line("Note: bring laptops")[0] is None
    assert parse_speaker_line("Agenda for today: nothing")[0] is None
    assert parse_speaker_line("The deadline is 10:30 tomorrow")[0] is None


def test_missing_speakers_produce_warning_not_crash():
    pre = preprocess("We need to finish the report. Then we review it.")
    assert all(s.speaker is None for s in pre.sentences)
    assert any("speaker" in w.lower() for w in pre.warnings)
    assert len(pre.sentences) == 2


def test_unlabelled_continuation_line_inherits_speaker_and_is_flagged():
    pre = preprocess("Rahul: first part\nand the second line")
    assert pre.sentences[1].speaker == "Rahul" and pre.sentences[1].speaker_inherited


def test_sentence_splitting_handles_abbreviations_and_decimals():
    text = "Dr. Rao said version 3.5 works, e.g. on Linux. Next item is testing."
    spans = split_into_spans(text)
    assert len(spans) == 2


def test_contractions_restored_only_in_analysis_view():
    assert restore_contractions("lets use it, i cant test and dont know") == "let's use it, i can't test and don't know"
    pre = preprocess("Sriya: lets use sqlite")
    assert pre.sentences[0].text == "let's use sqlite"
    assert pre.sentences[0].original == "lets use sqlite"


def test_lemmas_and_content_words():
    pre = preprocess("Rahul: the tests are failing on the servers")
    s = pre.sentences[0]
    assert "test" in s.content_lemmas and "server" in s.content_lemmas
    assert "the" not in s.content_lemmas  # stop word dropped from the content view
    assert "the" in s.tokens  # but kept in the token view


def test_empty_input_gives_no_sentences():
    assert preprocess("   \n\n ").sentences == []
