from core.parser_rules import classify_instruction_type


def test_end_tour_exact_phrase() -> None:
    assert classify_instruction_type("end the tour spot") == "end_tour"
    assert classify_instruction_type("please end the tour spot") != "end_tour"


def test_walk_command_classification() -> None:
    assert classify_instruction_type("continue") == "walk_command"


def test_question_classification_without_wake_word_stripping() -> None:
    assert classify_instruction_type("what is this") == "question"
    assert classify_instruction_type("spot what is this") == "unknown"


def test_unknown_classification() -> None:
    assert classify_instruction_type("banana blue") == "unknown"
