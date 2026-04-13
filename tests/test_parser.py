from core.parser_rules import classify_instruction_type, strip_wake_word


def test_strip_spot_wake_word() -> None:
    assert strip_wake_word("spot what is this") == "what is this"


def test_end_tour_exact_phrase() -> None:
    assert classify_instruction_type("end the tour spot") == "end_tour"
    assert classify_instruction_type("please end the tour spot") != "end_tour"


def test_walk_command_classification() -> None:
    assert classify_instruction_type("spot continue") == "walk_command"


def test_unknown_classification() -> None:
    assert classify_instruction_type("spot banana blue") == "unknown"
