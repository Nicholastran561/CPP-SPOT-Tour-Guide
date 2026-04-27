from core.parser_rules import classify_instruction_type, parse_instruction


def test_end_tour_exact_phrase() -> None:
    assert classify_instruction_type("end the tour spot") == "end_tour"
    assert classify_instruction_type("please end the tour spot") != "end_tour"


def test_walk_command_classification() -> None:
    assert classify_instruction_type("continue") == "walk_command"


def test_question_classification_without_wake_word_stripping() -> None:
    assert classify_instruction_type("what is this") == "question"
    assert classify_instruction_type("Give me information about Cal Poly Pomona.") == "question"
    assert classify_instruction_type("What is the next stop?") == "question"
    assert classify_instruction_type("Can you tell me about the next location") == "question"
    assert (
        classify_instruction_type("spot what is this", assume_unknown_as_question=False)
        == "unknown"
    )


def test_unknown_classification() -> None:
    assert classify_instruction_type("banana blue", assume_unknown_as_question=False) == "unknown"


def test_unknown_assumed_question_toggle() -> None:
    assert classify_instruction_type("banana blue", assume_unknown_as_question=True) == "question"
    assert parse_instruction("banana blue", assume_unknown_as_question=True)["instruction_type"] == "question"


def test_empty_transcript_stays_unknown_with_toggle() -> None:
    assert classify_instruction_type("", assume_unknown_as_question=True) == "unknown"
